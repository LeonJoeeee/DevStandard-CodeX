"""Real dispatch consumers and git worktrees; only GitHub is a stateful boundary double."""
import json
import os
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

from tests.github_fixture import GitHubFixture, ROOT


GH = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p=Path(os.environ['GH_FIXTURE']); s=json.loads(p.read_text()); a=sys.argv[1:]
s.setdefault('calls', []).append(a); p.write_text(json.dumps(s))
if a[:2] == ['repo','view']: value={'nameWithOwner':'owner/project'}
elif a[:2] == ['issue','view']:
    value={'number':2,'title':'Fix acceptance','body':s['issue'],'state':s.get('issue_state','OPEN')}
elif a == ['api','repos/owner/project/issues/2/comments','--paginate','--slurp']:
    value=[s.get('issue_comments', [])[:1],s.get('issue_comments', [])[1:]]
elif a == ['api','repos/owner/project/pulls/1']: value=s['pr']
else:
    print('Unexpected request: '+repr(a),file=sys.stderr);sys.exit(2)
print(json.dumps(value))
'''


class DispatchNativeTest(unittest.TestCase):
    def setUp(self):
        self.f = GitHubFixture()
        self.addCleanup(self.f.close)
        self.f.env['TMPDIR'] = str(self.f.root)
        (self.f.root / 'bin/gh').write_text(GH)
        self.worktree = self.f.root / 'lane'
        self.f.git('checkout', 'main')
        self.f.git('worktree', 'add', self.worktree, 'task/2-acceptance')
        self.branch = 'task/2-acceptance'
        self.record = self.f.project / '.git/codex-method/lanes/2.json'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                                 str(self.f.project), '--host-version', '0.160.0'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.f.state()
        self.long_comment = 'Record starts\n' + 'full comment content ' * 60 + '\nRECORD END'
        state['issue_comments'] = [
            {'id':10,'user':{'login':'human'},'created_at':'2026-10-01T01:00:00Z','body':self.long_comment},
            {'id':11,'user':{'login':'orchestrator'},'created_at':'2026-10-01T02:00:00Z',
             'body':'Dispatch receipt is part of the WHOLE record.'}]
        state['pr'].update(number=1, html_url='https://github.com/owner/project/pull/1',
                           merged=False, merge_commit_sha=None)
        state['pr']['head']['repo'] = {'full_name':'owner/project'}
        state['pr']['base']['repo'] = {'full_name':'owner/project'}
        self.f.save(state)

    def call(self, *args, qualify=True, explicit=True):
        cmd = [sys.executable, str(ROOT / 'scripts/dispatch'), '2', *map(str, args)]
        if explicit:
            cmd += ['--project', str(self.f.project)]
        if qualify:
            cmd += ['--host-version', '0.160.0']
        return subprocess.run(cmd, cwd=self.f.project, env=self.f.env, text=True, capture_output=True)

    def prepare(self, purpose='worker', **kwargs):
        return self.call('--purpose', purpose, '--adopt', '--branch', self.branch,
                         '--worktree', self.worktree, '--base', 'main', '--pr', 1, **kwargs)

    def prepared(self, **kwargs):
        result = self.prepare(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def evidence(self, name, value):
        path = self.f.root / name
        path.write_text(json.dumps(value))
        return path

    def spawn(self):
        data = self.prepared()
        spawn = json.loads(Path(data['instruction']).read_text())
        handle = '/root/' + spawn['task_name']
        result = self.call('--record-spawn', self.evidence('spawn.json', {'task_name':handle,'nickname':'worker'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        return handle

    def status(self, handle, status):
        return self.evidence('status.json', {'agents':[{'agent_name':handle,'agent_status':status}]})

    def finish(self):
        handle = self.spawn()
        evidence = self.status(handle, {'completed':'Returned PR and evidence.'})
        result = self.call('--record-status', evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        return handle, evidence

    def another_checkout(self):
        other = self.f.root / 'caller-b'
        self.f.git('branch', 'caller-b', 'main')
        self.f.git('worktree', 'add', other, 'caller-b')
        installed = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                                    str(other), '--host-version', '0.160.0'],
                                   env=self.f.env, capture_output=True, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        return other

    def call_from(self, project, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/dispatch'), '2', *map(str, args),
                               '--project', str(project), '--host-version', '0.160.0'],
                              cwd=project, env=self.f.env, capture_output=True, text=True)

    def install_isolated_user_roles(self):
        self.f.env['CODEX_HOME'] = str(self.f.root / 'codex-user')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                                 '--host-version', '0.160.0'], env=self.f.env,
                                cwd=self.f.project, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_current_user_roles_qualify_when_project_has_no_method_roles(self):
        self.install_isolated_user_roles()
        for path in (self.f.project / '.codex/agents').glob('method_*.toml'):
            path.unlink()
        config = self.f.project / '.codex/config.toml'
        original = '# unrelated project configuration\nmodel = "project-model"\n'
        config.write_text(original)
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_text(), original)
        self.assertFalse(list((self.f.project / '.codex/agents').glob('method_*.toml')))

    def test_current_user_roles_never_hide_stale_project_roles(self):
        self.install_isolated_user_roles()
        path = self.f.project / '.codex/agents/method_worker.toml'
        path.write_text(path.read_text().replace('developer_instructions =', 'stale_instructions ='))
        before = path.read_bytes()
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(self.record.exists())

    def test_project_disabling_v2_refuses_despite_current_user_roles(self):
        self.install_isolated_user_roles()
        for path in (self.f.project / '.codex/agents').glob('method_*.toml'):
            path.unlink()
        config = self.f.project / '.codex/config.toml'
        config.write_text('[features.multi_agent_v2]\nenabled = false\n')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())

    def test_a_subdirectory_cannot_replace_the_project_root_language_authority(self):
        self.install_isolated_user_roles()
        nested = self.f.project / 'nested'
        nested.mkdir()
        (nested / 'AGENTS.md').write_text('## Record language\nEnglish is canonical.\n')
        (self.f.project / 'AGENTS.md').write_text('## Record language\nChinese is canonical.\n')
        result = self.call_from(nested, '--purpose', 'worker', '--adopt', '--branch', self.branch,
                                '--worktree', self.worktree, '--base', 'main')
        self.assertNotEqual(result.returncode, 0, '--project must identify the actual checkout root')
        self.assertFalse(self.record.exists())

    def test_another_issue_cannot_adopt_an_owned_writer_worktree(self):
        self.prepared()
        fake = self.f.root / 'bin/gh'
        fake.write_text(GH.replace("'number':2", "'number':3").replace('issues/2/comments', 'issues/3/comments'))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/dispatch'), '3', '--project',
                                 str(self.f.project), '--host-version', '0.160.0', '--purpose', 'worker',
                                 '--adopt', '--branch', self.branch, '--worktree', str(self.worktree), '--base', 'main'],
                                cwd=self.f.project, env=self.f.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.record.parent / '3.json').exists())

    def test_another_checkout_can_cleanup_the_recorded_integrated_lane(self):
        handle, _ = self.finish()
        other = self.another_checkout()
        self.merged()
        result = self.call_from(other, '--cleanup', '--pr', 1,
                                '--native-status', self.status(handle, {'completed': 'done'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.worktree.exists())
        self.assertEqual(json.loads(self.record.read_text())['status'], 'cleaned')

    def test_initial_brief_reaches_both_native_and_retained_carriers_verbatim(self):
        brief = self.f.root / 'initial.txt'
        raw = 'Input dataset: 唯一数据.csv\nExpected output: complete result\r\n'
        brief.write_bytes(raw.encode())
        result = self.call('--purpose', 'worker', '--adopt', '--branch', self.branch,
                           '--worktree', self.worktree, '--base', 'main', '--brief', brief)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        request = json.loads(Path(record['instruction']).read_text())
        self.assertTrue(raw in request['message'], 'initial inputs were omitted or rewritten')
        self.assertTrue(raw in Path(record['brief']).read_bytes().decode(), 'retained brief lost inputs')
        self.assertIn('Inputs and expected output', request['message'])

    def test_missing_initial_brief_refuses_before_preparing_a_lane(self):
        result = self.call('--purpose', 'worker', '--adopt', '--branch', self.branch,
                           '--worktree', self.worktree, '--base', 'main', '--brief', self.f.root / 'missing')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())
        self.assertTrue(self.worktree.exists())
        self.assertFalse((self.f.project / '.git/codex-method/lanes').exists(),
                         'bad input must refuse before ownership or legacy-state mutations')

    def test_changed_legacy_receipt_after_import_blocks_shared_lane_actions(self):
        data = self.prepared()
        legacy = self.f.project / '.codex-method/lanes/2.json'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps(data))
        self.record.unlink()
        self.assertNotEqual(self.prepare().returncode, 0)
        before = self.record.read_bytes()
        altered = dict(data, status='finished')
        legacy.write_text(json.dumps(altered))
        request = json.loads(Path(data['instruction']).read_text())
        evidence = self.evidence('spawn.json', {'task_name': '/root/' + request['task_name']})
        result = self.call('--record-spawn', evidence)
        self.assertNotEqual(result.returncode, 0, 'changed old state was silently ignored after migration')
        self.assertEqual(self.record.read_bytes(), before)

    def test_other_checkout_cannot_adopt_a_running_writer_lane(self):
        handle = self.spawn()
        result = self.call('--record-status', self.status(handle, 'running'))
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.record.read_bytes()
        other = self.another_checkout()
        result = self.call_from(other, '--purpose', 'worker', '--adopt', '--branch', self.branch,
                                '--worktree', self.worktree, '--base', 'main')
        self.assertNotEqual(result.returncode, 0, 'another checkout commissioned a second writer')
        self.assertEqual(self.record.read_bytes(), before)

    def test_another_checkout_can_observe_and_continue_the_existing_lane(self):
        handle, _ = self.finish()
        other = self.another_checkout()
        brief = self.f.root / 'continue.txt'
        brief.write_text('Continue exactly the recorded lane.')
        result = self.call_from(other, '--continue', '--brief', brief,
                                '--native-status', self.status(handle, {'completed': 'done'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['worktree'], str(self.worktree))
        self.assertEqual(len(data['runs']), 2)
        self.assertEqual(json.loads(self.record.read_text())['lane_id'], data['lane_id'])

    def test_legacy_unfinished_record_is_preserved_and_blocks_another_writer(self):
        data = self.prepared()
        legacy = self.f.project / '.codex-method/lanes/2.json'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(data, indent=2)
        legacy.write_text(raw)
        shared = self.f.project / '.git/codex-method/lanes/2.json'
        if shared.exists():
            shared.unlink()
        other = self.another_checkout()
        result = self.call_from(other, '--purpose', 'worker', '--adopt', '--branch', self.branch,
                                '--worktree', self.worktree, '--base', 'main')
        self.assertNotEqual(result.returncode, 0, 'legacy reservation was treated as an unused lane')
        self.assertEqual(legacy.read_text(), raw)
        self.assertTrue(shared.is_file(), 'retain a reconciled shared receipt even when launch refuses')

    def test_conflicting_legacy_records_refuse_without_overwriting_either(self):
        data = self.prepared()
        shared = self.f.project / '.git/codex-method/lanes/2.json'
        if shared.exists():
            shared.unlink()
        legacy = self.f.project / '.codex-method/lanes/2.json'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps(data))
        other = self.another_checkout()
        conflict = dict(data, lane_id='other-unfinished-lane')
        alternative = other / '.codex-method/lanes/2.json'
        alternative.parent.mkdir(parents=True, exist_ok=True)
        alternative.write_text(json.dumps(conflict))
        before = (legacy.read_bytes(), alternative.read_bytes())
        result = self.call_from(other, '--record-status', self.status('/root/unknown', 'running'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((legacy.read_bytes(), alternative.read_bytes()), before)
        self.assertFalse(shared.exists())

    def test_a_new_legacy_copy_with_a_different_native_handle_refuses(self):
        handle = self.spawn()
        before = self.record.read_bytes()
        conflict = json.loads(before)
        run = conflict['runs'][-1]
        run['native_task_name'] = '/root/other_parent/' + run['task_name']
        run['spawn_observation']['result']['task_name'] = run['native_task_name']
        legacy = self.f.project / '.codex-method/lanes/2.json'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(conflict)
        legacy.write_text(raw)
        result = self.call('--record-status', self.status(handle, {'completed': 'shared writer done'}))
        self.assertNotEqual(result.returncode, 0, 'a conflicting native child was treated as historical copy')
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(legacy.read_text(), raw)

    def test_a_new_legacy_copy_cannot_relabel_the_same_run_host_version(self):
        handle = self.spawn()
        before = self.record.read_bytes()
        conflict = json.loads(before)
        conflict['runs'][-1]['host_version'] = '0.159.2'
        legacy = self.f.project / '.codex-method/lanes/2.json'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(conflict)
        legacy.write_text(raw)
        result = self.call('--record-status', self.status(handle, {'completed': 'done'}))
        self.assertNotEqual(result.returncode, 0, 'a historical run version was silently overwritten')
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(legacy.read_text(), raw)

    def test_root_record_language_declarations_reach_the_packet(self):
        for declaration, wanted in (
                ('## Record language\nChinese is canonical for code, comments, documentation, commits, and GitHub records.\n', 'Chinese'),
                ('## 记录语言\n中文是代码、注释、文档、提交与 GitHub 记录的规范语言。\n', '中文')):
            with self.subTest(declaration=declaration):
                (self.f.project / 'AGENTS.md').write_text('# Repo\n\n' + declaration)
                result = self.prepare()
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                request = json.loads(Path(data['instruction']).read_text())
                self.assertTrue('Record language: ' + wanted + '\n' in request['message'],
                                'packet ignored the explicit project record language')
                self.record.unlink()

    def test_no_root_record_language_declaration_defaults_to_english(self):
        data = self.prepared()
        request = json.loads(Path(data['instruction']).read_text())
        self.assertIn('Record language: English\n', request['message'])

    def test_empty_or_ambiguous_record_language_refuses_before_lane_preparation(self):
        for declaration in ('## Record language\n',
                            '## Record language\nEnglish is canonical.\nChinese is canonical.\n'):
            with self.subTest(declaration=declaration):
                (self.f.project / 'AGENTS.md').write_text(declaration)
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.record.exists())

    def test_receipt_has_only_real_v2_fields_one_static_role_and_whole_ordered_record(self):
        data = self.prepared()
        spawn = json.loads(Path(data['instruction']).read_text())
        self.assertEqual(set(spawn), {'task_name','message','agent_type','fork_turns','model','reasoning_effort'})
        self.assertEqual(spawn['agent_type'], 'method_worker')
        self.assertEqual(spawn['fork_turns'], 'none')
        self.assertEqual((spawn['model'],spawn['reasoning_effort']), ('gpt-6.1-sol','high'))
        installed = tomllib.loads((self.f.project / '.codex/agents/method_worker.toml').read_text())['developer_instructions']
        source = (ROOT / 'reference/worker.md').read_text()
        self.assertEqual(installed.count(source), 1)
        self.assertNotIn(source, spawn['message'])
        self.assertNotIn('Full role contract:', spawn['message'])
        self.assertIn('Discovered native role: method_worker', spawn['message'])
        self.assertIn(self.f.state()['issue'], spawn['message'])
        self.assertIn(self.long_comment, spawn['message'])
        self.assertLess(spawn['message'].index('RECORD END'), spawn['message'].index('Dispatch receipt is'))
        self.assertIn('human', spawn['message'])
        self.assertIn(str(self.worktree), spawn['message'])
        self.assertIn('workdir', spawn['message'])
        self.assertEqual(json.loads(self.record.read_text())['status'], 'awaiting-native-spawn')

    def test_default_project_is_callers_cwd(self):
        result = self.prepare(explicit=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.record.exists())

    def test_unknown_host_and_uninstalled_roles_refuse_before_lane_mutation(self):
        result = self.prepare(qualify=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())
        (self.f.project / '.codex/agents/method_worker.toml').unlink()
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())

    def test_current_native_version_is_qualified_for_dispatch(self):
        result = self.call('--host-version', '0.160.0', '--purpose', 'worker', '--adopt',
                           '--branch', self.branch, '--worktree', self.worktree, '--base', 'main', qualify=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['host_version'], '0.160.0')

    def test_old_run_host_version_survives_observation_and_fresh_continuation(self):
        handle = self.spawn()
        old = json.loads(self.record.read_text())
        old['host_version'] = '0.159.2'
        for run in old['runs']:
            run.pop('host_version', None)
        self.record.write_text(json.dumps(old))
        result = self.call('--record-status', self.status(handle, {'completed': 'old run completed'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed['host_version'], '0.159.2')
        self.assertEqual(observed['runs'][0].get('host_version'), '0.159.2')
        brief = self.f.root / 'upgrade.txt'
        brief.write_text('Continue the same lane under the newly observed native host.')
        result = self.call('--continue', '--brief', brief,
                           '--native-status', self.status(handle, {'completed': 'old run completed'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual([run.get('host_version') for run in data['runs']], ['0.159.2', '0.160.0'])

    def test_removed_process_flags_are_not_accepted(self):
        for flag in ('--wait', '--reconcile-lost'):
            result = self.call(flag)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.record.exists())

    def test_reviewer_requires_packet_and_gets_full_contract_in_fresh_context(self):
        result = self.prepare(purpose='reviewer')
        self.assertNotEqual(result.returncode, 0)
        packet = self.f.root / 'review.md'
        packet.write_text('Whole canonical filled packet and pinned evidence.\n')
        result = self.call('--purpose','reviewer','--adopt','--branch',self.branch,
                           '--worktree',self.worktree,'--base','main','--pr',1,'--packet',packet)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(Path(json.loads(result.stdout)['instruction']).read_text())
        self.assertEqual(receipt['agent_type'], 'method_reviewer')
        self.assertEqual(receipt['fork_turns'], 'none')
        installed = tomllib.loads((self.f.project / '.codex/agents/method_reviewer.toml').read_text())['developer_instructions']
        self.assertIn((ROOT / 'reference/code-review-prompt.md').read_text(), installed)
        self.assertNotIn((ROOT / 'reference/code-review-prompt.md').read_text(), receipt['message'])
        self.assertIn(packet.read_text(), receipt['message'])

    def test_fresh_review_of_worker_lane_preserves_the_worker_lifecycle_record(self):
        self.finish()
        before = self.record.read_bytes()
        packet = self.f.root / 'review.md'
        packet.write_text('Full canonical review packet.')
        result = self.call('--purpose','reviewer','--adopt','--branch',self.branch,
                           '--worktree',self.worktree,'--base','main','--pr',1,'--packet',packet)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.record.read_bytes(), before)
        review_record = self.f.project / '.git/codex-method/lanes/2-reviewer.json'
        self.assertTrue(review_record.is_file())
        self.assertEqual(json.loads(review_record.read_text())['purpose'],'reviewer')

    def test_cleanup_requires_finished_evidence_for_borrowing_reviewer_too(self):
        handle, evidence = self.finish()
        packet = self.f.root / 'review.md'
        packet.write_text('Full canonical review packet.')
        result = self.call('--purpose','reviewer','--adopt','--branch',self.branch,
                           '--worktree',self.worktree,'--base','main','--pr',1,'--packet',packet)
        self.assertEqual(result.returncode,0,result.stderr)
        request = json.loads(Path(json.loads(result.stdout)['instruction']).read_text())
        reviewer = '/root/' + request['task_name']
        result = self.call('--purpose','reviewer','--record-spawn',
                           self.evidence('review-spawn.json',{'task_name':reviewer}))
        self.assertEqual(result.returncode,0,result.stderr)
        self.merged()
        evidence = self.status(handle,{'completed':'worker done'})
        result = self.call('--cleanup','--pr',1,'--native-status',evidence)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.worktree.exists())
        both = self.evidence('all-status.json',{'agents':[
            {'agent_name':handle,'agent_status':{'completed':'worker done'}},
            {'agent_name':reviewer,'agent_status':{'completed':'review done'}}]})
        result = self.call('--cleanup','--pr',1,'--native-status',both)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_duplicate_live_lane_is_not_overwritten(self):
        self.spawn()
        before = self.record.read_bytes()
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.record.read_bytes(), before)

    def test_spawn_and_status_evidence_validate_real_task_handle(self):
        self.prepared()
        before = self.record.read_bytes()
        bad = self.evidence('bad.json', {'task_name':'/root/not-the-requested-task'})
        self.assertNotEqual(self.call('--record-spawn', bad).returncode, 0)
        self.assertEqual(self.record.read_bytes(), before)
        request = json.loads(Path(json.loads(self.record.read_text())['instruction']).read_text())
        handle = '/root/' + request['task_name']
        self.assertEqual(self.call('--record-spawn', self.evidence('good.json', {'task_name':handle})).returncode, 0)
        for status in ('not_found', 'interrupted', 'running', 'pending_init'):
            result = self.call('--record-status', self.status(handle,status))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(json.loads(self.record.read_text())['status'], 'finished')
        result = self.call('--record-status', self.status('/root/other', {'completed':'done'}))
        self.assertNotEqual(result.returncode, 0)
        result = self.call('--record-status', self.status(handle, {'completed':'done'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text())['status'], 'finished')

    def test_continuation_reloads_whole_updated_record_and_preserves_lane(self):
        handle, evidence = self.finish()
        brief = self.f.root / 'continuation.txt'
        brief.write_text('Fix the same lane. ORIGINAL CONTINUATION IN FULL\n')
        state = self.f.state()
        state['issue'] += '\nLATEST BODY'
        state['issue_comments'].append({'id':12,'user':{'login':'human'},
                                       'created_at':'2026-10-02T00:00:00Z','body':'LATEST STEERING'})
        self.f.save(state)
        evidence = self.status(handle, {'completed':'Returned PR and evidence.'})
        result = self.call('--continue','--brief',brief,'--native-status',evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        spawn = json.loads(Path(data['instruction']).read_text())
        for text in ('LATEST BODY','LATEST STEERING',self.long_comment,brief.read_text()):
            self.assertIn(text, spawn['message'])
        self.assertEqual(data['branch'], self.branch)
        self.assertEqual(data['worktree'], str(self.worktree))
        self.assertEqual(len(data['runs']), 2)

    def test_continuation_requires_finished_evidence_and_correct_recorded_lane(self):
        self.spawn()
        brief = self.f.root / 'brief.txt'
        brief.write_text('Continue')
        self.assertNotEqual(self.call('--continue','--brief',brief).returncode, 0)
        self.assertNotEqual(self.call('--continue','--brief',brief,'--branch','task/wrong').returncode, 0)

    def merged(self):
        state = self.f.state()
        state['pr'].update(merged=True, state='closed', merge_commit_sha=self.f.head)
        self.f.save(state)
        self.f.git('merge','--ff-only',self.branch)

    def test_cleanup_removes_clean_integrated_worktree_then_branch_only_with_native_evidence(self):
        handle, evidence = self.finish()
        self.merged()
        evidence = self.status(handle, {'completed':'Returned PR and evidence.'})
        result = self.call('--cleanup','--pr',1,'--native-status',evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.worktree.exists())
        refs = self.f.git('branch','--list',self.branch)
        self.assertFalse(refs.strip())
        self.assertEqual(json.loads(self.record.read_text())['status'], 'cleaned')

    def test_cleanup_preserves_unintegrated_commits_and_all_leftovers(self):
        handle, evidence = self.finish()
        self.merged()
        evidence = self.status(handle, {'completed':'Returned PR and evidence.'})
        for name in ('sole-copy.txt', '.ignored-leftover'):
            path = self.worktree / name
            path.write_text('must survive')
            if name.startswith('.'):
                exclude = Path(self.f.git('rev-parse','--git-common-dir').strip()) / 'info/exclude'
                exclude = self.f.project / exclude if not exclude.is_absolute() else exclude
                exclude.write_text(exclude.read_text() + '\n.ignored-leftover\n')
            result = self.call('--cleanup','--pr',1,'--native-status',evidence)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_text(), 'must survive')
            path.unlink()
        subprocess.check_call(['git','-C',str(self.worktree),'commit','--allow-empty','-m','unintegrated'],
                              stdout=subprocess.DEVNULL)
        self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',evidence).returncode, 0)
        self.assertTrue(self.worktree.exists())

    def test_new_worker_lane_creates_real_worktree_and_can_bind_returned_pr(self):
        ignore = self.f.project / '.gitignore'
        ignore.write_text('.codex-method/\n.codex/\n')
        self.f.git('add','.gitignore')
        self.f.git('commit','-m','ignore lanes')
        result = self.call('--purpose','worker','--base','main')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        lane = Path(data['worktree'])
        self.assertTrue((lane / '.git').is_file())
        self.assertIsNone(data['pr'])
        request = json.loads(Path(data['instruction']).read_text())
        handle = '/root/' + request['task_name']
        result = self.call('--record-spawn',self.evidence('spawn.json',{'task_name':handle}))
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.f.state()
        state['pr']['head']['ref'] = data['branch']
        state['pr']['head']['sha'] = subprocess.check_output(['git','-C',str(lane),'rev-parse','HEAD'],text=True).strip()
        self.f.save(state)
        result = self.call('--record-status',self.status(handle,{'completed':'PR 1'}),'--pr',1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['pr'], 'https://github.com/owner/project/pull/1')

    def test_completed_status_cannot_be_reused_as_fresh_cleanup_or_continuation_evidence(self):
        handle, old = self.finish()
        self.merged()
        result = self.call('--cleanup','--pr',1,'--native-status',old)
        self.assertNotEqual(result.returncode, 0)
        brief = self.f.root / 'brief.txt'
        brief.write_text('Continue')
        self.assertNotEqual(self.call('--continue','--brief',brief).returncode, 0)
        self.assertNotEqual(self.call('--continue','--brief',brief,'--native-status',old).returncode, 0)
        live = self.status(handle,'running')
        self.assertNotEqual(self.call('--continue','--brief',brief,'--native-status',live).returncode, 0)

    def test_stale_completed_capture_cannot_overwrite_newer_running_observation(self):
        handle, evidence = self.finish()
        old = self.evidence('old-finished.json',json.loads(evidence.read_text()))
        running = self.status(handle,'running')
        result = self.call('--record-status',running)
        self.assertEqual(result.returncode,0,result.stderr)
        before = self.record.read_bytes()
        result = self.call('--record-status',old)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.record.read_bytes(),before)

    def test_cleanup_checks_every_retained_native_handle_after_continuation(self):
        old_handle, evidence = self.finish()
        brief = self.f.root / 'continue.txt'
        brief.write_text('Same lane, refreshed task.')
        evidence = self.status(old_handle,{'completed':'first done'})
        result = self.call('--continue','--brief',brief,'--native-status',evidence)
        self.assertEqual(result.returncode,0,result.stderr)
        request = json.loads(Path(json.loads(result.stdout)['instruction']).read_text())
        handle = '/root/' + request['task_name']
        result = self.call('--record-spawn',self.evidence('spawn-2.json',{'task_name':handle}))
        self.assertEqual(result.returncode,0,result.stderr)
        result = self.call('--record-status',self.status(handle,{'completed':'second done'}))
        self.assertEqual(result.returncode,0,result.stderr)
        self.merged()
        latest = self.status(handle,{'completed':'second done'})
        self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',latest).returncode,0)
        both = self.evidence('both-runs.json',{'agents':[
            {'agent_name':old_handle,'agent_status':{'completed':'first done'}},
            {'agent_name':handle,'agent_status':{'completed':'second done'}}]})
        result = self.call('--cleanup','--pr',1,'--native-status',both)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_invalid_or_foreign_adoption_preserves_existing_worktree(self):
        result = self.call('--purpose','worker','--adopt','--branch','task/wrong',
                           '--worktree',self.worktree,'--base','main')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())
        self.assertTrue(self.worktree.exists())

    def test_cleanup_rejects_false_merge_identity_and_running_or_missing_native_evidence(self):
        handle, evidence = self.finish()
        self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',evidence).returncode, 0)
        self.merged()
        self.assertNotEqual(self.call('--cleanup','--pr',1).returncode, 0)
        self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',self.status(handle,'running')).returncode, 0)
        evidence = self.status(handle, {'completed':'done'})
        for field, value in (('html_url','https://github.com/other/repo/pull/1'),
                             ('number',999)):
            state = self.f.state(); original = state['pr'][field]; state['pr'][field] = value
            self.f.save(state)
            self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',evidence).returncode, 0)
            state['pr'][field] = original; self.f.save(state)
        self.assertTrue(self.worktree.exists())
