"""Test the qualification fixture's refusal paths; these are not runtime qualification."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/test-native-runtime.py'


class NativeRuntimeFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SCRIPT.exists():
            spec = importlib.util.spec_from_file_location('native_runtime_fixture', SCRIPT)
            cls.fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.fixture)

    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'native runtime qualification script is missing')

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
        schema = {'type': 'function', 'name': 'spawn_agent', 'parameters': {'properties': {
            key: {} for key in ('task_name', 'message', 'agent_type', 'fork_turns', 'model',
                                'reasoning_effort')}}}
        request = {'tools': [schema]}
        f.validate_spawn_schema(request)
        del schema['parameters']['properties']['fork_turns']
        with self.assertRaisesRegex(AssertionError, 'V2'):
            f.validate_spawn_schema(request)

    def test_function_and_custom_calls_follow_advertised_namespace(self):
        f = self.fixture
        request = {'tools': [{'type': 'namespace', 'name': 'collaboration', 'tools': [
            {'type': 'function', 'name': 'spawn_agent', 'parameters': {}}]},
            {'type': 'custom', 'name': 'apply_patch', 'format': {'type': 'grammar'}}]}
        spawn = f.tool_call(request, 'spawn_agent', {'task_name': 'worker'}, 'c1')
        self.assertEqual(spawn['namespace'], 'collaboration')
        self.assertEqual(json.loads(spawn['arguments']), {'task_name': 'worker'})
        patch = f.tool_call(request, 'apply_patch', '*** Begin Patch\n*** End Patch', 'c2')
        self.assertEqual(patch['type'], 'custom_tool_call')
        self.assertNotIn('namespace', patch)
        with self.assertRaisesRegex(AssertionError, 'not advertised'):
            f.tool_call(request, 'exec_command', {}, 'c3')

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
