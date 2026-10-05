"""Acceptance proofs through real git and packet/status/guard command consumers."""
import json
from pathlib import Path
import subprocess
import shutil
import fcntl
import hashlib
import os
import unittest

from tests.github_fixture import GitHubFixture


class ReuseFixture(GitHubFixture):
    def __init__(self):
        super().__init__()
        self.remote = self.root / 'destination.git'
        subprocess.run(['git','clone','--bare',str(self.project),str(self.remote)],
                       check=True,capture_output=True)
        self.git('remote','add','origin','https://github.com/owner/project.git')
        # Substitute only the network transport at the fixture boundary. All git
        # object/ancestry/replay operations still execute the real git binary.
        wrapper=self.root/'bin/git'
        wrapper.write_text('#!/usr/bin/env python3\nimport os,sys\n'
                           'a=sys.argv[1:]\n'
                           f"if 'fetch' in a and 'origin' in a: a[a.index('origin')]={str(self.remote)!r}\n"
                           f'os.execv({shutil.which("git")!r},["git",*a])\n')
        wrapper.chmod(0o755)

    def pin(self, base=None, head=None):
        self.base, self.head = base or self.base, head or self.head
        self.git('push',str(self.remote),f'+{self.base}:refs/heads/main',
                 f'+{self.head}:refs/heads/task/2-acceptance')
        state=self.state()
        state['pr']['base']['sha']=self.base;state['pr']['head']['sha']=self.head
        state['checks'][0]['name']=f'merged-result / {self.base} / {self.head}'
        self.save(state)

    def anchor(self, note=None):
        raw=self.verdict()
        if note:
            raw=raw.replace('None.\n',note)
        published=self.publish(raw)
        if published.returncode:
            raise AssertionError(published.stderr)
        self.original=self.state()['comments'][-1]['id']
        self.old_base,self.old_head=self.base,self.head
        return raw

    def reuse(self, kind, request):
        path=self.root / 'request.json';path.write_text(json.dumps(request))
        return self.command('review-packet','reuse',1,'--issue',2,'--attempt',self.original,
                            '--kind',kind,'--old-base',self.old_base,'--old-head',self.old_head,
                            '--base',self.base,'--head',self.head,'--request',path,
                            '--output',self.root/'proofs')

    def replay(self):
        self.git('checkout','--detach',self.old_base)
        (self.project/'main.txt').write_text('independent main change\n')
        self.git('add','main.txt');self.git('commit','-m','main moved')
        base=self.git('rev-parse','HEAD').strip()
        self.git('checkout','--detach',self.old_head)
        self.git('rebase','--onto',base,self.old_base)
        self.pin(base,self.git('rev-parse','HEAD').strip())

    def correction(self, body):
        (self.project/'code.txt').write_bytes(body)
        self.git('add','code.txt');self.git('commit','-m','prescribed Note')
        self.pin(head=self.git('rev-parse','HEAD').strip())

    def versions(self, value):
        for path in ('codex-method.json','.codex-plugin/plugin.json'):
            target=self.project/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('{\n  "version": "'+value+'",\n  "unchanged": true\n}\n')

    def version_history(self):
        original_head=self.head
        self.git('checkout','--detach',self.base);self.versions('0.1.0')
        self.git('add','.');self.git('commit','-m','descriptors base')
        self.base=self.git('rev-parse','HEAD').strip()
        self.git('cherry-pick',original_head);self.versions('0.2.0')
        self.git('add','.');self.git('commit','-m','reviewed versions')
        self.pin(head=self.git('rev-parse','HEAD').strip())

    def version_replay(self, value='0.4.0'):
        self.git('checkout','--detach',self.old_base);self.versions('0.3.0')
        self.git('add','.');self.git('commit','-m','main version')
        base=self.git('rev-parse','HEAD').strip()
        self.git('checkout','--detach',self.old_head)
        result=subprocess.run(['git','-C',str(self.project),'rebase','--onto',base,self.old_base],
                              capture_output=True,text=True)
        if result.returncode:
            self.versions(value);self.git('add','.');self.git('-c','core.editor=true','rebase','--continue')
        else:
            self.versions(value);self.git('add','.');self.git('commit','-m','synchronized final version')
        self.pin(base,self.git('rev-parse','HEAD').strip())


