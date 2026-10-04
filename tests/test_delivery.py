"""SessionStart delivery: the page arrives whole, part by part."""
import json
import math
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 8000
PAGE = ROOT / 'reference/orchestrator.md'
HOOK = ROOT / 'hooks/session-start'


def part(index, total=8):
    out = subprocess.run([str(HOOK), 'orchestrator', str(index), str(total)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    if not out.stdout.strip():
        return None
    return json.loads(out.stdout)['hookSpecificOutput']['additionalContext']


MARKER = re.compile(r'--- codex-method part \d+ of \d+ ---\n')


def body(payload):
    """Drop the per-part preamble; what remains is the file's own bytes."""
    return MARKER.split(payload, 1)[-1]


class DeliveryTest(unittest.TestCase):
    def test_parts_concatenate_to_the_files_exact_bytes(self):
        text = PAGE.read_text()
        parts = math.ceil(len(text.encode()) / CAP)
        rebuilt = ''.join(body(part(i)) for i in range(1, parts + 1))
        self.assertEqual(rebuilt, text)

    def test_part_one_carries_the_trust_and_reconstruction_notice(self):
        payload = part(1)
        self.assertIn('part 1 of', payload)
        self.assertIn('Concatenate', payload)

    def test_a_part_beyond_the_total_emits_nothing(self):
        self.assertIsNone(part(20))

    def test_the_worker_page_delivers_too(self):
        out = subprocess.run([str(HOOK), 'worker', '1', '8'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('Worker', json.loads(out.stdout)['hookSpecificOutput']['additionalContext'])

    def test_insufficient_handlers_refuse_before_emitting_partial_context(self):
        for index in (1, 8):
            out = subprocess.run([str(HOOK), 'orchestrator', str(index), '8'],
                                 env={**os.environ, 'CODEX_METHOD_CAP_BYTES': '64'},
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            payload = json.loads(out.stdout)
            self.assertIs(payload.get('continue'), False)
            self.assertIn('handler', payload['stopReason'])
            self.assertNotIn('hookSpecificOutput', payload)


if __name__ == '__main__':
    unittest.main()
