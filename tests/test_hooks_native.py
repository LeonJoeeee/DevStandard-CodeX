"""Consumers use Codex's observed hook payload names and blocking protocol."""
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hook(tool, inputs, role=None):
    payload = {'tool_name': tool, 'tool_input': inputs}
    if role:
        payload.update(agent_type=role, agent_id='native-child')
    return subprocess.run([str(ROOT / 'hooks/pre-tool-use')], input=json.dumps(payload),
                          capture_output=True, text=True)


class NativeHookTest(unittest.TestCase):
    def assertDenied(self, result):
        if result.returncode == 2:
            self.assertTrue(result.stderr.strip())
        else:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip(), 'hook admitted an operation that must be denied')
            output = json.loads(result.stdout)['hookSpecificOutput']
            self.assertEqual(output['hookEventName'], 'PreToolUse')
            self.assertEqual(output['permissionDecision'], 'deny')
            self.assertTrue(output['permissionDecisionReason'])

    def test_normalized_bash_identifies_worker_without_role_flag(self):
        self.assertDenied(hook('Bash', {'command': 'git merge feature'}, 'method_worker'))

    def test_git_directory_options_do_not_hide_ordinary_mutations(self):
        for prefix in ('git -C ordinary/path', 'git --git-dir ordinary/.git',
                       'git -C "ordinary path"', 'git -c advice.foo=false'):
            with self.subTest(prefix=prefix):
                self.assertDenied(hook('Bash', {'command': prefix + ' merge feature'}, 'method_worker'))
                self.assertDenied(hook('Bash', {'command': prefix + ' commit -am change'}, 'method_reviewer'))
                read = hook('Bash', {'command': prefix + ' diff HEAD'}, 'method_reviewer')
                self.assertEqual(read.returncode,0,read.stderr)
                self.assertFalse(read.stdout.strip())

    def test_reviewer_helpers_inherit_nonediting_role(self):
        for role in ('method_reviewer', 'method_review_helper'):
            for tool in ('apply_patch', 'Write', 'Edit', 'MultiEdit'):
                with self.subTest(role=role, tool=tool):
                    self.assertDenied(hook(tool, {'command': '*** Begin Patch'}, role))

    def test_reviewer_cannot_spawn_writer_or_fork_history(self):
        for inputs in ({'agent_type': 'method_helper', 'fork_turns': 'none'},
                       {'agent_type': 'default', 'fork_turns': 'none'},
                       {'agent_type': 'method_review_helper', 'fork_turns': 'all'}, {}):
            self.assertDenied(hook('spawn_agent', inputs, 'method_reviewer'))

    def test_reviewer_can_spawn_fresh_review_helper(self):
        result = hook('spawn_agent', {'agent_type': 'method_review_helper', 'fork_turns': 'none'},
                      'method_review_helper')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip())

    def test_reviewer_ordinary_shell_writes_are_denied(self):
        for command in ('rm code.txt', 'touch code.txt', 'mv old new', 'cp old new',
                        'printf hello > code.txt', 'sed -i s/a/b/ code.txt',
                        'git commit -am change', 'git checkout task/writer',
                        'git push origin task/writer', 'gh issue comment 2 --body hello',
                        'git branch -D task/writer', 'git tag release',
                        'git config user.name writer', 'git config --show-origin user.name writer',
                        'git branch -f task/writer HEAD', 'git remote add new https://example.invalid/r',
                        'gh pr edit 1 --body hello', 'gh api --method=POST repos/o/r/issues'):
            with self.subTest(command=command):
                self.assertDenied(hook('Bash', {'command': command}, 'method_reviewer'))

    def test_reviewer_reads_and_inert_prose_are_allowed(self):
        for command in ('cat ordinary/path.txt', 'git diff HEAD~1 HEAD',
                        'gh api -X GET repos/o/r/pulls', 'rg "rm code.txt" .',
                        'git branch --show-current', 'git branch --list task/reader',
                        'git tag --list v*', 'git config --get user.name', 'git remote -v',
                        'cat <<EOF\ngit commit -am nope\nEOF\n'):
            result = hook('Bash', {'command': command}, 'method_reviewer')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(result.stdout.strip(), command)

    def test_raw_exec_command_schema_is_supported_too(self):
        self.assertDenied(hook('exec_command', {'cmd': 'git push origin main'}, 'method_worker'))

    def test_command_wrappers_and_absolute_paths_keep_role_boundaries(self):
        for command in ('command rm sample.txt', '/bin/rm sample.txt',
                        'env NOTE=fixture /bin/rm sample.txt'):
            with self.subTest(command=command):
                self.assertDenied(hook('Bash', {'command': command}, 'method_reviewer'))
        for command in ('env git merge feature', '/usr/bin/env NOTE=fixture /usr/bin/git merge feature'):
            with self.subTest(command=command):
                self.assertDenied(hook('exec_command', {'cmd': command}, 'method_worker'))

    def test_search_arguments_are_not_mutating_commands(self):
        for role, command in (('method_worker', 'rg push main'),
                              ('method_reviewer', 'rg gh api --method README.md'),
                              ('method_reviewer', 'rg gh pr merge README.md'),
                              ('method_reviewer', 'rg guard merge --execute README.md'),
                              ('method_reviewer', 'rg ";" rm'),
                              ('method_reviewer', 'printf harmless # ; rm sample.txt')):
            with self.subTest(command=command):
                result = hook('Bash', {'command': command}, role)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(result.stdout.strip(), command)

    def test_worker_push_requires_an_explicit_branch_refspec(self):
        for command in ('git push', 'git push origin', 'git push origin HEAD',
                        'git push origin topic:refs/heads/main', 'git push --all origin'):
            with self.subTest(command=command):
                self.assertDenied(hook('Bash', {'command': command}, 'method_worker'))
        for command in ('git push origin task/topic',
                        'git push --force-with-lease origin task/topic',
                        'git push origin HEAD:refs/heads/task/topic'):
            with self.subTest(command=command):
                result = hook('Bash', {'command': command}, 'method_worker')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(result.stdout.strip(), command)

    def test_canonical_collaboration_spawn_preserves_fresh_reviewer_role(self):
        for name in ('collaborationspawn_agent', 'collaboration.spawn_agent', 'spawn_agent'):
            for inputs in ({'agent_type': 'method_worker', 'fork_turns': 'none'},
                           {'agent_type': 'method_review_helper', 'fork_turns': 'all'}):
                with self.subTest(name=name, inputs=inputs):
                    self.assertDenied(hook(name, inputs, 'method_reviewer'))
            allowed = hook(name, {'agent_type': 'method_review_helper', 'fork_turns': 'none'},
                           'method_reviewer')
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertFalse(allowed.stdout.strip())

    def test_known_patch_aliases_are_denied_without_matching_mcp_suffixes(self):
        for name in ('apply_patch', 'functions.apply_patch'):
            with self.subTest(name=name):
                self.assertDenied(hook(name, {'input': 'fixture patch'}, 'method_reviewer'))
        result = hook('mcp__example__apply_patch', {'input': 'fixture data'}, 'method_reviewer')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(result.stdout.strip())

    def test_resume_handlers_deliver_the_complete_orchestrator(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        import re
        contexts = []
        for entry in config['hooks']['SessionStart']:
            if re.search(entry['matcher'], 'resume'):
                for handler in entry['hooks']:
                    result = subprocess.run(handler['command'], shell=True,
                                            env={**os.environ, 'PLUGIN_ROOT': str(ROOT)},
                                            input='{"source":"resume"}', text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if result.stdout.strip():
                        context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                        contexts.append(context.partition('--- codex-method whole context ---\n')[2])
        self.assertEqual(''.join(contexts), (ROOT / 'reference/orchestrator.md').read_text())

    def test_unknown_native_child_role_refuses(self):
        self.assertDenied(hook('Bash', {'command': 'git merge feature'}, 'unknown_child'))

    def test_shipped_hook_commands_run_with_plugin_root(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        env = {**os.environ, 'PLUGIN_ROOT': str(ROOT)}
        env.pop('CODEX_PLUGIN_ROOT', None)
        command = config['hooks']['PreToolUse'][0]['hooks'][0]['command']
        result = subprocess.run(command, shell=True, env=env, text=True, capture_output=True,
                                input=json.dumps({'tool_name': 'Bash', 'agent_type': 'method_worker',
                                                  'tool_input': {'command': 'git merge x'}}))
        self.assertDenied(result)

    def test_session_start_delivers_one_whole_inline_page_in_native_protocol(self):
        config = json.loads((ROOT / 'hooks/hooks.json').read_text())
        env = {**os.environ, 'PLUGIN_ROOT':str(ROOT)}
        delivered = []
        for entry in config['hooks']['SessionStart']:
            for handler in entry['hooks']:
                result = subprocess.run(handler['command'], shell=True, env=env,
                                        capture_output=True, text=True,
                                        input=json.dumps({'hook_event_name':'SessionStart','source':'startup'}))
                self.assertEqual(result.returncode, 0, result.stderr)
                if not result.stdout.strip():
                    continue
                context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                # 0 disables host spilling; the complete page must remain inline.
                self.assertEqual(handler.get('additionalContextLimit'),0,
                                 'whole inline delivery must disable Codex context spilling')
                delivered.append(context.partition('--- codex-method whole context ---\n')[2])
        self.assertEqual(delivered, [(ROOT / 'reference/orchestrator.md').read_bytes().decode('utf-8')])

    def test_session_start_refuses_missing_role_page_in_real_protocol(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'hooks').mkdir()
            shutil.copy2(ROOT / 'hooks/session-start', root / 'hooks/session-start')
            result = subprocess.run([str(root / 'hooks/session-start'),'orchestrator'],
                                    text=True,capture_output=True,input='{}')
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertIs(output.get('continue'), False)
            self.assertIn('missing', output['stopReason'])
