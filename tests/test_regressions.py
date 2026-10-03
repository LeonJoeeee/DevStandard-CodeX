"""Pins for the defects an audit found behind a green suite.

Each test here asserts behaviour the code actually performs, not that a file exists.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hard_edges import Refusal, helper_rows  # noqa: E402

HOOK = ROOT / 'hooks/pre-tool-use'
SESSION = ROOT / 'hooks/session-start'


def run_hook(text, role='worker'):
    return subprocess.run([str(HOOK), '--role', role], input=text,
                          capture_output=True, text=True)


class HookRunsTest(unittest.TestCase):
    def test_the_hook_is_valid_python(self):
        proc = subprocess.run([sys.executable, '-m', 'py_compile', str(HOOK)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_an_ordinary_command_is_allowed(self):
        self.assertEqual(run_hook('cat reference/orchestrator.md').returncode, 0)


class HookMatrixTest(unittest.TestCase):
    def test_git_merge_base_is_not_a_merge(self):
        self.assertEqual(run_hook('git merge-base HEAD~3 HEAD').returncode, 0)

    def test_a_quoted_string_is_not_the_commands_text(self):
        self.assertEqual(run_hook('rg "git merge" reference/').returncode, 0)

    def test_a_heredoc_body_is_not_the_commands_text(self):
        self.assertEqual(run_hook('cat <<EOF\ngit merge\nEOF\n').returncode, 0)

    def test_a_worker_never_merges(self):
        proc = run_hook('git merge feature')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('a worker never merges', proc.stderr)

    def test_the_orchestrator_merges_through_the_guard(self):
        proc = run_hook('gh pr merge 12', role='orchestrator')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('guard merge', proc.stderr)

    def test_a_reviewer_is_read_only(self):
        proc = run_hook('gh api -X PATCH repos/x/issues/1', role='reviewer')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('read-only', proc.stderr)

    def test_a_worker_never_pushes_main(self):
        self.assertEqual(run_hook('git push origin main').returncode, 1)

    def test_a_worker_pushing_its_branch_is_allowed(self):
        self.assertEqual(run_hook('git push origin task/12-x').returncode, 0)

    def test_the_main_session_is_the_orchestrator_by_default(self):
        proc = subprocess.run([str(HOOK)], input='git merge x', capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class HooksJsonTest(unittest.TestCase):
    def test_the_session_hook_names_its_role(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        command = config['hooks']['PreToolUse'][0]['hooks'][0]['command']
        self.assertIn('--role orchestrator', command)

    def test_the_declared_parts_cover_the_page(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        parts = [h['command'] for h in config['hooks']['SessionStart'][0]['hooks']]
        indexes = [int(cmd.split()[-2]) for cmd in parts if 'orchestrator' in cmd]
        cap = int(os.environ.get('CODEX_METHOD_CAP_BYTES', 8000))
        need = math.ceil(len((ROOT / 'reference/orchestrator.md').read_bytes()) / cap)
        self.assertGreaterEqual(max(indexes), need,
                                'the page needs more parts than hooks.json declares')
        self.assertEqual(sorted(indexes), list(range(1, max(indexes) + 1)))


class MultiByteBoundaryTest(unittest.TestCase):
    def test_a_character_cut_by_the_part_boundary_still_delivers_whole(self):
        scratch = Path(tempfile.mkdtemp())
        (scratch / 'hooks').mkdir()
        (scratch / 'reference').mkdir()
        shutil.copy(SESSION, scratch / 'hooks/session-start')
        os.chmod(scratch / 'hooks/session-start', 0o755)
        # The em dash straddles byte 8000 exactly.
        payload = b'# P\n' + b'x' * 7995 + '—'.encode() + b'y' * 30
        (scratch / 'reference/orchestrator.md').write_bytes(payload)
        env = {**os.environ, 'CODEX_METHOD_CAP_BYTES': '8000'}
        chunks = []
        for index in (1, 2):
            proc = subprocess.run([str(scratch / 'hooks/session-start'), 'orchestrator', str(index), '2'],
                                  capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            chunks.append(json.loads(proc.stdout)['hookSpecificOutput']['additionalContext'])
        rebuilt = ''.join(c.split('---\n', 1)[-1] for c in chunks)
        self.assertEqual(rebuilt, payload.decode())


class TableContractTest(unittest.TestCase):
    def test_a_missing_helper_header_refuses_instead_of_leaking_anchored_rows(self):
        scratch = Path(tempfile.mkdtemp())
        (scratch / 'reference').mkdir()
        (scratch / 'reference/orchestrator.md').write_text(
            '| Role | Model at effort |\n|---|---|\n'
            '| worker | `gpt-6.1-sol` at `high` |\n'
            '| reviewer | `gpt-6.1-sol` at `high` |\n')
        with self.assertRaises(Refusal):
            helper_rows(scratch)


class DispatchCleanupTest(unittest.TestCase):
    def test_a_lane_record_carries_the_pull_url_and_cleanup_matches_it(self):
        source = (ROOT / 'scripts/dispatch').read_text()
        self.assertIn("/pull/{args.pr}", source)
        self.assertIn("recorded.endswith", source)


if __name__ == '__main__':
    unittest.main()
