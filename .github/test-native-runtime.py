#!/usr/bin/env python3
"""Qualify Codex 0.160.0 native agents against an auth-free LOCAL Responses provider.

One `codex exec` hosts the root and actual native children. No worker/reviewer CLI
processes, external provider, credentials, remote writes, or sandbox bypass are used.
Requires Python 3.11+ and loopback sockets. All fixture data and retained evidence
live beneath --scratch-root (or TMPDIR). A blocked run exits 2; failed checks exit 1.

Example:
  TMPDIR=/path/to/job/scratch python3 .github/test-native-runtime.py --codex-version 0.160.0
After scripts/install is finalized, add --installer scripts/install to qualify that
consumer too. Without it, instructions-only fixture roles are explicitly reported
as a missing installation consumer, even if the native runtime checks pass.

SSE mechanics adapted from devstandard/.github/test-codex-runtime.py. Runtime
contracts checked against openai/codex tag rust-v0.160.0, specifically native V2
spawn.rs, agent/child_config.rs, hooks/engine/discovery.rs, and config/fingerprint.rs.
The copied hook executable is instrumented to record actual payloads/results. Its
policy is unchanged for worker/reviewer. The sole ungated control is an exact local
write by runtime_readonly_control, whose accepted role file declares read-only.
The loader accepts sandbox_mode but rejects cwd; the negative control checks that
the native child still writes under parent permissions despite that declaration.
This qualifies ordinary hook paths, not adversarial OS or credential isolation.
"""
import argparse
from collections import Counter
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import runpy
import select
import time
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import tomllib


ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.160.0'
MODEL = 'gpt-6.1-sol'
EFFORT = 'high'
PRIVATE_PARENT = 'NATIVE_FIXTURE_PARENT_PRIVATE_1600'
PRIVATE_WORKER = 'NATIVE_FIXTURE_WORKER_PRIVATE_1600'
WORK_TASK = 'NATIVE_FIXTURE_WORK_TASK_1600'
REVIEW_TASK = 'NATIVE_FIXTURE_REVIEW_TASK_1600'
CONTROL_TASK = 'NATIVE_FIXTURE_CONTROL_TASK_1600'
HELPER_TASK = 'NATIVE_FIXTURE_HELPER_TASK_1600'
REVIEW_HELPER_TASK = 'NATIVE_FIXTURE_REVIEW_HELPER_TASK_1600'
DONE = {role: 'NATIVE_FIXTURE_' + role.upper() + '_DONE_1600'
        for role in ('root', 'worker', 'reviewer', 'control', 'helper', 'review_helper')}
