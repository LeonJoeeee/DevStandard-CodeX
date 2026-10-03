"""GitHub branch protection's read/apply boundary.

Only explicit apply writes. Its PUT adds named checks and the method's gates; existing
review requirements, push actors, app bindings and unrelated settings survive unchanged.
A failed API read never proves a plan limit or an empty policy.
"""
from __future__ import annotations

import json
from urllib.parse import quote

from hard_edges import Refusal, require

# These PUT options default to false: omitting them could weaken existing policy.
PRESERVED_FLAGS = ('required_linear_history', 'block_creations',
                   'required_conversation_resolution', 'lock_branch', 'allow_fork_syncing')
REVIEW_FLAGS = ('dismiss_stale_reviews', 'require_code_owner_reviews',
                'require_last_push_approval')


def _endpoint(repo, branch):
    require(isinstance(repo, str) and len(repo.split('/')) == 2
            and all(part.strip() and part == part.strip() for part in repo.split('/')),
            'a repository OWNER/REPO is required')
    require(isinstance(branch, str) and branch.strip() and branch == branch.strip(),
            'a branch is required')
    return 'repos/' + '/'.join(quote(part, safe='') for part in repo.split('/')), quote(branch, safe='')


def _api(endpoint, *, runner, cwd, payload=None):
    if runner is None:
        # Resolve at call time: consumers can inject the same boundary hard_edges uses.
        from hard_edges import run
        runner = run
    if payload is None:
        out = runner('gh', 'api', endpoint, cwd=cwd)
    else:
        out = runner('gh', 'api', '-X', 'PUT', endpoint, '--input', '-',
                     cwd=cwd, input=json.dumps(payload))
    try:
        return json.loads(out)
    except (TypeError, ValueError) as error:
        raise Refusal(f'GitHub did not return JSON for {endpoint}: {error}') from error


def _object(value, name):
    require(isinstance(value, dict), f'GitHub {name} must be an object')
    return value


def _text(value, name):
    require(isinstance(value, str) and value.strip(), f'GitHub {name} must be a nonblank string')
    return value


def _boolean(value, name):
    require(type(value) is bool, f'GitHub {name} must be a boolean')
    return value


def _enabled(body, name):
    return _boolean(_object(body.get(name), name).get('enabled'), name + '.enabled')


def _actors(value, name, *, apps_required=False):
    body = _object(value, name)
    result = {}
    for group, key in (('users', 'login'), ('teams', 'slug'), ('apps', 'slug')):
        if group == 'apps' and group not in body and not apps_required:
            continue  # GitHub marks apps optional on review allowances, not push restrictions.
        records = body.get(group)
        require(isinstance(records, list), f'GitHub {name}.{group} must be an array')
        result[group] = [_text(_object(record, name + '.' + group).get(key),
                                name + '.' + group + '.' + key) for record in records]
    return result


def _status(value):
    if value is None:
        return None
    body = _object(value, 'required_status_checks')
    strict = _boolean(body.get('strict'), 'required_status_checks.strict')
    contexts = body.get('contexts')
    checks = body.get('checks')
    require(isinstance(contexts, list) and isinstance(checks, list),
            'GitHub required_status_checks needs contexts and checks arrays')
    contexts = [_text(name, 'required_status_checks.contexts') for name in contexts]
    normalized = []
    for item in checks:
        item = _object(item, 'required_status_checks.checks entry')
        context = _text(item.get('context'), 'required_status_checks.checks.context')
        require('app_id' in item, 'GitHub required_status_checks.checks.app_id is missing')
        app = item['app_id']
        require(app is None or (type(app) is int and app >= -1),
                'GitHub required_status_checks.checks.app_id must be an integer or null')
        # null means any app in GET. Omission in PUT would instead auto-select a recent app.
        normalized.append({'context': context, 'app_id': -1 if app is None else app})
    require(set(contexts) == {item['context'] for item in normalized},
            'GitHub required_status_checks contexts and checks disagree')
    return {'strict': strict, 'contexts': [], 'checks': normalized}


def _reviews(value):
    if value is None:
        return None
    body = _object(value, 'required_pull_request_reviews')
    count = body.get('required_approving_review_count')
    require(type(count) is int and 0 <= count <= 6,
            'GitHub required_approving_review_count must be an integer from 0 to 6')
    result = {name: _boolean(body.get(name), 'required_pull_request_reviews.' + name)
              for name in REVIEW_FLAGS}
    result['required_approving_review_count'] = count
    for name in ('dismissal_restrictions', 'bypass_pull_request_allowances'):
        if name in body:
            result[name] = _actors(body[name], 'required_pull_request_reviews.' + name)
    return result


def _snapshot(body, *, applying=False):
    body = _object(body, 'branch protection')
    _text(body.get('url'), 'branch protection.url')
    # GitHub omits these optional sections when their protection is disabled. This is
    # the documented GET shape, not a failed read from which to guess an empty policy.
    result = {
        'required_status_checks': _status(body.get('required_status_checks')),
        'enforce_admins': _enabled(body, 'enforce_admins'),
        'required_pull_request_reviews': _reviews(body.get('required_pull_request_reviews')),
        'restrictions': None if body.get('restrictions') is None
                        else _actors(body['restrictions'], 'restrictions', apps_required=True),
        'allow_force_pushes': _enabled(body, 'allow_force_pushes'),
        'allow_deletions': _enabled(body, 'allow_deletions'),
    }
    for name in PRESERVED_FLAGS:
        if applying or name in body:
            result[name] = _enabled(body, name)
    if 'required_signatures' in body:
        _enabled(body, 'required_signatures')  # separate API; never put this field
    return result


