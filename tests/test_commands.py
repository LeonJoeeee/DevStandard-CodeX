"""The three commands: what each prepares, and what each refuses."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hard_edges import Refusal, anchored_roles, helper_rows  # noqa: E402


class AnchoredRowFormTest(unittest.TestCase):
    def test_both_rows_take_the_cell_form_a_reader_can_parse(self):
        page = (ROOT / 'reference/orchestrator.md').read_text()
        rows = [line for line in page.splitlines()
                if line.startswith('| worker |') or line.startswith('| reviewer |')]
        self.assertEqual(len(rows), 2)
        for line in rows:
            self.assertRegex(line, r'^\| (worker|reviewer) \| `[^`]+` at `[^`]+` \|$')

    def test_the_helper_table_has_a_closing_default_row(self):
        rows = helper_rows(ROOT)
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(rows[-1][0].startswith('Mechanical'))


class ScriptSurfaceTest(unittest.TestCase):
    def test_dispatch_refuses_without_an_issue(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/dispatch'), '--purpose', 'worker'],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn('refused', out.stderr)

    def test_review_packet_and_guard_help(self):
        for script in ('review-packet', 'guard'):
            out = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), '--help'],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)

    def test_no_command_offers_a_cross_host_executor(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/dispatch'), '--help'],
                             capture_output=True, text=True).stdout
        self.assertNotIn('implementation', out)
        self.assertNotIn('codex-native', out)
        self.assertNotIn('claude', out.lower())


class HookBindingTest(unittest.TestCase):
    def test_the_role_hook_exists_and_is_executable(self):
        hook = ROOT / 'hooks/pre-tool-use'
        self.assertTrue(hook.is_file())
        self.assertTrue(hook.stat().st_mode & 0o111)


if __name__ == '__main__':
    unittest.main()
