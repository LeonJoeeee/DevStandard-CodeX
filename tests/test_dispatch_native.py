"""Real dispatch/Git worktrees; GitHub double and delegating Git fault injection."""
import json
import os
import shutil
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
elif a == ['api','repos/owner/project/pulls/1']:
    s['pr_reads']=s.get('pr_reads',0)+1
    if s.get('pr_race') and s['pr_reads']>=s['pr_race']:
        s['pr']['head']['sha']='c'*40
    p.write_text(json.dumps(s)); value=s['pr']
elif a == ['api','repos/owner/project']:
    value=s.get('repository', {'full_name':'owner/project', 'clone_url':'https://github.com/owner/project.git'})
elif a == ['api','repos/owner/project/git/ref/heads/main']:
    s['base_reads']=s.get('base_reads',0)+1
    sha=s['current_base'] if not s.get('base_race') or s['base_reads']<s['base_race'] else 'd'*40
    p.write_text(json.dumps(s))
    value={'ref':'refs/heads/main','object':{'type':'commit','sha':sha}}
else:
    print('Unexpected request: '+repr(a),file=sys.stderr);sys.exit(2)
print(json.dumps(value))
'''


GIT_FAULT = r"""#!/usr/bin/env python3
import json, os, signal, subprocess, sys
from pathlib import Path
p=Path(os.environ['GH_FIXTURE']); s=json.loads(p.read_text()); a=sys.argv[1:]
s.setdefault('git_calls', []).append(a)
fault=s.get('git_fault')
matched=fault and all(word in a for word in fault['contains'])
if matched:
    s.pop('git_fault')
p.write_text(json.dumps(s))
def act():
    if fault['action']=='crash':
        os.kill(os.getppid(), signal.SIGKILL)
        sys.exit(97)  # A pre-command crash must not let this wrapper execute Git afterward.
    elif fault['action']=='symbolic':
        subprocess.check_call([os.environ['REAL_GIT'], 'symbolic-ref', fault['archive'], fault['target']])
    elif fault['action']=='conflict':
        subprocess.check_call([os.environ['REAL_GIT'], 'update-ref', fault['archive'], fault['head']])
    elif fault['action']=='branch-move':
        head=subprocess.check_output([os.environ['REAL_GIT'], 'commit-tree', fault['tree'], '-p', fault['head']],
                                     input='extra committed work\n', text=True).strip()
        subprocess.check_call([os.environ['REAL_GIT'], 'update-ref', fault['branch_ref'], head])
if matched and fault['when']=='before': act()
result=subprocess.run([os.environ['REAL_GIT'], *a])
if matched and fault['when']=='after' and result.returncode==0: act()
sys.exit(result.returncode)
"""


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
        self.publish_remote()

    def publish_remote(self):
        remote = self.f.root / 'remote.git'
        if not remote.exists():
            self.f.git('clone', '--bare', str(self.f.project), str(remote))
            self.f.git('config', 'url.' + remote.as_uri() + '.insteadOf',
                       'https://github.com/owner/project.git')
        else:
            self.f.git('push', str(remote), 'main:main')
        state = self.f.state()
        state['current_base'] = self.f.git('rev-parse', 'main').strip()
        self.f.save(state)
        return remote

    def squash_merged(self, advance=False, stale=False):
        self.f.git('merge', '--squash', self.branch)
        self.f.git('commit', '-m', 'squash integration')
        integration = self.f.git('rev-parse', 'HEAD').strip()
        self.assertNotEqual(integration, self.f.head)
        state = self.f.state()
        state['pr'].update(merged=True, state='closed', merge_commit_sha=integration)
        self.f.save(state)
        if advance:
            (self.f.project / 'later.txt').write_text('later base change\n')
            self.f.git('add', 'later.txt')
            self.f.git('commit', '-m', 'later base advancement')
        remote = self.publish_remote()
        if stale:
            self.f.git('reset', '--hard', self.f.base)
        return integration, remote

    def test_cleanup_squash_preserves_original_head_with_advanced_remote_and_stale_local_main(self):
        handle, _ = self.finish()
        integration, remote = self.squash_merged(advance=True, stale=True)
        self.assertEqual(self.f.git('rev-parse', 'main').strip(), self.f.base)
        self.assertEqual(self.f.git('rev-parse', integration + '^{tree}'),
                         self.f.git('rev-parse', self.f.head + '^{tree}'))
        result = self.call('--cleanup', '--pr', 1,
                           '--native-status', self.status(handle, {'completed':'done'}))
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(self.record.read_text())
        archive = record['cleanup']['archive_ref']
        self.assertEqual(self.f.git('rev-parse', archive).strip(), self.f.head)
        self.assertEqual(self.f.git('show', archive + ':code.txt'), 'base\nhead\n')
        self.assertFalse(self.worktree.exists())
        self.assertFalse(self.f.git('branch', '--list', self.branch).strip())
        self.assertEqual(record['status'], 'cleaned')
        self.assertTrue(record['cleanup']['proof']['local_base_stale'])
        self.assertEqual(record['cleanup']['proof']['local_base_sha'], self.f.base)
        self.assertEqual(record['cleanup']['proof']['base_sha'], self.f.state()['current_base'])
        remote_head = subprocess.check_output(['git', '--git-dir', str(remote),
                                               'rev-parse', 'refs/heads/' + self.branch], text=True).strip()
        self.assertEqual(remote_head, self.f.head)

    def archive_ref(self):
        return 'refs/codex-method/archive/2/' + json.loads(self.record.read_text())['lane_id']

    def inject_git_fault(self, **fault):
        self.f.env['REAL_GIT'] = shutil.which('git')
        path = self.f.root / 'bin/git'
        path.write_text(GIT_FAULT)
        path.chmod(0o755)
        state = self.f.state()
        state['git_fault'] = fault
        self.f.save(state)

    def cleanup_call(self, handle):
        return self.call('--cleanup', '--pr', 1,
                         '--native-status', self.status(handle, {'completed':'done'}))

    def assert_lane_preserved(self, head=None):
        self.assertTrue(self.worktree.exists())
        self.assertEqual(self.f.git('rev-parse', 'refs/heads/' + self.branch).strip(), head or self.f.head)
        self.assertNotEqual(json.loads(self.record.read_text())['status'], 'cleaned')

    def test_cleanup_ancestor_allows_different_integration_tree(self):
        handle, _ = self.finish()
        self.merged()
        (self.f.project / 'extra.txt').write_text('base addition')
        self.f.git('add', 'extra.txt')
        self.f.git('commit', '-m', 'merge integration with extra base content')
        state = self.f.state()
        state['pr']['merge_commit_sha'] = self.f.git('rev-parse', 'HEAD').strip()
        self.f.save(state)
        self.publish_remote()
        self.assertNotEqual(self.f.git('rev-parse', 'HEAD^{tree}'),
                            self.f.git('rev-parse', self.f.head + '^{tree}'))
        result = self.cleanup_call(handle)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.f.git('rev-parse', self.archive_ref()).strip(), self.f.head)

    def test_cleanup_tracked_squash_preserves_unrelated_effective_config(self):
        handle, _ = self.finish()
        self.squash_merged()
        self.f.git('branch', '--set-upstream-to=main', self.branch)
        self.f.git('config', 'example.unrelated', 'keep-me')
        before = self.f.git('config', '--local', '--list').splitlines()
        result = self.cleanup_call(handle)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = self.f.git('config', '--local', '--list').splitlines()
        self.assertEqual(after, [line for line in before if not line.startswith('branch.' + self.branch + '.')])
        self.assertEqual(self.f.git('rev-parse', self.archive_ref()).strip(), self.f.head)

    def test_cleanup_refuses_inherited_multimerge_and_logical_remote_collision(self):
        handle, _ = self.finish()
        self.squash_merged()
        inherited = self.f.root / 'inherited.config'
        self.f.git('config', 'include.path', str(inherited))
        before = self.f.git('config', '--local', '--list')
        lane = json.loads(self.record.read_text())['lane_id']
        for config in ('[branch "' + self.branch + '"]\nmerge = refs/heads/main\nmerge = refs/heads/other\n',
                       '[remote "codex-method-cleanup-' + lane + '"]\nurl = somewhere\n'):
            inherited.write_text(config)
            result = self.cleanup_call(handle)
            self.assertNotEqual(result.returncode, 0)
            self.assert_lane_preserved()
            self.assertEqual(inherited.read_text(), config)
            self.assertEqual(self.f.git('config', '--local', '--list'), before)

    def test_cleanup_refuses_integration_proof_mismatch_without_removing_lane(self):
        handle, _ = self.finish()
        integration, _ = self.squash_merged()
        original = self.f.state()
        cases = [('integration', self.f.base), ('unreachable', self.f.head), ('base', self.f.head), ('repository', 'other/repo'),
                 ('missing', 'f' * 40), ('base-ref', 'unknown')]
        for kind, value in cases:
            state = json.loads(json.dumps(original))
            if kind in ('integration', 'unreachable', 'missing'): state['pr']['merge_commit_sha'] = value
            elif kind=='base': state['current_base'] = value
            elif kind=='base-ref': state['pr']['base']['ref'] = value
            else: state['repository'] = {'full_name':value, 'clone_url':'https://github.com/owner/project.git'}
            self.f.save(state)
            result = self.cleanup_call(handle)
            self.assertNotEqual(result.returncode, 0, kind)
            self.assert_lane_preserved()

    def test_cleanup_refuses_direct_archive_conflict_and_symbolic_archives(self):
        handle, _ = self.finish()
        self.squash_merged()
        archive = self.archive_ref()
        target = 'refs/heads/archive-target'
        for kind in ('direct', 'symbolic', 'dangling'):
            if kind=='direct': self.f.git('update-ref', archive, self.f.base)
            else:
                if kind=='symbolic': self.f.git('update-ref', target, self.f.base)
                self.f.git('symbolic-ref', archive, target)
            result = self.cleanup_call(handle)
            self.assertNotEqual(result.returncode, 0, kind)
            self.assert_lane_preserved()
            if kind=='direct':
                self.assertEqual(self.f.git('rev-parse', archive).strip(), self.f.base)
            else:
                self.assertEqual(self.f.git('symbolic-ref', archive).strip(), target)
                found = subprocess.run(['git','show-ref','--verify',target], cwd=self.f.project,
                                       capture_output=True, text=True)
                self.assertEqual(found.returncode, 0 if kind=='symbolic' else 128)
            self.f.git('update-ref', '--no-deref', '-d', archive)
            if kind=='symbolic': self.f.git('update-ref', '-d', target)

    def test_cleanup_cas_refuses_dangling_symbolic_winner_at_transaction(self):
        handle, _ = self.finish()
        self.squash_merged()
        archive = self.archive_ref()
        target = 'refs/heads/untouched-dangling-target'
        self.inject_git_fault(contains=['update-ref','--no-deref',archive], when='before',
                              action='symbolic', archive=archive, target=target)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode, 0)
        self.assert_lane_preserved()
        self.assertEqual(self.f.git('symbolic-ref', archive).strip(), target)
        found = subprocess.run(['git','show-ref','--verify',target], cwd=self.f.project,
                               capture_output=True, text=True)
        self.assertNotEqual(found.returncode, 0)

    def test_cleanup_recovers_after_each_removal_before_progress_write(self):
        for boundary in ('worktree', 'branch'):
            with self.subTest(boundary=boundary):
                if boundary=='branch':
                    self.f.close()
                    self.setUp()
                handle, _ = self.finish()
                self.squash_merged()
                contains = ['worktree','remove'] if boundary=='worktree' else ['branch','-d']
                self.inject_git_fault(contains=contains, when='after', action='crash')
                result = self.cleanup_call(handle)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.worktree.exists())
                record = json.loads(self.record.read_text())
                self.assertNotEqual(record['status'], 'cleaned')
                self.assertTrue(record['cleanup_intent']['archive_verified'])
                self.assertEqual(record['cleanup_intent']['phase'],
                                 'worktree-removing' if boundary=='worktree' else 'worktree-removed')
                retained = self.f.git('branch','--list',self.branch).strip()
                self.assertEqual(bool(retained), boundary=='worktree')
                self.assertEqual(self.f.git('rev-parse', self.archive_ref()).strip(), self.f.head)
                result = self.cleanup_call(handle)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(self.record.read_text())['status'], 'cleaned')
                self.assertFalse(self.f.git('branch','--list',self.branch).strip())

    def test_cleanup_refuses_missing_worktree_without_intent(self):
        handle, _ = self.finish()
        self.squash_merged()
        self.f.git('worktree','remove',str(self.worktree))
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(), self.f.head)
        self.assertNotEqual(json.loads(self.record.read_text())['status'], 'cleaned')

    def test_cleanup_refuses_committed_head_move_after_worktree_removal(self):
        handle, _ = self.finish()
        self.squash_merged()
        self.inject_git_fault(contains=['worktree','remove'], when='after', action='branch-move',
                              tree=self.f.git('rev-parse',self.f.head+'^{tree}').strip(),
                              head=self.f.head, branch_ref='refs/heads/'+self.branch)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode, 0)
        extra = self.f.git('rev-parse',self.branch).strip()
        self.assertNotEqual(extra, self.f.head)
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)
        self.assertNotEqual(json.loads(self.record.read_text())['status'],'cleaned')
        self.assertNotEqual(self.cleanup_call(handle).returncode,0)
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(),extra)

    def test_cleanup_refuses_api_base_and_pr_races_preserving_lane(self):
        handle, _ = self.finish()
        self.squash_merged()
        state = self.f.state()
        state['base_race'] = state.get('base_reads',0) + 2
        self.f.save(state)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        state = self.f.state()
        state.pop('base_race')
        state['pr_race'] = state['pr_reads'] + 2
        self.f.save(state)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()

    def test_cleanup_refuses_other_worktree_occupying_branch(self):
        handle, _ = self.finish()
        self.squash_merged()
        occupied = self.f.root / 'occupied'
        self.f.git('worktree','add','--force',str(occupied),self.branch)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertTrue(occupied.exists())
        self.assertEqual((occupied/'code.txt').read_text(),'base\nhead\n')

    def test_cleanup_cas_refuses_direct_winner_without_overwrite(self):
        handle, _ = self.finish()
        self.squash_merged()
        archive = self.archive_ref()
        self.inject_git_fault(contains=['update-ref','--no-deref',archive],when='before',
                              action='conflict',archive=archive,head=self.f.base)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertEqual(self.f.git('rev-parse',archive).strip(),self.f.base)

    def interrupted_worktree(self):
        handle, _ = self.finish()
        self.squash_merged()
        self.inject_git_fault(contains=['worktree','remove'],when='after',action='crash')
        evidence = self.status(handle, {'completed':'done'})
        result = self.call('--cleanup','--pr',1,'--native-status',evidence)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.worktree.exists())
        return handle, evidence

    def test_cleanup_marker_refuses_recreated_clean_linked_worktree(self):
        handle, _ = self.interrupted_worktree()
        self.f.git('worktree','add',str(self.worktree),self.branch)
        before = self.record.read_bytes()
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertEqual((self.worktree/'code.txt').read_text(),'base\nhead\n')
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)
        self.assertEqual(self.record.read_bytes(),before)
        self.assertIn('worktree-removing',result.stderr)
        self.assertIn('path present',result.stderr)
        self.assertIn(self.archive_ref(),result.stderr)
        self.assertIn(self.f.head,result.stderr)
        self.assertIn('caller inspection/disposition',result.stderr)

    def test_cleanup_marker_refuses_original_after_precommand_crash(self):
        handle, _ = self.finish()
        self.squash_merged()
        self.inject_git_fault(contains=['worktree','remove'],when='before',action='crash')
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)
        before = self.record.read_bytes()
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertEqual((self.worktree/'code.txt').read_text(),'base\nhead\n')
        self.assertEqual(self.record.read_bytes(),before)
        self.assertEqual(json.loads(before)['cleanup_intent']['phase'],'worktree-removing')
        self.assertIn('may have begun',result.stderr)
        self.assertIn('path present',result.stderr)
        self.assertIn('caller inspection/disposition',result.stderr)

    def test_cleanup_retry_requires_new_native_observation_and_blocks_redispatch(self):
        handle, old = self.interrupted_worktree()
        before = self.record.read_bytes()
        result = self.call('--cleanup','--pr',1,'--native-status',old)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.record.read_bytes(),before)
        brief = self.f.root/'resume.txt'
        brief.write_text('Do not redispatch pending teardown.')
        result = self.call('--continue','--brief',brief,'--native-status',self.status(handle,{'completed':'done'}))
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(),self.f.head)
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)

    def test_cleanup_recovery_refuses_reappeared_files_and_changed_archive(self):
        handle, _ = self.interrupted_worktree()
        self.worktree.mkdir()
        leftover = self.worktree/'new-sole-copy'
        leftover.write_text('preserve reappeared file')
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(leftover.read_text(),'preserve reappeared file')
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(),self.f.head)
        leftover.unlink()
        self.worktree.rmdir()
        self.f.git('update-ref',self.archive_ref(),self.f.base)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.base)
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(),self.f.head)
        self.assertNotEqual(json.loads(self.record.read_text())['status'],'cleaned')

    def test_cleanup_tracked_files_and_unknown_native_handles_preserve_exact_state(self):
        handle, _ = self.finish()
        self.squash_merged()
        original = (self.worktree/'code.txt').read_text()
        (self.worktree/'code.txt').write_text('dirty tracked file')
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assert_lane_preserved()
        self.assertEqual((self.worktree/'code.txt').read_text(),'dirty tracked file')
        (self.worktree/'code.txt').write_text(original)
        for status in ('not_found','interrupted','running','pending_init','unqualified'):
            before = self.record.read_bytes()
            result = self.call('--cleanup','--pr',1,'--native-status',self.status(handle,status))
            self.assertNotEqual(result.returncode,0)
            self.assert_lane_preserved()
            self.assertEqual(self.record.read_bytes(),before)

    def test_cleanup_archive_retains_development_ancestry_after_gc(self):
        original = self.f.head
        subprocess.check_call(['git','-C',str(self.worktree),'commit','--allow-empty','-m','second original commit'],
                              stdout=subprocess.DEVNULL)
        self.f.head = subprocess.check_output(['git','-C',str(self.worktree),'rev-parse','HEAD'],text=True).strip()
        state = self.f.state()
        state['pr']['head']['sha'] = self.f.head
        self.f.save(state)
        handle, _ = self.finish()
        self.squash_merged()
        result = self.cleanup_call(handle)
        self.assertEqual(result.returncode,0,result.stderr)
        self.f.git('reflog','expire','--expire=now','--all')
        self.f.git('gc','--prune=now')
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()+'^').strip(),original)
        self.assertEqual(self.f.git('show',original+':code.txt'),'base\nhead\n')

    def test_cleanup_accepts_single_inherited_tracking_source_without_config_write(self):
        handle, _ = self.finish()
        self.squash_merged()
        inherited = self.f.root/'tracking.config'
        config = '[branch "'+self.branch+'"]\nremote = origin\nmerge = refs/heads/main\n'
        inherited.write_text(config)
        self.f.git('config','include.path',str(inherited))
        before = self.f.git('config','--local','--list')
        result = self.cleanup_call(handle)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(inherited.read_text(),config)
        self.assertEqual(self.f.git('config','--local','--list'),before)
        self.assertEqual(self.f.git('rev-parse',self.archive_ref()).strip(),self.f.head)

    def test_cleanup_refuses_changed_pr_repository_and_branch_identity(self):
        handle, _ = self.finish()
        self.squash_merged()
        original = self.f.state()
        for part, field, value in [('head','ref','task/foreign'),('head','repo',{'full_name':'other/repo'}),
                                   ('base','repo',{'full_name':'other/repo'}),('head','sha','a'*40)]:
            state = json.loads(json.dumps(original))
            state['pr'][part][field] = value
            self.f.save(state)
            result = self.cleanup_call(handle)
            self.assertNotEqual(result.returncode,0)
            self.assert_lane_preserved()

    def test_cleanup_refuses_symlink_redirect_of_recorded_worktree(self):
        handle, _ = self.finish()
        self.squash_merged()
        moved = self.f.root/'moved-lane'
        self.f.git('worktree','move',str(self.worktree),str(moved))
        self.worktree.symlink_to(moved,target_is_directory=True)
        result = self.cleanup_call(handle)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.worktree.is_symlink())
        self.assertTrue(moved.exists())
        self.assertEqual((moved/'code.txt').read_text(),'base\nhead\n')
        self.assertEqual(self.f.git('rev-parse',self.branch).strip(),self.f.head)
        self.assertNotEqual(json.loads(self.record.read_text())['status'],'cleaned')

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
            self.assert_lane_preserved()
            path.unlink()
        subprocess.check_call(['git','-C',str(self.worktree),'commit','--allow-empty','-m','unintegrated'],
                              stdout=subprocess.DEVNULL)
        self.assertNotEqual(self.call('--cleanup','--pr',1,'--native-status',evidence).returncode, 0)
        extra = subprocess.check_output(['git','-C',str(self.worktree),'rev-parse','HEAD'],text=True).strip()
        self.assertNotEqual(extra,self.f.head)
        self.assert_lane_preserved(head=extra)

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