PLUGIN_ID = 'codex-method@codex-method'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fragments(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from fragments(item)
    elif isinstance(value, list):
        for item in value:
            yield from fragments(item)


def input_text(request):
    return '\n'.join(fragments(request.get('input', [])))


def agent_message_text(item):
    # MultiAgentV2 splits the envelope and task across input_text and
    # encrypted_content blocks; in the local fixture the latter holds plain text.
    return '\n'.join(block.get(key, '') for block in item.get('content', [])
                    for kind, key in (('input_text', 'text'), ('encrypted_content', 'encrypted_content'))
                    if block.get('type') == kind and isinstance(block.get(key), str))


def request_role(request):
    # Only user tasks and top-level NEW_TASK deliveries select a thread. Never
    # scan tool outputs or ordinary/final mailbox messages for task markers.
    # Paths cross-check the marker, never select a role: this fixture's children
    # must receive NEW_TASK from /root at /root/<selected role>.
    tasks, deliveries = [], []
    for item in request.get('input', []):
        if item.get('type') in ('function_call_output', 'custom_tool_call_output'):
            continue
        if item.get('type') == 'agent_message':
            text = agent_message_text(item)
            if text.startswith('Message Type: NEW_TASK\n'):
                tasks.append(text)
                deliveries.append(item)
        elif item.get('role') == 'user':
            tasks.extend(fragments(item.get('content', '')))
    selection = '\n'.join(tasks)
    matches = [role for role, marker in (('root', PRIVATE_PARENT), ('worker', WORK_TASK),
               ('reviewer', REVIEW_TASK), ('control', CONTROL_TASK), ('helper', HELPER_TASK),
               ('review_helper', REVIEW_HELPER_TASK)) if marker in selection]
    require(len(matches) == 1, 'cannot uniquely identify actual requesting thread: ' + repr(matches))
    for item in deliveries:
        require(matches[0] != 'root' and item.get('author') == '/root'
                and item.get('recipient') == '/root/' + matches[0],
                matches[0] + ': NEW_TASK delivery paths disagree with task marker: '
                + repr((item.get('author'), item.get('recipient'))))
    return matches[0]


def validate_request(request, role, full_role):
    require(request.get('model') == MODEL, role + ': actual model routing changed')
    require(request.get('reasoning', {}).get('effort') == EFFORT,
            role + ': actual reasoning effort routing changed')
    if role == 'reviewer':
        carried = '\n'.join(fragments([request.get('instructions', ''), request.get('input', [])]))
        require(PRIVATE_PARENT not in carried, 'reviewer received private parent conversation')
        require(PRIVATE_WORKER not in carried, 'reviewer received private worker sentinel')
        require(full_role and full_role in carried, 'reviewer did not receive the full review role')


def validate_root_context(request, page):
    """Require one complete inline carrier in actual provider input, never recovered spill text."""
    marker = '--- codex-method whole context ---\n'
    supplied = list(fragments([request.get('instructions', ''), request.get('input', [])]))
    contexts = [text for text in supplied if marker in text]
    require(page and len(contexts) == 1 and contexts[0].count(marker) == 1
            and marker + page in contexts[0],
            'root: one whole inline orchestrator page is required in provider input')


def advertised_tools(request):
    """Retain the actual wire catalog, including the code-mode input item."""
    supplied = list(request.get('tools', []))
    for item in request.get('input', []):
        if item.get('type') == 'additional_tools':
            supplied.extend(item.get('tools', []))
    return supplied


def catalog(request):
    found = {}
    for tool in advertised_tools(request):
        if tool.get('type') == 'namespace':
            for member in tool.get('tools', []):
                found[member['name']] = (tool['name'], member)
        elif tool.get('name'):
            found[tool['name']] = (None, tool)
    return found


def tool_call(request, name, arguments, call_id):
    offered = catalog(request)
    require(name in offered, name + ' not advertised by actual runtime')
    namespace, schema = offered[name]
    item = {'id': 'fc_' + call_id, 'call_id': call_id, 'name': name}
    if namespace:
        item['namespace'] = namespace
    if schema.get('type') == 'custom':
        require(isinstance(arguments, str), name + ': expected raw custom tool input')
        item.update(type='custom_tool_call', input=arguments)
    else:
        require(isinstance(arguments, dict), name + ': expected structured function arguments')
        item.update(type='function_call', arguments=json.dumps(arguments))
    return item


def validate_spawn_schema(request):
    offered = catalog(request)
    require('spawn_agent' in offered, 'actual runtime did not advertise V2 spawn_agent')
    fields = offered['spawn_agent'][1].get('parameters', {}).get('properties', {})
    expected = {'task_name', 'message', 'agent_type', 'fork_turns', 'model', 'reasoning_effort'}
    require(expected <= fields.keys(), 'actual spawn schema lacks V2 fields or explicit overrides')
    require(not {'cwd', 'sandbox', 'prompt', 'fork_context', 'subagent_type',
                 'effort', 'run_in_background', 'hook_settings'}.intersection(fields),
            'actual spawn schema advertises unsupported V2 fields')
    return sorted(fields)


def output_text(output):
    return output if isinstance(output, str) else '\n'.join(fragments(output))


def canonical_handle(result, task):
    try:
        parsed = json.loads(result)
    except (ValueError, TypeError):
        raise AssertionError(task + ': spawn returned no JSON canonical handle') from None
    handle = parsed.get('task_name') if isinstance(parsed, dict) else None
    require(isinstance(handle, str) and handle.startswith('/') and handle.endswith('/' + task),
            task + ': spawn did not return its canonical task_name: ' + str(result))
    return handle


def toml(value):
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(key) + '=' + toml(item) for key, item in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(toml(item) for item in value) + ']'
    return json.dumps(value, ensure_ascii=False)


def trusted_inventory(response):
    require('error' not in response, 'actual hooks/list failed: ' + repr(response.get('error')))
    rows = response.get('result', {}).get('data', [])
    require(len(rows) == 1, 'hooks/list did not return the exact fixture cwd')
    row = rows[0]
    require(not row.get('errors'), 'hook discovery errors: ' + repr(row.get('errors')))
    hooks = row.get('hooks', [])
    require(hooks, 'actual hooks/list discovered no shipped hooks')
    trust = []
    for hook in hooks:
        key, digest = hook.get('key', ''), hook.get('currentHash', '')
        require(key.startswith(PLUGIN_ID + ':hooks/hooks.json:'),
                'unexpected hook source in isolated fixture: ' + key)
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'invalid engine hook hash')
        trust.append({'key': key, 'hash': digest})
    require(any(':pre_tool_use:' in item['key'] for item in trust), 'no shipped PreToolUse hook')
    require(any(':session_start:' in item['key'] for item in trust), 'no shipped SessionStart hook')
    require(len({item['key'] for item in trust}) == len(trust), 'duplicate hook identity')
    return trust


