"""Real dispatch consumers and git worktrees; only GitHub is a stateful boundary double."""
import json
import os
import subprocess
import sys
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
        self.record = self.f.project / '.codex-method/lanes/2.json'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                                 str(self.f.project), '--host-version', '0.159.2'],
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
            cmd += ['--host-version', '0.159.2']
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

    def test_receipt_has_only_real_v2_fields_and_whole_role_and_ordered_record(self):
        data = self.prepared()
        spawn = json.loads(Path(data['instruction']).read_text())
        self.assertEqual(set(spawn), {'task_name','message','agent_type','fork_turns','model','reasoning_effort'})
        self.assertEqual(spawn['agent_type'], 'method_worker')
        self.assertEqual(spawn['fork_turns'], 'none')
        self.assertEqual((spawn['model'],spawn['reasoning_effort']), ('gpt-6.1-sol','high'))
        self.assertIn((ROOT / 'reference/worker.md').read_text(), spawn['message'])
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
        self.assertIn((ROOT / 'reference/code-review-prompt.md').read_text(), receipt['message'])
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
        review_record = self.f.project / '.codex-method/lanes/2-reviewer.json'
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
