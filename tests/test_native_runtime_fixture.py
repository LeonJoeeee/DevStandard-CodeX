"""Test the qualification fixture's refusal paths; these are not runtime qualification."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/test-native-runtime.py'


def native_request(marker):
    """Representative 0.159.2 wire catalog: nested tools are not outer members."""
    return {'input': [{'role': 'user', 'content': marker},
        {'type': 'additional_tools', 'tools': [
            {'type': 'namespace', 'name': 'functions', 'tools': [
                {'type': 'custom', 'name': 'exec', 'format': {'type': 'grammar',
                    'syntax': 'lark', 'definition': 'start: /[\\s\\S]+/'}}]},
            {'type': 'namespace', 'name': 'collaboration', 'tools': [
                {'type': 'function', 'name': name, 'parameters': {'properties': {
                    key: {} for key in fields}}}
                for name, fields in (
                    ('spawn_agent', ('task_name', 'message', 'agent_type', 'fork_turns',
                                     'model', 'reasoning_effort')),
                    ('send_message', ('target', 'message')), ('wait_agent', ('timeout_ms',)))]}]}]}


class NativeRuntimeFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SCRIPT.exists():
            spec = importlib.util.spec_from_file_location('native_runtime_fixture', SCRIPT)
            cls.fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.fixture)

    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'native runtime qualification script is missing')
        directory = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(directory.cleanup)
        self.scratch = Path(directory.name)
        self.project = self.scratch / 'project'
        roles = self.project / '.codex/agents'
        roles.mkdir(parents=True)
        (roles / 'method_reviewer.toml').write_text('developer_instructions="full review role"\n')
        self.runtime = self.fixture.ResponsesFixture(self.project, self.scratch,
            'touch ' + str(self.project / 'inherited-permissions.txt'), self.project / 'gh')

    def request(self, marker):
        f = self.fixture
        request = native_request(marker)
        request.update(model=f.MODEL, reasoning={'effort': f.EFFORT})
        if marker == f.REVIEW_TASK:
            request['input'].append({'role': 'developer', 'content': 'full review role'})
        return request

    def nested_arguments(self, item, tool):
        self.assertEqual(item['type'], 'custom_tool_call')
        self.assertEqual((item['namespace'], item['name']), ('functions', 'exec'))
        self.assertNotIn('arguments', item)
        match = re.fullmatch(r'const r = await tools\.' + tool + r'\((.*)\); text\(r(?:\.output)?\);',
                             item['input'])
        self.assertIsNotNone(match, 'custom exec must receive raw JavaScript and surface the result')
        return json.loads(match[1])

    def test_reviewer_leak_refuses_before_any_response(self):
        f = self.fixture
        request = {'model': f.MODEL, 'reasoning': {'effort': f.EFFORT}, 'input': [
            {'role': 'user', 'content': f.REVIEW_TASK},
            {'role': 'developer', 'content': 'full review role ' + f.PRIVATE_PARENT}]}
        with self.assertRaisesRegex(AssertionError, 'parent'):
            f.validate_request(request, 'reviewer', 'full review role')
        request['input'][1]['content'] = 'full review role ' + f.PRIVATE_WORKER
        with self.assertRaisesRegex(AssertionError, 'worker'):
            f.validate_request(request, 'reviewer', 'full review role')

    def test_reviewer_requires_full_role_and_exact_routing(self):
        f = self.fixture
        request = {'model': f.MODEL, 'reasoning': {'effort': f.EFFORT}, 'input': [
            {'role': 'user', 'content': f.REVIEW_TASK},
            {'role': 'developer', 'content': 'partial role'}]}
        with self.assertRaisesRegex(AssertionError, 'full review'):
            f.validate_request(request, 'reviewer', 'full review role')
        request['input'][1]['content'] = 'full review role'
        f.validate_request(request, 'reviewer', 'full review role')
        request['model'] = 'other'
        with self.assertRaisesRegex(AssertionError, 'model'):
            f.validate_request(request, 'reviewer', 'full review role')

    def test_canonical_handle_must_come_from_actual_result(self):
        f = self.fixture
        self.assertEqual(f.canonical_handle('{"task_name":"/root/worker"}', 'worker'),
                         '/root/worker')
        for result in ('{"agent_id":"fake"}', '{"task_name":"worker"}',
                       '{"task_name":"/root/reviewer"}', 'unknown field cwd'):
            with self.subTest(result=result), self.assertRaises(AssertionError):
                f.canonical_handle(result, 'worker')

    def test_schema_must_advertise_v2_overrides(self):
        f = self.fixture
        request = native_request(f.PRIVATE_PARENT)
        schema = request['input'][1]['tools'][1]['tools'][0]
        fields = schema['parameters']['properties']
        f.validate_spawn_schema(request)
        for key in tuple(fields):
            with self.subTest(missing=key):
                del fields[key]
                with self.assertRaisesRegex(AssertionError, 'V2'):
                    f.validate_spawn_schema(request)
                fields[key] = {}
        for key in ('cwd', 'sandbox', 'prompt', 'fork_context', 'subagent_type',
                    'effort', 'run_in_background', 'hook_settings'):
            with self.subTest(unsupported=key):
                fields[key] = {}
                with self.assertRaisesRegex(AssertionError, 'unsupported'):
                    f.validate_spawn_schema(request)
                del fields[key]

    def test_function_and_custom_calls_follow_advertised_namespace(self):
        f = self.fixture
        request = native_request(f.PRIVATE_PARENT)
        spawn = f.tool_call(request, 'spawn_agent', {'task_name': 'worker'}, 'c1')
        self.assertEqual(spawn['namespace'], 'collaboration')
        self.assertEqual(json.loads(spawn['arguments']), {'task_name': 'worker'})
        script = 'text(await tools.apply_patch("*** Begin Patch\\n*** End Patch"));'
        custom = f.tool_call(request, 'exec', script, 'c2')
        self.assertEqual(custom['type'], 'custom_tool_call')
        self.assertEqual(custom['namespace'], 'functions')
        self.assertEqual(custom['input'], script)
        for name in ('exec_command', 'apply_patch'):
            with self.subTest(tool=name), self.assertRaisesRegex(AssertionError, 'not advertised'):
                f.tool_call(request, name, {}, 'c3')
        with self.assertRaisesRegex(AssertionError, 'raw custom'):
            f.tool_call(request, 'exec', {'input': script}, 'c4')

    def test_shell_uses_nested_exec_and_preserves_command_and_cwd(self):
        command = 'printf "%s\\n" "quoted `text` $value"'
        item = self.runtime.shell(self.request(self.fixture.PRIVATE_PARENT), command,
                                  'root_pwd', self.project / 'worker-lane')
        self.assertEqual(self.nested_arguments(item, 'exec_command'), {
            'cmd': command, 'workdir': str(self.project / 'worker-lane'),
            'max_output_tokens': 1000, 'yield_time_ms': 30000})
        self.assertTrue(item['input'].endswith('text(r.output);'))
        item = self.runtime.shell(self.request(self.fixture.PRIVATE_PARENT), 'pwd', 'pwd')
        self.assertNotIn('workdir', self.nested_arguments(item, 'exec_command'))

    def test_reviewer_patch_uses_nested_freeform_tool(self):
        item = self.runtime.response_item(self.request(self.fixture.REVIEW_TASK))
        self.assertEqual(item['call_id'], 'reviewer_patch')
        self.assertEqual(self.nested_arguments(item, 'apply_patch'),
            '*** Begin Patch\n*** Add File: reviewer-patch.txt\n+harmless fixture\n*** End Patch')

    def test_root_archives_actual_additional_tools_and_collects_custom_outputs(self):
        request = self.request(self.fixture.PRIVATE_PARENT)
        request['input'].append({'type': 'custom_tool_call_output', 'call_id': 'previous_pwd',
                                'output': [{'type': 'text', 'text': str(self.project) + '\n'}]})
        self.runtime.root_stage = 8
        self.runtime.response_item(request)
        self.assertEqual(json.loads((self.scratch / 'root.tools.json').read_text()),
                         request['input'][1]['tools'])
        self.assertIn(str(self.project), self.runtime.outputs['previous_pwd'].splitlines())

    def test_worker_attempts_merge_before_completion(self):
        request = self.request(self.fixture.WORK_TASK)
        self.runtime.counts['worker'] = 2
        item = self.runtime.response_item(request)
        self.assertEqual(item.get('call_id'), 'worker_merge')
        self.assertEqual(self.nested_arguments(item, 'exec_command')['cmd'], 'git merge fixture-never-merge')
        self.assertEqual(self.runtime.response_item(request)['content'][0]['text'], self.fixture.DONE['worker'])

    def test_spawn_negative_probes_require_handler_error_outputs(self):
        request = self.request(self.fixture.PRIVATE_PARENT)
        self.runtime.root_stage = 2
        item = self.runtime.root_response(request)
        self.assertEqual(json.loads(item['arguments'])['cwd'], str(self.project))
        with self.assertRaisesRegex(AssertionError, 'real handler error'):
            self.runtime.root_response(request)
        self.runtime.root_stage = 3
        self.runtime.outputs['unknown_field'] = 'unknown field `cwd`'
        item = self.runtime.root_response(request)
        self.assertEqual(json.loads(item['arguments'])['fork_context'], True)
        with self.assertRaisesRegex(AssertionError, 'real handler error'):
            self.runtime.root_response(request)
        self.runtime.outputs['invalid_fork'] = 'fork_context is not supported'
        item = self.runtime.root_response(request)
        self.assertEqual(item['call_id'], 'spawn_worker')

    def hook_record(self, tool, inputs, role):
        payload = {'agent_type': role, 'agent_id': 'native-child',
                   'tool_name': tool, 'tool_input': inputs}
        result = subprocess.run([str(ROOT / 'hooks/pre-tool-use')], input=json.dumps(payload),
                                capture_output=True, text=True, check=True)
        return {'payload': payload, 'exit_code': result.returncode, 'stdout': result.stdout,
                'stderr': result.stderr, 'plugin_root': str(self.scratch), 'ungated_control': False}

    def verification_records(self, tool='Bash', key='command'):
        f, runtime = self.fixture, self.runtime
        runtime.root_stage = 8
        runtime.handles = {role: '/root/' + role for role in ('worker', 'reviewer', 'control')}
        runtime.outputs.update(root_pwd=str(self.project), worker_lane_pwd=str(self.project / 'worker-lane'),
                               worker_session_pwd=str(self.project))
        (self.project / 'inherited-permissions.txt').touch()
        (self.project / 'fake-gh-calls.jsonl').write_text('["--version"]\n')
        records = [self.hook_record('apply_patch', {'input': '*** Begin Patch'}, 'method_reviewer')]
        probes = [('reviewer_shell', 'touch reviewer-shell.txt', 'method_reviewer'),
                  ('reviewer_remote', str(runtime.fake) + ' issue comment 1 --body fixture', 'method_reviewer'),
                  ('worker_merge', 'git merge fixture-never-merge', 'method_worker')]
        for call, command, role in probes:
            records.append(self.hook_record(tool, {key: command}, role))
            runtime.outputs[call] = 'refused: hook denied operation'
        runtime.outputs['reviewer_patch'] = 'refused: hook denied operation'
        records.append({'payload': {'agent_type': 'runtime_readonly_control'}, 'ungated_control': True})
        return records

    def verify_records(self, records):
        (self.project / 'hook-payloads.jsonl').write_text(
            ''.join(json.dumps(record) + '\n' for record in records))
        return self.runtime.verify(self.fixture.DONE['root'])

    def test_hook_denials_bind_to_shell_commands_for_both_payload_shapes(self):
        for tool, key in (('Bash', 'command'), ('exec_command', 'cmd')):
            with self.subTest(tool=tool):
                records = self.verification_records(tool, key)
                checks = self.verify_records(records)
                self.assertIn('worker_merge_denials', checks)
                self.assertEqual(checks['worker_merge_denials'], [tool])
                self.runtime.outputs['reviewer_remote'] = ''
                with self.assertRaisesRegex(AssertionError, 'blocking denial'):
                    self.verify_records(records)

    def test_worker_merge_requires_blocking_hook_and_native_denial_output(self):
        records = self.verification_records()
        for mutation in ('missing', 'allowed', 'no-output', 'wrong-command'):
            with self.subTest(mutation=mutation):
                altered = json.loads(json.dumps(records))
                self.runtime.outputs['worker_merge'] = 'refused: hook denied operation'
                if mutation == 'missing':
                    del altered[3]
                elif mutation == 'allowed':
                    altered[3]['stdout'] = ''
                elif mutation == 'no-output':
                    self.runtime.outputs['worker_merge'] = ''
                else:
                    altered[3]['payload']['tool_input']['command'] = 'git status'
                with self.assertRaisesRegex(AssertionError, 'worker|blocking denial'):
                    self.verify_records(altered)

    def test_observer_control_is_exact_for_both_shell_payload_shapes(self):
        observer = self.scratch / 'pre-tool-use'
        observer.write_text(self.fixture.HOOK_OBSERVER)
        shutil.copy2(ROOT / 'hooks/pre-tool-use', self.scratch / 'pre-tool-use.shipped')
        log = self.scratch / 'observer.jsonl'
        (self.scratch / 'fixture-observer.json').write_text(json.dumps({
            'control_command': self.runtime.control_command, 'log': str(log)}))
        for tool, key in (('Bash', 'command'), ('exec_command', 'cmd')):
            for role, command, expected in (
                ('runtime_readonly_control', self.runtime.control_command, True),
                ('runtime_readonly_control', self.runtime.control_command + ' extra', False),
                ('method_reviewer', self.runtime.control_command, False)):
                with self.subTest(tool=tool, role=role, command=command):
                    result = subprocess.run([os.sys.executable, str(observer)], capture_output=True,
                        text=True, input=json.dumps({'tool_name': tool, 'tool_input': {key: command},
                                                     'agent_type': role, 'agent_id': 'native-child'}), check=True)
                    record = json.loads(log.read_text().splitlines()[-1])
                    self.assertIs(record['ungated_control'], expected)
                    if expected:
                        self.assertEqual(result.stdout, '')
                    else:
                        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_shipped_hook_blocks_nested_reviewer_writes_and_worker_merge(self):
        for tool, key in (('Bash', 'command'), ('exec_command', 'cmd')):
            for role, command in (('method_reviewer', 'touch reviewer-shell.txt'),
                                  ('method_reviewer', 'gh api --method=POST repos/o/r/issues'),
                                  ('method_worker', 'git merge fixture-never-merge')):
                with self.subTest(tool=tool, role=role, command=command):
                    record = self.hook_record(tool, {key: command}, role)
                    output = json.loads(record['stdout'])['hookSpecificOutput']
                    self.assertEqual(output['permissionDecision'], 'deny')
                    self.assertIn('refused', output['permissionDecisionReason'])

    def test_tool_outputs_do_not_confuse_role_classification(self):
        f = self.fixture
        request = {'input': [{'role': 'user', 'content': f.PRIVATE_PARENT},
                            {'type': 'function_call_output', 'output': f.REVIEW_TASK}]}
        self.assertEqual(f.request_role(request), 'root')
        request['input'][0]['content'] = f.REVIEW_TASK
        self.assertEqual(f.request_role(request), 'reviewer')

    def test_isolated_environment_drops_inherited_credentials(self):
        f = self.fixture
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
            env = f.isolated_env(Path(directory), {
                'PATH': '/usr/bin:/bin', 'OPENAI_API_KEY': 'never-forward',
                'GH_TOKEN': 'never-forward', 'CODEX_HOME': '/private/home',
                'HTTPS_PROXY': 'never-forward', 'HOME': '/private/home'})
            self.assertEqual(env['CODEX_HOME'], str(Path(directory) / 'codex-home'))
            self.assertEqual(env['TMPDIR'], str(Path(directory) / 'tmp'))
            for key in ('OPENAI_API_KEY', 'GH_TOKEN', 'HTTPS_PROXY'):
                self.assertNotIn(key, env)

    def test_hook_trust_changes_when_command_or_timeout_changes(self):
        f = self.fixture
        handler = {'type': 'command', 'command': 'fixture command', 'timeout': 30}
        baseline = f.hook_hash('PreToolUse', '.*', handler)
        self.assertTrue(baseline.startswith('sha256:'))
        self.assertEqual(baseline, f.hook_hash('PreToolUse', '.*',
                                              dict(handler, **{'async': False})))
        self.assertNotEqual(baseline, f.hook_hash('PreToolUse', '.*',
                                                 dict(handler, timeout=31)))
        self.assertNotEqual(baseline, f.hook_hash('PreToolUse', '.*',
                                                 dict(handler, command='other')))

    def test_inventory_stops_at_real_fixture_git_root(self):
        f = self.fixture
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
            scratch = Path(directory)
            (scratch / '.codex').mkdir()
            (scratch / '.codex/config.toml').write_text('unrelated parent config')
            project = scratch / 'project'
            project.mkdir()
            subprocess.run(['git', 'init', '--quiet', str(project)], check=True,
                           capture_output=True)
            home = scratch / 'isolated-home'
            home.mkdir()
            self.assertEqual(f.inventory(project, home)['external_layers'], [])
            (project / '.codex').mkdir()
            (project / '.codex/hooks.json').write_text('{}')
            with self.assertRaisesRegex(AssertionError, 'external'):
                f.inventory(project, home)
