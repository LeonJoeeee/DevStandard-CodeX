"""The protection consumer reads GitHub state and emits a non-weakening PUT."""
import copy
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hard_edges import Refusal, protection_check  # noqa: E402

PROTECTION = 'repos/owner/project/branches/main/protection'
RULES = 'repos/owner/project/rules/branches/main?per_page=100&page=1'


def github_state():
    """A modern GET response; actor records retain their GitHub object shape."""
    url = 'https://api.github.com/' + PROTECTION
    return {
        'url': url,
        'required_status_checks': {
            'url': url + '/required_status_checks',
            'contexts_url': url + '/required_status_checks/contexts',
            'strict': True,
            'contexts': ['build', 'lint'],
            'checks': [{'context': 'build', 'app_id': 15368},
                       {'context': 'lint', 'app_id': None}],
        },
        'enforce_admins': {'url': url + '/enforce_admins', 'enabled': True},
        'required_pull_request_reviews': {
            'url': url + '/required_pull_request_reviews',
            'dismiss_stale_reviews': True,
            'require_code_owner_reviews': True,
            'required_approving_review_count': 2,
            'require_last_push_approval': True,
            'dismissal_restrictions': {
                'url': url + '/dismissal_restrictions',
                'users_url': url + '/dismissal_restrictions/users',
                'teams_url': url + '/dismissal_restrictions/teams',
                'users': [{'login': 'octocat', 'id': 1}],
                'teams': [{'slug': 'maintainers', 'id': 12}],
                'apps': [{'slug': 'review-app', 'id': 99}],
            },
            'bypass_pull_request_allowances': {
                'users': [{'login': 'release-user', 'id': 2}],
                'teams': [{'slug': 'release-team', 'id': 13}],
                'apps': [{'slug': 'release-app', 'id': 100}],
            },
        },
        'restrictions': {
            'url': url + '/restrictions',
            'users_url': url + '/restrictions/users',
            'teams_url': url + '/restrictions/teams',
            'apps_url': url + '/restrictions/apps',
            'users': [{'login': 'octocat', 'id': 1}],
            'teams': [{'slug': 'maintainers', 'id': 12}],
            'apps': [{'slug': 'push-app', 'id': 101}],
        },
        'required_signatures': {'url': url + '/required_signatures', 'enabled': True},
        'required_linear_history': {'enabled': True},
        'allow_force_pushes': {'enabled': False},
        'allow_deletions': {'enabled': False},
        'block_creations': {'enabled': True},
        'required_conversation_resolution': {'enabled': True},
        'lock_branch': {'enabled': True},
        'allow_fork_syncing': {'enabled': True},
    }


