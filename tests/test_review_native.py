"""The actual review-start consumer prepares a fresh native call, never an executor."""
import json
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

from tests.github_fixture import GitHubFixture, ROOT
from scripts.review_packet import render


class ReviewNativeTest(unittest.TestCase):
    def setUp(self):
        self.fx = GitHubFixture()
        self.addCleanup(self.fx.close)
        installed = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                                    str(self.fx.project), '--host-version', '0.160.0'],
                                   capture_output=True, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)

    def start(self, *args):
        return self.fx.command('review-packet', 'start', 1, '--issue', 2,
                               '--architecture-level', 'yes', '--output', self.fx.output,
                               '--host-version', '0.160.0', *args)

    def test_start_returns_the_complete_native_request_with_exact_fresh_role_and_pins(self):
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn('instruction', data, 'a brief alone is not a native invocation')
        request = json.loads(Path(data['instruction']).read_text())
        self.assertEqual(set(request), {'task_name', 'message', 'agent_type', 'fork_turns',
                                       'model', 'reasoning_effort'})
        self.assertEqual(request['agent_type'], 'method_reviewer')
        self.assertEqual(request['fork_turns'], 'none')
        self.assertEqual((request['model'], request['reasoning_effort']), ('gpt-6.1-sol', 'high'))
        packet = Path(data['packet'])
        saved = json.loads((self.fx.output / 'packet.json').read_text())
        self.assertIn(render(saved, data['identity']), request['message'])
        self.assertIn(self.fx.head, request['message'])
        self.assertIn(self.fx.base, request['message'])
        self.assertIn(str(packet.resolve()), request['message'])
        self.assertIn(hashlib.sha256(packet.read_bytes()).hexdigest(), request['message'])
        self.assertNotIn((ROOT / 'reference/code-review-prompt.md').read_text(), request['message'])
        self.assertNotIn(packet.read_text(), request['message'])
        self.assertIn('before and after', request['message'])
        self.assertIn('Floor 1 FAIL', request['message'])
        self.assertIn('numbered chunks', request['message'])
        attempt = json.loads(self.fx.ledger.read_text())['attempts'][-1]
        self.assertEqual(attempt['packet_carrier'], 'file-sha256-v1')
        self.assertEqual(attempt['packet_sha256'], hashlib.sha256(packet.read_bytes()).hexdigest())
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_large_evidence_remains_complete_without_growing_native_message(self):
        state = self.fx.state()
        marker = 'FULL_HISTORICAL_COMMENT_SENTINEL_' + 'x' * 240000
        state['issue_comments'] = [{'id': 7, 'body': marker, 'user': {'login': 'owner'}}]
        self.fx.save(state)
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        request = json.loads(Path(data['instruction']).read_text())
        self.assertIn(marker, Path(data['packet']).read_text())
        self.assertNotIn(marker, request['message'])
        self.assertLess(len(request['message']), 40000)

    def test_new_bundle_missing_or_drift_refuses_before_returning_reserved_call(self):
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        path = Path(data['packet'])
        original = path.read_bytes()
        for mutation in ('missing', 'drift', 'newline'):
            with self.subTest(mutation=mutation):
                if mutation == 'missing':
                    path.unlink()
                elif mutation == 'newline':
                    path.write_bytes(original.replace(b'\n', b'\r\n'))
                else:
                    path.write_bytes(original + b'changed')
                result = self.fx.command('review-packet', 'status', 1, '--issue', 2)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('evidence bundle', result.stderr)
                self.assertEqual(len(self.fx.state()['comments']), 1)
                path.write_bytes(original)
                # Status recovers the same reservation; do not allocate a second attempt.
                result = self.fx.command('review-packet', 'status', 1, '--issue', 2)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_returned_ready_bundle_drift_blocks_status_and_real_guard_then_recovers(self):
        started = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        data = json.loads(started.stdout)
        bundle = Path(data['packet'])
        original = bundle.read_bytes()
        verdict = self.fx.root / 'verdict.md'
        verdict.write_text(self.fx.verdict())
        published = self.fx.command('review-packet', 'publish', 1, '--issue', 2,
                                    '--attempt', data['comment_id'], '--verdict', verdict)
        self.assertEqual(published.returncode, 0, published.stderr)
        for mutation in ('missing', 'drift', 'newline'):
            with self.subTest(mutation=mutation):
                if mutation == 'missing':
                    bundle.unlink()
                else:
                    bundle.write_bytes(original + b'drift' if mutation == 'drift'
                                       else original.replace(b'\n', b'\r\n'))
                status = self.fx.command('review-packet', 'status', 1, '--issue', 2)
                guard = self.fx.guard()
                for result in (status, guard):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('evidence bundle', result.stderr)
                bundle.write_bytes(original)
                self.assertEqual(self.fx.guard().returncode, 0)
                restored = self.fx.command('review-packet', 'status', 1, '--issue', 2)
                self.assertEqual(json.loads(restored.stdout)['next'], 'accepted')
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_historical_inline_receipt_has_no_file_carrier_retrofit(self):
        started = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        data = json.loads(started.stdout)
        ledger = json.loads(self.fx.ledger.read_text())
        ledger['attempts'][-1].pop('packet_carrier')
        self.fx.ledger.write_text(json.dumps(ledger))
        Path(data['packet']).unlink()
        verdict = self.fx.root / 'verdict.md'
        verdict.write_text(self.fx.verdict())
        published = self.fx.command('review-packet', 'publish', 1, '--issue', 2,
                                    '--attempt', data['comment_id'], '--verdict', verdict)
        self.assertEqual(published.returncode, 0, published.stderr)
        status = self.fx.command('review-packet', 'status', 1, '--issue', 2)
        self.assertEqual(json.loads(status.stdout)['next'], 'accepted')
        self.assertEqual(self.fx.guard().returncode, 0)

    def test_missing_bundle_does_not_block_whole_floor1_fail_publication(self):
        started = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        data = json.loads(started.stdout)
        Path(data['packet']).unlink()
        raw = self.fx.verdict(floor1='Fail')
        verdict = self.fx.root / 'verdict.md'
        verdict.write_text(raw)
        published = self.fx.command('review-packet', 'publish', 1, '--issue', 2,
                                    '--attempt', data['comment_id'], '--verdict', verdict)
        self.assertEqual(published.returncode, 0, published.stderr)
        self.assertTrue(self.fx.state()['comments'][0]['body'].endswith(raw))
        status = self.fx.command('review-packet', 'status', 1, '--issue', 2)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)['next'], 'needs-continuation')
        self.assertNotEqual(self.fx.guard().returncode, 0)

    def test_arbitration_override_survives_the_actual_native_request(self):
        result = self.start('--model', 'gpt-6-astra', '--effort', 'max')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn('instruction', data)
        request = json.loads(Path(data['instruction']).read_text())
        self.assertEqual((request['model'], request['reasoning_effort']), ('gpt-6-astra', 'max'))
        self.assertEqual(data['identity'], 'Codex, gpt-6-astra at max, read-only')

    def test_missing_host_or_stale_roles_refuse_before_remote_reservation(self):
        result = self.fx.command('review-packet', 'start', 1, '--issue', 2,
                                 '--architecture-level', 'yes', '--output', self.fx.output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.fx.state()['comments'])
        (self.fx.project / '.codex/agents/method_reviewer.toml').write_text('name="stale"\n')
        result = self.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.fx.state()['comments'])

    def test_lost_reservation_response_recovers_the_same_native_request_without_another_post(self):
        state = self.fx.state()
        state['mutation_fault'] = {'method': 'POST', 'outcome': 'lost-response'}
        self.fx.save(state)
        self.assertNotEqual(self.start().returncode, 0)
        self.assertTrue(self.fx.ledger.exists(), 'retain the reservation intent before sending')
        before = json.loads(self.fx.ledger.read_text())
        intended = before['pending']['attempt']
        self.assertIn('native_instruction', intended)
        original = Path(intended['native_instruction']).read_bytes()
        result = self.fx.command('review-packet', 'status', 1, '--issue', 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['instruction'], intended['native_instruction'])
        self.assertEqual(Path(data['instruction']).read_bytes(), original)
        self.assertEqual(data['rounds'], 0)
        self.assertEqual(len(self.fx.state()['comments']), 1)

    def test_changed_native_request_cannot_be_returned_as_the_reserved_instruction(self):
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn('instruction', data)
        path = Path(data['instruction'])
        request = json.loads(path.read_text())
        request['fork_turns'] = 'all'
        path.write_text(json.dumps(request))
        result = self.fx.command('review-packet', 'status', 1, '--issue', 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('native instruction', result.stderr)
        self.assertEqual(len(self.fx.state()['comments']), 1)
