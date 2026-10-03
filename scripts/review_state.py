"""One attempt boundary for reservation, publication, accounting and acceptance.

The shared-git-directory ledger belongs to the integrating session. Comment markers
are an envelope, not authentication. Receipt identity, author and exact published
bytes must match; this does not isolate a malicious actor with the same credentials
and filesystem access. Missing local receipts block acceptance rather than guess.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from hard_edges import Refusal, require, run
from review_packet import decision_line, floor_results, normalize, verdict_shape

FORMAT = 'codex-method-attempt-v2'
MARKER = re.compile(r'\A## Merge check 1 — round (\d+)\n<!-- codex-method-attempt-v2 (\{[^\n]+\}) -->\n\n')
RETURNED = ('returned', 'invalid')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def ledger_path(project, repo, pr):
    common = Path(run('git', 'rev-parse', '--git-common-dir', cwd=project).strip())
    if not common.is_absolute():
        common = Path(project) / common
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo), 'invalid repository identity')
    return common.resolve() / 'codex-method' / 'reviews' / repo / f'{pr}.json'


def load(path, repo, pr):
    if not path.exists():
        return {'format': FORMAT, 'repo': repo, 'pr': pr, 'attempts': []}
    try:
        body = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refusal(f'unreadable review ledger: {error}')
    require(body.get('format') == FORMAT and body.get('repo') == repo and body.get('pr') == pr,
            'review ledger identity differs')
    require(isinstance(body.get('attempts'), list), 'review ledger has no attempt list')
    return body


def save(path, body):
    temporary = path.with_suffix('.new')
    with temporary.open('w', encoding='utf-8') as stream:
        stream.write(json.dumps(body, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def locked(project, repo, pr):
    path = ledger_path(project, repo, pr)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal('review ledger is locked; inspect the originating run, never launch a second one')
        body = load(path, repo, pr)
        yield body
        save(path, body)
    finally:
        # Keep the inode: unlinking lets another caller lock a different file. A crash
        # releases this kernel lock without PID files or an originating-run supervisor.
        os.close(fd)


def no_pending(ledger):
    require(not ledger.get('pending'),
            'pending remote outcome; run review-packet status before further review actions; '
            'do not POST another reservation, launch a reviewer, replace output or mark no-output')


def write_pending(path, ledger, intended, body, previous=None):
    """Durably retain exact outbound bytes and the old receipt before any mutation."""
    no_pending(ledger)
    ledger['pending'] = {'operation': 'PATCH' if previous else 'POST', 'body': body,
                         'attempt': deepcopy(intended), 'previous': deepcopy(previous)}
    save(path, ledger)


def finish_pending(ledger, comment):
    require(isinstance(comment, dict), 'GitHub returned no identifiable comment receipt')
    pending = ledger['pending']
    attempt = deepcopy(pending['attempt'])
    body = pending['body']
    meta, text = parsed(body)
    expected, _ = parsed(envelope(attempt, ''))
    require(meta == expected, 'pending intended metadata differs from its receipt')
    if attempt['state'] in RETURNED:
        require(digest(text) == attempt.get('verdict_sha256'), 'pending verdict bytes differ')
    targets = [i for i, old in enumerate(ledger['attempts']) if old['token'] == attempt['token']]
    require(len(targets) == 1, 'pending intent has no unique local attempt')
    previous = pending['previous']
    if pending['operation'] == 'PATCH':
        require(previous == ledger['attempts'][targets[0]], 'pending previous receipt differs')
        require(comment.get('id') == previous.get('comment_id'), 'pending comment id differs')
    else:
        require(pending['operation'] == 'POST' and previous is None
                and attempt == ledger['attempts'][targets[0]], 'pending reservation association differs')
    record_comment(attempt, comment, body)
    ledger['attempts'][targets[0]] = attempt
    del ledger['pending']
    return attempt


def recover_pending(ledger, comments):
    """Reconcile only exact intended remote bytes; never retry an uncertain mutation."""
    pending = ledger.get('pending')
    if not pending:
        return False
    token = pending['attempt']['token']
    previous = pending['previous']
    candidates = []
    for comment in comments:
        # Even a damaged envelope mentioning this unique token is ambiguous history.
        # A PATCH additionally pins the previously receipted GitHub id.
        if token in (comment.get('body') or '') or (previous and comment.get('id') == previous['comment_id']):
            candidates.append(comment)
    direction = ('pending remote outcome cannot be recovered: exact intended comment bytes, '
                 'author, id and token association are required. Retain the ledger and whole output; '
                 'inspect the GitHub comment and run review-packet status again. '
                 'Do not POST another reservation, launch a reviewer, replace output or mark no-output')
    try:
        require(len(candidates) == 1, 'pending comment is missing or ambiguous')
        finish_pending(ledger, candidates[0])
    except Refusal as error:
        raise Refusal(f'{direction}: {error}')
    return True


def new_attempt(ledger, issue, head, base, identity, author, packet):
    no_pending(ledger)
    require(not any(a['state'] == 'reserved' for a in ledger['attempts']),
            'a reviewer reservation is still active; recover its output before starting another')
    last = ledger['attempts'][-1] if ledger['attempts'] else None
    if any(a.get('floor2_stop') or a.get('results', {}).get('floor2') == 'Fail'
           for a in ledger['attempts']):
        raise Refusal('Floor 2 stopped this lane; obtain human direction, not another review round')
    if last and last['state'] == 'returned' and last['head'] == head:
        require(last['results']['ready'] != 'Yes', 'accepted head: Notes do not authorize another round')
    attempt = {'token': uuid.uuid4().hex, 'issue': issue, 'head': head, 'base': base,
               'identity': identity, 'author': author, 'packet_sha256': digest(packet),
               'round': 1 + sum(a['state'] in RETURNED for a in ledger['attempts']),
               'state': 'reserved', 'repo': ledger['repo'], 'pr': ledger['pr']}
    ledger['attempts'].append(attempt)
    return attempt


def envelope(attempt, text):
    meta = {key: attempt[key] for key in ('token', 'issue', 'head', 'base', 'identity', 'author',
                                        'packet_sha256', 'round', 'state', 'repo', 'pr')}
    return (f'## Merge check 1 — round {attempt["round"]}\n<!-- {FORMAT} '
            + json.dumps(meta, sort_keys=True, separators=(',', ':')) + ' -->\n\n' + text)


def parsed(body):
    match = MARKER.match(body)
    require(match, 'comment is not an attempt envelope')
    try:
        meta = json.loads(match[2])
    except ValueError:
        raise Refusal('attempt envelope has malformed metadata')
    require(meta.get('round') == int(match[1]), 'envelope heading and round differ')
    return meta, body[match.end():]


def record_comment(attempt, comment, body):
    require(comment.get('id') and (comment.get('user') or {}).get('login') == attempt['author'],
            'GitHub returned a different comment identity or author')
    require(comment.get('body') == body, 'GitHub returned altered comment bytes')
    attempt['comment_id'] = comment['id']
    attempt['comment_sha256'] = digest(body)


def associated(attempt, comments):
    matches = [c for c in comments if c.get('id') == attempt.get('comment_id')]
    require(len(matches) == 1, 'recorded attempt comment is absent or duplicated')
    comment = matches[0]
    require((comment.get('user') or {}).get('login') == attempt['author'], 'attempt comment author differs')
    body = comment.get('body') or ''
    require(digest(body) == attempt.get('comment_sha256'), 'published attempt bytes differ from the receipt')
    meta, text = parsed(body)
    expected, _ = parsed(envelope(attempt, ''))
    require(meta == expected, 'attempt metadata differs from the receipt')
    return text


def publish(attempt, text):
    require(isinstance(text, str) and text.strip(), 'empty output is not a returned verdict')
    require(len(text.encode('utf-8')) <= 55000, 'verdict exceeds whole-comment delivery; retain and disclose it')
    require(attempt['state'] == 'reserved', 'this attempt is already resolved; its returned verdict is immutable')
    defect = verdict_shape(text, attempt['head'], attempt['identity'])
    attempt['state'] = 'invalid' if defect else 'returned'
    attempt['defect'] = defect
    attempt['verdict_sha256'] = digest(text)
    attempt['results'] = results(text) if not defect else {}
    # A malformed envelope must not erase a returned authorization failure.
    attempt['floor2_stop'] = 'Fail' in floor_results(text, '2. Authorization and scope')
    return envelope(attempt, text)


def results(text):
    text = normalize(text)
    return {key: re.search(decision_line(label, grounds=True), text, re.M)[1]
            for key, label in [('goal', 'Goal verdict'), ('floor1', '1. Evidence-backed completion claim'),
                               ('floor2', '2. Authorization and scope'), ('ready', 'Ready to merge')]}


def accepted(project, repo, pr, comments, head, base):
    ledger = load(ledger_path(project, repo, pr), repo, pr)
    no_pending(ledger)
    require(ledger['attempts'], f'no recorded review attempt on head {head}')
    attempt = ledger['attempts'][-1]
    require(attempt['state'] == 'returned', 'latest attempt has no valid returned verdict')
    require(attempt['head'] == head and attempt['base'] == base, 'reviewed head or base differs')
    text = associated(attempt, comments)
    require(digest(text) == attempt.get('verdict_sha256'), 'returned verdict bytes differ')
    defect = verdict_shape(text, head, attempt['identity'])
    require(not defect, f'the returned verdict is malformed: {defect}')
    answer = results(text)
    require(answer == {'goal': 'Yes', 'floor1': 'Pass', 'floor2': 'Pass', 'ready': 'Yes'},
            'the latest verdict is not Goal Yes with both Floors passing')
    return attempt, text


def status(ledger, comments):
    no_pending(ledger)
    attempts = ledger['attempts']
    for attempt in attempts:
        associated(attempt, comments)
    current = attempts[-1] if attempts else None
    next_step = 'awaiting-verdict'
    if current:
        if current.get('floor2_stop'):
            next_step = 'human-direction'
        elif current['state'] == 'invalid':
            next_step = 'invalid-verdict'
        elif current['state'] == 'returned':
            result = current['results']
            next_step = ('accepted' if result['ready'] == 'Yes' else
                         'human-direction' if result['floor2'] == 'Fail' else 'needs-continuation')
        elif current['state'] == 'failed':
            next_step = 'awaiting-review'
    return {'rounds': sum(a['state'] in RETURNED for a in attempts), 'next': next_step,
            'attempts': [{'round':a['round'], 'comment_id':a.get('comment_id'), 'state':a['state'],
                          'head':a['head'], 'defect':a.get('defect')} for a in attempts]}