class GitHubRunner:
    """Only the remote boundary is doubled; the real helpers build every request."""
    def __init__(self, body=None, rules=None, put_response=None):
        self.body = github_state() if body is None else body
        self.rules = [] if rules is None else rules
        self.put_response = put_response
        self.calls = []
        self.writes = []
        self.failures = {}
        self.rule_pages = {}
        self.branch = {'name': 'main', 'protected': True,
                       'commit': {'sha': 'a' * 40},
                       'protection_url': 'https://api.github.com/' + PROTECTION}
        self.repo = {'full_name': 'owner/project', 'private': False,
                     'owner': {'login': 'owner', 'type': 'Organization'}}

    def __call__(self, *args, cwd=None, input=None):
        self.calls.append((args, cwd, input))
        if args[:4] == ('gh', 'api', '-X', 'PUT'):
            if args[4:] != (PROTECTION, '--input', '-'):
                raise AssertionError(f'unexpected PUT: {args}')
            payload = json.loads(input)
            self.writes.append(payload)
            status = payload['required_status_checks']
            # The live 2026-10-04 API rejected both selectors with a oneOf error.
            # Validate the request before modeling a successful response.
            if 'contexts' in status and 'checks' in status:
                raise Refusal('gh: ambiguous status-check selectors (HTTP 422)')
            if PROTECTION in self.failures:
                raise self.failures[PROTECTION]
            if self.put_response is not None:
                return json.dumps(self.put_response)
            # Model the server transformation back to its response schema.
            body = copy.deepcopy(self.body)
            checks = payload['required_status_checks']
            body['required_status_checks'] = {
                'url': body['url'] + '/required_status_checks',
                'contexts_url': body['url'] + '/required_status_checks/contexts',
                'strict': checks['strict'],
                'contexts': [check['context'] for check in checks['checks']],
                'checks': [dict(check, app_id=check.get('app_id', 12345))
                           for check in checks['checks']],
            }
            for field in ('enforce_admins', 'allow_force_pushes', 'allow_deletions'):
                body[field] = {'enabled': payload[field]}
            if body.get('required_pull_request_reviews') is None:
                body['required_pull_request_reviews'] = {
                    'url': body['url'] + '/required_pull_request_reviews',
                    'dismiss_stale_reviews': False,
                    'require_code_owner_reviews': False,
                    'required_approving_review_count': 0,
                    'require_last_push_approval': False,
                }
            return json.dumps(body)
        if len(args) != 3 or args[:2] != ('gh', 'api') or input is not None:
            raise AssertionError(f'unexpected API request: {args}')
        endpoint = args[2]
        if endpoint in self.failures:
            raise self.failures[endpoint]
        if endpoint == 'repos/owner/project':
            return json.dumps(self.repo)
        if endpoint == 'repos/owner/project/branches/main':
            return json.dumps(self.branch)
        if endpoint == PROTECTION:
            return json.dumps(self.body)
        if endpoint == RULES:
            return json.dumps(self.rules)
        if endpoint in self.rule_pages:
            return json.dumps(self.rule_pages[endpoint])
        raise AssertionError(f'unexpected GET: {endpoint}')


class ProtectionReadTest(unittest.TestCase):
    def check(self, runner):
        # This is the existing consumer API, not a replacement mocked check.
        with patch('hard_edges.run', runner):
            return protection_check('owner/project', 'main')

    def test_github_enabled_objects_pass_and_branch_rules_are_read(self):
        runner = GitHubRunner()
        result = self.check(runner)
        self.assertEqual(result['state'], 'expected')
        self.assertTrue(result['no_force_pushes'])
        self.assertTrue(result['no_deletions'])
        self.assertTrue(result['merge_queue_off'])
        self.assertIn(('gh', 'api', RULES), [call[0] for call in runner.calls])
        self.assertEqual(runner.writes, [])

    def test_zero_required_approvals_is_still_a_pr_gate(self):
        body = github_state()
        body['required_pull_request_reviews']['required_approving_review_count'] = 0
        self.assertTrue(self.check(GitHubRunner(body))['pr_required'])

    def test_every_loosened_gate_refuses(self):
        for field in ('strict', 'enforce_admins', 'allow_force_pushes', 'allow_deletions',
                      'required_pull_request_reviews', 'required_status_checks'):
            with self.subTest(field=field):
                body = github_state()
                if field == 'strict':
                    body['required_status_checks']['strict'] = False
                elif field.startswith('required_'):
                    body[field] = None
                else:
                    body[field]['enabled'] = field.startswith('allow_')
                with self.assertRaises(Refusal):
                    self.check(GitHubRunner(body))

    def test_boolean_and_truthy_impostors_do_not_pass_as_github_objects(self):
        for field in ('enforce_admins', 'allow_force_pushes', 'allow_deletions'):
            for wrong in (False, True, {}, {'enabled': 'false'}, {'enabled': 0}, None):
                with self.subTest(field=field, wrong=wrong):
                    body = github_state()
                    body[field] = wrong
                    with self.assertRaises(Refusal):
                        self.check(GitHubRunner(body))

    def test_missing_fields_and_missing_checks_are_refused(self):
        for field in ('enforce_admins', 'allow_force_pushes', 'allow_deletions',
                      'required_pull_request_reviews', 'required_status_checks'):
            with self.subTest(field=field):
                body = github_state()
                del body[field]
                with self.assertRaises(Refusal):
                    self.check(GitHubRunner(body))
        body = github_state()
        body['required_status_checks']['contexts'] = []
        body['required_status_checks']['checks'] = []
        with self.assertRaises(Refusal):
            self.check(GitHubRunner(body))

    def test_active_inherited_merge_queue_refuses(self):
        runner = GitHubRunner(rules=[{
            'type': 'merge_queue', 'ruleset_source_type': 'Organization',
            'ruleset_source': 'owner', 'ruleset_id': 7,
            'parameters': {'check_response_timeout_minutes': 30,
                           'grouping_strategy': 'ALLGREEN', 'max_entries_to_build': 5,
                           'max_entries_to_merge': 1, 'merge_method': 'SQUASH',
                           'min_entries_to_merge': 1, 'min_entries_to_merge_wait_minutes': 5},
        }])
        with self.assertRaisesRegex(Refusal, 'merge.queue'):
            self.check(runner)

    def test_rules_are_paginated_before_queue_absence_is_claimed(self):
        runner = GitHubRunner(rules=[{'type': 'deletion', 'ruleset_id': i,
                                    'ruleset_source_type': 'Repository',
                                    'ruleset_source': 'owner/project'} for i in range(100)])
        runner.rule_pages['repos/owner/project/rules/branches/main?per_page=100&page=2'] = [
            {'type': 'merge_queue', 'ruleset_id': 101,
             'ruleset_source_type': 'Repository', 'ruleset_source': 'owner/project'}]
        with self.assertRaises(Refusal):
            self.check(runner)

    def test_unreadable_or_malformed_rules_never_proves_queue_off(self):
        for rules in ({}, None, [None], [{}], [{'type': None}]):
            with self.subTest(rules=rules):
                runner = GitHubRunner()
                runner.rules = rules
                with self.assertRaises(Refusal):
                    self.check(runner)
        runner = GitHubRunner()
        runner.failures[RULES] = Refusal('gh: rulesets API unavailable (404)')
        with self.assertRaises(Refusal):
            self.check(runner)

    def test_private_404_is_not_a_plan_limit_waiver(self):
        runner = GitHubRunner()
        runner.failures[PROTECTION] = Refusal('gh exited 1: private repo protection (HTTP 404)')
        with self.assertRaises(Refusal):
            self.check(runner)


