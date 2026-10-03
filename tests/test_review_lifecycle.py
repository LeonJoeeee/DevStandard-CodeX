"""Run reservation → publication → status → guard, not isolated parsing helpers.

Deleting consumer validation, association or head pinning must turn a refusal into
an observable merge admission and fail these tests.
"""
import json
import unittest
from tests.github_fixture import GitHubFixture


class ReviewLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.fx = GitHubFixture()
        self.addCleanup(self.fx.close)

    def test_published_favorable_verdict_reaches_guard(self):
        published = self.fx.publish()
        self.assertEqual(published.returncode, 0, published.stderr)
        guarded = self.fx.guard('--execute')
        self.assertEqual(guarded.returncode, 0, guarded.stderr)
        merge = self.fx.state()['merged']
        self.assertIn('--match-head-commit', merge)
        self.assertIn(self.fx.head, merge)

    def test_status_does_not_call_a_reservation_accepted(self):
        started = self.fx.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        status = self.fx.command('review-packet', 'status', 1, '--issue', 2)
        self.assertEqual(status.returncode, 0, status.stderr)
        data = json.loads(status.stdout)
        self.assertEqual(data['rounds'], 0)
        self.assertEqual(data['next'], 'awaiting-verdict')
        self.assertNotEqual(self.fx.guard().returncode, 0)

    def test_raw_forged_marker_is_not_a_published_attempt(self):
        state = self.fx.state()
        state['comments'].append({'id':9, 'user':{'login':'owner'},
                                  'body':self.fx.verdict()+'<!-- codex-method-review-v1 -->'})
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)
        self.assertNotIn('merged', self.fx.state())

    def test_no_and_failed_floors_are_recorded_but_never_admitted(self):
        for decision in [('No','Pass','Pass'), ('Yes','Fail','Pass'), ('Yes','Pass','Fail')]:
            with self.subTest(decision=decision):
                fixture = GitHubFixture()
                self.addCleanup(fixture.close)
                result=fixture.publish(fixture.verdict(*decision))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotEqual(fixture.guard('--execute').returncode, 0)
                status=fixture.command('review-packet','status',1,'--issue',2)
                self.assertEqual(json.loads(status.stdout)['rounds'], 1)
                self.assertNotIn('merged', fixture.state())

    def test_wrong_head_and_duplicate_decisions_burn_invalid_return(self):
        variants = [self.fx.verdict().replace(self.fx.head, 'b'*40),
                    self.fx.verdict().replace('### Notes',
                                              'Ready to merge: No — duplicate.\n### Notes')]
        for text in variants:
            with self.subTest(text=text):
                fixture=GitHubFixture()
                self.addCleanup(fixture.close)
                # Match the new fixture's head, except in the deliberate wrong-head variant.
                text=text.replace(self.fx.head, fixture.head)
                published=fixture.publish(text)
                self.assertEqual(published.returncode, 0, published.stderr)
                status=fixture.command('review-packet','status',1,'--issue',2)
                data=json.loads(status.stdout)
                self.assertEqual(data['rounds'], 1)
                self.assertEqual(data['next'], 'invalid-verdict')
                self.assertNotEqual(fixture.guard('--execute').returncode, 0)

    def test_malformed_output_cannot_hide_floor_two_failure(self):
        verdict=self.fx.verdict(floor2='Fail').replace(self.fx.head, 'b'*40)
        published=self.fx.publish(verdict)
        self.assertEqual(published.returncode,0,published.stderr)
        status=self.fx.command('review-packet','status',1,'--issue',2)
        self.assertEqual(json.loads(status.stdout)['next'],'human-direction')
        restarted=self.fx.start()
        self.assertNotEqual(restarted.returncode,0)
        self.assertIn('Floor 2 stopped this lane',restarted.stderr)
        self.assertEqual(len(self.fx.state()['comments']),1)

    def test_conflicting_duplicate_floor_two_cannot_hide_failure(self):
        verdict=self.fx.verdict().replace('### Notes',
            '2. Authorization and scope: Fail — conflicting returned decision.\n### Notes')
        self.assertEqual(self.fx.publish(verdict).returncode,0)
        self.assertNotEqual(self.fx.start().returncode,0)
        self.assertEqual(len(self.fx.state()['comments']),1)

    def test_groundless_floor_two_fail_still_stops_the_lane(self):
        verdict=self.fx.verdict(floor2='Fail').replace(
            'Fail — authorized tree checked.', 'Fail')
        self.assertEqual(self.fx.publish(verdict).returncode,0)
        self.assertNotEqual(self.fx.start().returncode,0)
        self.assertEqual(len(self.fx.state()['comments']),1)

    def test_tampered_published_comment_is_refused(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state()
        state['comments'][-1]['body']=state['comments'][-1]['body'].replace(
            'evidence checked.', 'different evidence.')
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)

    def test_changed_comment_author_is_refused(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state()
        state['comments'][-1]['user']['login']='unrelated'
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)

    def test_head_move_after_publication_is_refused(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state()
        state['pr']['head']['sha']='b'*40
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)

    def test_failed_attempt_is_not_a_returned_round(self):
        started=self.fx.start()
        attempt=json.loads(started.stdout)['comment_id']
        failed=self.fx.command('review-packet','fail',1,'--issue',2,'--attempt',attempt,
                               '--reason','No reviewer was launched.')
        self.assertEqual(failed.returncode, 0, failed.stderr)
        status=self.fx.command('review-packet','status',1,'--issue',2)
        self.assertEqual(json.loads(status.stdout)['rounds'], 0)

    def test_pending_attempt_blocks_second_start(self):
        self.assertEqual(self.fx.start().returncode, 0)
        second=self.fx.start()
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_returned_verdict_cannot_be_reclassified_as_no_output(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        attempt=self.fx.state()['comments'][-1]['id']
        fail=self.fx.command('review-packet','fail',1,'--issue',2,'--attempt',attempt,
                             '--reason','Pretend no output.')
        self.assertNotEqual(fail.returncode, 0)

    def test_forged_integration_check_app_is_refused(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state()
        state['checks'][0]['app']={'id':9, 'slug':'unrelated-app'}
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)

    def test_behind_current_base_is_refused(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state();state['behind']=1;self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute').returncode, 0)

    def test_ci_fallback_cannot_be_enabled_by_an_arbitrary_comment(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        state=self.fx.state()
        state['checks']=[]
        url='https://github.com/owner/project/pull/1#issuecomment-999'
        state['comments'].append({'id':999,'user':{'login':'owner'},
                                  'body':'CI-FALLBACK <!-- codex-method-review-v1 --> '+url})
        self.fx.save(state)
        self.assertNotEqual(self.fx.guard('--execute','--ci-fallback',url).returncode, 0)
