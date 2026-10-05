"""Exact accepted-context and content proofs, never a source of review judgment.

Public consumers hold the review ledger lock. Git operations address immutable
objects; replay runs in an isolated repository and never moves caller refs/index.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from hard_edges import Refusal, api, require

CONTEXT = 'context-v1'
REUSE = 'codex-method-reuse-v1'
NATIVE = 'codex-method-native-v1'
DESCRIPTORS = {b'codex-method.json', b'.codex-plugin/plugin.json'}
SHA = re.compile(r'[0-9a-f]{40}\Z')
VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def constant(value):
        raise Refusal(f'unsupported JSON constant: {value}')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError) as error:
        raise Refusal(f'invalid complete JSON: {error}')


def history(repo, number):
    pages = api(f'repos/{repo}/issues/{number}/comments', '--paginate', '--slurp') or []
    return [comment for page in pages for comment in page]


def comment_tuples(comments):
    result = []
    for comment in comments:
        identifier, author, body = (comment.get('id'), (comment.get('user') or {}).get('login'),
                                    comment.get('body'))
        require(type(identifier) is int and identifier > 0 and isinstance(author, str)
                and isinstance(body, str), 'incomplete context comment')
        require(identifier not in [row[0] for row in result], 'duplicate context comment id')
        result.append([identifier, author, body])
    return result


def capture(repo, pr, issue):
    raw = {'issue': api(f'repos/{repo}/issues/{issue}'),
           'pr': api(f'repos/{repo}/pulls/{pr}'),
           'issue_comments': history(repo, issue), 'pr_comments': history(repo, pr)}
    pull = raw['pr']
    identities = {}
    for side in ('base', 'head'):
        item = pull.get(side) or {}
        name = (item.get('repo') or {}).get('full_name')
        require(isinstance(name, str) and isinstance(item.get('ref'), str),
                f'PR {side} repository/ref identity is missing')
        identities[side] = {'repo': name, 'ref': item['ref']}
    require(isinstance(raw['issue'].get('body'), str)
            and isinstance(pull.get('title'), str)
            and (pull.get('body') is None or isinstance(pull.get('body'), str)),
            'incomplete issue/PR context text')
    return {'format': CONTEXT, 'raw': raw,
            'fields': {'issue_body': raw['issue']['body'], 'title': pull['title'],
                       'body': pull['body'] or '', 'identities': identities,
                       'issue_comments': comment_tuples(raw['issue_comments']),
                       'pr_comments': comment_tuples(raw['pr_comments'])}}


def context_attachment(context):
    return '\n\n## Accepted context-v1 capture (whole API evidence)\n' + canonical(context) + '\n'


def validate_context(attempt):
    context = attempt.get('context')
    require(isinstance(context, dict) and context.get('format') == CONTEXT,
            'receipt has no supported context-v1 binding; use fresh review')
    require(sha(canonical(context)) == attempt.get('context_sha256'), 'context receipt bytes differ')
    bundle = Path(attempt['packet_path']).read_bytes()
    attachment = context_attachment(context).encode('utf-8')
    require(bundle.endswith(attachment), 'context binding differs from retained review evidence')
    return context


def associated_record(record, comments):
    selected = [c for c in comments if c.get('id') == record.get('comment_id')]
    require(len(selected) == 1, 'published proof/native comment is absent or duplicated')
    comment = selected[0]
    require((comment.get('user') or {}).get('login') == record['author']
            and comment.get('body') == record['body']
            and sha(comment['body']) == record['comment_sha256']
            and record['body'] == record_body(record),
            'published proof/native comment association differs')
    return [comment['id'], record['author'], record['body']]


def context_diff(attempt, ledger, current, external_body=None):
    """Return substantive drift; missing/corrupted associated evidence refuses."""
    from review_state import associated
    previous = deepcopy(validate_context(attempt)['fields'])
    expected = deepcopy(previous)
    pr_comments = current['raw']['pr_comments']
    associated(attempt, pr_comments)
    anchor = next(c for c in pr_comments if c['id'] == attempt['comment_id'])
    extras = [[anchor['id'], attempt['author'], anchor['body']]]
    for record in ledger.get('reuses', []):
        if record.get('attempt_token') == attempt['token']:
            validate_reuse_files(record)
            extras.append(associated_record(record, pr_comments))
    # Only exact retained records after the snapshot are allowances. Ordering of
    # these append-only records is by the actual published monotonically assigned id.
    expected['pr_comments'] += sorted(extras, key=lambda row: row[0])
    native = attempt.get('native_record')
    if native:
        require(native.get('format') == NATIVE and native['attempt_token'] == attempt['token']
                and native['attempt_id'] == attempt['comment_id'] and native['issue'] == attempt['issue']
                and native['repo'] == attempt['repo'] and native['pr'] == attempt['pr']
                and native['head'] == attempt['head'] and native['base'] == attempt['base']
                and native['author'] == attempt['author']
                and native['instruction_sha256'] == attempt['native_instruction_sha256'],
                'native observation original association differs')
        expected['issue_comments'].append(associated_record(native, current['raw']['issue_comments']))
        observation = Path(native['observation_path']).read_bytes()
        require(sha(observation) == native['observation_sha256'], 'native observation bytes differ')
    if external_body is not None:
        expected['body'] = external_body
    return {key: {'accepted': expected[key], 'current': current['fields'][key]}
            for key in expected if expected[key] != current['fields'][key]}


def require_context(attempt, ledger, current, external_body=None):
    drift = context_diff(attempt, ledger, current, external_body)
    require(not drift, f'accepted context differs: {list(drift)}; obtain fresh review or exact external proof')


def original(project, ledger, current, identifier=None):
    from review_state import accepted, validate_instruction
    require(ledger['attempts'], 'no original accepted review receipt')
    require(not any(a['state'] == 'reserved' for a in ledger['attempts']), 'active reviewer blocks reuse')
    require(not any(a.get('floor2_stop') or a.get('results', {}).get('floor2') == 'Fail'
                    for a in ledger['attempts']), 'Floor 2 stopped this lane')
    latest = ledger['attempts'][-1]
    require(identifier is None or latest.get('comment_id') == identifier,
            'reuse must anchor to the latest original accepted attempt, never another proof')
    attempt, text = accepted(project, ledger['repo'], ledger['pr'], current['raw']['pr_comments'],
                             latest['head'], latest['base'], ledger)
    require(attempt.get('packet_carrier') == 'file-sha256-v1', 'reuse requires intact retained packet evidence')
    validate_instruction(attempt)
    validate_context(attempt)
    return attempt, text


def source_fields(record):
    keys = ('format','repo','pr','issue','token','kind','attempt_token','attempt_id','author',
            'old_base','old_head','base','head','original_packet_sha256','original_instruction_sha256',
            'original_verdict_sha256','original_comment_sha256','request_sha256')
    return {key: record[key] for key in keys}


def record_body(record):
    require(record.get('format') in (REUSE, NATIVE), 'unknown proof/native receipt version')
    if record['format'] == NATIVE:
        keys = ('repo','pr','issue','token','attempt_token','attempt_id','head','base','author',
                'instruction_sha256','native_handle','observation_sha256')
        return '<!-- '+NATIVE+' '+canonical({key: record[key] for key in keys})+' -->\n'
    metadata = {**source_fields(record), 'bundle_sha256': record['bundle_sha256']}
    return ('## Accepted review reuse — '+record['kind']+'\n<!-- '+REUSE+' '+canonical(metadata)+
            ' -->\n\n'+json.dumps({'request':record['request'],'proof':record['proof']},
                                   indent=2,ensure_ascii=False)+'\n')


def validate_reuse_files(record):
    require(record.get('format') == REUSE, 'unknown reuse receipt version')
    require(record.get('body') == record_body(record), 'published proof differs from local source association')
    raw = Path(record['request_path']).read_bytes()
    require(sha(raw) == record['request_sha256'], 'retained request bytes differ')
    request = request_of(record['kind'], raw)
    require(request == record.get('request'), 'published request locator differs from retained input')
    bundle_raw = Path(record['bundle_path']).read_bytes()
    require(sha(bundle_raw) == record['bundle_sha256'], 'retained proof bundle bytes differ')
    bundle = strict_json(bundle_raw)
    require(bundle.get('source') == source_fields(record) and bundle.get('proof') == record['proof']
            and bundle.get('request_raw') == raw.decode('utf-8'), 'retained proof source/request binding differs')
    require(sha(bundle.get('verdict_raw', '')) == record['original_verdict_sha256'],
            'retained proof original verdict binding differs')
    return request, bundle


def prepare_reuse(project, ledger, current, attempt_id, kind, pins, raw, output):
    attempt, verdict = original(project, ledger, current, attempt_id)
    require(attempt['base'] == pins[0] and attempt['head'] == pins[1], 'original reviewed pins differ')
    request = request_of(kind, raw)
    objects(project, ledger['repo'], current, pins)
    proof = prove(project, kind, pins, request, verdict, current)
    if kind == 'external':
        before = validate_context(attempt)['fields']['body']
        require(before != proof['replacement'], 'external correction is empty')
        proof.update({'before': before, 'before_sha256': sha(before), 'after': proof['replacement']})
    require_context(attempt, ledger, current, proof['replacement'] if kind == 'external' else None)
    record = {'format': REUSE, 'repo': ledger['repo'], 'pr': ledger['pr'], 'issue': attempt['issue'],
              'token': uuid.uuid4().hex, 'kind': kind, 'attempt_token': attempt['token'],
              'attempt_id': attempt['comment_id'], 'author': attempt['author'],
              'old_base': pins[0], 'old_head': pins[1], 'base': pins[2], 'head': pins[3],
              'original_packet_sha256': attempt['packet_sha256'],
              'original_instruction_sha256': attempt['native_instruction_sha256'],
              'original_verdict_sha256': attempt['verdict_sha256'],
              'original_comment_sha256': attempt['comment_sha256'], 'request_sha256': sha(raw),
              'request':request, 'proof': proof}
    directory = output.resolve() / record['token'];directory.mkdir(parents=True)
    request_path, bundle_path = directory / 'request.json', directory / 'proof.json'
    request_path.write_bytes(raw)
    bundle = {'source': source_fields(record), 'request_raw': raw.decode('utf-8'),
              'verdict_raw': verdict, 'context': current, 'proof': proof}
    bundle_path.write_bytes((canonical(bundle)+'\n').encode('utf-8'))
    record.update({'request_path': str(request_path), 'bundle_path': str(bundle_path),
                   'bundle_sha256': sha(bundle_path.read_bytes())})
    body = record_body(record)
    require(len(body.encode('utf-8')) <= 55000, 'proof exceeds whole-comment delivery; retain its complete artifacts')
    return record, body


def verify_reuse(project, ledger, current, identifier):
    matches = [record for record in ledger.get('reuses', []) if record.get('comment_id') == identifier]
    require(len(matches) == 1, 'selected proof has no unique local reuse receipt')
    record = matches[0]
    associated_record(record, current['raw']['pr_comments'])
    request, bundle = validate_reuse_files(record)
    attempt, verdict = original(project, ledger, current, record['attempt_id'])
    require(record['attempt_token'] == attempt['token'] and record['issue'] == attempt['issue']
            and record['repo'] == ledger['repo'] and record['pr'] == ledger['pr']
            and record['author'] == attempt['author'], 'reuse original identity association differs')
    for name, source in [('packet','packet_sha256'),('instruction','native_instruction_sha256'),
                         ('verdict','verdict_sha256'),('comment','comment_sha256')]:
        require(record['original_'+name+'_sha256'] == attempt[source], 'reuse original evidence binding differs')
    pins = [record[key] for key in ('old_base','old_head','base','head')]
    require(pins[:2] == [attempt['base'], attempt['head']], 'reuse original commit pins differ')
    objects(project, ledger['repo'], current, pins)
    proof = prove(project, record['kind'], pins, request, verdict, current)
    if record['kind'] == 'external':
        before = validate_context(attempt)['fields']['body']
        require(before != proof['replacement'], 'external correction is empty')
        proof.update({'before': before, 'before_sha256': sha(before), 'after': proof['replacement']})
    require(proof == record['proof'] == bundle['proof'], 'recomputed proof differs from published retained proof')
    require_context(attempt, ledger, current, proof['replacement'] if record['kind'] == 'external' else None)
    return attempt, record


def git_bytes(project, *args, env=None, check=True, input=None):
    if env is None:
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env['GIT_NO_REPLACE_OBJECTS'] = '1'
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgSign=false',
                             '-c', 'rerere.enabled=false', '-c', 'maintenance.auto=false',
                             *map(str, args)], cwd=project, env=env, input=input,
                            capture_output=True)
    if check:
        require(result.returncode == 0, f'git {args[0]} exited {result.returncode}: '
                + (result.stderr or result.stdout).decode('utf-8', errors='replace'))
        return result.stdout
    return result


def origin_repo(url):
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)' 
                         r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?', url)
    return match[1] if match else None


def objects(project, repo, current, pins):
    require(all(isinstance(pin, str) and SHA.fullmatch(pin) for pin in pins),
            'proof pins must be full immutable commit SHAs')
    pull = current['raw']['pr']
    require(all((pull[side].get('repo') or {}).get('full_name') == repo for side in ('base', 'head')),
            'reuse requires the verified destination repository on both PR sides')
    origin = git_bytes(project, 'remote', 'get-url', '--all', 'origin').decode('utf-8').splitlines()
    require(len(origin) == 1 and origin_repo(origin[0]) == repo,
            'checkout origin differs from the API destination repository')
    destination = api(f'repos/{repo}')
    require(destination.get('full_name') == repo
            and origin_repo(destination.get('clone_url', '')) == repo,
            'API destination repository identity differs')
    require(pull['base']['ref'] == destination['default_branch'], 'reuse PR is not on default base')
    tip = api(f'repos/{repo}/git/ref/heads/{destination["default_branch"]}')['object']['sha']
    require(pull['base']['sha'] == pins[2] == tip and pull['head']['sha'] == pins[3]
            and pull['state'] == 'open', 'API/current proof head or base differs')
    # Explicit SHA fetches add only objects: no caller refs, FETCH_HEAD, index or
    # worktree change. Never fetch a caller-supplied URL or a guessed repository.
    git_bytes(project, 'fetch', '--no-write-fetch-head', '--no-tags', '--no-recurse-submodules',
              'origin', *dict.fromkeys(pins))
    for pin in pins:
        require(git_bytes(project, 'cat-file', '-t', pin).strip() == b'commit', 'pin is not a commit')
        require(git_bytes(project, 'rev-parse', '--verify', pin + '^{commit}').strip().decode() == pin,
                'fetched immutable commit identity differs')
    require(git_bytes(project, 'merge-base', '--is-ancestor', pins[2], pins[3], check=False).returncode == 0,
            'new head does not contain the current base')


def tree(project, pin, env=None):
    result = {}
    for row in git_bytes(project, 'ls-tree', '-rz', '--full-tree', pin, env=env).split(b'\0'):
        if not row:
            continue
        metadata, path = row.split(b'\t', 1)
        mode, kind, oid = metadata.split(b' ')
        result[path] = (mode, kind, oid)
    return result


def blob(project, entry, env=None):
    return git_bytes(project, 'cat-file', 'blob', entry[2].decode(), env=env)


def changed(project, base, head, env=None):
    return set(filter(None, git_bytes(project, 'diff', '--no-ext-diff', '--no-textconv',
                                      '--no-renames', '--name-only', '-z', base, head, env=env).split(b'\0')))


def version_blob(raw):
    document = strict_json(raw)
    require(isinstance(document, dict), 'descriptor must be a JSON object')
    value = document.get('version')
    require(isinstance(value, str) and VERSION.fullmatch(value), 'invalid strict descriptor version')
    # Mask exactly the whole physical version-value line's string, leaving its
    # indentation, key, punctuation and line ending byte-identical.
    pattern = rb'(?m)^(\s*"version"\s*:\s*)"' + re.escape(value.encode()) + rb'"([ \t]*,?[ \t]*\r?$)'
    matches = list(re.finditer(pattern, raw))
    require(len(matches) == 1, 'descriptor has no unique version-value line')
    match = matches[0]
    return tuple(map(int, value.split('.'))), raw[:match.start()] + match[1] + b'"<VERSION>"' + match[2] + raw[match.end():]


def descriptor_versions(project, entries, env=None):
    versions, masked = [], {}
    for path in DESCRIPTORS:
        entry = entries.get(path)
        require(entry and entry[0] in (b'100644', b'100755') and entry[1] == b'blob',
                'descriptor must retain regular-file type and mode')
        version, body = version_blob(blob(project, entry, env))
        versions.append(version);masked[path] = body
    require(versions[0] == versions[1], 'descriptor versions are not synchronized')
    return versions[0], masked


def version_difference(project, old, new, env=None, require_increase=True):
    older, masked_old = descriptor_versions(project, old, env)
    newer, masked_new = descriptor_versions(project, new, env)
    require(masked_old == masked_new and all(old[p][:2] == new[p][:2] for p in DESCRIPTORS),
            'descriptor differs outside version values or mode')
    require(all(old[p] != new[p] for p in DESCRIPTORS), 'descriptor changes are not in lockstep')
    if require_increase:
        require(newer > older, 'descriptor version is not strictly increasing')
    return older, newer


def note(raw, request, kind):
    data = raw.encode('utf-8')
    begin, end = b'<!-- codex-method-note-v1 -->\n', b'<!-- /codex-method-note-v1 -->\n'
    require(data.count(b'codex-method-note-v1') == 2
            and data.count(begin) == 1 and data.count(end) == 1, 'Note is missing, duplicated or ambiguous')
    lines = data.splitlines(keepends=True)
    offsets, cursor = [], 0
    for line in lines:
        offsets.append(cursor);cursor += len(line)
    notes = [i for i, line in enumerate(lines) if line == b'### Notes\n']
    require(len(notes) == 1, 'raw verdict has no unique Notes section')
    start = lines.index(begin)
    require(start > notes[0], 'replacement belongs outside Notes')
    # Establish physical top-level placement, including fences surrounding examples.
    fence = None
    for line in lines[:start]:
        opened = re.match(rb' {0,3}(`{3,}|~{3,})([^\r\n]*)\r?\n?$', line)
        if fence:
            if re.fullmatch(rb' {0,3}' + re.escape(fence[:1]) + rb'{'+str(len(fence)).encode()+rb',}[ \t]*\r?\n?', line):
                fence = None
        elif opened:
            fence = opened[1]
    require(fence is None and not any(re.match(rb'^#{1,6} ', line) for line in lines[notes[0]+1:start]),
            'replacement is quoted, fenced or outside the unique Notes section')
    require(start + 4 < len(lines) and lines[start+1].startswith(b'Replacement: ')
            and lines[start+1].endswith(b'\n') and not lines[start+1].endswith(b'\r\n'),
            'unsupported Note metadata line')
    metadata = strict_json(lines[start+1][len(b'Replacement: '):-1])
    expected = {key: request[key] for key in request if key != 'fence_offset'}
    require(isinstance(metadata, dict), 'reviewed locator must be strict JSON metadata')
    reviewed = request_of(kind, canonical({**metadata, 'fence_offset': request['fence_offset']}))
    require(reviewed == request and metadata == expected, 'reviewed locator differs from request')
    opening = re.fullmatch(rb'( {0,3})(`{3,}|~{3,})replacement\n', lines[start+2])
    require(opening and offsets[start+2] == request['fence_offset'], 'replacement fence or raw byte offset differs')
    closing = opening[1] + opening[2] + b'\n'
    stop = start + 3
    while stop < len(lines) and lines[stop] != closing:
        require(not re.match(rb' {0,3}(?:`{3,}|~{3,})', lines[stop])
                and b'codex-method-note-v1' not in lines[stop]
                and not lines[stop].startswith(b'Replacement: '), 'extra/nested fence or metadata in replacement')
        stop += 1
    require(stop + 1 < len(lines) and lines[stop+1] == end,
            'replacement is unclosed or has intervening closing prose')
    require(not any(re.match(rb'^#{1,6} ', line) for line in lines[start+1:start+2]), 'unsupported placement')
    content = lines[start+3:stop]
    prefixes = [re.match(rb'[ \t]*', line)[0] for line in content if line.strip(b' \t\r\n')]
    prefix = os.path.commonprefix(prefixes) if prefixes else b''
    return b''.join(line[len(prefix):] if line.strip(b' \t\r\n') else line for line in content)


def request_of(kind, raw):
    value = strict_json(raw)
    fields = {'replay': set(), 'note': {'target','start','end','fence_offset'},
              'external': {'artifact','fence_offset'}}
    require(kind in fields and isinstance(value, dict) and set(value) == fields[kind],
            'unsupported kind-specific proof request')
    for key in ('start', 'end', 'fence_offset'):
        if key in value:
            require(type(value[key]) is int and value[key] >= 0, 'offsets must be nonnegative exact integers')
    if kind == 'note':
        path = value['target']
        require(isinstance(path, str) and path and not path.startswith('/') and '\0' not in path
                and all(part not in ('', '.', '..') for part in path.split('/')),
                'target must be a literal repository path')
    if kind == 'external':
        require(value['artifact'] == 'pr-description', 'unsupported external artifact')
    return value


def prove(project, kind, pins, request, verdict, current):
    old_base, old_head, base, head = pins
    if kind == 'external':
        require(old_head == head and old_base == base, 'external reuse requires identical exact commits')
        body = note(verdict, request, kind).decode('utf-8')
        require(current['fields']['body'] == body, 'current PR description differs from prescribed raw replacement')
        return {'kind': kind, 'replacement': body, 'after_sha256': sha(body)}
    before, after = tree(project, old_head), tree(project, head)
    if kind == 'note':
        require(base == old_base, 'Note reuse base changed')
        parents = git_bytes(project, 'rev-list', '--parents', '-n', '1', head).split()
        require(parents == [head.encode(), old_head.encode()], 'Note head must be one commit with sole parent reviewed head')
        path = request['target'].encode('utf-8');entry = before.get(path)
        require(entry and entry[0] in (b'100644', b'100755') and entry[1] == b'blob', 'Note target is not a regular file')
        original = blob(project, entry);original.decode('utf-8')
        start, end = request['start'], request['end']
        require(0 <= start <= end <= len(original), 'target range is out of bounds')
        original[:start].decode('utf-8');original[end:].decode('utf-8')
        replacement = note(verdict, request, kind)
        expected = original[:start] + replacement + original[end:]
        require(expected != original, 'Note substitution is empty')
        require(set(before) == set(after) and before[path][:2] == after[path][:2]
                and all(before[p] == after[p] for p in before if p != path)
                and blob(project, after[path]) == expected, 'entire Note tree differs from sole exact substitution')
        return {'kind': kind, 'target': request['target'], 'before_sha256': sha(original),
                'after_sha256': sha(expected), 'replacement_sha256': sha(replacement)}
    return replay(project, pins)


def replay(project, pins):
    old_base, old_head, base, head = pins
    require(base != old_base, 'replay requires a moved base')
    for parent, child in ((old_base, old_head), (old_base, base), (base, head)):
        require(git_bytes(project, 'merge-base', '--is-ancestor', parent, child, check=False).returncode == 0,
                'replay ancestry differs')
    paths = changed(project, old_base, old_head) | changed(project, base, head)
    require(changed(project, old_base, old_head) and changed(project, base, head), 'empty PR delta cannot reuse acceptance')
    for first, last in ((old_base, old_head), (base, head)):
        require(not git_bytes(project, 'rev-list', '--merges', f'{first}..{last}').strip(), 'merge commits cannot replay')
        commits = [first] + git_bytes(project, 'rev-list', f'{first}..{last}').decode().splitlines()
        require(all(all(item[0] != b'160000' for item in tree(project, commit).values()) for commit in commits),
                'gitlinks cannot replay')
    old, new = tree(project, old_head), tree(project, head)
    differing = {path for path in paths if old.get(path) != new.get(path)}
    if differing:
        require(differing == DESCRIPTORS, 'reviewed/new changed-path bytes, type, mode or absence differ')
        version_difference(project, old, new)
    with tempfile.TemporaryDirectory(prefix='codex-method-replay-') as directory:
        checkout = Path(directory) / 'repo';checkout.mkdir()
        home = Path(directory) / 'home';home.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update({'HOME': str(home), 'XDG_CONFIG_HOME': str(home), 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_NO_REPLACE_OBJECTS': '1',
                    'GIT_EDITOR': 'true', 'GIT_SEQUENCE_EDITOR': 'true', 'GIT_TERMINAL_PROMPT': '0'})
        git_bytes(checkout, 'init', env=env)
        git_bytes(checkout, 'config', 'user.name', 'codex-method replay', env=env)
        git_bytes(checkout, 'config', 'user.email', 'replay@invalid', env=env)
        git_bytes(checkout, 'fetch', '--no-write-fetch-head', '--no-tags', str(project), *dict.fromkeys(pins), env=env)
        git_bytes(checkout, 'checkout', '--detach', old_head, env=env)
        result = git_bytes(checkout, 'rebase', '--reapply-cherry-picks', '--empty=keep', '--onto', base, old_base,
                           env=env, check=False)
        resolved = 0
        while result.returncode:
            unmerged = git_bytes(checkout, 'ls-files', '-u', '-z', env=env)
            stages = {number: {} for number in (1, 2, 3)}
            for row in filter(None, unmerged.split(b'\0')):
                meta, path = row.split(b'\t', 1);mode, oid, number = meta.split()
                require(path in DESCRIPTORS, 'replay has a non-version conflict')
                stages[int(number)][path] = (mode, b'blob', oid)
            require(all(set(stage) == DESCRIPTORS for stage in stages.values()), 'replay conflict stages are incomplete')
            version_difference(checkout, stages[1], stages[2], env)
            version_difference(checkout, stages[1], stages[3], env)
            # Stage 2 is the new-base side in rebase. No edited conflict text.
            for path, entry in stages[2].items():
                target = checkout / os.fsdecode(path)
                target.write_bytes(blob(checkout, entry, env))
                target.chmod(0o755 if entry[0] == b'100755' else 0o644)
            git_bytes(checkout, 'add', '--', *(os.fsdecode(path) for path in DESCRIPTORS), env=env)
            result = git_bytes(checkout, 'rebase', '--continue', env=env, check=False)
            resolved += 1
            require(resolved <= len(git_bytes(project, 'rev-list', f'{old_base}..{old_head}').splitlines()),
                    'replay conflict continuation did not converge')
        reproduced = tree(checkout, 'HEAD', env)
        mismatch = {path for path in set(reproduced) | set(new) if reproduced.get(path) != new.get(path)}
        if differing:
            replay_version, _ = descriptor_versions(checkout, reproduced, env)
            proposed_version, _ = descriptor_versions(checkout, new, env)
            require(proposed_version > replay_version, 'exempt version must exceed the actual replay version')
        if mismatch:
            require(mismatch == DESCRIPTORS and differing == DESCRIPTORS,
                    'complete replay tree differs from proposed head')
            version_difference(checkout, reproduced, new, env)
        # A stable tree digest is enough here: commit dates/ids are not acceptance.
        reproduced_tree = git_bytes(checkout, 'rev-parse', 'HEAD^{tree}', env=env).strip().decode()
    return {'kind': 'replay', 'changed_paths_hex': sorted(path.hex() for path in paths),
            'replay_tree': reproduced_tree, 'head_tree': git_bytes(project, 'rev-parse', head+'^{tree}').strip().decode(),
            'version_exemption': bool(differing), 'version_conflicts_resolved': resolved}
