"""The actual review-start consumer prepares a fresh native call, never an executor."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.github_fixture import GitHubFixture, ROOT


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
        self.assertIn((ROOT / 'reference/code-review-prompt.md').read_text(), request['message'])
        self.assertIn(self.fx.state()['issue'], request['message'])
        self.assertIn(self.fx.head, request['message'])
        self.assertIn(self.fx.base, request['message'])
        self.assertIn(Path(data['packet']).read_text(), request['message'])
        self.assertEqual(len(self.fx.state()['comments']), 1)

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
