"""Critical portable entry points, including the temporary Windows host.

These use explicit Python argv and isolated local fixtures. They do not claim that
the entire Unix-oriented lifecycle suite has been ported to Windows.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.github_fixture import GitHubFixture
from tests.github_fixture_runner import fixture_command


ROOT = Path(__file__).resolve().parents[1]


class WindowsRuntimeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.scratch = Path(directory.name).resolve()

    def session(self, data, *args):
        page = self.scratch / 'reference/orchestrator.md'
        page.parent.mkdir(exist_ok=True)
        if data is not None:
            page.write_bytes(data)
        return subprocess.run([sys.executable, '-X', 'utf8',
            str(ROOT / 'hooks/session-start.py'), str(self.scratch), *args],
            capture_output=True, text=True, encoding='utf-8', check=True)

    def test_python_session_delivers_one_complete_utf8_page(self):
        page = ('中文规则 — café 🚀\n' * 31).encode('utf-8')
        result = self.session(page, 'orchestrator')
        output = json.loads(result.stdout)['hookSpecificOutput']
        self.assertEqual(output['hookEventName'], 'SessionStart')
        marker = '--- codex-method whole context ---\n'
        self.assertEqual(output['additionalContext'].count(marker), 1)
        self.assertEqual(output['additionalContext'].partition(marker)[2].encode('utf-8'), page)
        self.assertLessEqual(len(output['additionalContext'].encode('utf-8')), 64000)

    def test_session_budget_counts_utf8_bytes_and_refuses_partial_context(self):
        result = self.session(('界' * 22000).encode('utf-8'), 'orchestrator')
        output = json.loads(result.stdout)
        self.assertIs(output['continue'], False)
        self.assertIn('64000 UTF-8 byte budget', output['stopReason'])
        self.assertNotIn('hookSpecificOutput', output)

    def test_session_refuses_missing_empty_malformed_and_split_page(self):
        for data, args, reason in ((None, ('orchestrator',), 'missing'),
                (b' \n', ('orchestrator',), 'empty'),
                (b'\xff', ('orchestrator',), 'valid UTF-8'),
                (b'complete', ('orchestrator', '1'), 'one role argument')):
            with self.subTest(reason=reason):
                output = json.loads(self.session(data, *args).stdout)
                self.assertIs(output['continue'], False)
                self.assertIn(reason, output['stopReason'])
                self.assertNotIn('hookSpecificOutput', output)

    def test_github_fixture_uses_exact_double_for_live_consumer(self):
        fixture = GitHubFixture()
        self.addCleanup(fixture.close)
        fixture.assert_boundary()
        result = fixture.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(fixture.state()['calls'])
        if os.name == 'nt':
            fixture.executable.unlink()
            refused = subprocess.run([sys.executable, '-c',
                'raise AssertionError("consumer must never start")'], env=fixture.env,
                capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('GitHub fixture startup refused', refused.stderr)
        self.assertTrue(any(call[:2] == ['issue', 'view'] for call in fixture.state()['calls']))

    def test_github_fixture_refuses_before_launch_when_double_changes(self):
        fixture = GitHubFixture()
        self.addCleanup(fixture.close)
        fixture.executable.write_text('changed fixture', encoding='utf-8')
        with patch('tests.github_fixture.subprocess.run') as launched:
            with self.assertRaisesRegex(AssertionError, 'missing or changed'):
                fixture.start()
            launched.assert_not_called()
        fixture.executable.unlink()
        with patch('tests.github_fixture.subprocess.run') as launched:
            with self.assertRaisesRegex(AssertionError, 'missing or changed'):
                fixture.guard('--execute')
            launched.assert_not_called()

    def test_github_fixture_accepts_explicit_alternate_stateful_double(self):
        from tests.test_dispatch_native import GH
        fixture = GitHubFixture()
        self.addCleanup(fixture.close)
        fixture.executable.write_text(GH, encoding='utf-8')
        fixture.assert_boundary()
        result = fixture.command('dispatch', '--help')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_fixture_consumer_inherits_fail_closed_boundary(self):
        fixture = GitHubFixture()
        self.addCleanup(fixture.close)
        result = subprocess.run([sys.executable, '-X', 'utf8',
            str(ROOT / 'scripts/review-packet'), 'start', '1', '--issue', '2',
            '--architecture-level', 'yes', '--output', str(fixture.output),
            '--model', 'gpt-6.1-sol', '--effort', 'high', '--host-version', '0.160.0',
            '--project', str(fixture.project)], env=fixture.env, cwd=fixture.project,
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(fixture.state()['calls'])

    def test_windows_bootstrap_never_resolves_real_gh(self):
        fake = self.scratch / 'gh'
        fake.write_text('fixture', encoding='utf-8')
        with patch.dict(os.environ, {'GH_FIXTURE_SCRIPT': str(fake)}):
            for selected in ('gh', 'gh.exe', str(self.scratch / 'real/gh.exe')):
                with self.subTest(selected=selected):
                    self.assertEqual(fixture_command([selected, 'api', 'user'], fake),
                                     [sys.executable, '-X', 'utf8', str(fake), 'api', 'user'])
            fake.unlink()
            with self.assertRaisesRegex(AssertionError, 'missing or changed'):
                fixture_command(['gh', 'api', 'user'], fake)

    def lock_command(self, path, hold=False):
        code = ('import os,sys,time;sys.path.insert(0,sys.argv[1]);'
                'from filelock import try_lock;'
                'fd=os.open(sys.argv[2],os.O_RDWR|os.O_CREAT,0o600);'
                'print(try_lock(fd),flush=True);'
                + ('time.sleep(60);' if hold else '') + 'os.close(fd)')
        return [sys.executable, '-X', 'utf8', '-c', code, str(ROOT / 'scripts'), str(path)]

    def test_file_lock_contention_and_release_on_descriptor_close(self):
        spec = importlib.util.spec_from_file_location('portable_filelock', ROOT / 'scripts/filelock.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = self.scratch / 'lock'
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            self.assertTrue(module.try_lock(fd))
            child = subprocess.run(self.lock_command(path), capture_output=True,
                                   text=True, encoding='utf-8', check=True, timeout=10)
            self.assertEqual(child.stdout.strip(), 'False')
        finally:
            os.close(fd)
        child = subprocess.run(self.lock_command(path), capture_output=True,
                               text=True, encoding='utf-8', check=True, timeout=10)
        self.assertEqual(child.stdout.strip(), 'True')

    def test_file_lock_is_released_on_process_exit(self):
        path = self.scratch / 'lock'
        child = subprocess.Popen(self.lock_command(path, hold=True), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding='utf-8')
        try:
            self.assertEqual(child.stdout.readline().strip(), 'True')
            contender = subprocess.run(self.lock_command(path), capture_output=True,
                                       text=True, encoding='utf-8', check=True, timeout=10)
            self.assertEqual(contender.stdout.strip(), 'False')
        finally:
            child.terminate()
            child.communicate(timeout=10)
        contender = subprocess.run(self.lock_command(path), capture_output=True,
                                   text=True, encoding='utf-8', check=True, timeout=10)
        self.assertEqual(contender.stdout.strip(), 'True')


if __name__ == '__main__':
    unittest.main()