def block(meta, text='corrected\n'):
    return ('<!-- codex-method-note-v1 -->\nReplacement: '+json.dumps(meta,separators=(',',':'))+
            '\n```replacement\n'+text+'```\n<!-- /codex-method-note-v1 -->\n')


class AcceptanceReuseTest(unittest.TestCase):
    def setUp(self):
        self.fx=ReuseFixture();self.addCleanup(self.fx.close)

    def passed(self, result):
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def refused(self, result):
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('merged',self.fx.state())

    def test_ordinary_guard_rejects_changed_accepted_context(self):
        self.fx.anchor()
        state=self.fx.state();state['description']+='\nchanged contract';self.fx.save(state)
        self.refused(self.fx.guard('--execute'))

    def test_disjoint_replay_is_published_then_recomputed_without_another_round(self):
        self.fx.anchor();original=self.fx.state()['comments'][0]['body'];self.fx.replay()
        result=self.passed(self.fx.reuse('replay',{}))
        self.refused(self.fx.guard())
        self.passed(self.fx.guard('--reuse',result['comment_id'],'--execute'))
        self.assertEqual(self.fx.state()['comments'][0]['body'],original)
        status=self.passed(self.fx.command('review-packet','status',1,'--issue',2))
        self.assertEqual(status['rounds'],1)

    def test_exact_raw_note_requires_single_prescribed_commit(self):
        raw=self.fx.anchor(block({'target':'code.txt','start':0,'end':10}))
        self.fx.correction(b'corrected\n')
        proof=self.passed(self.fx.reuse('note',{'target':'code.txt','start':0,'end':10,
                                              'fence_offset':raw.encode().index(b'```replacement')}))
        self.passed(self.fx.guard('--reuse',proof['comment_id']))

    def test_same_head_external_requires_selected_proof(self):
        raw=self.fx.anchor(block({'artifact':'pr-description'}))
        state=self.fx.state();state['description']='corrected\n';self.fx.save(state)
        proof=self.passed(self.fx.reuse('external',{'artifact':'pr-description',
                                                   'fence_offset':raw.encode().index(b'```replacement')}))
        self.refused(self.fx.guard())
        self.passed(self.fx.guard('--reuse',proof['comment_id']))

    def test_record_native_is_exact_associated_issue_addition(self):
        started=self.passed(self.fx.start())
        observed=self.fx.root/'native-return.json';observed.write_text('{"agent_id":"actual-handle"}\n')
        self.passed(self.fx.command('review-packet','record-native',1,'--issue',2,
                                   '--attempt',started['comment_id'],'--native-handle','actual-handle',
                                   '--observation',observed))
        verdict=self.fx.root/'verdict.md';verdict.write_text(self.fx.verdict())
        self.passed(self.fx.command('review-packet','publish',1,'--issue',2,
                                   '--attempt',started['comment_id'],'--verdict',verdict))
        self.passed(self.fx.guard())
        state=self.fx.state();state['issue_comments'][0]['body']+='extra prose';self.fx.save(state)
        self.refused(self.fx.guard())

    def test_same_head_drift_can_receive_fresh_judgment_but_notes_cannot(self):
        self.fx.anchor();self.refused(self.fx.start())
        state=self.fx.state();state['issue']+='\nChanged done-check.';self.fx.save(state)
        self.passed(self.fx.start())
        self.assertEqual(len(self.fx.state()['comments']),2)

    def test_replay_preserves_deletion_symlink_literal_names_and_caller_state(self):
        (self.fx.project/'code.txt').unlink()
        (self.fx.project/'link').symlink_to('odd\nname')
        (self.fx.project/'odd\nname').write_bytes(b'\x00exact binary\xff')
        self.fx.git('add','-A');self.fx.git('commit','-m','literal entries')
        self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
        self.fx.anchor();self.fx.replay()
        before=(self.fx.git('show-ref'),self.fx.git('status','--porcelain','-uall'),
                hashlib.sha256((self.fx.project/'.git/index').read_bytes()).hexdigest())
        proof=self.passed(self.fx.reuse('replay',{}))
        self.passed(self.fx.guard('--reuse',proof['comment_id']))
        after=(self.fx.git('show-ref'),self.fx.git('status','--porcelain','-uall'),
               hashlib.sha256((self.fx.project/'.git/index').read_bytes()).hexdigest())
        self.assertEqual(before,after)

    def test_strict_synchronized_version_conflict_replay(self):
        self.fx.version_history();self.fx.anchor();self.fx.version_replay()
        proof=self.passed(self.fx.reuse('replay',{}))
        self.passed(self.fx.guard('--reuse',proof['comment_id']))
        ledger=json.loads(self.fx.ledger.read_text())
        self.assertEqual(ledger['reuses'][0]['proof']['version_conflicts_resolved'],1)

    def test_replay_content_mode_and_full_tree_drift_refuse(self):
        self.fx.anchor();self.fx.replay()
        valid=self.fx.head
        for change in ('content','mode','extra-main-path'):
            with self.subTest(change=change):
                self.fx.git('checkout','--detach',valid)
                if change=='content': (self.fx.project/'code.txt').write_text('adapted\n')
                elif change=='mode': (self.fx.project/'code.txt').chmod(0o755)
                else: (self.fx.project/'main.txt').write_text('changed outside PR paths\n')
                self.fx.git('add','-A');self.fx.git('commit','-m',change)
                self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
                self.refused(self.fx.reuse('replay',{}))
                self.assertFalse(json.loads(self.fx.ledger.read_text()).get('reuses'))

    def test_note_preserves_whitespace_and_utf8_half_open_boundaries(self):
        self.fx.correction('aé\nend\n'.encode())
        raw=self.fx.anchor(block({'target':'code.txt','start':1,'end':4},'  repl  \n\n  second\r\n'))
        self.fx.correction(b'arepl  \n\nsecond\r\nend\n')
        request={'target':'code.txt','start':1,'end':4,'fence_offset':raw.encode().index(b'```replacement')}
        proof=self.passed(self.fx.reuse('note',request));self.passed(self.fx.guard('--reuse',proof['comment_id']))

    def test_note_rejects_adaptation_mode_extra_files_parent_and_offsets(self):
        raw=self.fx.anchor(block({'target':'code.txt','start':0,'end':10}))
        old=self.fx.head
        for change in ('adapted','mode','extra','two-commits','amend'):
            with self.subTest(change=change):
                self.fx.git('checkout','--detach',old)
                (self.fx.project/'code.txt').write_bytes(b'adapted\n' if change=='adapted' else b'corrected\n')
                if change=='mode': (self.fx.project/'code.txt').chmod(0o755)
                if change=='extra': (self.fx.project/'extra.txt').write_text('extra')
                self.fx.git('add','-A')
                self.fx.git('commit',*(['--amend','--no-edit'] if change=='amend' else ['-m',change]))
                if change=='two-commits': self.fx.git('commit','--allow-empty','-m','extra commit')
                self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
                self.refused(self.fx.reuse('note',{'target':'code.txt','start':0,'end':10,
                                                  'fence_offset':raw.encode().index(b'```replacement')}))
        self.fx.git('checkout','--detach',old);self.fx.correction(b'corrected\n')
        for offsets in ({'start':False},{'end':11},{'fence_offset':1},{'start':0.0},{'start':1}):
            request={'target':'code.txt','start':0,'end':10,'fence_offset':raw.encode().index(b'```replacement'),**offsets}
            self.refused(self.fx.reuse('note',request))

    def test_ordinary_context_rejects_unknown_author_marker_edit_order_and_duplicates(self):
        initial=self.fx.state()
        initial['issue_comments']=[{'id':1,'user':{'login':'owner'},'body':'original issue context'}]
        initial['comments']=[{'id':2,'user':{'login':'other'},'body':'original PR context'}]
        self.fx.save(initial);self.fx.anchor();valid=self.fx.state()
        changes=('issue_body','title','issue_edit','pr_edit','new_owner_marker','duplicate','order','repo','ref')
        for change in changes:
            with self.subTest(change=change):
                state=json.loads(json.dumps(valid))
                if change=='issue_body': state['issue']+='changed'
                elif change=='title': state['title']='changed title'
                elif change=='issue_edit': state['issue_comments'][0]['body']+='changed'
                elif change=='pr_edit': state['comments'][0]['body']+='changed'
                elif change=='new_owner_marker': state['issue_comments'].append({'id':7,'user':{'login':'owner'},'body':'<!-- codex-method-native-v1 {} -->\n'})
                elif change=='duplicate': state['comments'].append(state['comments'][0])
                elif change=='order': state['comments'].reverse()
                elif change=='repo': state['pr']['head']['repo']['full_name']='other/repo'
                else: state['pr']['head']['ref']='different-ref'
                self.fx.save(state);self.refused(self.fx.guard('--execute'))
        self.fx.save(valid);self.passed(self.fx.guard())

    def test_proof_and_original_evidence_drift_refuse_at_actual_guard(self):
        self.fx.anchor();self.fx.replay();proof=self.passed(self.fx.reuse('replay',{}))
        ledger=json.loads(self.fx.ledger.read_text());record=ledger['reuses'][0];attempt=ledger['attempts'][0]
        for name in ('request_path','bundle_path','packet_path','native_instruction'):
            with self.subTest(file=name):
                path=Path((record if name in record else attempt)[name]);original=path.read_bytes()
                path.write_bytes(original+b'drift')
                self.refused(self.fx.guard('--reuse',proof['comment_id'],'--execute'));path.write_bytes(original)
        valid=self.fx.state()
        for change in ('proof-body','proof-author','original-body','original-author','duplicate-proof','missing-proof'):
            with self.subTest(change=change):
                state=json.loads(json.dumps(valid))
                if change.endswith('body'): state['comments'][0 if change.startswith('original') else -1]['body']+='drift'
                elif change.endswith('author'): state['comments'][0 if change.startswith('original') else -1]['user']['login']='other'
                elif change=='duplicate-proof': state['comments'].append(state['comments'][-1])
                else: state['comments'].pop()
                self.fx.save(state);self.refused(self.fx.guard('--reuse',proof['comment_id'],'--execute'))
        self.fx.save(valid);self.passed(self.fx.guard('--reuse',proof['comment_id']))

    def test_pending_reuse_lost_response_recovers_exactly_once(self):
        self.fx.anchor();self.fx.replay()
        state=self.fx.state();state['mutation_fault']={'method':'POST','outcome':'lost-response'};self.fx.save(state)
        self.refused(self.fx.reuse('replay',{}))
        self.refused(self.fx.guard('--execute'))
        before=json.loads(self.fx.ledger.read_text());self.assertEqual(before['pending']['record_type'],'reuse')
        recovered=self.passed(self.fx.command('review-packet','status',1,'--issue',2))
        self.assertEqual(recovered['rounds'],1)
        record=json.loads(self.fx.ledger.read_text())['reuses'][0]
        self.passed(self.fx.guard('--reuse',record['comment_id']))
        self.assertEqual(len(self.fx.state()['comments']),2)

    def test_unknown_pending_reuse_blocks_without_retry(self):
        self.fx.anchor();self.fx.replay()
        state=self.fx.state();state['mutation_fault']={'method':'POST','outcome':'unknown'};self.fx.save(state)
        self.refused(self.fx.reuse('replay',{}))
        self.refused(self.fx.command('review-packet','status',1,'--issue',2))
        self.refused(self.fx.reuse('replay',{}));self.refused(self.fx.start())
        self.assertEqual(len(self.fx.state()['comments']),1)
        self.assertIn('pending',json.loads(self.fx.ledger.read_text()))

    def test_native_lost_response_recovers_issue_target_and_duplicate_refuses(self):
        started=self.passed(self.fx.start());path=self.fx.root/'observation';path.write_bytes(b'actual return')
        state=self.fx.state();state['mutation_fault']={'method':'POST','outcome':'lost-response'};self.fx.save(state)
        self.refused(self.fx.command('review-packet','record-native',1,'--issue',2,'--attempt',started['comment_id'],
                                    '--native-handle','native-id','--observation',path))
        self.passed(self.fx.command('review-packet','status',1,'--issue',2))
        ledger=json.loads(self.fx.ledger.read_text());self.assertIn('native_record',ledger['attempts'][0])
        self.refused(self.fx.command('review-packet','record-native',1,'--issue',2,'--attempt',started['comment_id'],
                                    '--native-handle','native-id','--observation',path))
        self.assertEqual(len(self.fx.state()['issue_comments']),1)

    def test_exact_ci_and_current_pin_races_still_block_reuse(self):
        self.fx.anchor();self.fx.replay();proof=self.passed(self.fx.reuse('replay',{}));valid=self.fx.state()
        for change in ('ci-app','ci-failed','ci-missing','ci-other-failed','head-race','base','head'):
            with self.subTest(change=change):
                state=json.loads(json.dumps(valid))
                if change=='ci-app': state['checks'][0]['app']['id']=9
                elif change=='ci-failed': state['checks'][0]['conclusion']='failure'
                elif change=='ci-missing': state['checks']=[]
                elif change=='ci-other-failed': state['checks'].append({'id':2,'name':'failed','status':'completed','conclusion':'failure','app':{'id':15368}})
                elif change=='head-race': state['race']=state['pr_reads']+1
                elif change=='base': state['pr']['base']['sha']=self.fx.old_base
                else: state['pr']['head']['sha']=self.fx.old_head
                self.fx.save(state);self.refused(self.fx.guard('--reuse',proof['comment_id'],'--execute'))
        self.fx.save(valid);self.passed(self.fx.guard('--reuse',proof['comment_id']))

    def test_lock_blocks_publication_and_guard(self):
        self.fx.anchor();self.fx.replay()
        path=self.fx.ledger.with_suffix('.lock')
        with path.open('rb') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.refused(self.fx.reuse('replay',{}));self.refused(self.fx.guard('--execute'))

    def test_no_receipt_or_failing_goal_cannot_reuse_same_head(self):
        raw=self.fx.verdict(goal='No').replace('None.\n',block({'artifact':'pr-description'}))
        self.passed(self.fx.publish(raw));self.fx.original=self.fx.state()['comments'][-1]['id']
        self.fx.old_base,self.fx.old_head=self.fx.base,self.fx.head
        state=self.fx.state();state['description']='corrected\n';self.fx.save(state)
        self.refused(self.fx.reuse('external',{'artifact':'pr-description','fence_offset':raw.encode().index(b'```replacement')}))
        self.passed(self.fx.start())

    def test_post_publication_context_race_does_not_report_success(self):
        self.fx.anchor();self.fx.replay()
        state=self.fx.state();state['context_change_on_post']=True;self.fx.save(state)
        self.refused(self.fx.reuse('replay',{}))
        self.assertEqual(len(self.fx.state()['comments']),2)
        self.refused(self.fx.guard('--execute'))

    def test_guard_rechecks_request_bundle_instruction_and_context_after_ci(self):
        self.fx.anchor();self.fx.replay();proof=self.passed(self.fx.reuse('replay',{}))
        ledger=json.loads(self.fx.ledger.read_text());record=ledger['reuses'][0];attempt=ledger['attempts'][0]
        valid=self.fx.state()
        for path in (record['request_path'],record['bundle_path'],attempt['native_instruction']):
            with self.subTest(path=path):
                target=Path(path);original=target.read_bytes()
                state=json.loads(json.dumps(valid));state['drift_file_on_check']=path;self.fx.save(state)
                self.refused(self.fx.guard('--reuse',proof['comment_id'],'--execute'))
                target.write_bytes(original)
        state=json.loads(json.dumps(valid));state['context_race']=state['pr_reads']+2;self.fx.save(state)
        self.refused(self.fx.guard('--reuse',proof['comment_id'],'--execute'))

    def test_version_exemption_must_exceed_the_actual_replay_version(self):
        self.fx.version_history();self.fx.anchor()
        # Conflict resolution leaves the replay at base's 0.3.0. The proposed
        # head must carry its own strictly greater synchronized bump.
        self.fx.version_replay('0.3.0')
        self.refused(self.fx.reuse('replay',{}))

    def test_native_ledger_association_cannot_allow_a_forged_issue_record(self):
        started=self.passed(self.fx.start());path=self.fx.root/'observation';path.write_bytes(b'actual return')
        self.passed(self.fx.command('review-packet','record-native',1,'--issue',2,'--attempt',started['comment_id'],
                                   '--native-handle','actual','--observation',path))
        verdict=self.fx.root/'verdict.md';verdict.write_text(self.fx.verdict())
        self.passed(self.fx.command('review-packet','publish',1,'--issue',2,'--attempt',started['comment_id'],'--verdict',verdict))
        ledger=json.loads(self.fx.ledger.read_text());record=ledger['attempts'][0]['native_record']
        record['attempt_id']+=1
        self.fx.ledger.write_text(json.dumps(ledger))
        self.refused(self.fx.guard('--execute'))

    def test_raw_note_rejects_quoted_duplicate_nested_unclosed_and_unsupported_grammar(self):
        valid=block({'target':'code.txt','start':0,'end':10})
        variants={'duplicate':valid+valid,
                  'quoted':''.join('> '+line for line in valid.splitlines(keepends=True)),
                  'example':'~~~~text\n'+valid+'~~~~\n',
                  'nested':valid.replace('corrected\n','~~~replacement\nnested\n~~~\n'),
                  'unclosed':valid.replace('\n```\n','\n````\n'),
                  'extra-prose':valid.replace('```replacement\n','between\n```replacement\n'),
                  'crlf-wrapper':valid.replace(' -->\n',' -->\r\n'),
                  'metadata-key':valid.replace('"end":10','"end":10,"other":true'),
                  'duplicate-key':valid.replace('"end":10','"end":10,"end":10'),
                  'alternative':valid.replace('```replacement','```example'),
                  'marker-content':valid.replace('corrected\n','<!-- codex-method-note-v1 -->\n'),
                  'after-section':'#### Another section\n'+valid}
        for name,note_text in variants.items():
            with self.subTest(name=name):
                fx=ReuseFixture();self.addCleanup(fx.close)
                raw=fx.anchor(note_text);fx.correction(b'corrected\n')
                request={'target':'code.txt','start':0,'end':10,'fence_offset':max(0,raw.encode().find(b'```'))}
                result=fx.reuse('note',request)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertFalse(json.loads(fx.ledger.read_text()).get('reuses'))
                fx.close()

    def test_invalid_nonmonotonic_unsynchronized_or_nonvalue_descriptor_changes_refuse(self):
        self.fx.version_history();self.fx.anchor();self.fx.version_replay()
        valid=self.fx.head
        for mutation in ('backwards','leading-zero','unsynchronized','json-field','duplicate-json','delete','symlink','mode'):
            with self.subTest(mutation=mutation):
                self.fx.git('checkout','--detach',valid)
                path=self.fx.project/'codex-method.json'
                if mutation=='backwards': self.fx.versions('0.1.0')
                elif mutation=='leading-zero': self.fx.versions('0.04.0')
                elif mutation=='unsynchronized': path.write_text(path.read_text().replace('0.4.0','0.4.1'))
                elif mutation=='json-field': path.write_text(path.read_text().replace('true','false'))
                elif mutation=='duplicate-json': path.write_text(path.read_text().replace('"unchanged": true','"version":"0.4.0", "unchanged": true'))
                elif mutation=='delete': path.unlink()
                elif mutation=='symlink': path.unlink();path.symlink_to('code.txt')
                else: path.chmod(0o755)
                self.fx.git('add','-A');self.fx.git('commit','-m',mutation)
                self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
                self.refused(self.fx.reuse('replay',{}))

    def test_conflicting_replay_merge_commit_gitlink_and_wrong_parent_refuse(self):
        self.fx.anchor()
        self.fx.git('checkout','--detach',self.fx.old_base)
        (self.fx.project/'code.txt').write_text('conflicting main\n')
        self.fx.git('commit','-am','conflicting main');base=self.fx.git('rev-parse','HEAD').strip()
        (self.fx.project/'code.txt').write_text('base\nhead\n')
        self.fx.git('commit','-am','equal reviewed bytes but conflict resolution')
        self.fx.pin(base,self.fx.git('rev-parse','HEAD').strip())
        self.refused(self.fx.reuse('replay',{}))
        self.fx.git('checkout','--detach',self.fx.old_head);self.fx.replay()
        valid=self.fx.head
        self.fx.git('update-index','--add','--cacheinfo',f'160000,{self.fx.old_head},submodule')
        self.fx.git('commit','-m','gitlink');self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
        self.refused(self.fx.reuse('replay',{}))
        self.fx.git('checkout','--detach',valid)
        self.fx.git('merge','--no-ff','--no-edit',self.fx.old_head)
        self.fx.pin(head=self.fx.git('rev-parse','HEAD').strip())
        self.refused(self.fx.reuse('replay',{}))

    def test_legacy_keeps_only_exact_head_route_and_explicit_intact_refresh(self):
        self.fx.anchor()
        self.fx.legacy_receipt()
        state=self.fx.state();state['description']='changed legacy context';self.fx.save(state)
        self.passed(self.fx.guard())
        self.refused(self.fx.reuse('external',{'artifact':'pr-description','fence_offset':0}))
        self.refused(self.fx.start())
        result=self.fx.command('review-packet','start',1,'--issue',2,'--architecture-level','yes',
                               '--output',self.fx.output,'--host-version','0.160.0',
                               '--refresh-context','--attempt',self.fx.original)
        self.passed(result)
        self.assertEqual(len(json.loads(self.fx.ledger.read_text())['attempts']),2)

    def test_new_attempt_invalidates_prior_external_proof_selection(self):
        raw=self.fx.anchor(block({'artifact':'pr-description'}))
        state=self.fx.state();state['description']='corrected\n';self.fx.save(state)
        proof=self.passed(self.fx.reuse('external',{'artifact':'pr-description','fence_offset':raw.encode().index(b'```replacement')}))
        state=self.fx.state();state['title']='new substantive context';self.fx.save(state)
        started=self.passed(self.fx.start())
        self.refused(self.fx.guard('--reuse',proof['comment_id']))
        verdict=self.fx.root/'fresh.md';verdict.write_text(self.fx.verdict())
        self.passed(self.fx.command('review-packet','publish',1,'--issue',2,'--attempt',started['comment_id'],'--verdict',verdict))
        self.refused(self.fx.guard('--reuse',proof['comment_id']));self.passed(self.fx.guard())

    def test_pending_proof_crash_and_duplicate_or_edited_recovery_refuse(self):
        self.fx.anchor();self.fx.replay()
        state=self.fx.state();state['mutation_fault']={'method':'POST','outcome':'crash'};self.fx.save(state)
        self.refused(self.fx.reuse('replay',{}));valid=self.fx.state()
        for mutation in ('duplicate','body','author'):
            with self.subTest(mutation=mutation):
                state=json.loads(json.dumps(valid))
                if mutation=='duplicate': state['comments'].append(state['comments'][-1])
                elif mutation=='body': state['comments'][-1]['body']+='edited'
                else: state['comments'][-1]['user']['login']='other'
                self.fx.save(state);self.refused(self.fx.command('review-packet','status',1,'--issue',2))
                self.assertIn('pending',json.loads(self.fx.ledger.read_text()))
        self.fx.save(valid);self.passed(self.fx.command('review-packet','status',1,'--issue',2))

    def test_wrong_origin_repository_and_evidence_receipt_binding_refuse(self):
        self.fx.anchor();self.fx.replay()
        original_origin=self.fx.git('remote','get-url','origin').strip()
        self.fx.git('remote','set-url','origin','https://github.com/other/repo.git')
        self.refused(self.fx.reuse('replay',{}));self.fx.git('remote','set-url','origin',original_origin)
        ledger=json.loads(self.fx.ledger.read_text());valid=json.dumps(ledger)
        for key in ('packet_sha256','native_instruction_sha256','verdict_sha256','comment_sha256','context_sha256'):
            with self.subTest(key=key):
                changed=json.loads(valid);changed['attempts'][0][key]='0'*64
                self.fx.ledger.write_text(json.dumps(changed));self.refused(self.fx.reuse('replay',{}))
        self.fx.ledger.write_text(valid)

    def test_partial_context_receipt_cannot_silently_downgrade_to_legacy(self):
        self.fx.anchor();original=self.fx.ledger.read_text()
        for value in (None,{},[]):
            with self.subTest(value=value):
                ledger=json.loads(original);ledger['attempts'][0]['context']=value
                self.fx.ledger.write_text(json.dumps(ledger));self.refused(self.fx.guard('--execute'))

    def test_empty_pr_description_keeps_ordinary_review_available(self):
        state=self.fx.state();state['description']=None;self.fx.save(state)
        self.fx.anchor();self.passed(self.fx.guard())

    def test_published_proof_exposes_exact_request_locator_alongside_hashes(self):
        raw=self.fx.anchor(block({'target':'code.txt','start':0,'end':10}));self.fx.correction(b'corrected\n')
        request={'target':'code.txt','start':0,'end':10,'fence_offset':raw.encode().index(b'```replacement')}
        self.passed(self.fx.reuse('note',request))
        body=self.fx.state()['comments'][-1]['body']
        payload=json.loads(body.split('\n\n',1)[1])
        self.assertEqual(payload.get('request'),request)

    def test_reviewed_locator_offsets_are_exact_integers_too(self):
        for value in (False,0.0):
            with self.subTest(value=value):
                fx=ReuseFixture();self.addCleanup(fx.close)
                raw=fx.anchor(block({'target':'code.txt','start':value,'end':10}));fx.correction(b'corrected\n')
                result=fx.reuse('note',{'target':'code.txt','start':0,'end':10,
                                       'fence_offset':raw.encode().index(b'```replacement')})
                self.assertNotEqual(result.returncode,0,result.stdout)
                fx.close()
