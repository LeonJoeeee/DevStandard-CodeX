"""SessionStart delivers one complete UTF-8 page or stops without partial rules."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 64000
MARKER = '--- codex-method whole context ---\n'


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'hooks').mkdir()
        (self.root / 'reference').mkdir()
        shutil.copy2(ROOT / 'hooks/session-start', self.root / 'hooks/session-start')
        self.page = self.root / 'reference/orchestrator.md'

    def deliver(self, data=None, env=None, role='orchestrator'):
        if data is not None:
            self.page.write_bytes(data)
        result = subprocess.run([str(self.root / 'hooks/session-start'), role],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(result.stderr, result.stderr)
        return json.loads(result.stdout)

    def context(self, data):
        return self.deliver(data)['hookSpecificOutput']['additionalContext']

    def assertStopped(self, data, reason):
        output = self.deliver(data)
        self.assertIs(output.get('continue'), False)
        self.assertIn(reason, output['stopReason'])
        self.assertNotIn('hookSpecificOutput', output)
        self.assertNotIn('additionalContext', output)

    def test_single_output_contains_the_whole_shipped_page_and_root(self):
        data = (ROOT / 'reference/orchestrator.md').read_bytes()
        context = self.context(data)
        self.assertEqual(context.partition(MARKER)[2].encode('utf-8'), data)
        self.assertIn(str(self.root), context.partition(MARKER)[0])
        self.assertEqual(context.count(MARKER), 1)
        self.assertLessEqual(len(context.encode('utf-8')), CAP)

    def test_utf8_crossing_old_8000_boundary_and_crlf_are_unchanged(self):
        data = b'# P\r\n' + b'x' * 7994 + '—中文'.encode() + b'\r\n' + b'y' * 9000
        self.assertEqual(self.context(data).partition(MARKER)[2].encode(), data)

    def test_complete_context_at_cap_is_delivered(self):
        header = self.context(b'x').partition(MARKER)[0] + MARKER
        data = b'x' * (CAP - len(header.encode()))
        context = self.context(data)
        self.assertEqual(len(context.encode()), CAP)
        self.assertEqual(context.partition(MARKER)[2].encode(), data)

    def test_multibyte_page_near_cap_is_whole(self):
        header = self.context(b'x').partition(MARKER)[0] + MARKER
        count = (CAP - len(header.encode())) // 3
        data = '中'.encode() * count
        context = self.context(data)
        self.assertGreaterEqual(len(context.encode()), CAP - 2)
        self.assertEqual(context.partition(MARKER)[2].encode(), data)

    def test_header_budget_overflow_stops_without_partial_context(self):
        header = self.context(b'x').partition(MARKER)[0] + MARKER
        self.assertStopped(b'x' * (CAP - len(header.encode()) + 1), '64000')

    def test_raw_page_over_cap_stops_without_partial_context(self):
        self.assertStopped(b'x' * (CAP + 1), '64000')

    def test_missing_page_stops_without_partial_context(self):
        self.assertStopped(None, 'missing')

    def test_empty_and_whitespace_pages_stop(self):
        for data in (b'', b' \r\n\t'):
            with self.subTest(data=data):
                self.assertStopped(data, 'empty')

    def test_invalid_utf8_stops_without_partial_context(self):
        self.assertStopped(b'valid prefix\n\xff', 'UTF-8')

    def test_old_cap_environment_cannot_expand_or_segment_delivery(self):
        for value in ('0', '4', '999999'):
            with self.subTest(value=value):
                env = {**os.environ, 'CODEX_METHOD_CAP_BYTES': value}
                context = self.deliver(b'x' * 10000, env)['hookSpecificOutput']['additionalContext']
                self.assertEqual(context.partition(MARKER)[2], 'x' * 10000)
                output = self.deliver(b'x' * (CAP + 1), env)
                self.assertIs(output.get('continue'), False)
                self.assertNotIn('hookSpecificOutput', output)

    def test_worker_page_can_be_delivered_whole(self):
        data = (ROOT / 'reference/worker.md').read_bytes()
        (self.root / 'reference/worker.md').write_bytes(data)
        output = self.deliver(role='worker')
        self.assertEqual(output['hookSpecificOutput']['additionalContext'].partition(MARKER)[2].encode(), data)

    def test_each_transition_has_one_synchronous_full_inline_handler(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        import re
        for source in ('startup', 'resume', 'clear', 'compact'):
            with self.subTest(source=source):
                handlers = [handler for entry in config['hooks']['SessionStart']
                            if re.fullmatch(entry['matcher'], source) for handler in entry['hooks']]
                self.assertEqual(len(handlers), 1)
                handler = handlers[0]
                self.assertIs(handler.get('async'), False)
                self.assertEqual(handler.get('additionalContextLimit'), 0)
                result = subprocess.run(handler['command'], shell=True,
                    env={**os.environ, 'PLUGIN_ROOT': str(ROOT)},
                    input=json.dumps({'source': source}), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                self.assertEqual(context.partition(MARKER)[2].encode(),
                                 (ROOT / 'reference/orchestrator.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
