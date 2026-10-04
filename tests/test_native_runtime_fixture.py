"""Test the qualification fixture's refusal paths; these are not runtime qualification."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/test-native-runtime.py'


def native_request(marker):
    """Representative 0.160.0 wire catalog: nested tools are not outer members."""
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


def agent_message(kind, author, recipient, payload, encrypted=False):
    header = f'Message Type: {kind}\nTask name: {recipient}\nSender: {author}\nPayload:\n'
    content = [{'type': 'input_text', 'text': header + ('' if encrypted else payload)}]
    if encrypted:
        content.append({'type': 'encrypted_content', 'encrypted_content': payload})
    return {'type': 'agent_message', 'id': 'amsg_fixture', 'author': author,
            'recipient': recipient, 'content': content}


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
        self.scratch = Path(directory.name).resolve()
        self.project = self.scratch / 'project'
        roles = self.project / '.codex/agents'
        roles.mkdir(parents=True)
        (roles / 'method_reviewer.toml').write_text('developer_instructions="full review role"\n')
        delivered = subprocess.run([str(ROOT / 'hooks/session-start'), 'orchestrator'],
            capture_output=True, text=True, check=True)
        self.whole_context = json.loads(delivered.stdout)['hookSpecificOutput']['additionalContext']
        self.session_record = {'payload': {'source': 'startup', 'hook_event_name': 'SessionStart'},
            'exit_code': delivered.returncode, 'stdout': delivered.stdout, 'stderr': delivered.stderr,
            'plugin_root': str(ROOT)}
        self.runtime = self.fixture.ResponsesFixture(self.project, self.scratch,
            'touch ' + str(self.project / 'inherited-permissions.txt'), self.project / 'gh')

    def request(self, marker):
        f = self.fixture
        request = native_request(marker)
        request.update(model=f.MODEL, reasoning={'effort': f.EFFORT})
        if marker == f.REVIEW_TASK:
            request['input'].append({'role': 'developer', 'content': 'full review role'})
        elif marker == f.PRIVATE_PARENT:
            request['input'].append({'role': 'developer', 'content': self.whole_context})
        return request

    def nested_arguments(self, item, tool):
        self.assertEqual(item['type'], 'custom_tool_call')
        self.assertEqual((item['namespace'], item['name']), ('functions', 'exec'))
        self.assertNotIn('arguments', item)
        match = re.fullmatch(r'const r = await tools\.' + tool + r'\((.*)\); text\(r(?:\.output)?\);',
                             item['input'])
        self.assertIsNotNone(match, 'custom exec must receive raw JavaScript and surface the result')
        return json.loads(match[1])

    def test_duplicate_static_worker_role_in_actual_request_refuses(self):
        (self.project / '.codex/agents/method_reviewer.toml').unlink()
        installed = subprocess.run([os.sys.executable, str(ROOT / 'scripts/install'),
            '--project', str(self.project), '--host-version', '0.160.0'],
            capture_output=True, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        runtime = self.fixture.ResponsesFixture(self.project, self.scratch,
            'touch ' + str(self.project / 'inherited-permissions.txt'), self.project / 'gh')
        contract = tomllib.loads((self.project / '.codex/agents/method_worker.toml').read_text())['developer_instructions']
        request = self.request(self.fixture.WORK_TASK)
        request['input'].extend([{'role': 'developer', 'content': contract},
                                 {'role': 'user', 'content': contract}])
        with self.assertRaisesRegex(AssertionError, 'static role must occur once'):
            runtime.response_item(request)

    def installed_helper_runtime(self):
        (self.project / '.codex/agents/method_reviewer.toml').unlink()
        installed = subprocess.run([os.sys.executable, str(ROOT / 'scripts/install'),
            '--project', str(self.project), '--host-version', '0.160.0'],
            capture_output=True, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        return self.fixture.ResponsesFixture(self.project, self.scratch,
            'touch ' + str(self.project / 'inherited-permissions.txt'), self.project / 'gh')

    def helper_request(self, runtime, role):
        marker = self.fixture.HELPER_TASK if role == 'helper' else self.fixture.REVIEW_HELPER_TASK
        request = self.request(marker)
        request['input'].append({'role': 'developer', 'content': runtime.role_contracts[role]})
        return request

    def test_helpers_probe_merge_write_and_cross_role_after_ordinary_read(self):
        runtime = self.installed_helper_runtime()
        for role, steps in (('helper', ('helper_material', 'helper_merge')),
                            ('review_helper', ('review_helper_material', 'review_helper_shell',
                                               'review_helper_cross_role'))):
            for index, call in enumerate(steps):
                runtime.counts[role] = index
                request = self.helper_request(runtime, role)
                item = runtime.response_item(request)
                self.assertEqual(item['call_id'], call)
                if call.endswith('_material'):
                    args = self.nested_arguments(item, 'exec_command')
                    self.assertEqual(args['cmd'], 'cat helper-material.txt')
                    self.assertEqual(args['workdir'], str(self.project))
                elif call.endswith('cross_role'):
                    args = json.loads(item['arguments'])
                    self.assertEqual(args['agent_type'], 'method_helper')
                    self.assertEqual(args['fork_turns'], 'none')

    def test_helper_requests_reject_leaks_partial_role_and_wrong_settings(self):
        runtime = self.installed_helper_runtime()
        for role in ('helper', 'review_helper'):
            for mutation in ('parent', 'worker', 'partial', 'duplicate', 'duplicate-shared', 'missing-shared', 'model', 'effort'):
                with self.subTest(role=role, mutation=mutation):
                    request = self.helper_request(runtime, role)
                    if mutation in ('parent', 'worker'):
                        request['input'].append({'role': 'developer', 'content':
                            self.fixture.PRIVATE_PARENT if mutation == 'parent' else self.fixture.PRIVATE_WORKER})
                    elif mutation == 'partial':
                        request['input'][-1]['content'] = runtime.role_contracts[role][:500]
                    elif mutation == 'duplicate':
                        request['input'].append(request['input'][-1])
                    elif mutation == 'duplicate-shared':
                        request['input'].append({'role': 'developer', 'content': runtime.shared})
                    elif mutation == 'missing-shared':
                        request['input'][-1]['content'] = runtime.role_contracts[role].replace(runtime.shared, '')
                    elif mutation == 'model':
                        request['model'] = 'wrong'
                    else:
                        request['reasoning']['effort'] = 'low'
                    with self.assertRaises(AssertionError):
                        runtime.response_item(request)

    def test_helper_denials_require_actual_hook_identity_command_and_tool_output(self):
        records = self.verification_records()
        runtime = self.installed_helper_runtime()
        runtime.outputs.update(self.runtime.outputs)
        runtime.handles = {role: '/root/' + role for role in runtime.sequence}
        runtime.root_stage = runtime.finished_stage
        runtime.root_context_verified = True
        runtime.outputs.update(helper_material='Ordinary material; no repository lane or PR is assigned.',
                               review_helper_material='Ordinary material; no repository lane or PR is assigned.')
        probes = [('helper_merge', 'exec_command', {'cmd': 'git merge fixture-never-merge'}, 'method_helper'),
                  ('review_helper_shell', 'exec_command', {'cmd': 'touch review-helper-shell.txt'}, 'method_review_helper'),
                  ('review_helper_cross_role', 'collaborationspawn_agent', {
                      'agent_type': 'method_helper', 'task_name': 'rejected_helper_cross_role',
                      'fork_turns': 'none', 'model': self.fixture.MODEL,
                      'reasoning_effort': self.fixture.EFFORT}, 'method_review_helper')]
        for call, tool, inputs, role in probes:
            records.append(self.hook_record(tool, inputs, role))
            runtime.outputs[call] = 'refused: hook denied operation'
        self.runtime = runtime
        checks = self.verify_records(records)
        self.assertEqual(checks['helper_merge_denials'], ['exec_command'])
        self.assertEqual(len(checks['review_helper_denials']), 2)
        for call, _, _, _ in probes:
            with self.subTest(call=call):
                saved = runtime.outputs[call]
                runtime.outputs[call] = ''
                with self.assertRaisesRegex(AssertionError, 'blocking denial'):
                    self.verify_records(records)
                runtime.outputs[call] = saved
        for index in range(len(records) - 3, len(records)):
            for mutation in ('missing', 'allowed', 'wrong-role', 'wrong-input'):
                with self.subTest(index=index, mutation=mutation):
                    altered = json.loads(json.dumps(records))
                    if mutation == 'missing':
                        del altered[index]
                    elif mutation == 'allowed':
                        altered[index]['stdout'] = ''
                    elif mutation == 'wrong-role':
                        altered[index]['payload']['agent_type'] = 'method_worker'
                    else:
                        altered[index]['payload']['tool_input'] = {'cmd': 'git status'}
                    with self.assertRaises(AssertionError):
                        self.verify_records(altered)

    def test_root_provider_requires_one_complete_inline_orchestrator(self):
        page = (ROOT / 'reference/orchestrator.md').read_bytes().decode('utf-8')
        marker = '--- codex-method whole context ---\n'
        for content in (marker + page[:8000],
                        marker + page[:8000] + '\nSaved full output to file /scratch/spill.txt',
                        marker + page + marker + page):
            with self.subTest(content=content[:50]):
                request = self.request(self.fixture.PRIVATE_PARENT)
                request['input'] = [item for item in request['input'] if item.get('role') != 'developer']
                request['input'].append({'role': 'developer', 'content': content})
                with self.assertRaisesRegex(AssertionError, 'whole inline orchestrator'):
                    self.runtime.response_item(request)

    def test_root_provider_rejects_context_reassembled_across_fragments(self):
        page = (ROOT / 'reference/orchestrator.md').read_bytes().decode('utf-8')
        request = self.request(self.fixture.PRIVATE_PARENT)
        request['input'] = [item for item in request['input'] if item.get('role') != 'developer']
        request['input'].extend([{'role': 'developer', 'content':
            '--- codex-method whole context ---\n' + page[:8000]},
            {'role': 'developer', 'content': page[8000:]}])
        with self.assertRaisesRegex(AssertionError, 'whole inline orchestrator'):
            self.runtime.response_item(request)

    def test_actual_hook_inventory_uses_resolved_hashes_and_rejects_other_sources(self):
        f = self.fixture
        prefix = f.PLUGIN_ID + ':hooks/hooks.json:'
        hooks = [{'key': prefix + event + ':0:0', 'currentHash': 'sha256:' + 'a' * 64}
                 for event in ('session_start', 'pre_tool_use')]
        response = {'result': {'data': [{'hooks': hooks, 'errors': []}]}}
        self.assertEqual(f.trusted_inventory(response),
                         [{'key': hook['key'], 'hash': hook['currentHash']} for hook in hooks])
        for wrong in ({'error': {'message': 'refused'}}, {'result': {'data': []}},
                      {'result': {'data': [{'hooks': [dict(hooks[0], key='unrelated')]}]}},
                      {'result': {'data': [{'hooks': [dict(hooks[0], currentHash='wrong')]}]}}):
            with self.subTest(response=wrong), self.assertRaises(AssertionError):
                f.trusted_inventory(wrong)

    def test_reviewer_cross_role_spawn_is_an_actual_typed_native_call(self):
        self.runtime.counts['reviewer'] = 3
        item = self.runtime.response_item(self.request(self.fixture.REVIEW_TASK))
        self.assertEqual(item['call_id'], 'reviewer_cross_role')
        args = json.loads(item['arguments'])
        self.assertEqual(args['agent_type'], 'method_worker')
        self.assertEqual((args['model'], args['reasoning_effort'], args['fork_turns']),
                         ('gpt-6.1-sol', 'high', 'none'))

    def test_prepare_registers_declared_readonly_control_without_rejected_cwd(self):
        f = self.fixture
        run_logged = f.run_logged
        installed = {}

        def local_setup(command, env, cwd, directory, name, **kwargs):
            # Plugin registration needs the CLI; keep Git, installer, role writes,
            # and hook setup real without launching a provider or binding sockets.
            if name in ('marketplace-add', 'plugin-add'):
                return subprocess.CompletedProcess(command, 0, '', '')
            result = run_logged(command, env, cwd, directory, name, **kwargs)
            if name == 'role-install':
                installed.update({path.name: path.read_bytes()
                                  for path in (cwd / '.codex/agents').glob('*.toml')})
            return result

        for installer in (None, ROOT / 'scripts/install'):
            with self.subTest(installer=installer):
                scratch = self.scratch / ('installed' if installer else 'fallback')
                scratch.mkdir()
                env = f.isolated_env(scratch)
                with patch.object(f, 'run_logged', side_effect=local_setup), \
                        patch.object(f, 'discover_hook_trust', return_value=[
                            {'key': f.PLUGIN_ID + ':hooks/hooks.json:pre_tool_use:0:0',
                             'hash': 'sha256:' + 'a' * 64}]):
                    project, command, fake = f.prepare('unused-codex', scratch, env, installer, {})
                roles = project / '.codex/agents'
                control = tomllib.loads((roles / 'runtime_readonly_control.toml').read_text())
                self.assertEqual(set(control), {
                    'name', 'description', 'developer_instructions', 'sandbox_mode'})
                self.assertEqual(control['name'], 'runtime_readonly_control')
                self.assertTrue(control['description'].strip())
                self.assertIn(f.CONTROL_TASK, control['developer_instructions'])
                self.assertEqual(control['sandbox_mode'], 'read-only')
                for name, content in installed.items():
                    self.assertEqual((roles / name).read_bytes(), content)

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
        runtime.response_item(self.request(f.PRIVATE_PARENT))
        (self.project / 'session-start-payloads.jsonl').write_text(json.dumps(self.session_record) + '\n')
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
        records.append(self.hook_record('collaborationspawn_agent', {
            'agent_type': 'method_worker', 'task_name': 'rejected_cross_role',
            'fork_turns': 'none', 'model': f.MODEL, 'reasoning_effort': f.EFFORT}, 'method_reviewer'))
        runtime.outputs['reviewer_cross_role'] = 'refused: hook denied operation'
        records.append({'payload': {'agent_type': 'runtime_readonly_control'}, 'ungated_control': True})
        return records

    def verify_records(self, records):
        (self.project / 'hook-payloads.jsonl').write_text(
            ''.join(json.dumps(record) + '\n' for record in records))
        return self.runtime.verify(self.fixture.DONE['root'])

    def test_extra_session_start_invocations_fail_runtime_verification(self):
        records = self.verification_records()
        path = self.project / 'session-start-payloads.jsonl'
        path.write_text(path.read_text() * 8)
        with self.assertRaisesRegex(AssertionError, 'one SessionStart invocation'):
            self.verify_records(records)

    def test_root_provider_accepts_whole_inline_page(self):
        self.runtime.response_item(self.request(self.fixture.PRIVATE_PARENT))
        self.assertTrue(self.runtime.root_context_verified)

    def test_bwrap_setup_failure_is_diagnosed_and_never_passes_probe_assertions(self):
        error = 'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n'
        for call in ('root_pwd', 'worker_lane_pwd', 'worker_session_pwd', 'control_write'):
            for success_evidence in (False, True):
                with self.subTest(call=call, success_evidence=success_evidence):
                    records = self.verification_records()
                    command_output = self.runtime.outputs.get(call, '') if success_evidence else ''
                    if call == 'control_write' and not success_evidence:
                        (self.project / 'inherited-permissions.txt').unlink()
                    request = self.request(self.fixture.PRIVATE_PARENT)
                    request['input'].append({'type': 'custom_tool_call_output', 'call_id': call,
                        'output': [
                            {'type': 'input_text', 'text': 'Script completed\nWall time 0.1 seconds\nOutput:\n'},
                            {'type': 'input_text', 'text': error + command_output}]})
                    self.runtime.response_item(request)
                    with self.assertRaisesRegex(AssertionError, call + ':.*sandbox setup.*bwrap:') as failure:
                        self.verify_records(records)
                    self.assertIn(error.strip(), str(failure.exception))

    def test_real_pwd_outputs_still_pass_verification(self):
        records = self.verification_records()
        lane = self.project / 'worker-lane'
        lane.mkdir()
        request = self.request(self.fixture.PRIVATE_PARENT)
        for call, cwd in (('root_pwd', self.project), ('worker_lane_pwd', lane),
                          ('worker_session_pwd', self.project)):
            result = subprocess.run(['pwd'], cwd=cwd, capture_output=True, text=True, check=True)
            request['input'].append({'type': 'custom_tool_call_output', 'call_id': call,
                'output': [
                    {'type': 'input_text', 'text': 'Script completed\nWall time 0.1 seconds\nOutput:\n'},
                    {'type': 'input_text', 'text': result.stdout}]})
        self.runtime.response_item(request)
        checks = self.verify_records(records)
        self.assertTrue(checks['worker_explicit_lane_cwd'])
        self.assertEqual(checks['child_session_cwd'], str(self.project))

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

    def test_readonly_result_reports_declared_role_and_requires_filesystem_write(self):
        records = self.verification_records()
        checks = self.verify_records(records)
        self.assertEqual(checks['per_role_readonly'],
                         "UNSUPPORTED: declared read-only role's exact ungated child write "
                         'succeeded with parent permissions')
        (self.project / 'inherited-permissions.txt').unlink()
        with self.assertRaisesRegex(AssertionError, 'did not actually write'):
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
                                  ('method_worker', 'git merge fixture-never-merge'),
                                  ('method_helper', 'git merge fixture-never-merge'),
                                  ('method_helper', 'git push'),
                                  ('method_helper', 'scripts/guard merge --execute'),
                                  ('method_review_helper', 'touch review-helper-shell.txt'),
                                  ('method_review_helper', 'gh issue comment 1 --body fixture')):
                with self.subTest(tool=tool, role=role, command=command):
                    record = self.hook_record(tool, {key: command}, role)
                    output = json.loads(record['stdout'])['hookSpecificOutput']
                    self.assertEqual(output['permissionDecision'], 'deny')
                    self.assertIn('refused', output['permissionDecisionReason'])

    def test_review_helper_reads_and_only_fresh_review_descendants_are_admitted(self):
        read = self.hook_record('exec_command', {'cmd': 'cat helper-material.txt'}, 'method_review_helper')
        self.assertEqual(read['stdout'], '')
        for agent_type, fork, allowed in (('method_review_helper', 'none', True),
                                          ('method_review_helper', 'all', False),
                                          ('method_helper', 'none', False),
                                          ('method_worker', 'none', False)):
            with self.subTest(agent_type=agent_type, fork=fork):
                record = self.hook_record('collaborationspawn_agent', {
                    'agent_type': agent_type, 'fork_turns': fork, 'task_name': 'nested_review',
                    'model': self.fixture.MODEL, 'reasoning_effort': self.fixture.EFFORT}, 'method_review_helper')
                if allowed:
                    self.assertEqual(record['stdout'], '')
                else:
                    self.assertEqual(json.loads(record['stdout'])['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_tool_outputs_do_not_confuse_role_classification(self):
        f = self.fixture
        request = {'input': [{'role': 'user', 'content': f.PRIVATE_PARENT},
                            {'type': 'function_call_output', 'output': f.REVIEW_TASK}]}
        self.assertEqual(f.request_role(request), 'root')
        request['input'][0]['content'] = f.REVIEW_TASK
        self.assertEqual(f.request_role(request), 'reviewer')

    def test_new_task_agent_message_selects_actual_child_response(self):
        f = self.fixture
        for role, marker, call_id in (('worker', f.WORK_TASK, 'worker_lane_pwd'),
                                      ('reviewer', f.REVIEW_TASK, 'reviewer_patch'),
                                      ('control', f.CONTROL_TASK, 'control_write')):
            for encrypted in (False, True):
                with self.subTest(role=role, encrypted=encrypted):
                    request = self.request(marker)
                    request['input'][0]['content'] = [
                        {'type': 'input_text', 'text': '<environment_context>fixture</environment_context>'}]
                    payload = marker + ('\n' + f.PRIVATE_WORKER if role == 'worker' else '')
                    request['input'].append(agent_message('NEW_TASK', '/root', '/root/' + role,
                                                         payload, encrypted))
                    other_marker = f.WORK_TASK if role == 'reviewer' else f.REVIEW_TASK
                    other_role = 'worker' if role == 'reviewer' else 'reviewer'
                    for kind in ('function_call_output', 'custom_tool_call_output'):
                        request['input'].append({'type': kind, 'call_id': kind, 'output': [
                            {'type': 'text', 'text': other_marker},
                            agent_message('NEW_TASK', '/root', '/root/' + other_role, other_marker, True)]})
                    self.runtime.counts[role] = 0
                    self.assertEqual(self.runtime.response_item(request)['call_id'], call_id)

    def test_new_task_requires_one_marker_and_matching_delivery_paths(self):
        f = self.fixture
        for payload, author, recipient, error in (
                ('no task marker', '/root', '/root/worker', 'cannot uniquely identify'),
                (f.WORK_TASK + '\n' + f.REVIEW_TASK, '/root', '/root/worker', 'cannot uniquely identify'),
                (f.WORK_TASK, '/root', '/root/reviewer', 'delivery paths'),
                (f.WORK_TASK, '/root/control', '/root/worker', 'delivery paths')):
            with self.subTest(payload=payload, author=author, recipient=recipient):
                request = {'input': [agent_message('NEW_TASK', author, recipient, payload, True)]}
                with self.assertRaisesRegex(AssertionError, error):
                    f.request_role(request)

    def test_mailbox_messages_do_not_select_requesting_thread(self):
        f = self.fixture
        for kind in ('FINAL_ANSWER', 'MESSAGE'):
            with self.subTest(kind=kind):
                request = self.request(f.PRIVATE_PARENT)
                request['input'].append(agent_message(kind, '/root/worker', '/root', f.WORK_TASK, True))
                self.assertEqual(f.request_role(request), 'root')
                request['input'][0]['content'] = 'environment only'
                with self.assertRaisesRegex(AssertionError, 'cannot uniquely identify'):
                    f.request_role(request)

    def test_errored_final_answer_fails_before_mailbox_wait(self):
        f = self.fixture
        payload = 'Agent errored: provider refused the child request.\nThis agent\'s turn failed.'
        for role, stage in (('worker', 5), ('reviewer', 6), ('control', 7)):
            for encrypted in (False, True):
                with self.subTest(role=role, encrypted=encrypted):
                    self.runtime.root_stage = stage
                    self.runtime.handles.pop(role, None)
                    self.runtime.outputs['spawn_' + role] = json.dumps({'task_name': '/root/' + role})
                    request = self.request(f.PRIVATE_PARENT)
                    request['input'].append(agent_message('FINAL_ANSWER', '/root/' + role, '/root',
                                                         payload, encrypted))
                    with self.assertRaisesRegex(AssertionError, role + ':.*Agent errored') as failure:
                        self.runtime.response_item(request)
                    self.assertIn(payload, str(failure.exception))
                    self.assertEqual(self.runtime.waits[role], 0)
                    self.assertEqual(self.runtime.root_stage, stage)

    def test_successful_final_answer_advances_parent_without_wait(self):
        f = self.fixture
        for role, stage, next_role in (('worker', 5, 'reviewer'), ('reviewer', 6, 'control'),
                                       ('control', 7, None)):
            for encrypted in (False, True):
                with self.subTest(role=role, encrypted=encrypted):
                    self.runtime.root_stage = stage
                    self.runtime.handles[role] = '/root/' + role
                    self.runtime.outputs['ack_' + role] = ''
                    request = self.request(f.PRIVATE_PARENT)
                    request['input'].append(agent_message('FINAL_ANSWER', '/root/' + role, '/root',
                                                         f.DONE[role], encrypted))
                    item = self.runtime.response_item(request)
                    if next_role:
                        self.assertEqual(item['call_id'], 'spawn_' + next_role)
                    else:
                        self.assertEqual(item['content'][0]['text'], f.DONE['root'])
                    self.assertEqual(self.runtime.root_stage, stage + 1)
                    self.assertEqual(self.runtime.waits[role], 0)

    def test_error_text_outside_expected_child_final_answer_still_waits(self):
        f = self.fixture
        error = 'Agent errored: unrelated message'
        for item in (agent_message('MESSAGE', '/root/worker', '/root', error),
                     agent_message('FINAL_ANSWER', '/root/reviewer', '/root', error),
                     agent_message('FINAL_ANSWER', '/root/worker', '/root/control', error),
                     {'type': 'custom_tool_call_output', 'call_id': 'other', 'output':
                      agent_message('FINAL_ANSWER', '/root/worker', '/root', error)}):
            with self.subTest(item=item):
                self.runtime.root_stage = 5
                self.runtime.handles['worker'] = '/root/worker'
                self.runtime.outputs['ack_worker'] = ''
                self.runtime.waits['worker'] = 0
                request = self.request(f.PRIVATE_PARENT)
                request['input'].append(item)
                response = self.runtime.response_item(request)
                self.assertEqual(response['name'], 'wait_agent')
                self.assertEqual(self.runtime.waits['worker'], 1)

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
