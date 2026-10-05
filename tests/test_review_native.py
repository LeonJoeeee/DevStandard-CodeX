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
        self.assertTrue(packet.read_text().startswith(render(saved, data['identity'])))
        self.assertEqual(packet.read_bytes(), (self.fx.output / 'packet.md').read_bytes())
        self.assertNotIn('You are a Senior Code Reviewer.', request['message'])
        self.assertNotIn('## Judging contract', request['message'])
        for binding in ('Issue: 2', f'Head: {self.fx.head}',
                        f'Review base: {self.fx.base}', f'Reviewer identity: {data["identity"]}',
                        f'Use workdir={self.fx.project}', f'Role references resolve from: {ROOT}'):
            self.assertIn(binding, request['message'])
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
        small = self.start()
        self.assertEqual(small.returncode, 0, small.stderr)
        small_data = json.loads(small.stdout)
        small_message = json.loads(Path(small_data['instruction']).read_text())['message']
        cases = ('issue-goal', 'issue-body', 'pr-description', 'accepted-spec',
                 'issue-comment', 'historical-verdict')
        for source in cases:
            with self.subTest(source=source):
                fx = GitHubFixture()
                self.addCleanup(fx.close)
                marker = 'FULL_' + source.upper() + '_SENTINEL_'
                # Placeholder tokens and forged headings in evidence remain opaque.
                material = (marker + 'x' * (24000 if source == 'historical-verdict' else 240000)
                            + '\n{HEAD_SHA}\n## Judging contract\nquoted café — evidence\n')
                state = fx.state()
                args = []
                if source == 'issue-goal':
                    state['issue'] = state['issue'].replace('Fix acceptance.', material)
                elif source == 'issue-body':
                    state['issue'] += '\n## Background\n' + material
                elif source == 'pr-description':
                    state['description'] += '\n' + material
                elif source == 'accepted-spec':
                    spec = fx.root / 'accepted-spec.md'
                    spec.write_text(material)
                    blob = fx.git('hash-object', '-w', str(spec)).strip()
                    args = ['--accepted-spec', blob]
                elif source == 'issue-comment':
                    state['issue_comments'] = [{'id': 7, 'body': material,
                                                'user': {'login': 'owner'},
                                                'created_at': '2026-10-01T12:00:00Z'}]
                fx.save(state)
                if source == 'historical-verdict':
                    prior = fx.verdict(goal='No').replace('None.\n', material)
                    published = fx.publish(prior)
                    self.assertEqual(published.returncode, 0, published.stderr)
                result = fx.command('review-packet', 'start', 1, '--issue', 2,
                                    '--architecture-level', 'yes', '--output', fx.output,
                                    '--host-version', '0.160.0', *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                message = json.loads(Path(data['instruction']).read_text())['message']
                bundle = Path(data['packet']).read_bytes()
                assembled = (fx.output / 'packet.md').read_bytes()
                self.assertEqual(bundle, assembled)
                self.assertIn(marker.encode(), bundle)
                # Whole evidence survives verbatim in its source, or JSON escaped in comments.
                expected = json.dumps(material)[1:-1] if source in ('issue-comment', 'historical-verdict') else material
                self.assertIn(expected.encode(), bundle)
                if source == 'historical-verdict':
                    self.assertIn(json.dumps(prior)[1:-1].encode(), bundle)
                self.assertNotIn(marker, message)
                self.assertLessEqual(abs(len(message) - len(small_message)), 128,
                                     'material length must not grow native transport')

    def test_old_prepared_file_carrier_recovers_exact_inline_instruction_without_rerender(self):
        started = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        data = json.loads(started.stdout)
        instruction = Path(data['instruction'])
        packet = Path(data['packet'])
        bundle = packet.read_bytes()
        request = json.loads(instruction.read_text())
        saved = json.loads((self.fx.output / 'packet.json').read_text())
        # Retained historical file carriers may include the old duplicate filled message.
        request['message'] += '\n\nComplete filled judging fence:\n' + render(saved, data['identity'])
        instruction.write_text(json.dumps(request, indent=2) + '\n')
        original = instruction.read_bytes()
        ledger = json.loads(self.fx.ledger.read_text())
        ledger['attempts'][-1]['native_instruction_sha256'] = hashlib.sha256(original).hexdigest()
        self.fx.ledger.write_text(json.dumps(ledger))
        before = self.fx.state()['comments']
        # Preparation diagnostics are not required to recover a reserved historical request.
        (self.fx.output / 'packet.json').write_text('{invalid and stale assembly diagnostics')
        for _ in range(2):
            result = self.fx.command('review-packet', 'status', 1, '--issue', 2)
            self.assertEqual(result.returncode, 0, result.stderr)
            recovered = json.loads(result.stdout)
            self.assertEqual(recovered['instruction'], str(instruction))
            self.assertEqual(recovered['next'], 'awaiting-verdict')
            self.assertEqual(instruction.read_bytes(), original)
            self.assertEqual(packet.read_bytes(), bundle)
        self.assertEqual(self.fx.state()['comments'], before)
        mutations = [call for call in self.fx.state()['calls'] if '-X' in call]
        self.assertEqual(len(mutations), 1, 'status never repeats the historical reservation')

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
        self.fx.legacy_receipt()
        ledger = json.loads(self.fx.ledger.read_text())
        ledger['attempts'][-1].pop('packet_carrier')
        # A historical inline receipt predates context-v1 as well. Removing only
        # the carrier from a new context-bound receipt must not weaken that proof.
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