class ProtectionApplyTest(unittest.TestCase):
    def apply(self, runner, checks=('build', 'test')):
        # Import lazily so the first red run can still reproduce the old read bug.
        helper = importlib.import_module('protection').protection_apply
        return helper('owner/project', 'main', checks, runner=runner, cwd=ROOT)

    def test_put_preserves_approvals_restrictions_review_options_and_app_ids(self):
        runner = GitHubRunner()
        result = self.apply(runner)
        self.assertTrue(result['applied'])
        self.assertEqual(result['state'], 'expected')
        self.assertEqual(len(runner.writes), 1)
        payload = runner.writes[0]
        self.assertEqual(payload['required_status_checks'], {
            'strict': True,
            'checks': [{'context': 'build', 'app_id': 15368},
                       {'context': 'lint', 'app_id': -1}, {'context': 'test'}],
        })
        self.assertEqual(payload['required_pull_request_reviews'], {
            'dismiss_stale_reviews': True, 'require_code_owner_reviews': True,
            'required_approving_review_count': 2, 'require_last_push_approval': True,
            'dismissal_restrictions': {'users': ['octocat'], 'teams': ['maintainers'],
                                       'apps': ['review-app']},
            'bypass_pull_request_allowances': {'users': ['release-user'],
                                              'teams': ['release-team'],
                                              'apps': ['release-app']},
        })
        self.assertEqual(payload['restrictions'], {
            'users': ['octocat'], 'teams': ['maintainers'], 'apps': ['push-app'],
        })
        for field in ('required_linear_history', 'block_creations',
                      'required_conversation_resolution', 'lock_branch', 'allow_fork_syncing'):
            self.assertIs(payload[field], True, field)
        self.assertNotIn('required_signatures', payload)  # separate API, never cleared here
        self.assertIs(payload['enforce_admins'], True)
        self.assertIs(payload['allow_force_pushes'], False)
        self.assertIs(payload['allow_deletions'], False)
        self.assertTrue(all(call[1] == ROOT for call in runner.calls))

    def test_put_preserves_multiple_producers_for_the_same_context(self):
        body = github_state()
        body['required_status_checks']['checks'].append({'context': 'build', 'app_id': 999})
        runner = GitHubRunner(body)
        self.apply(runner, checks=('build', 'test', 'test'))
        self.assertEqual(runner.writes[0]['required_status_checks'], {
            'strict': True,
            'checks': [{'context': 'build', 'app_id': 15368},
                       {'context': 'lint', 'app_id': -1},
                       {'context': 'build', 'app_id': 999}, {'context': 'test'}],
        })

    def test_a_new_pr_requirement_uses_zero_approvals(self):
        body = github_state()
        body['required_pull_request_reviews'] = None
        body['restrictions'] = None
        result = self.apply(GitHubRunner(body))
        self.assertTrue(result['pr_required'])
        runner = GitHubRunner(body)
        self.apply(runner)
        self.assertEqual(runner.writes[0]['required_pull_request_reviews'], {
            'required_approving_review_count': 0,
        })
        self.assertIsNone(runner.writes[0]['restrictions'])

    def test_founding_uses_verified_unprotected_branch_not_a_guessed_404(self):
        body = github_state()
        body['required_pull_request_reviews'] = None
        body['restrictions'] = None
        runner = GitHubRunner(body)
        runner.branch['protected'] = False
        # Explicit metadata, not a failed protection GET, proves absence.
        self.apply(runner)
        self.assertEqual(runner.writes[0], {
            'required_status_checks': {
                'strict': True,
                'checks': [{'context': 'build'}, {'context': 'test'}],
            },
            'enforce_admins': True,
            'required_pull_request_reviews': {'required_approving_review_count': 0},
            'restrictions': None,
            'allow_force_pushes': False, 'allow_deletions': False,
        })
        get_endpoints = [call[0][2] for call in runner.calls if len(call[0]) == 3]
        self.assertIn('repos/owner/project', get_endpoints)
        self.assertIn('repos/owner/project/branches/main', get_endpoints)
        self.assertIn(RULES, get_endpoints)
        self.assertNotIn(PROTECTION, get_endpoints)

    def test_missing_or_unauthentic_branch_metadata_does_not_authorize_founding(self):
        for branch in ({}, {'name': 'main'}, {'name': 'main', 'protected': None},
                       {'name': 'main', 'protected': 'false'},
                       {'name': 'elsewhere', 'protected': False}):
            with self.subTest(branch=branch):
                runner = GitHubRunner()
                runner.branch = branch
                with self.assertRaises(Refusal):
                    self.apply(runner)
                self.assertEqual(runner.writes, [])
        runner = GitHubRunner()
        runner.branch['protected'] = False
        runner.failures['repos/owner/project'] = Refusal('gh: repository not readable (404)')
        with self.assertRaises(Refusal):
            self.apply(runner)
        self.assertEqual(runner.writes, [])

    def test_founding_with_unreadable_rules_never_writes(self):
        runner = GitHubRunner()
        runner.branch['protected'] = False
        runner.failures[RULES] = Refusal('gh: rules API unavailable (404)')
        with self.assertRaises(Refusal):
            self.apply(runner)
        self.assertEqual(runner.writes, [])

    def test_apply_strengthens_the_authorized_gate_booleans(self):
        body = github_state()
        body['required_status_checks']['strict'] = False
        body['enforce_admins']['enabled'] = False
        body['allow_force_pushes']['enabled'] = True
        body['allow_deletions']['enabled'] = True
        runner = GitHubRunner(body)
        result = self.apply(runner)
        self.assertEqual(result['state'], 'expected')
        self.assertEqual(runner.writes[0]['required_status_checks']['strict'], True)

    def test_apply_without_explicit_nonblank_checks_has_no_remote_write(self):
        for checks in (None, [], (), [''], [' '], 'build', [7]):
            with self.subTest(checks=checks):
                runner = GitHubRunner()
                with self.assertRaises(Refusal):
                    self.apply(runner, checks)
                self.assertEqual(runner.calls, [])
                self.assertEqual(runner.writes, [])

    def test_unreadable_protection_and_rules_refuse_before_any_put(self):
        for endpoint in (PROTECTION, RULES):
            with self.subTest(endpoint=endpoint):
                runner = GitHubRunner()
                runner.failures[endpoint] = Refusal('gh: private repo (404)')
                with self.assertRaises(Refusal):
                    self.apply(runner)
                self.assertEqual(runner.writes, [])
        runner = GitHubRunner(rules=[{'type': 'merge_queue'}])
        with self.assertRaises(Refusal):
            self.apply(runner)
        self.assertEqual(runner.writes, [])

    def test_incomplete_existing_state_refuses_instead_of_clearing_settings(self):
        for field in ('enforce_admins', 'allow_force_pushes', 'allow_deletions',
                      'required_linear_history', 'block_creations',
                      'required_conversation_resolution', 'lock_branch', 'allow_fork_syncing'):
            with self.subTest(field=field):
                body = github_state()
                del body[field]
                runner = GitHubRunner(body)
                with self.assertRaises(Refusal):
                    self.apply(runner)
                self.assertEqual(runner.writes, [])

    def test_disabled_optional_sections_can_be_omitted_in_authentic_get(self):
        body = github_state()
        for field in ('required_status_checks', 'required_pull_request_reviews', 'restrictions'):
            del body[field]
        runner = GitHubRunner(body)
        self.apply(runner)
        self.assertEqual(runner.writes[0]['required_pull_request_reviews'], {
            'required_approving_review_count': 0,
        })
        self.assertIsNone(runner.writes[0]['restrictions'])
        self.assertEqual(runner.writes[0]['required_status_checks']['checks'], [
            {'context': 'build'}, {'context': 'test'},
        ])

    def test_malformed_existing_checks_reviews_and_actors_refuse_before_put(self):
        mutations = [
            ('required_status_checks', 'strict', 'true'),
            ('required_status_checks', 'checks', [{'context': 'build'}]),
            ('required_status_checks', 'checks', [{'context': 'build', 'app_id': True}]),
            ('required_status_checks', 'contexts', ['another-check']),
            ('required_pull_request_reviews', 'required_approving_review_count', -1),
            ('required_pull_request_reviews', 'required_approving_review_count', True),
            ('required_pull_request_reviews', 'require_last_push_approval', 0),
            ('restrictions', 'users', ['octocat']),
            ('restrictions', 'apps', [{'id': 101}]),
        ]
        for parent, field, wrong in mutations:
            with self.subTest(parent=parent, field=field, wrong=wrong):
                body = github_state()
                body[parent][field] = wrong
                runner = GitHubRunner(body)
                with self.assertRaises(Refusal):
                    self.apply(runner)
                self.assertEqual(runner.writes, [])

    def test_a_put_response_that_did_not_establish_the_gate_is_refused(self):
        for response in ({}, [], {'message': 'success'}, github_state()):
            with self.subTest(response=response):
                runner = GitHubRunner(put_response=response)
                # The unchanged response is missing the newly requested test check.
                with self.assertRaises(Refusal):
                    self.apply(runner)
                self.assertEqual(len(runner.writes), 1)


