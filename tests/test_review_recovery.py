"""Real CLI recovery across remote mutation, lost response and process death."""
import json
import unittest

from tests.github_fixture import GitHubFixture


class ReviewRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.fx = GitHubFixture()
        self.addCleanup(self.fx.close)

    def fault(self, method, outcome='lost-response'):
        state = self.fx.state()
        state['mutation_fault'] = {'method': method, 'outcome': outcome}
        self.fx.save(state)

    def status(self):
        return self.fx.command('review-packet', 'status', 1, '--issue', 2)

    def publish(self, attempt, text=None):
        path = self.fx.root / 'returned.md'
        path.write_bytes((text if text is not None else self.fx.verdict()).encode('utf-8'))
        return self.fx.command('review-packet', 'publish', 1, '--issue', 2,
                               '--attempt', attempt, '--verdict', path)

    def fail_no_output(self, attempt):
        return self.fx.command('review-packet', 'fail', 1, '--issue', 2,
                               '--attempt', attempt, '--reason', 'No output.')

    def mutations(self):
        return [a for a in self.fx.state()['calls'] if '-X' in a]

    def test_post_lost_response_retains_exact_intent_before_mutation_and_recovers_once(self):
        self.fault('POST')
        result = self.fx.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('status', result.stderr)
        self.assertTrue(self.fx.ledger.exists(), 'reservation intent must survive response loss')
        state = self.fx.state()
        before = state['boundary_ledgers'][-1]
        self.assertEqual(before['pending']['body'], state['comments'][0]['body'])
        self.assertEqual(before['pending']['attempt']['token'],
                         json.loads(state['comments'][0]['body'].split('\n')[1].split(' ', 2)[2][:-4])['token'])
        count = len(self.mutations())
        recovered = self.status()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        data = json.loads(recovered.stdout)
        self.assertEqual((data['rounds'], data['next']), (0, 'awaiting-verdict'))
        self.assertIn('--attempt 100', data['next_command'])
        self.assertEqual(self.status().returncode, 0)
        self.assertNotEqual(self.fx.start().returncode, 0)
        self.assertEqual(len(self.mutations()), count)
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_unknown_post_blocks_second_reservation_and_reviewer_handoff(self):
        self.fault('POST', 'unknown')
        self.assertNotEqual(self.fx.start().returncode, 0)
        count = len(self.mutations())
        again = self.fx.start()
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('pending', again.stderr)
        self.assertIn('do not', again.stderr.lower())
        result = self.status()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip(), 'uncertain reservation must return no native handoff')
        self.assertEqual(len(self.mutations()), count)

    def test_post_process_death_leaves_recoverable_intent_without_stale_lock(self):
        self.fault('POST', 'crash')
        self.assertNotEqual(self.fx.start().returncode, 0)
        self.assertTrue(self.fx.ledger.exists())
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rounds'], 0)
        self.assertNotEqual(self.fx.start().returncode, 0)
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_empty_mutation_response_retains_intent_and_prints_recovery_directions(self):
        for method in ('POST', 'PATCH'):
            with self.subTest(method=method):
                self.fx.close()
                self.fx = GitHubFixture()
                self.addCleanup(self.fx.close)
                if method == 'PATCH':
                    self.assertEqual(self.fx.start().returncode, 0)
                self.fault(method, 'empty-response')
                result = self.fx.start() if method == 'POST' else self.publish(100)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('pending intent retained', result.stderr)
                self.assertIn('review-packet status 1 --issue 2', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(self.status().returncode, 0)

    def test_patch_lost_response_recovers_exact_raw_verdict_and_previous_receipt(self):
        started = self.fx.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        attempt = json.loads(started.stdout)['comment_id']
        previous = json.loads(self.fx.ledger.read_text())['attempts'][0]
        raw = self.fx.verdict() + '\nUnedited Notes: café — full bytes.\r\n'
        self.fault('PATCH')
        result = self.publish(attempt, raw)
        self.assertNotEqual(result.returncode, 0)
        state = self.fx.state()
        self.assertIn('pending', state['boundary_ledgers'][-1])
        pending = state['boundary_ledgers'][-1]['pending']
        self.assertEqual(pending['previous'], previous)
        self.assertTrue(pending['body'].endswith(raw))
        self.assertEqual(pending['body'], state['comments'][0]['body'])
        count = len(self.mutations())
        (self.fx.root / 'returned.md').write_text('changed after response loss')
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rounds'], 1)
        self.assertEqual(json.loads(result.stdout)['next'], 'accepted')
        self.assertEqual(self.fx.guard().returncode, 0)
        self.assertNotEqual(self.publish(attempt, self.fx.verdict(goal='No')).returncode, 0)
        self.assertNotEqual(self.fail_no_output(attempt).returncode, 0)
        self.assertNotEqual(self.fx.start().returncode, 0)
        self.assertEqual(len(self.mutations()), count)
        self.assertTrue(self.fx.state()['comments'][0]['body'].endswith(raw))

    def test_unknown_patch_cannot_erase_a_possibly_returned_verdict(self):
        self.assertEqual(self.fx.start().returncode, 0)
        self.fault('PATCH', 'unknown')
        self.assertNotEqual(self.publish(100).returncode, 0)
        self.assertTrue(self.fx.ledger.exists())
        ledger = json.loads(self.fx.ledger.read_text())
        self.assertIn('pending', ledger)
        self.assertTrue(ledger['pending']['body'].endswith(self.fx.verdict()))
        count = len(self.mutations())
        for result in [self.status(), self.fail_no_output(100), self.publish(100, 'substitute'), self.fx.start()]:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pending', result.stderr)
        self.assertEqual(len(self.mutations()), count)
        self.assertEqual(json.loads(self.fx.ledger.read_text())['pending'], ledger['pending'])

    def test_patch_process_death_recovers_without_another_round_or_patch(self):
        self.assertEqual(self.fx.start().returncode, 0)
        self.fault('PATCH', 'crash')
        self.assertNotEqual(self.publish(100).returncode, 0)
        count = len(self.mutations())
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rounds'], 1)
        self.assertEqual(self.fx.guard().returncode, 0)
        self.assertEqual(len(self.mutations()), count)

    def test_failed_no_output_patch_loss_recovers_without_burning_a_round(self):
        self.assertEqual(self.fx.start().returncode, 0)
        self.fault('PATCH')
        self.assertNotEqual(self.fail_no_output(100).returncode, 0)
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((json.loads(result.stdout)['rounds'], json.loads(result.stdout)['next']),
                         (0, 'awaiting-review'))
        self.assertEqual(self.fx.start().returncode, 0)

    def test_pending_recovery_refuses_missing_ambiguous_tampered_author_or_id(self):
        for method in ('POST', 'PATCH'):
            for change in ('missing', 'duplicate', 'body', 'author', 'metadata', 'id'):
                if method == 'POST' and change == 'id':
                    continue  # A POST has no remote id until its exact response is recovered.
                with self.subTest(method=method, change=change):
                    self.fx.close()
                    self.fx = GitHubFixture()
                    self.addCleanup(self.fx.close)
                    if method == 'PATCH':
                        self.assertEqual(self.fx.start().returncode, 0)
                    self.fault(method)
                    failed = self.fx.start() if method == 'POST' else self.publish(100)
                    self.assertNotEqual(failed.returncode, 0)
                    state = self.fx.state()
                    comment = state['comments'][0]
                    if change == 'missing': state['comments'] = []
                    elif change == 'duplicate': state['comments'].append(dict(comment))
                    elif change == 'body': comment['body'] += 'tampered'
                    elif change == 'author': comment['user']['login'] = 'unrelated'
                    elif change == 'metadata': comment['body'] = comment['body'].replace(self.fx.head, 'b'*40, 1)
                    elif change == 'id': comment['id'] = 999
                    self.fx.save(state)
                    count = len(self.mutations())
                    self.assertNotEqual(self.status().returncode, 0)
                    self.assertNotEqual(self.fx.guard().returncode, 0)
                    self.assertNotEqual(self.fx.start().returncode, 0)
                    self.assertEqual(len(self.mutations()), count)

    def test_missing_ledger_never_authenticates_even_exact_remote_marker(self):
        self.assertEqual(self.fx.publish().returncode, 0)
        self.fx.ledger.unlink()
        self.assertNotEqual(self.fx.guard().returncode, 0)
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rounds'], 0)

    def test_recovered_malformed_floor_two_fail_always_stops_the_lane(self):
        for change in ('head', 'grounds', 'duplicate'):
            with self.subTest(change=change):
                self.fx.close()
                self.fx = GitHubFixture()
                self.addCleanup(self.fx.close)
                self.assertEqual(self.fx.start().returncode, 0)
                verdict = self.fx.verdict(floor2='Fail')
                if change == 'head': verdict = verdict.replace(self.fx.head, 'b'*40)
                elif change == 'grounds': verdict = verdict.replace('Fail — authorized tree checked.', 'Fail')
                else: verdict = self.fx.verdict().replace('### Notes',
                    '2. Authorization and scope: Fail\n### Notes')
                self.fault('PATCH')
                self.assertNotEqual(self.publish(100, verdict).returncode, 0)
                result = self.status()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((json.loads(result.stdout)['rounds'], json.loads(result.stdout)['next']),
                                 (1, 'human-direction'))
                restarted = self.fx.start()
                self.assertNotEqual(restarted.returncode, 0)
                self.assertIn('Floor 2 stopped this lane', restarted.stderr)
                self.assertEqual(len(self.fx.state()['comments']), 1)
