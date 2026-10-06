"""Script-only ordinary Windows role-policy probes; represented commands never execute."""
import json
import subprocess
import sys
import unittest

from tests.test_hooks_native import ROOT, hook


class WindowsPolicyTest(unittest.TestCase):
    def assertDenied(self, command, role='method_reviewer', shell='powershell'):
        result = hook('exec_command', {'cmd': command, 'shell': shell}, role)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip(), command)
        output = json.loads(result.stdout)['hookSpecificOutput']
        self.assertEqual(output['permissionDecision'], 'deny', command)
        self.assertTrue(output['permissionDecisionReason'])

    def assertAllowed(self, command, role='method_reviewer', shell='powershell'):
        result = hook('exec_command', {'cmd': command, 'shell': shell}, role)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(result.stdout.strip(), command)

    def test_windows_git_executable_spellings_keep_worker_merge_boundary(self):
        for executable in ('git.exe', 'GIT.EXE', r'C:\Git\bin\git.exe',
                           r'& "C:\Program Files\Git\bin\git.exe"',
                           r"& 'C:\Program Files\Git\bin\GIT.EXE'",
                           r'& \\server\tools\git.exe', './git.exe', 'git.cmd', 'git.bat'):
            with self.subTest(executable=executable):
                self.assertDenied(executable + ' merge feature', 'method_worker')

    def test_windows_git_executables_keep_reviewer_write_boundary(self):
        for command in ('git.exe commit -am change',
                        r'& "C:\Program Files\Git\bin\git.exe" -C "C:\my repo" commit -am change',
                        r'C:\Git\bin\git.exe push origin main'):
            with self.subTest(command=command):
                self.assertDenied(command)

    def test_powershell_direct_mutators_and_aliases_are_denied(self):
        for executable in ('Set-Content', 'Add-Content', 'Clear-Content', 'Out-File',
                           'New-Item', 'Remove-Item', 'Move-Item', 'Copy-Item', 'Rename-Item',
                           'Set-Item', 'Set-ItemProperty', 'Remove-ItemProperty', 'Set-Acl',
                           'Export-Csv', 'Export-Clixml', 'Tee-Object', 'Export-PSSession',
                           'sc', 'ac', 'clc', 'ni', 'ri', 'rni', 'cpi', 'rip', 'rnp',
                           'del', 'erase', 'ren', 'copy', 'move', 'md', 'rd'):
            with self.subTest(executable=executable):
                self.assertDenied(executable + " -LiteralPath 'C:\\my repo\\sample.txt' -Value change")

    def test_powershell_call_operator_and_module_qualified_mutators_are_denied(self):
        for command in ("& 'Set-Content' -LiteralPath sample.txt -Value change",
                        'New-Item -ItemType File -Path reviewer-write.txt',
                        "Microsoft.PowerShell.Management\\Set-Content sample.txt change",
                        "Get-Content sample.txt | Microsoft.PowerShell.Utility\\Out-File copy.txt"):
            with self.subTest(command=command):
                self.assertDenied(command)

    def test_powershell_redirects_are_denied_but_stream_routing_is_allowed(self):
        for command in ('Write-Output change > sample.txt', 'Write-Output change >> sample.txt',
                        'Write-Output change 2> errors.txt', 'Write-Output change *> all.txt',
                        'Get-Content sample.txt | Out-File copy.txt'):
            with self.subTest(command=command):
                self.assertDenied(command)
        self.assertAllowed('Get-Content sample.txt 2>&1')

    def test_windows_gh_merge_paths_are_denied_for_all_roles(self):
        for role in (None, 'method_worker', 'method_reviewer'):
            for command in ('gh.exe pr merge 12',
                            r'& "C:\Program Files\GitHub CLI\GH.EXE" -R owner/repo pr merge 12',
                            r'& "C:\fixture tools\gh.cmd" pr merge 12',
                            r'& "C:\fixture tools\GH.BAT" pr merge 12',
                            r'C:\tools\gh.exe api -X PUT repos/o/r/pulls/12/merge'):
                with self.subTest(role=role, command=command):
                    self.assertDenied(command, role)

    def test_windows_github_mutations_keep_reviewer_boundary(self):
        for command in ('GH.EXE issue comment 2 --body hello',
                        r'& "C:\Program Files\GitHub CLI\gh.exe" pr edit 1 --body hello',
                        r'C:\tools\gh.exe api --method=POST repos/o/r/issues',
                        r'C:\tools\curl.exe -X PUT https://api.github.com/repos/o/r/pulls/12/merge'):
            with self.subTest(command=command):
                self.assertDenied(command)

    def test_windows_reads_and_quoted_prose_remain_allowed(self):
        for command in (r"Get-Content -LiteralPath 'C:\my repo\sample.txt'",
                        r'& "C:\Program Files\Git\bin\git.exe" -C "C:\my repo" diff HEAD',
                        r'C:\tools\gh.exe api -X GET repos/o/r/pulls',
                        r'& "C:\fixture tools\gh.cmd" api -X GET repos/o/r/pulls',
                        r'& "C:\fixture tools\GH.BAT" api -X GET repos/o/r/pulls',
                        r'rg.exe "Set-Content sample.txt; git.exe commit > file" .',
                        r'rg.exe "C:\Git\bin\git.exe merge" .',
                        "Get-Content sample.txt # ; Set-Content sample.txt change",
                        r"Write-Output '>'", r"rg.exe ';' Set-Content"):
            with self.subTest(command=command):
                self.assertAllowed(command)

    def test_windows_compatibility_payload_never_executes_represented_commands(self):
        result = subprocess.run([sys.executable, str(ROOT / 'hooks/pre-tool-use'), '--role', 'worker'],
                                input=r'C:\Git\bin\git.exe merge feature',
                                text=True, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('a worker never merges', result.stderr)

    def test_unix_quoting_and_escapes_keep_existing_boundaries(self):
        for command in (r'/usr/bin/g\it merge feature',
                        r'env NOTE=fixture /usr/bin/git merge feature'):
            with self.subTest(command=command):
                self.assertDenied(command, 'method_worker', '/bin/bash')
        for command in (r'rg "rm sample.txt; git merge" .', r'printf \>'):
            with self.subTest(command=command):
                self.assertAllowed(command, shell='/bin/bash')


if __name__ == '__main__':
    unittest.main()