class GuardProtectionCliTest(unittest.TestCase):
    """Exercise argparse, the real guard and lazy hard_edges.run through a PATH gh double."""
    guard_script = ROOT / 'scripts/guard'

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        directory = Path(self.scratch.name)
        self.fixture_path = directory / 'github.json'
        self.capture_path = directory / 'calls.jsonl'
        bin_path = directory / 'bin'
        bin_path.mkdir()
        gh = bin_path / 'gh'
        gh.write_text('''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, os.environ['PROTECTION_TEST_ROOT'])
from tests.test_protection import GitHubRunner
fixture = json.loads(Path(os.environ['PROTECTION_GH_FIXTURE']).read_text())
runner = GitHubRunner(fixture['body'], fixture['rules'])
runner.repo = fixture['repo']
runner.branch = fixture['branch']
args = ('gh', *sys.argv[1:])
text = sys.stdin.read() if args[:4] == ('gh', 'api', '-X', 'PUT') else None
response = runner(*args, input=text)
with Path(os.environ['PROTECTION_GH_CAPTURE']).open('a') as stream:
    stream.write(json.dumps({'argv': args, 'writes': runner.writes}) + '\\n')
sys.stdout.write(response)
''')
        gh.chmod(0o755)
        self.env = {
            **os.environ,
            'PATH': str(bin_path) + os.pathsep + os.environ['PATH'],
            'PYTHONPATH': str(ROOT / 'scripts') + os.pathsep + os.environ.get('PYTHONPATH', ''),
            'PROTECTION_TEST_ROOT': str(ROOT),
            'PROTECTION_GH_FIXTURE': str(self.fixture_path),
            'PROTECTION_GH_CAPTURE': str(self.capture_path),
        }
        boundary = GitHubRunner()
        self.fixture = {'body': github_state(), 'rules': [],
                        'repo': boundary.repo, 'branch': boundary.branch}

    def invoke(self, *options):
        self.fixture_path.write_text(json.dumps(self.fixture))
        return subprocess.run([
            sys.executable, str(self.guard_script), 'protection',
            '--repo', 'owner/project', '--branch', 'main', '--project', str(ROOT), *options,
        ], env=self.env, cwd=ROOT, text=True, capture_output=True)

    def captured_writes(self):
        if not self.capture_path.exists():
            return []
        calls = [json.loads(line) for line in self.capture_path.read_text().splitlines()]
        return [payload for call in calls for payload in call['writes']]

    def test_guard_apply_emits_the_nonweakening_put_not_just_a_success_message(self):
        proc = self.invoke('--apply', '--check', 'build', '--check', 'test')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = json.loads(proc.stdout)
        self.assertEqual(state['action'], 'protection')
        self.assertEqual(state['state'], 'expected')
        self.assertTrue(state['applied'])
        self.assertTrue(state['pr_required'])
        writes = self.captured_writes()
        self.assertEqual(len(writes), 1)
        payload = writes[0]
        self.assertEqual(payload['required_status_checks'], {
            'strict': True,
            'checks': [{'context': 'build', 'app_id': 15368},
                       {'context': 'lint', 'app_id': -1}, {'context': 'test'}],
        })
        self.assertEqual(payload['required_pull_request_reviews']['required_approving_review_count'], 2)
        self.assertTrue(payload['required_pull_request_reviews']['require_code_owner_reviews'])
        self.assertEqual(payload['restrictions'], {
            'users': ['octocat'], 'teams': ['maintainers'], 'apps': ['push-app'],
        })
        self.assertIs(payload['required_linear_history'], True)
        self.assertIs(payload['enforce_admins'], True)
        self.assertIs(payload['allow_force_pushes'], False)
        self.assertIs(payload['allow_deletions'], False)

    def test_guard_founding_test_check_avoids_rejected_selector_combination(self):
        self.fixture['branch']['protected'] = False
        self.fixture['body']['required_pull_request_reviews'] = None
        self.fixture['body']['restrictions'] = None
        proc = self.invoke('--apply', '--check', 'test')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)['pr_required'])
        writes = self.captured_writes()
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['required_status_checks'], {
            'strict': True, 'checks': [{'context': 'test'}],
        })
        self.assertEqual(writes[0]['required_pull_request_reviews'], {
            'required_approving_review_count': 0,
        })
        self.assertIsNotNone(writes[0]['required_pull_request_reviews'])

    def test_guard_without_apply_never_puts(self):
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['state'], 'expected')
        self.assertEqual(self.captured_writes(), [])

    def test_guard_apply_without_named_checks_refuses_before_writing(self):
        proc = self.invoke('--apply')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('--check', proc.stderr)
        self.assertEqual(self.captured_writes(), [])


if __name__ == '__main__':
    unittest.main()
