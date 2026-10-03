"""Assembler consumers must capture pinned evidence and name what is missing."""
import json
import unittest
from tests.github_fixture import GitHubFixture


class PacketEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.fx=GitHubFixture()
        self.addCleanup(self.fx.close)

    def test_three_successful_diff_captures_are_in_the_actual_packet(self):
        result=self.fx.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        packet=(self.fx.output / 'packet.md').read_text()
        self.assertIn('## Pinned diff captures',packet)
        self.assertIn('--name-status',packet)
        self.assertIn('--stat',packet)
        self.assertIn('+head',packet)
        self.assertIn('"exit": 0',packet)

    def test_missing_past_status_is_disclosed_not_replaced_by_clean_now(self):
        self.assertEqual(self.fx.start().returncode,0)
        packet=(self.fx.output / 'packet.md').read_text()
        self.assertIn('pre-write worktree status: not supplied',packet)
        self.assertIn('delivery worktree status: not supplied',packet)

    def test_supplied_status_captures_travel_unchanged(self):
        before=self.fx.root / 'before.json';after=self.fx.root / 'after.json'
        before.write_text('{"status":" M existing.txt","kind":"actual pre-write"}')
        after.write_text('{"status":"","kind":"actual delivery"}')
        result=self.fx.command('review-packet','assemble',1,'--issue',2,
                               '--architecture-level','yes','--output',self.fx.output,
                               '--pre-write-status',before,'--delivery-status',after)
        self.assertEqual(result.returncode,0,result.stderr)
        packet=json.loads((self.fx.output / 'packet.json').read_text())
        self.assertFalse(any('worktree status' in gap for gap in packet['integrity_gaps']))
        text=(self.fx.output / 'packet.md').read_text()
        self.assertIn('actual pre-write',text)
        self.assertIn(' M existing.txt',text)
        self.assertIn('actual delivery',text)

    def test_description_race_refuses_the_packet(self):
        state=self.fx.state();state['race']=0;self.fx.save(state)
        # Fake API races are used by guard; force an assembly race at the PR-view seam.
        fake=self.fx.root / 'bin/gh'
        original=fake.read_text()
        fake.write_text(original.replace("if a[:2] == ['pr', 'view']:\n    r=s['pr'];out(",
                                        "if a[:2] == ['pr', 'view']:\n    s['views']=s.get('views',0)+1\n    if s['views']>1: s['description']='Changed during assembly'\n    r=s['pr'];out("))
        result=self.fx.start()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('moved while assembling',result.stderr)
        self.assertFalse(self.fx.state()['comments'])

    def test_assembler_carries_whole_prior_pr_comments_without_authenticating_them(self):
        # A genuine unfavorable review and arbitrary lookalike both travel as history.
        self.assertEqual(self.fx.publish(self.fx.verdict(goal='No')).returncode, 0)
        state = self.fx.state()
        state['comments'].append({'id': 998, 'user': {'login': 'visitor'},
                                  'body': 'Repeated finding: missing test.\n' + self.fx.verdict(),
                                  'created_at': '2026-10-01T12:00:00Z'})
        state['issue_comments'] = [{'id': 999, 'user': {'login': 'owner'},
                                     'body': 'Issue direction: keep original bounds.'}]
        self.fx.save(state)
        result = self.fx.command('review-packet', 'assemble', 1, '--issue', 2,
                                 '--architecture-level', 'yes', '--output', self.fx.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((self.fx.output / 'packet.json').read_text())
        self.assertEqual(packet.get('pr_comments'), state['comments'])
        text = (self.fx.output / 'packet.md').read_text()
        self.assertIn('## Ordered PR comments', text)
        history = json.loads(text.split('## Ordered PR comments', 1)[1].split('\n', 1)[1]
                             .split('\n\n## ', 1)[0])
        self.assertEqual(history, state['comments'])
        self.assertIn('Issue direction: keep original bounds.', text)
        self.assertNotEqual(self.fx.guard().returncode, 0)

    def test_assembler_includes_pending_reservation_as_whole_pr_history(self):
        self.assertEqual(self.fx.start().returncode, 0)
        state = self.fx.state()
        result = self.fx.command('review-packet', 'assemble', 1, '--issue', 2,
                                 '--architecture-level', 'yes', '--output', self.fx.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((self.fx.output / 'packet.json').read_text())
        self.assertEqual(packet.get('pr_comments'), state['comments'])
        self.assertIn('Reviewer reserved;', (self.fx.output / 'packet.md').read_text())
        self.assertNotEqual(self.fx.guard().returncode, 0)

    def test_unknown_convention_base_stays_unpinned_with_accepted_spec_and_missing_history(self):
        blob = self.fx.git('hash-object', '-w', 'code.txt').strip()
        result = self.fx.command('review-packet', 'assemble', 1, '--issue', 2,
                                 '--architecture-level', 'yes', '--output', self.fx.output,
                                 '--accepted-spec', blob)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((self.fx.output / 'packet.json').read_text())
        self.assertEqual(packet['slots']['CONVENTION_BASE_SHA'], 'NOT PINNED')
        self.assertEqual(packet['slots']['ACCEPTED_SPEC_BLOB_SHA'], blob)
        self.assertEqual(packet['accepted_spec_contents'], 'base\nhead\n')
        text = (self.fx.output / 'packet.md').read_text()
        self.assertIn('CONVENTION_BASE_SHA: NOT PINNED', text)
        self.assertIn('pre-write worktree status: not supplied', text)
        self.assertIn('delivery worktree status: not supplied', text)

    def test_explicit_convention_base_is_pinned_independently_of_pr_base(self):
        result = self.fx.command('review-packet', 'assemble', 1, '--issue', 2,
                                 '--architecture-level', 'yes', '--output', self.fx.output,
                                 '--convention-base', self.fx.head)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((self.fx.output / 'packet.json').read_text())
        self.assertEqual(packet['slots']['CONVENTION_BASE_SHA'], self.fx.head)
        self.assertEqual(packet['slots']['REVIEW_BASE_SHA'], self.fx.base)