def discover_hook_trust(binary, env, project, scratch):
    """Ask the actual engine for resolved hashes; do not emulate its hashing API."""
    command = [binary, 'app-server', '--strict-config']
    (scratch / 'hook-discovery.command.json').write_text(json.dumps(command) + '\n')
    with (scratch / 'hook-discovery.stderr').open('w') as error_log, \
            (scratch / 'hook-discovery.jsonl').open('w') as log:
        process = subprocess.Popen(command, env=env, cwd=project, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=error_log)
        buffered = b''
        def send(identity, method, params):
            message = {'method': method, 'params': params}
            if identity is not None:
                message['id'] = identity
            process.stdin.write((json.dumps(message) + '\n').encode())
            process.stdin.flush()
        def receive(identity):
            nonlocal buffered
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                while b'\n' in buffered:
                    line, buffered = buffered.split(b'\n', 1)
                    if not line:
                        continue
                    log.write(line.decode() + '\n')
                    log.flush()
                    response = json.loads(line)
                    if response.get('id') == identity:
                        return response
                if not select.select([process.stdout], [], [], 0.25)[0]:
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                require(chunk, 'hook discovery app-server exited before its response')
                buffered += chunk
            raise TimeoutError('hook discovery response ' + str(identity))
        try:
            send(1, 'initialize', {'clientInfo': {'name': 'codex_method_qualification', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
            require('error' not in receive(1), 'app-server initialize rejected')
            send(None, 'initialized', {})
            send(2, 'hooks/list', {'cwds': [str(project)]})
            return trusted_inventory(receive(2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()


def isolated_env(scratch, inherited=None):
    inherited = os.environ if inherited is None else inherited
    env = {'PATH': inherited.get('PATH', '/usr/bin:/bin'), 'LANG': 'C.UTF-8',
           'HOME': str(scratch / 'home'), 'CODEX_HOME': str(scratch / 'codex-home'),
           'TMPDIR': str(scratch / 'tmp'), 'PYTHONDONTWRITEBYTECODE': '1'}
    for key in ('HOME', 'CODEX_HOME', 'TMPDIR'):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME'):
        env[key] = str(scratch / key.lower())
        Path(env[key]).mkdir(exist_ok=True)
    return env


def inventory(project, codex_home):
    require((project / '.git/HEAD').is_file(), 'fixture must have a real local Git root')
    candidates = [Path('/etc/codex/config.toml'), Path('/etc/codex/requirements.toml'),
                  Path('/etc/codex/managed_config.toml')]
    # 0.160.0 config/loader/mod.rs discovers project layers only between cwd and
    # its nearest .git root, inclusive. This fixture's cwd IS that fresh root;
    # unrelated ancestor user homes are outside the loader's project boundary.
    candidates.extend(project / '.codex' / name for name in
                      ('config.toml', 'hooks.json', 'requirements.toml'))
    candidates.append(project / '.agents/plugins/marketplace.json')
    candidates.extend(codex_home / name for name in ('hooks.json', 'requirements.toml'))
    found = sorted({str(path) for path in candidates if path.exists()})
    require(not found, 'external configuration/hook layers prevent fixture isolation: ' + repr(found))
    return {'external_layers': [], 'hook_trust': 'actual hooks/list currentHash; no bypass',
            'environment': 'allowlisted; HOME and CODEX_HOME isolated', 'rules': 'preserved'}


def run_logged(command, env, cwd, directory, name, **kwargs):
    (directory / (name + '.command.json')).write_text(json.dumps(command) + '\n')
    try:
        result = subprocess.run(command, env=env, cwd=cwd, capture_output=True, text=True,
                                timeout=kwargs.pop('timeout', 30), **kwargs)
    except subprocess.TimeoutExpired as error:
        for suffix, data in (('stdout', error.stdout), ('stderr', error.stderr)):
            (directory / (name + '.' + suffix)).write_bytes(
                data if isinstance(data, bytes) else (data or '').encode())
        raise
    (directory / (name + '.stdout')).write_text(result.stdout)
    (directory / (name + '.stderr')).write_text(result.stderr)
    require(result.returncode == 0, name + ' failed (' + str(result.returncode) + '): '
            + result.stderr[-2000:])
    return result


HOOK_OBSERVER = '''#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
payload_text = sys.stdin.read()
payload = json.loads(payload_text)
settings = json.loads((Path(__file__).parent / 'fixture-observer.json').read_text())
ungated = (payload.get('agent_type') == 'runtime_readonly_control'
           and payload.get('tool_name') in ('Bash', 'exec_command')
           and payload.get('tool_input', {}).get('command',
               payload.get('tool_input', {}).get('cmd')) == settings['control_command'])
if ungated:
    code, out, err = 0, '', ''
else:
    result = subprocess.run([str(Path(__file__).with_name('pre-tool-use.shipped'))],
                            input=payload_text, capture_output=True, text=True)
    code, out, err = result.returncode, result.stdout, result.stderr
record = {'payload': payload, 'exit_code': code, 'stdout': out, 'stderr': err,
          'ungated_control': ungated, 'plugin_root': os.environ.get('PLUGIN_ROOT'),
          'plugin_data': os.environ.get('PLUGIN_DATA')}
with open(settings['log'], 'a') as stream:
    stream.write(json.dumps(record) + '\\n')
sys.stdout.write(out)
sys.stderr.write(err)
sys.exit(code)
'''


SESSION_OBSERVER = '''#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
payload_text = sys.stdin.read()
settings = json.loads((Path(__file__).parent / 'fixture-observer.json').read_text())
result = subprocess.run([str(Path(__file__).with_name('session-start.shipped')), *sys.argv[1:]],
                        input=payload_text, capture_output=True, text=True)
record = {'payload': json.loads(payload_text), 'exit_code': result.returncode,
          'stdout': result.stdout, 'stderr': result.stderr, 'plugin_root': os.environ.get('PLUGIN_ROOT')}
with open(settings['session_log'], 'a') as stream:
    stream.write(json.dumps(record) + '\\n')
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
'''


def prepare(binary, scratch, env, installer, evidence):
    project, package = scratch / 'project', scratch / 'marketplace'
    project.mkdir()
    (project / 'worker-lane').mkdir()
    (project / 'helper-material.txt').write_text('Ordinary material; no repository lane or PR is assigned.\n')
    run_logged(['git', 'init', '--quiet', str(project)], env, scratch, scratch, 'git-init')
    evidence['isolation'] = inventory(project, Path(env['CODEX_HOME']))
    # Snapshot only shipped local assets; never copy .git, auth, or home state.
    package.mkdir()
    for name in ('hooks', 'reference', 'scripts', 'skills', '.codex-plugin'):
        if (ROOT / name).is_dir():
            shutil.copytree(ROOT / name, package / name, ignore=shutil.ignore_patterns('__pycache__'))
    manifest = package / '.codex-plugin/plugin.json'
    require(manifest.exists(), 'legacy plugin manifest consumer missing')
    require(json.loads(manifest.read_text()).get('hooks') == './hooks/hooks.json',
            'legacy plugin manifest does not bind shipped hooks')
    marketplace = package / '.agents/plugins/marketplace.json'
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(json.dumps({'name': 'codex-method', 'plugins': [
        {'name': 'codex-method', 'source': './'}]}) + '\n')

    control_command = 'touch ' + shlex.quote(str(project / 'inherited-permissions.txt'))
    observer = package / 'hooks/pre-tool-use'
    evidence['shipped_hook_sha256'] = hashlib.sha256(observer.read_bytes()).hexdigest()
    observer.rename(observer.with_name('pre-tool-use.shipped'))
    observer.write_text(HOOK_OBSERVER)
    observer.chmod(0o755)
    (observer.parent / 'fixture-observer.json').write_text(json.dumps({
        'log': str(project / 'hook-payloads.jsonl'), 'control_command': control_command,
        'session_log': str(project / 'session-start-payloads.jsonl')}))
    session = package / 'hooks/session-start'
    evidence['shipped_session_start_sha256'] = hashlib.sha256(session.read_bytes()).hexdigest()
    session.rename(session.with_name('session-start.shipped'))
    session.write_text(SESSION_OBSERVER)
    session.chmod(0o755)
    evidence['instrumentation'] = 'payload observer; exact control bypass only; shipped policy delegated'

    home_config = Path(env['CODEX_HOME']) / 'config.toml'
    home_config.write_text('[projects.' + json.dumps(str(project)) + ']\ntrust_level="trusted"\n')
    run_logged([binary, 'plugin', 'marketplace', 'add', str(package)],
               env, project, scratch, 'marketplace-add')
    run_logged([binary, 'plugin', 'add', PLUGIN_ID], env, project, scratch, 'plugin-add')
    evidence['plugin_consumer'] = 'actual codex plugin marketplace add + plugin add (local)'

    roles = project / '.codex/agents'
    if installer:
        require(installer.resolve() == (ROOT / 'scripts/install').resolve(),
                '--installer must select this repository scripts/install')
        evidence['installer_sha256'] = hashlib.sha256(installer.read_bytes()).hexdigest()
        run_logged([sys.executable, str(installer.resolve()), '--project', str(project),
                    '--host-version', VERSION], env, project, scratch, 'role-install')
        evidence['role_consumer'] = 'scripts/install ran on fixture project'
    else:
        roles.mkdir(parents=True)
        for name, source in (('method_worker', 'worker.md'), ('method_reviewer', 'code-review-prompt.md')):
            instructions = (package / 'reference' / source).read_text()
            (roles / (name + '.toml')).write_text('\n'.join(key + '=' + toml(value)
                for key, value in {'name': name, 'description': 'Local qualification ' + name,
                                   'developer_instructions': instructions}.items()) + '\n')
        evidence['role_consumer'] = 'MISSING: instructions-only fixture roles; installer not selected'
    for name in (('method_worker', 'method_reviewer', 'method_helper', 'method_review_helper')
                 if installer else ('method_worker', 'method_reviewer')):
        role = tomllib.loads((roles / (name + '.toml')).read_text())
        source = 'code-review-prompt.md' if 'review' in name else 'worker.md'
        require((package / 'reference' / source).read_text() in role.get('developer_instructions', ''),
                name + ': installed role does not carry the full shipped role')
        for key in ('model', 'model_reasoning_effort'):
            # If an installer fixes these values, they must agree with the requested
            # spawn route. Never rewrite installed role settings to manufacture a pass.
            if key in role:
                require(role[key] == (MODEL if key == 'model' else EFFORT),
                        name + ': installed role overrides the qualification route')
    # Codex 0.160.0's role loader accepts sandbox_mode="read-only" but rejects
    # cwd as an unknown field and ignores the entire role. Keep the accepted
    # sandbox declaration: the exact ungated filesystem write is the negative
    # control for per-role OS isolation, not an instructions-only write probe.
    control = {'name': 'runtime_readonly_control', 'description': 'Per-role sandbox negative control',
               'developer_instructions': 'Harmless local inherited-permission control. ' + CONTROL_TASK,
               'sandbox_mode': 'read-only'}
    (roles / 'runtime_readonly_control.toml').write_text('\n'.join(
        key + '=' + toml(value) for key, value in control.items()) + '\n')

    trust = discover_hook_trust(binary, env, project, scratch)
    for item in trust:
        with home_config.open('a') as stream:
            stream.write('\n[hooks.state.' + toml(item['key']) + ']\nenabled=true\ntrusted_hash='
                         + toml(item['hash']) + '\n')
    (scratch / 'hook-trust.json').write_text(json.dumps(trust, indent=2) + '\n')
    evidence['trusted_hook_count'] = len(trust)
    fake = project / 'fixture-bin/gh'
    fake.parent.mkdir()
    fake.write_text('#!' + sys.executable + '\nimport json, sys\nfrom pathlib import Path\n'
        + 'p=Path(' + repr(str(project / 'fake-gh-calls.jsonl')) + ')\n'
        + "with p.open('a') as s: s.write(json.dumps(sys.argv[1:])+'\\n')\n"
        + "print('NATIVE_FIXTURE_FAKE_GH_ONLY')\n")
    fake.chmod(0o755)
    return project, control_command, fake


class ResponsesFixture:
    def __init__(self, project, scratch, control_command, fake):
        self.project, self.scratch = project, scratch
        self.control_command, self.fake = control_command, fake
        self.requests, self.errors, self.outputs, self.handles = [], [], {}, {}
        self.counts, self.waits = Counter(), Counter()
        self.spawn_fields = None
        self.root_stage = 0
        self.root_context_verified = False
        self.review_role = tomllib.loads((project / '.codex/agents/method_reviewer.toml').read_text())[
            'developer_instructions']
        roles = project / '.codex/agents'
        self.role_contracts = {name: tomllib.loads((roles / ('method_' + name + '.toml')).read_text())['developer_instructions']
                               for name in ('worker', 'reviewer', 'helper', 'review_helper')
                               if (roles / ('method_' + name + '.toml')).exists()}
        self.shared = (runpy.run_path(str(ROOT / 'scripts/install'))['shared_agreements']()
                       if 'worker' in self.role_contracts and
                       '## Shared collaboration agreements' in self.role_contracts['worker'] else None)
        self.sequence = ['worker', 'reviewer', 'control']
        if all(name in self.role_contracts for name in ('helper', 'review_helper')):
            self.sequence += ['helper', 'review_helper']
        self.finished_stage = 5 + len(self.sequence)
        self.lock = threading.Lock()
        self.server = None

    def __enter__(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                if self.path.split('?', 1)[0] != '/v1/models' or self.headers.get('Authorization'):
                    outer.errors.append('unexpected GET or authentication')
                    self.send_error(403)
                    return
                # Use the actual CLI's bundled advertised gpt-6.1-sol metadata.
                body = b'{"models":[]}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                try:
                    require(self.path.rstrip('/') == '/v1/responses', 'unexpected local endpoint')
                    require(not self.headers.get('Authorization'), 'provider received authentication')
                    require(self.headers.get('Content-Encoding', 'identity') == 'identity',
                            'disable request compression')
                    request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    with outer.lock:
                        outer.requests.append(request)
                        number = len(outer.requests)
                        # Archive before validation, including malformed/leaking requests.
                        with (scratch / 'requests.jsonl').open('a') as trace:
                            trace.write(json.dumps(request) + '\n')
                        require(number <= 100, 'unexpected extra continuation / mailbox stall')
                        item = outer.response_item(request)
                    response = {'id': 'resp_native_' + str(number), 'object': 'response',
                                'status': 'completed', 'output': [item],
                                'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    for event in [
                        {'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
                        {'type': 'response.output_item.added', 'output_index': 0, 'item': item},
                        {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                        {'type': 'response.completed', 'response': response}]:
                        self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
                    self.wfile.flush()
                except Exception as error:
                    outer.errors.append(str(error))
                    self.send_error(500, 'local qualification refused request')

        # Do not escalate or select an external provider if this socket is denied.
        scratch = self.scratch
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def call(self, request, name, args, call_id):
        return tool_call(request, name, args, call_id)

    def shell(self, request, command, call_id, workdir=None):
        args = {'cmd': command, 'max_output_tokens': 1000, 'yield_time_ms': 30000}
        if workdir:
            args['workdir'] = str(workdir)
        # exec is the advertised custom JavaScript tool; exec_command is nested
        # only. Print output itself so cwd verification still compares whole lines.
        source = 'const r = await tools.exec_command(' + json.dumps(args) + '); text(r.output);'
        return self.call(request, 'exec', source, call_id)

    def spawn(self, request, role, **extra):
        agent_type, message = {
            'worker': ('method_worker', WORK_TASK + '\n' + PRIVATE_WORKER),
            'reviewer': ('method_reviewer', REVIEW_TASK + '\nReturn a local fixture verdict.'),
            'control': ('runtime_readonly_control', CONTROL_TASK),
            'helper': ('method_helper', HELPER_TASK + '\nRead helper-material.txt in the supplied directory and return findings and limits to your caller.\nWorking directory: ' + str(self.project)),
            'review_helper': ('method_review_helper', REVIEW_HELPER_TASK + '\nIndependently inspect helper-material.txt read-only in the supplied directory; return findings and limits to the caller.\nWorking directory: ' + str(self.project))}[role]
        args = dict(task_name=role, message=message, agent_type=agent_type,
                    fork_turns='none', model=MODEL, reasoning_effort=EFFORT)
        args.update(extra)
        return self.call(request, 'spawn_agent', args, 'spawn_' + role)

    def response_item(self, request):
        role = request_role(request)
        validate_request(request, role, self.review_role)
        if role in self.role_contracts and self.shared:
            carried = '\n'.join(fragments([request.get('instructions', ''), request.get('input', [])]))
            require(carried.count(self.role_contracts[role]) == 1,
                    role + ': static role must occur once in actual provider input')
            require(carried.count(self.shared) == 1,
                    role + ': shared agreements must occur once in actual provider input')
            require((ROOT / 'reference/orchestrator.md').read_text() not in carried,
                    role + ': full orchestrator must not promote a child')
        for item in request.get('input', []):
            if item.get('type') in ('function_call_output', 'custom_tool_call_output'):
                self.outputs[item['call_id']] = output_text(item.get('output', ''))
        index = self.counts[role]
        if index == 0:
            (self.scratch / (role + '.tools.json')).write_text(json.dumps(advertised_tools(request), indent=2))
            if role == 'root':
                validate_root_context(request, (ROOT / 'reference/orchestrator.md').read_bytes().decode('utf-8'))
                self.root_context_verified = True
                self.spawn_fields = validate_spawn_schema(request)
        self.counts[role] += 1
        if role == 'root':
            return self.root_response(request)
        if role == 'worker':
            if index == 0:
                return self.shell(request, 'pwd', 'worker_lane_pwd', self.project / 'worker-lane')
            if index == 1:
                return self.shell(request, 'pwd', 'worker_session_pwd')
            if index == 2:
                return self.shell(request, 'git merge fixture-never-merge', 'worker_merge', self.project)
        elif role == 'reviewer':
            if index == 0:
                patch = '*** Begin Patch\n*** Add File: reviewer-patch.txt\n+harmless fixture\n*** End Patch'
                source = 'const r = await tools.apply_patch(' + json.dumps(patch) + '); text(r);'
                return self.call(request, 'exec', source, 'reviewer_patch')
            if index == 1:
                return self.shell(request, 'touch reviewer-shell.txt', 'reviewer_shell', self.project)
            if index == 2:
                return self.shell(request, shlex.quote(str(self.fake)) + ' issue comment 1 --body fixture',
                                  'reviewer_remote', self.project)
            if index == 3:
                return self.call(request, 'spawn_agent', dict(task_name='rejected_cross_role',
                    message='Local refusal probe; this child must never start.',
                    agent_type='method_worker', fork_turns='none', model=MODEL,
                    reasoning_effort=EFFORT), 'reviewer_cross_role')
        elif role in ('helper', 'review_helper') and index == 0:
            return self.shell(request, 'cat helper-material.txt', role + '_material', self.project)
        elif role == 'control' and index == 0:
            return self.shell(request, self.control_command, 'control_write')
        require(index == {'worker': 3, 'reviewer': 4, 'control': 1, 'helper': 1, 'review_helper': 1}[role],
                role + ': unexpected continuation after final')
        return self.final(role)

    @staticmethod
    def final(role):
        return {'type': 'message', 'id': 'msg_' + role, 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': DONE[role], 'annotations': []}]}

    def root_response(self, request):
        stage = self.root_stage
        if stage < 4:
            self.root_stage += 1
            if stage == 0:
                return self.shell(request, 'pwd', 'root_pwd')
            if stage == 1:
                return self.shell(request, shlex.quote(str(self.fake)) + ' --version', 'fake_gh_baseline')
            if stage == 2:
                args = dict(task_name='bad_unknown', message='Harmless invalid spawn',
                            fork_turns='none', cwd=str(self.project))
                return self.call(request, 'spawn_agent', args, 'unknown_field')
            error = self.outputs.get('unknown_field', '')
            require('unknown field' in error and 'cwd' in error,
                    'V2 unknown field did not produce a real handler error: ' + error)
            return self.call(request, 'spawn_agent', dict(task_name='bad_fork',
                             message='Harmless invalid fork', fork_context=True), 'invalid_fork')
        if stage == 4:
            error = self.outputs.get('invalid_fork', '')
            require('fork_context' in error and 'not supported' in error,
                    'V2 fork_context did not produce a real handler error: ' + error)
            self.root_stage += 1
            return self.spawn(request, 'worker')
        role = self.sequence[stage - 5] if 5 <= stage < self.finished_stage else None
        if role:
            # A failed child cannot deliver DONE. Surface its actual final payload
            # before acknowledging or waiting; unrelated messages are not failures.
            for item in request.get('input', []):
                if (item.get('type') == 'agent_message' and item.get('author') == '/root/' + role
                        and item.get('recipient') == '/root'):
                    text = agent_message_text(item)
                    if text.startswith('Message Type: FINAL_ANSWER\n'):
                        payload = text.partition('\nPayload:\n')[2].strip()
                        require(not payload.startswith('Agent errored'),
                                role + ': child FINAL_ANSWER failed: ' + payload)
            if role not in self.handles:
                self.handles[role] = canonical_handle(self.outputs.get('spawn_' + role, ''), role)
                return self.call(request, 'send_message', {
                    'target': self.handles[role], 'message': 'Local fixture canonical handle acknowledgment.'},
                    'ack_' + role)
            require('ack_' + role in self.outputs and self.outputs['ack_' + role] == '',
                    role + ': canonical target was not accepted by actual send_message handler')
            if DONE[role] not in input_text(request):
                self.waits[role] += 1
                require(self.waits[role] <= 12, role + ': completion not delivered through mailbox')
                return self.call(request, 'wait_agent', {'timeout_ms': 10000},
                                 f'wait_{role}_{self.waits[role]}')
            self.root_stage += 1
            if self.root_stage < self.finished_stage:
                return self.spawn(request, self.sequence[self.root_stage - 5])
        require(self.root_stage == self.finished_stage, 'unexpected root stage')
        return self.final('root')

    def verify(self, events):
        require(not self.errors, 'provider errors: ' + repr(self.errors))
        require(self.root_stage == self.finished_stage and DONE['root'] in events, 'root did not complete qualification')
        require(set(self.handles) == set(self.sequence), 'missing native spawn handles')
        for call in ('root_pwd', 'worker_lane_pwd', 'worker_session_pwd', 'control_write'):
            setup_errors = [line.strip() for line in self.outputs.get(call, '').splitlines()
                            if line.strip().startswith('bwrap:')]
            require(not setup_errors, call + ': sandbox setup failed: ' + '; '.join(setup_errors))
        for call, expected in (('root_pwd', self.project), ('worker_lane_pwd', self.project / 'worker-lane'),
                               ('worker_session_pwd', self.project)):
            require(str(expected) in self.outputs.get(call, '').splitlines(), call + ': actual cwd mismatch')
        require((self.project / 'inherited-permissions.txt').exists(),
                'per-role read-only negative control did not actually write under parent permissions')
        for name in ('reviewer-patch.txt', 'reviewer-shell.txt'):
            require(not (self.project / name).exists(), 'reviewer sentinel was written: ' + name)
        fake_calls = [json.loads(line) for line in (self.project / 'fake-gh-calls.jsonl').read_text().splitlines()]
        require(fake_calls == [['--version']], 'reviewer remote probe reached the fake gh executable')
        require(self.root_context_verified, 'whole inline orchestrator was not observed at the provider')
        session_log = self.project / 'session-start-payloads.jsonl'
        require(session_log.exists(), 'actual SessionStart invocation was not observed')
        starts = [json.loads(line) for line in session_log.read_text().splitlines()]
        require(len(starts) == 1 and starts[0]['payload'].get('source') == 'startup',
                'expected one SessionStart invocation for root startup, without extra part calls')
        start = starts[0]
        require(start['exit_code'] == 0 and not start['stderr'], 'SessionStart command failed')
        output = json.loads(start['stdout'])
        context = output.get('hookSpecificOutput', {}).get('additionalContext', '')
        marker = '--- codex-method whole context ---\n'
        require(context.partition(marker)[2].encode('utf-8') == (ROOT / 'reference/orchestrator.md').read_bytes()
                and context.count(marker) == 1 and len(context.encode('utf-8')) <= 64000
                and start['plugin_root'] in context.partition(marker)[0],
                'SessionStart did not deliver one complete budgeted page from its actual plugin root')
        hook_log = self.project / 'hook-payloads.jsonl'
        require(hook_log.exists(), 'installed plugin hook did not run')
        records = [json.loads(line) for line in hook_log.read_text().splitlines()]
        denied, reviewer_calls, worker_denied = [], [], []
        for record in records:
            payload = record['payload']
            role = payload.get('agent_type')
            tool = payload.get('tool_name')
            inputs = payload.get('tool_input') or {}
            command = inputs.get('command', inputs.get('cmd', ''))
            shell_tool = tool in ('Bash', 'exec_command')
            worker_merge = (role == 'method_worker' and shell_tool
                            and command == 'git merge fixture-never-merge')
            if role != 'method_reviewer' and not worker_merge:
                continue
            require(payload.get('agent_id'), role + ' hook has no native child identity')
            if worker_merge:
                call_id = 'worker_merge'
            elif tool == 'apply_patch':
                call_id = 'reviewer_patch'
            elif tool == 'collaborationspawn_agent':
                require(inputs.get('agent_type') == 'method_worker',
                        'cross-role probe used an unexpected native role')
                call_id = 'reviewer_cross_role'
            else:
                require(shell_tool, 'unexpected reviewer hook tool: ' + str(tool))
                commands = {'touch reviewer-shell.txt': 'reviewer_shell',
                            shlex.quote(str(self.fake)) + ' issue comment 1 --body fixture': 'reviewer_remote'}
                require(command in commands, 'unexpected reviewer hook command: ' + str(command))
                call_id = commands[command]
            reason = record['stderr'] if record['exit_code'] == 2 else ''
            if record['exit_code'] == 0 and record['stdout'].strip():
                output = json.loads(record['stdout']).get('hookSpecificOutput', {})
                if output.get('hookEventName') == 'PreToolUse' and output.get('permissionDecision') == 'deny':
                    reason = output.get('permissionDecisionReason', '')
            require(reason.strip(), role + ' hook did not return a blocking denial for ' + str(tool))
            require('refused' in self.outputs.get(call_id, ''),
                    call_id + ': blocking denial did not reach native tool output')
            require(record['plugin_root'] and str(self.scratch) in record['plugin_root'],
                    'hook did not bind fixture PLUGIN_ROOT')
            if worker_merge:
                worker_denied.append(tool)
            else:
                denied.append(tool)
                reviewer_calls.append(call_id)
        require(Counter(reviewer_calls) == Counter({'reviewer_patch': 1, 'reviewer_shell': 1,
                                                   'reviewer_remote': 1, 'reviewer_cross_role': 1}),
                'did not observe the four actual reviewer hook denials: ' + repr(denied))
        require(len(worker_denied) == 1, 'did not observe the actual worker merge hook denial')
        require(sum(record['ungated_control'] for record in records) == 1,
                'exact ungated per-role sandbox control was not observed')
        helpers = [role for role in self.sequence if role.endswith('helper')]
        for role in helpers:
            require('Ordinary material; no repository lane or PR is assigned.' in
                    self.outputs.get(role + '_material', ''), role + ': ordinary material was not read')
        return {'single_session_start_whole_inline': True, 'session_start_invocations': len(starts),
                'shared_role_delivery': bool(self.shared),
                'task_local_helpers_without_pr': helpers,

                'native_handles': self.handles, 'provider_requests_by_role': dict(self.counts),
                'actual_spawn_schema_fields': self.spawn_fields,
                'canonical_targets': 'actual send_message accepted each returned task_name',
                'fresh_reviewer_full_role': True, 'reviewer_cross_role_spawn_denied': True,
                'worker_explicit_lane_cwd': True,
                'child_session_cwd': str(self.project), 'reviewer_denials': denied,
                'worker_merge_denials': worker_denied,
                'unknown_fields': 'actual V2 handler rejected cwd and fork_context',
                'mailbox_completion': ', '.join(self.sequence) + ' completion delivered to root',
                'per_role_readonly': "UNSUPPORTED: declared read-only role's exact ungated child write "
                                     'succeeded with parent permissions'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-version', default=VERSION, help='exact qualification pin, only 0.160.0')
    parser.add_argument('--codex', default='codex', help='CLI executable')
    parser.add_argument('--scratch-root', type=Path, default=os.environ.get('TMPDIR'))
    parser.add_argument('--log-dir', type=Path, help='optional additional summary location within scratch-root')
    parser.add_argument('--installer', type=Path, help='opt in to finalized repository scripts/install consumer')
    args = parser.parse_args()
    require(args.codex_version == VERSION, 'this qualification is pinned to Codex ' + VERSION)
    require(args.scratch_root, 'set TMPDIR or --scratch-root; fixture never uses implicit user/home temp data')
    scratch_root = Path(args.scratch_root).resolve()
    scratch_root.mkdir(parents=True, exist_ok=True)
    if args.log_dir:
        require(args.log_dir.resolve().is_relative_to(scratch_root), '--log-dir must be under scratch-root')
        args.log_dir.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='codex-native-runtime-', dir=scratch_root)).resolve()
    evidence = {'status': 'failed', 'qualified': False, 'installed_end_to_end': False,
                'pinned_version': VERSION, 'source_tag': 'rust-v' + VERSION,
                'model': MODEL, 'effort': EFFORT, 'root_sessions_started': 0,
                'qualification_kind': 'deterministic-local-provider', 'production_model_validated': False,
                'desktop_ui_validated': False,
                'evidence_dir': str(scratch)}
    fixture = None
    phase = 'setup'
    try:
        env = isolated_env(scratch)
        binary = shutil.which(args.codex, path=env['PATH'])
        require(binary, 'Codex CLI executable is missing')
        observed = run_logged([binary, '--version'], env, scratch, scratch, 'version').stdout.strip()
        require(observed == 'codex-cli ' + VERSION, 'wrong CLI pin: ' + observed)
        evidence['observed_version'] = observed
        project, control_command, fake = prepare(binary, scratch, env, args.installer, evidence)
        fixture = ResponsesFixture(project, scratch, control_command, fake)
        phase = 'local-provider-bind'
        with fixture:
            phase = 'native-session'
            settings = {
                'model_provider': 'native-fixture', 'model_reasoning_effort': EFFORT,
                'model_providers.native-fixture': {
                    'name': 'Local native agent qualification',
                    'base_url': f'http://127.0.0.1:{fixture.server.server_port}/v1',
                    'wire_api': 'responses', 'requires_openai_auth': False,
                    'supports_websockets': False, 'request_max_retries': 0,
                    'stream_max_retries': 0, 'stream_idle_timeout_ms': 10000},
                'agents.enabled': True, 'agents.max_threads': 4,
                'agents.default_subagent_model': MODEL,
                'agents.default_subagent_reasoning_effort': EFFORT,
                'features.multi_agent_v2.enabled': True,
                'features.multi_agent_v2.expose_spawn_agent_model_overrides': True,
                'features.hooks': True, 'features.plugins': True,
                'features.apps': False, 'features.remote_plugin': False,
                'features.enable_request_compression': False, 'features.code_mode': False,
                'features.shell_snapshot': False, 'features.skip_host_skill_discovery': True,
                'web_search': 'disabled', 'check_for_update_on_startup': False,
                'analytics.enabled': False, 'allow_login_shell': False,
                'shell_environment_policy.inherit': 'none',
                'shell_environment_policy.set': {key: env[key] for key in ('PATH', 'HOME', 'TMPDIR')},
                'approval_policy': 'never'}
            command = [binary, 'exec', '--strict-config', '--ephemeral', '--json',
                       '-s', 'workspace-write', '-C', str(project), '-m', MODEL]
            for key, value in settings.items():
                command.extend(['-c', key + '=' + toml(value)])
            command.append('-')
            evidence['root_sessions_started'] = 1
            result = run_logged(command, env, project, scratch, 'codex-events', timeout=180,
                input='Qualify the local native runtime. Parent conversation private token: '
                      + PRIVATE_PARENT + '\nUse only the deterministic fixture tool calls.\n')
        phase = 'runtime-evidence'
        evidence['checks'] = fixture.verify(result.stdout)
        evidence['qualified'] = True
        evidence['installed_end_to_end'] = args.installer is not None
        evidence['status'] = 'passed' if args.installer else 'runtime-passed-consumer-missing'
    except Exception as error:
        if phase == 'local-provider-bind' and isinstance(error, OSError):
            evidence['status'] = 'blocked'
        evidence.update(blocker_phase=phase, error_type=type(error).__name__, error=str(error))
        (scratch / 'failure.txt').write_text(traceback.format_exc())
    finally:
        if fixture:
            evidence['provider_requests'] = len(fixture.requests)
            evidence['provider_errors'] = fixture.errors
        (scratch / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n')
        # Keep empty traces on pre-session failures so absence is explicit evidence.
        for name in ('requests.jsonl', 'codex-events.stdout', 'codex-events.stderr'):
            (scratch / name).touch(exist_ok=True)
        if args.log_dir:
            (args.log_dir / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence))
    return 0 if evidence['qualified'] else 2 if evidence['status'] == 'blocked' else 1


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        sys.exit(main())
    except (AssertionError, OSError) as error:
        print(json.dumps({'status': 'failed', 'qualified': False, 'error': str(error)}))
        sys.exit(1)
