"""Exercise the collector's refusals with real Git and durable files.

Remote/OS boundaries are doubled; all fixture cause data is simulated.
"""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ci-evidence'


def command(cwd, *args):
    return subprocess.check_output(list(args), cwd=cwd, stderr=subprocess.DEVNULL).decode().strip()


def proof(cause='provider-outage'):
    return {
        'cause': cause, 'scope': 'github.com/account owner',
        'why_waiting_ruled_out': 'Rehearsal of a documented urgent decision, no real outage.',
        'observed_at': '2026-10-05T06:00:00+00:00',
        'prevents_all_eligible_pushes': True, 'external_to_repo': True,
        'diagnostics': {'authenticated': True, 'readable': True, 'workflow_enabled': True,
                        'event_eligible': True, 'org_enabled': True, 'runs': []},
        'captures': [{'argv': ['curl', 'https://www.githubstatus.com/api/v2/incidents/unresolved.json'],
                      'exit_code': 0, 'captured_at': '2026-10-05T06:00:00+00:00',
                      'stdout': json.dumps({'incidents': [{'id': 'fixture-incident',
                                  'status': 'investigating', 'name': 'Actions workflow runs cannot start',
                                  'components': [{'name': 'Actions', 'status': 'major_outage'}]}]}),
                      'stderr': ''}],
        'simulated': True,
    }


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def load(self):
        self.assertTrue(SCRIPT.is_file(), 'focused collector is missing')
        return runpy.run_path(str(SCRIPT))

    def test_cli_has_no_merge_or_release_operation(self):
        r = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('--verify', r.stdout)
        bad = subprocess.run([sys.executable, str(SCRIPT), '--execute'], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)

    def test_named_causes_require_whole_original_proof_and_exclude_repo_failures(self):
        m = self.load()
        for cause in ('provider-outage', 'minutes-exhausted'):
            p = proof(cause)
            if cause == 'minutes-exhausted':
                p['private_repo'] = True
                p['blocking_capture_index'] = 0
                p['captures'][0] = {'argv': ['browser-read', 'https://github.com/settings/billing'],
                    'exit_code': 0, 'captured_at': p['observed_at'],
                    'stdout': 'SIMULATED: Actions included minutes exhausted; further hosted usage blocked for this account.', 'stderr': ''}
            self.assertEqual(m['qualify'](p, rehearsal=True)['operationally_qualified'], False)
            self.assertEqual(m['qualify'](p, rehearsal=True)['candidate'], True)
        for field, value in [('cause', 'queued'), ('external_to_repo', False),
                             ('prevents_all_eligible_pushes', False), ('captures', []),
                             ('why_waiting_ruled_out', '')]:
            p = proof(); p[field] = value
            with self.subTest(field=field), self.assertRaises(m['Refusal']):
                m['qualify'](p, rehearsal=True)
        for flag in ('authenticated', 'readable', 'workflow_enabled', 'event_eligible', 'org_enabled'):
            p = proof(); p['diagnostics'][flag] = False
            with self.subTest(flag=flag), self.assertRaises(m['Refusal']):
                m['qualify'](p, rehearsal=True)
        for status in ('queued', 'in_progress', 'completed'):
            p = proof(); p['diagnostics']['runs'] = [{'status': status, 'conclusion': 'failure'}]
            with self.subTest(status=status), self.assertRaises(m['Refusal']):
                m['qualify'](p, rehearsal=True)

    def test_simulation_cannot_be_presented_as_operational_outage(self):
        m = self.load()
        with self.assertRaises(m['Refusal']):
            m['qualify'](proof(), rehearsal=False)
        p = proof(); p['simulated'] = False
        p['captures'][0]['stdout'] = '{}'
        with self.assertRaises(m['Refusal']):
            m['qualify'](p, rehearsal=False)

    def repo(self):
        repo = self.home / 'repo'; repo.mkdir()
        command(repo, 'git', 'init', '-b', 'main')
        command(repo, 'git', 'config', 'user.name', 'Fixture')
        command(repo, 'git', 'config', 'user.email', 'fixture@example.invalid')
        (repo / '.github/workflows').mkdir(parents=True)
        for p in (ROOT / '.github/workflows').glob('*.yml'):
            (repo / '.github/workflows' / p.name).write_bytes(p.read_bytes())
        (repo / 'code').write_text('base\n')
        command(repo, 'git', 'add', '.')
        command(repo, 'git', 'commit', '-m', 'base')
        base = command(repo, 'git', 'rev-parse', 'HEAD')
        command(repo, 'git', 'checkout', '-b', 'task')
        (repo / 'code').write_text('head\n')
        command(repo, 'git', 'commit', '-am', 'head')
        return repo, base, command(repo, 'git', 'rev-parse', 'HEAD')

    def test_materialization_is_actual_ordered_two_parent_merge(self):
        m = self.load(); repo, base, head = self.repo()
        out = self.home / 'evidence'; out.mkdir()
        recorder = m['Recorder'](out)
        result = m['materialize'](repo, base, head, out, recorder)
        parents = command(repo, 'git', 'rev-list', '--parents', '-n', '1', result['commit']).split()
        self.assertEqual(parents[1:], [base, head])
        self.assertEqual(result['tree'], command(repo, 'git', 'merge-tree', '--write-tree', base, head))
        self.assertTrue((out / 'merge.bundle').is_file())
        self.assertTrue(result['archive_ref'].startswith('refs/codex-method/ci-evidence/'))

    def test_changed_workflow_cannot_keep_the_old_job_coverage(self):
        m = self.load(); repo, _, _ = self.repo()
        map_path = ROOT / 'scripts/ci-evidence-map.json'
        approved = json.loads(map_path.read_text())
        m['check_map'](repo, approved)
        with (repo / '.github/workflows/ci.yml').open('a') as f:
            f.write('\n  new-job:\n    runs-on: ubuntu-latest\n')
        with self.assertRaises(m['Refusal']):
            m['check_map'](repo, approved)

    def test_input_inventory_detects_dirty_source_and_ignored_input_drift(self):
        m = self.load(); repo, _, _ = self.repo()
        (repo / '.gitignore').write_text('input.dat\n')
        command(repo, 'git', 'add', '.gitignore'); command(repo, 'git', 'commit', '-m', 'ignore')
        (repo / 'input.dat').write_bytes(b'first')
        first = m['inventory'](repo, ignored_inputs=['input.dat'])
        (repo / 'input.dat').write_bytes(b'second')
        second = m['inventory'](repo, ignored_inputs=['input.dat'])
        with self.assertRaises(m['Refusal']):
            m['unchanged'](first, second)
        (repo / 'code').write_text('dirty')
        with self.assertRaises(m['Refusal']):
            m['inventory'](repo, ignored_inputs=['input.dat'])

    def test_recorder_keeps_binary_output_exit_and_interrupted_intent(self):
        m = self.load(); out = self.home / 'captures'; out.mkdir()
        recorder = m['Recorder'](out)
        result = recorder.run([sys.executable, '-c', "import os;os.write(1,b'full\\xff');raise SystemExit(7)"], self.home)
        self.assertEqual(result.returncode, 7)
        capture = json.loads((out / 'captures/0000-result.json').read_text())
        self.assertEqual(base64.b64decode(capture['stdout_b64']), b'full\xff')
        with patch('subprocess.run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                recorder.run(['unstarted'], self.home)
        self.assertTrue((out / 'captures/0001-started.json').exists())
        self.assertFalse((out / 'captures/0001-result.json').exists())

    def test_unknown_publication_only_recovers_one_exact_author_body(self):
        m = self.load(); out = self.home / 'pub'; out.mkdir()
        intent = m['publication_intent'](out, 'owner/project', 1, 'owner', 'whole evidence', 'token1')
        receipt = {'id': 8, 'body': intent['body'], 'user': {'login': 'owner'},
                   'html_url': 'https://github.com/owner/project/pull/1#issuecomment-8',
                   'created_at': '2026-10-05T06:00:00Z', 'updated_at': '2026-10-05T06:00:00Z'}
        with self.assertRaises(m['Refusal']):
            m['publication_recover'](out, [])
        with self.assertRaises(m['Refusal']):
            m['publication_recover'](out, [receipt, receipt])
        altered = copy.deepcopy(receipt); altered['body'] += 'edited'
        with self.assertRaises(m['Refusal']):
            m['publication_recover'](out, [altered])
        wrong = copy.deepcopy(receipt); wrong['user']['login'] = 'intruder'
        with self.assertRaises(m['Refusal']):
            m['publication_recover'](out, [wrong])
        quote = copy.deepcopy(receipt); quote['id'] = 9; quote['body'] = 'Audit quotes evidence:\n'+intent['body']
        got = m['publication_recover'](out, [receipt, quote])
        self.assertEqual(got['comment_id'], 8)
        self.assertTrue((out / 'publication-receipt.json').exists())
        old = (out / 'publication-receipt.json').read_bytes()
        self.assertEqual(m['publication_recover'](out, [receipt]), got)
        self.assertEqual((out / 'publication-receipt.json').read_bytes(), old)
        changed = copy.deepcopy(receipt); changed['updated_at'] = '2026-10-05T06:01:00Z'
        with self.assertRaises(m['Refusal']): m['publication_recover'](out, [changed])

    def test_bundle_tampering_and_partial_capture_never_verify_complete(self):
        m = self.load(); out = self.home / 'bundle'; out.mkdir()
        recorder = m['Recorder'](out)
        recorder.run([sys.executable, '-c', "print('all output')"], self.home)
        m['seal'](out, {'merge_permitted': False, 'coverage_complete': False})
        with self.assertRaises(m['Refusal']): m['verify'](out, '0'*64)
        report = m['verify'](out, hashlib.sha256((out/'bundle-receipt.json').read_bytes()).hexdigest())
        self.assertFalse(report['merge_permitted'])
        self.assertFalse(report['coverage_complete'])
        (out / 'captures/0000-result.json').write_text('{}')
        with self.assertRaises(m['Refusal']):
            m['verify'](out)


    def test_step_removal_or_arbitrary_command_cannot_be_called_reviewed(self):
        m = self.load(); repo, _, _ = self.repo()
        canonical = json.loads((ROOT / 'scripts/ci-evidence-map.json').read_text())
        for edit in ('remove', 'command', 'kind', 'secret', 'matrix'):
            changed = copy.deepcopy(canonical)
            if edit == 'remove': changed['jobs'][0]['steps'].pop()
            elif edit == 'command': changed['jobs'][0]['steps'][0]['run'] = 'true'
            elif edit == 'kind': changed['jobs'][0]['steps'][0]['kind'] = 'unknown-action'
            else: changed['jobs'][0][edit] = {'unexpected': True}
            with self.subTest(edit=edit), self.assertRaises(m['Refusal']):
                m['check_map'](repo, changed)

    def test_parts_reconstruct_the_whole_carrier_and_detect_tampering(self):
        m = self.load(); out = self.home / 'parts'; out.mkdir()
        r = m['Recorder'](out); r.run([sys.executable, '-c', "print('whole')"], self.home)
        m['seal'](out, {'coverage_complete': False, 'simulated': True})
        index = json.loads((out / 'publication-parts.json').read_text())
        joined = ''.join((out / x['path']).read_text().split('\n\n', 1)[1] for x in index['parts'])
        self.assertEqual(joined, (out / 'evidence.md').read_text())
        self.assertEqual(hashlib.sha256(joined.encode()).hexdigest(), index['carrier_sha256'])
        (out / index['parts'][0]['path']).write_text('tampered')
        with self.assertRaises(m['Refusal']): m['verify'](out)

    def test_same_capture_counts_do_not_hide_a_missing_result(self):
        m = self.load(); out = self.home / 'partial'; out.mkdir()
        r = m['Recorder'](out); r.run([sys.executable, '-c', 'pass'], self.home)
        (out / 'captures/0000-result.json').rename(out / 'captures/0001-result.json')
        m['seal'](out, {'coverage_complete': False})
        with self.assertRaises(m['Refusal']): m['verify'](out)

    def test_all_jobs_account_for_failure_incapability_and_always_artifacts(self):
        m = self.load(); repo, base, head = self.repo(); out = self.home / 'jobs'; out.mkdir()
        r = m['Recorder'](out); identity = m['materialize'](repo, base, head, out, r)
        approved = json.loads((ROOT / 'scripts/ci-evidence-map.json').read_text())
        executed = []; original_run = r.run
        def fake_run(argv, cwd, **kwargs):
            if argv[0] != 'bash': return original_run(argv, cwd, **kwargs)
            executed.append(argv[-1]); return subprocess.CompletedProcess(argv,
                1 if 'SUITE_RESULT' in kwargs.get('env', {}) else 0, b'fixture output', b'')
        with patch.object(r, 'run', side_effect=fake_run), patch('platform.system', return_value='Darwin'), \
                patch.dict(m['run_jobs'].__globals__, {'environment_snapshot': lambda *a, **k: {'fixture': 'simulated'}}):
            report = m['run_jobs'](Path(identity['checkout']), approved, r, out)
        self.assertFalse(report['coverage_complete'])
        self.assertEqual(set(report['jobs']), {'suite', 'native', 'test', 'merged-result'})
        self.assertEqual(report['jobs']['native'], 'incapable')
        self.assertEqual(report['jobs']['merged-result'], 'dependency-failed')
        retained = [s for s in report['steps'] if s['step'] == 'retain-native-artifact']
        self.assertEqual(len(retained), 1)
        self.assertIn('artifact', retained[0]['result'])
        self.assertNotIn('npm install --global @openai/codex@0.160.0', executed)

    def test_changed_remote_base_or_head_cannot_reuse_pins(self):
        m = self.load()
        original = {'base': 'a'*40, 'head': 'b'*40, 'branch': 'main'}
        for key in ('base', 'head', 'branch'):
            current = {**original, key: 'c'*40}
            with self.subTest(key=key), self.assertRaises(m['Refusal']):
                m['same_identity'](original, current)

    def test_generated_output_is_allowed_only_as_declared_and_inputs_stay_bound(self):
        m = self.load(); repo, _, _ = self.repo()
        (repo / '.gitignore').write_text('__pycache__/\n')
        command(repo, 'git', 'add', '.gitignore'); command(repo, 'git', 'commit', '-m', 'ignore')
        before = m['inventory'](repo)
        cache = repo / '__pycache__'; cache.mkdir(); (cache / 'generated.pyc').write_bytes(b'generated')
        after = m['inventory'](repo, generated=['__pycache__/*.pyc'])
        m['unchanged'](before, after)
        (cache / 'unknown').write_text('unexpected input')
        with self.assertRaises(m['Refusal']): m['inventory'](repo, generated=['__pycache__/*.pyc'])


    def test_old_usage_totals_and_paid_overage_do_not_prove_a_block(self):
        m = self.load(); p = proof('minutes-exhausted'); p['private_repo'] = True
        p['captures'][0]['argv'] = ['gh', 'api', 'user/settings/billing/actions']
        p['captures'][0]['stdout'] = json.dumps({'total_minutes_used': 2000, 'included_minutes': 2000})
        with self.assertRaises(m['Refusal']): m['qualify'](p, rehearsal=True)

    def test_full_success_covers_all_steps_and_setup_boundaries(self):
        m = self.load(); repo, base, head = self.repo(); out = self.home / 'full'; out.mkdir()
        r = m['Recorder'](out); identity = m['materialize'](repo, base, head, out, r)
        approved = json.loads((ROOT / 'scripts/ci-evidence-map.json').read_text())
        original = Path.is_file; commands = []; original_run = r.run
        def is_file(path): return True if str(path) == '/etc/os-release' else original(path)
        def read_text(path, *a, **k):
            if str(path) == '/etc/os-release': return 'ID=ubuntu\n'
            return original_read(path, *a, **k)
        original_read = Path.read_text
        def fake_run(argv, cwd, **kwargs):
            if argv[0] != 'bash': return original_run(argv, cwd, **kwargs)
            self.assertFalse(kwargs['inherit_environment'])
            self.assertNotIn('GH_TOKEN', kwargs['env'])
            commands.append(argv[-1])
            if 'test-native-runtime.py' in argv[-1]:
                log = out/'native/evidence'; log.mkdir(); (log/'fixture.json').write_text('SIMULATED native artifact')
            return subprocess.CompletedProcess(argv, 0, b'SIMULATED OS output', b'')
        with patch.object(r, 'run', side_effect=fake_run), patch('platform.system', return_value='Linux'), \
                patch.object(Path, 'is_file', is_file), patch.object(Path, 'read_text', read_text), \
                patch.dict(m['run_jobs'].__globals__, {'environment_snapshot': lambda *a, **k: {'fixture': 'simulated'}}):
            report = m['run_jobs'](Path(identity['checkout']), approved, r, out)
        self.assertTrue(report['coverage_complete'])
        self.assertEqual(len(report['steps']), sum(len(job['steps']) for job in approved['jobs']))
        self.assertEqual(commands, [s['run'] for j in approved['jobs'] for s in j['steps'] if s['kind'] != 'artifact'])
        self.assertTrue(all('toolchain_before' in s and 'toolchain_after' in s for s in report['steps']))


    def test_collection_retains_original_failure_when_remote_head_moves(self):
        m = self.load(); repo, base, head = self.repo(); out = self.home / 'collection'
        cause = self.home / 'proof.json'; cause.write_text(json.dumps(proof()))
        context = self.home / 'context'; context.mkdir()
        for name in ('issue.json', 'accepted-spec.md', 'source-checklist.md'):
            (context / name).write_text('whole simulated context '+name)
        args = Namespace(project=repo, repo='owner/project', pr=1, proof=cause,
                         map=ROOT/'scripts/ci-evidence-map.json', output=out, rehearsal=True, context=context)
        original = m['Recorder'].read; views = 0
        def read(recorder, argv, cwd, **kwargs):
            nonlocal views
            if argv[:2] == ['gh', 'api']:
                endpoint = argv[-1]
                if endpoint == 'repos/owner/project': return json.dumps({'default_branch': 'main'})
                if '/pulls/' in endpoint:
                    views += 1
                    return json.dumps({'state':'open','base':{'ref':'main','sha':base},
                                       'head':{'sha':head if views <= 2 else 'c'*40}})
                if '/git/ref/' in endpoint: return json.dumps({'object':{'sha':base}})
                if '/actions/workflows' in endpoint: return json.dumps([{'workflows':[
                    {'path':'.github/workflows/ci.yml','state':'active'},
                    {'path':'.github/workflows/release.yml','state':'active'}]}])
                if '/actions/runs' in endpoint: return json.dumps([{'workflow_runs':[]}])
                self.fail(endpoint)
            if argv == ['git','remote','get-url','origin']: return 'https://github.com/owner/project.git'
            if argv[:3] == ['git','fetch','origin']:
                argv = ['git','fetch',str(repo),'main' if argv[3] == 'main' else 'task']
            return original(recorder, argv, cwd, **kwargs)
        with patch.object(m['Recorder'], 'read', read), patch.dict(m['collect'].__globals__,
                {'run_jobs': lambda *a,**k: {'coverage_complete':True,'jobs':{},'steps':[],'gaps':[]}}):
            with self.assertRaises(m['Refusal']): m['collect'](args)
        report = m['verify'](out)
        self.assertFalse(report['coverage_complete']); self.assertIn('moved', report['error'])
        self.assertEqual((out/'cause-original.json').read_bytes(), cause.read_bytes())
        self.assertTrue((out/'merge.bundle').exists()); self.assertTrue((out/'checkout/.git').exists())
        self.assertEqual(command(repo,'git','rev-parse','HEAD'),head)

    def test_audit_context_cannot_be_missing_or_symlinked(self):
        m = self.load(); context = self.home/'audit'; context.mkdir(); output=self.home/'copy';output.mkdir()
        with self.assertRaises(m['Refusal']): m['retain_context'](context, output)
        for name in ('issue.json','accepted-spec.md','source-checklist.md'):
            (context/name).write_text('whole context')
        (context/'issue.json').unlink(); (context/'issue.json').symlink_to(context/'accepted-spec.md')
        with self.assertRaises(m['Refusal']): m['retain_context'](context, output)


    def test_tracked_symlink_cannot_hide_an_external_input(self):
        m = self.load(); repo, _, _ = self.repo()
        secret = self.home/'outside'; secret.write_text('unaccounted input')
        (repo/'link').symlink_to(secret)
        command(repo,'git','add','link'); command(repo,'git','commit','-m','symlink')
        with self.assertRaises(m['Refusal']): m['inventory'](repo)


if __name__ == '__main__':
    unittest.main()