def _queue_off(repo_endpoint, branch, *, runner, cwd):
    # This endpoint returns only applicable *active* rules, including inherited rulesets.
    # A protection object alone says nothing about a ruleset's merge queue.
    page = 1
    while True:
        endpoint = f'{repo_endpoint}/rules/branches/{branch}?per_page=100&page={page}'
        rules = _api(endpoint, runner=runner, cwd=cwd)
        require(isinstance(rules, list), 'GitHub branch rules must be an array')
        for rule in rules:
            kind = _text(_object(rule, 'branch rule').get('type'), 'branch rule.type')
            require(kind != 'merge_queue', 'branch protection requires merge_queue_off; an active ruleset requires a merge queue')
        if len(rules) < 100:
            return True
        page += 1


def _expected(snapshot):
    status = snapshot['required_status_checks']
    observed = {
        'strict_up_to_date': status is not None and status['strict'],
        'admin_enforced': snapshot['enforce_admins'],
        'no_deletions': not snapshot['allow_deletions'],
        'pr_required': snapshot['required_pull_request_reviews'] is not None,
        'no_force_pushes': not snapshot['allow_force_pushes'],
        'merge_queue_off': True,  # caller has inspected branch rules, never inferred from GET protection
    }
    missing = [name for name, ok in observed.items() if not ok]
    if status is not None and not status['checks']:
        missing.append('required_checks')
    require(not missing, f'branch protection is missing: {", ".join(missing)}')
    return {'state': 'expected', **observed}


def protection_check(repo, branch, *, runner=None, cwd=None):
    """Read and verify classic protection plus active inherited branch rules (no writes).

    runner accepts hard_edges.run's command/keyword contract and returns JSON text.
    All unreadable, missing, malformed or weakened state raises hard_edges.Refusal.
    """
    base, encoded = _endpoint(repo, branch)
    body = _api(f'{base}/branches/{encoded}/protection', runner=runner, cwd=cwd)
    snapshot = _snapshot(body)
    _queue_off(base, encoded, runner=runner, cwd=cwd)
    return _expected(snapshot)


def protection_apply(repo, branch, checks, *, runner=None, cwd=None):
    """Explicitly add check names and enforce the gates without weakening existing policy.

    Founding requires readable repository/branch metadata proving protected=false and
    readable active branch rules. A 404 never substitutes for that proof. PR-required
    does not impose a native approval count: new review protection starts at zero.
    Return verified state plus applied=True and the complete resulting check names.
    """
    base, encoded = _endpoint(repo, branch)
    require(isinstance(checks, (list, tuple)) and checks,
            '--apply needs at least one --check NAME')
    for check in checks:
        require(isinstance(check, str) and check.strip() and check == check.strip(),
                '--apply check names must be nonblank strings')
    metadata = _object(_api(base, runner=runner, cwd=cwd), 'repository')
    require(metadata.get('full_name') == repo, 'GitHub repository identity does not match')
    _boolean(metadata.get('private'), 'repository.private')
    branch_state = _object(_api(f'{base}/branches/{encoded}', runner=runner, cwd=cwd), 'branch')
    require(branch_state.get('name') == branch, 'GitHub branch identity does not match')
    protected = _boolean(branch_state.get('protected'), 'branch.protected')
    body = None
    if protected:
        body = _api(f'{base}/branches/{encoded}/protection', runner=runner, cwd=cwd)
        payload = _snapshot(body, applying=True)
    else:
        # These are the mandatory PUT fields, not unrelated options with guessed defaults.
        payload = {'required_status_checks': None, 'enforce_admins': True,
                   'required_pull_request_reviews': None, 'restrictions': None,
                   'allow_force_pushes': False, 'allow_deletions': False}
    _queue_off(base, encoded, runner=runner, cwd=cwd)
    status = payload['required_status_checks'] or {'strict': True, 'contexts': [], 'checks': []}
    status['strict'] = True
    known = {item['context'] for item in status['checks']}
    for check in checks:
        if check not in known:
            status['checks'].append({'context': check})
            known.add(check)
    payload['required_status_checks'] = status
    payload['enforce_admins'] = True
    payload['allow_force_pushes'] = False
    payload['allow_deletions'] = False
    if payload['required_pull_request_reviews'] is None:
        payload['required_pull_request_reviews'] = {'required_approving_review_count': 0}
    response = _api(f'{base}/branches/{encoded}/protection', runner=runner, cwd=cwd, payload=payload)
    after = _snapshot(response, applying=True)
    result = _expected(after)
    actual = {(item['context'], item['app_id']) for item in after['required_status_checks']['checks']}
    require(known == {item[0] for item in actual}, 'GitHub PUT did not establish the requested check names')
    for item in status['checks']:
        if 'app_id' in item:
            require((item['context'], item['app_id']) in actual,
                    'GitHub PUT changed an existing required check app binding')
    for name, wanted in payload.items():
        if name == 'required_status_checks':
            continue
        if name == 'required_pull_request_reviews':
            require(all(after[name].get(key) == value for key, value in wanted.items()),
                    'GitHub PUT changed required review settings')
        else:
            require(after.get(name) == wanted, f'GitHub PUT changed {name}')
    if body is not None and 'required_signatures' in body:
        require(_enabled(response, 'required_signatures') == _enabled(body, 'required_signatures'),
                'GitHub PUT changed required_signatures')
    _queue_off(base, encoded, runner=runner, cwd=cwd)
    return {**result, 'applied': True, 'checks': list(dict.fromkeys(item['context'] for item in status['checks']))}
