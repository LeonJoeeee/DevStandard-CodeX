"""Generate and check real project-discovered agent role files, without user config writes."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def install(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                               str(self.project), '--host-version', '0.160.0', *args],
                              capture_output=True, text=True, encoding='utf-8')

    def test_install_preserves_unrelated_config_and_roles(self):
        config = self.project / '.codex/config.toml'
        config.parent.mkdir()
        prior = '# keep this\nmodel = "some-other-model"\n[features]\nweb_search = true\n'
        config.write_text(prior, encoding='utf-8')
        agents = config.parent / 'agents'
        agents.mkdir()
        other = agents / 'other.toml'
        other.write_text('name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n', encoding='utf-8')
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(config.read_text(encoding='utf-8').startswith(prior))
        parsed = tomllib.loads(config.read_text(encoding='utf-8'))
        self.assertTrue(parsed['features']['multi_agent_v2']['enabled'])
        self.assertTrue(parsed['features']['multi_agent_v2']['expose_spawn_agent_model_overrides'])
        self.assertEqual(other.read_text(encoding='utf-8'), 'name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        for role in ('method_worker', 'method_reviewer', 'method_helper', 'method_review_helper'):
            parsed = tomllib.loads((agents / (role + '.toml')).read_text(encoding='utf-8'))
            self.assertEqual(parsed['name'], role)
            # Native role config wins over spawn overrides; keep model/effort in the call.
            for forbidden in ('model', 'model_reasoning_effort', 'cwd', 'sandbox_mode', 'approval_policy', 'hooks'):
                self.assertNotIn(forbidden, parsed)
            instructions = parsed['developer_instructions']
            source = ('task-helper.md' if role.endswith('helper') else
                      'code-review-prompt.md' if 'review' in role else 'worker.md')
            self.assertIn((ROOT / 'reference' / source).read_text(encoding='utf-8'), instructions)
            self.assertIn('method_review_helper', instructions)
            self.assertIn('fork_turns', instructions)
        first = config.read_bytes()
        self.assertEqual(self.install('--check').returncode, 0)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(config.read_bytes(), first)

    def test_shared_agreements_reach_each_role_once_without_promoting_children(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        source = (ROOT / 'reference/orchestrator.md').read_text(encoding='utf-8')
        start = '<!-- BEGIN SHARED COLLABORATION AGREEMENTS -->'
        end = '<!-- END SHARED COLLABORATION AGREEMENTS -->'
        self.assertIn(start, source, 'shared instructions have no extractable source')
        shared = source.split(start, 1)[1].split(end, 1)[0].strip()
        self.assertTrue(shared)
        for role in ('method_worker', 'method_reviewer', 'method_helper', 'method_review_helper'):
            with self.subTest(role=role):
                instructions = tomllib.loads((self.project / '.codex/agents' / (role + '.toml')).read_text(encoding='utf-8'))['developer_instructions']
                self.assertEqual(instructions.count(shared), 1)
                self.assertNotIn('# Orchestrator\n', instructions)
                if role.endswith('helper'):
                    self.assertIn((ROOT / 'reference/task-helper.md').read_text(encoding='utf-8'), instructions)

    def test_missing_ambiguous_or_empty_shared_source_refuses_before_any_write(self):
        package = self.project / 'package'
        (package / 'scripts').mkdir(parents=True)
        shutil.copy2(ROOT / 'scripts/install', package / 'scripts/install')
        shutil.copy2(ROOT / 'scripts/hard_edges.py', package / 'scripts/hard_edges.py')
        shutil.copy2(ROOT / 'scripts/host_contract.py', package / 'scripts/host_contract.py')
        shutil.copytree(ROOT / 'reference', package / 'reference')
        page = package / 'reference/orchestrator.md'
        start = '<!-- BEGIN SHARED COLLABORATION AGREEMENTS -->'
        end = '<!-- END SHARED COLLABORATION AGREEMENTS -->'
        for text in ('# No shared section\n', start + '\n' + end,
                     start + '\nx\n' + end + '\n' + start + '\ny\n' + end):
            with self.subTest(text=text):
                page.write_text(text, encoding='utf-8')
                target = self.project / 'target'
                target.mkdir(exist_ok=True)
                result = subprocess.run([sys.executable, str(package / 'scripts/install'), '--project',
                                         str(target), '--host-version', '0.160.0'], capture_output=True, text=True, encoding='utf-8')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('shared collaboration', result.stderr)
                self.assertFalse((target / '.codex').exists())

    def test_helpers_select_only_task_source_and_native_excerpt(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        helper_source = ROOT / 'reference/task-helper.md'
        self.assertTrue(helper_source.is_file(), 'neutral helper source is missing')
        harness = (ROOT / 'reference/harness-codex.md').read_text(encoding='utf-8')
        start = '<!-- BEGIN NATIVE HELPER MECHANICS -->'
        end = '<!-- END NATIVE HELPER MECHANICS -->'
        self.assertIn(start, harness, 'helper mechanics selector is missing')
        excerpt = harness.split(start, 1)[1].split(end, 1)[0].strip()
        for role in ('method_helper', 'method_review_helper'):
            instructions = tomllib.loads((self.project / '.codex/agents' / (role + '.toml')).read_text(encoding='utf-8'))['developer_instructions']
            self.assertEqual(instructions.count(helper_source.read_text(encoding='utf-8')), 1)
            self.assertEqual(instructions.count(excerpt), 1)
            for source in ('worker.md', 'code-review-prompt.md'):
                self.assertNotIn((ROOT / 'reference' / source).read_text(encoding='utf-8'), instructions)
            self.assertNotIn(harness, instructions)
            self.assertNotIn('## Driving a PR to green', instructions)
            self.assertNotIn('Ready-to-merge:', instructions)
        ordinary = tomllib.loads((self.project / '.codex/agents/method_helper.toml').read_text(encoding='utf-8'))['developer_instructions']
        review = tomllib.loads((self.project / '.codex/agents/method_review_helper.toml').read_text(encoding='utf-8'))['developer_instructions']
        self.assertIn('superpowers:test-driven-development', ordinary)
        self.assertNotIn('superpowers:test-driven-development', review)

    def test_invalid_helper_sources_refuse_without_config_role_or_backup_writes(self):
        package = self.project / 'package'
        shutil.copytree(ROOT / 'scripts', package / 'scripts')
        shutil.copytree(ROOT / 'reference', package / 'reference')
        page = package / 'reference/harness-codex.md'
        original = page.read_text(encoding='utf-8')
        start = '<!-- BEGIN NATIVE HELPER MECHANICS -->'
        end = '<!-- END NATIVE HELPER MECHANICS -->'
        target = self.project / 'target'
        target.mkdir()
        installed = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--project',
                                    str(target), '--host-version', '0.160.0'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(installed.returncode, 0, installed.stderr)
        before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        for text in ('# No marked mechanics\n', start, end, start + '\n' + end,
                     start + '\nx\n' + end + '\n' + start + '\ny\n' + end,
                     end + '\nx\n' + start):
            with self.subTest(text=text):
                page.write_text(text, encoding='utf-8')
                result = subprocess.run([sys.executable, str(package / 'scripts/install'), '--project',
                                         str(target), '--host-version', '0.160.0'], capture_output=True, text=True, encoding='utf-8')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('native helper mechanics', result.stderr)
                self.assertEqual({str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}, before)
        page.unlink()
        missing_harness = subprocess.run([sys.executable, str(package / 'scripts/install'), '--project',
                                         str(target), '--host-version', '0.160.0'], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(missing_harness.returncode, 0)
        self.assertEqual({str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}, before)
        page.write_text(original, encoding='utf-8')
        helper = package / 'reference/task-helper.md'
        for absent in (False, True):
            with self.subTest(absent=absent):
                if absent:
                    helper.unlink()
                else:
                    helper.write_text('', encoding='utf-8')
                result = subprocess.run([sys.executable, str(package / 'scripts/install'), '--project',
                                         str(target), '--host-version', '0.160.0'], capture_output=True, text=True, encoding='utf-8')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual({str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}, before)

    def test_stale_helpers_block_formal_consumers_until_complete_reinstall(self):
        from tests.github_fixture import GitHubFixture
        for helper in ('method_helper', 'method_review_helper'):
            with self.subTest(helper=helper):
                fixture = GitHubFixture()
                self.addCleanup(fixture.close)
                fixture.env['TMPDIR'] = str(fixture.root)
                fake = fixture.root / 'bin/gh'
                fake.write_text(fake.read_text(encoding='utf-8').replace(
                    "out({'body': s['issue'], 'state': 'OPEN'",
                    "out({'number': 2, 'body': s['issue'], 'state': 'OPEN'"), encoding='utf-8')
                fixture.git('checkout', 'main')
                lane = fixture.root / 'lane'
                fixture.git('worktree', 'add', lane, 'task/2-acceptance')
                path = fixture.project / '.codex/agents' / (helper + '.toml')
                formal = 'method_reviewer' if 'review' in helper else 'method_worker'
                previous = (fixture.project / '.codex/agents' / (formal + '.toml')).read_text(encoding='utf-8').replace(
                    'name = "' + formal + '"', 'name = "' + helper + '"')
                path.write_text(previous, encoding='utf-8')
                # Current user-scope roles cannot hide a stale project helper.
                fixture.env['CODEX_HOME'] = str(fixture.root / 'user-config')
                user_install = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                    '--host-version', '0.160.0'], env=fixture.env, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(user_install.returncode, 0, user_install.stderr)
                args = ('2', '--purpose', 'worker', '--adopt', '--branch', 'task/2-acceptance',
                        '--worktree', str(lane), '--base', 'main', '--host-version', '0.160.0')
                dispatch = fixture.command('dispatch', *args)
                review = fixture.start()
                for result in (dispatch, review):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('drift', result.stderr)
                self.assertFalse((fixture.project / '.git/codex-method/lanes/2.json').exists())
                self.assertFalse(fixture.state()['comments'])
                self.assertEqual(path.read_text(encoding='utf-8'), previous)
                installed = fixture.command('install', '--host-version', '0.160.0')
                self.assertEqual(installed.returncode, 0, installed.stderr)
                backups = [Path(item) for item in json.loads(installed.stdout)['backups']]
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(encoding='utf-8'), previous)
                self.assertNotIn(path.parent, backups[0].parents)
                dispatched = fixture.command('dispatch', *args)
                self.assertEqual(dispatched.returncode, 0, dispatched.stderr)
                reviewed = fixture.start()
                self.assertEqual(reviewed.returncode, 0, reviewed.stderr)

    def test_check_detects_missing_install_and_drift_without_writing(self):
        result = self.install('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())
        self.assertEqual(self.install().returncode, 0)
        path = self.project / '.codex/agents/method_worker.toml'
        path.write_text(path.read_text(encoding='utf-8').replace('Return the PR', 'Changed return the PR'), encoding='utf-8')
        # A valid but different generated role must be detected too.
        path.write_text(path.read_text(encoding='utf-8') + '\nmodel_verbosity="low"\n', encoding='utf-8')
        before = path.read_bytes()
        self.assertNotEqual(self.install('--check').returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_role_collision_refuses_before_any_write(self):
        path = self.project / '.codex/agents/method_worker.toml'
        path.parent.mkdir(parents=True)
        path.write_text('name="method_worker"\ndescription="mine"\ndeveloper_instructions="mine"\n', encoding='utf-8')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex/config.toml').exists())
        self.assertIn('mine', path.read_text(encoding='utf-8'))

    def test_unknown_host_and_missing_destination_refuse(self):
        result = self.install('--host-version', '0.161.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_explicit_user_install_preserves_other_roles_and_config(self):
        codex_home = self.project / 'user-home'
        codex_home.mkdir()
        config = codex_home / 'config.toml'
        config.write_text('# preserve user settings\nmodel="keep-model"\n', encoding='utf-8')
        agents = codex_home / 'agents'
        agents.mkdir()
        other = agents / 'other.toml'
        other.write_text('name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n', encoding='utf-8')
        env = dict(os.environ, CODEX_HOME=str(codex_home))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                                 '--host-version', '0.160.0'], env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['scope'], 'user')
        self.assertEqual(report['codex_home'], str(codex_home))
        self.assertEqual(tomllib.loads(config.read_text(encoding='utf-8'))['model'], 'keep-model')
        self.assertEqual(other.read_text(encoding='utf-8'), 'name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        self.assertTrue((agents / 'method_reviewer.toml').is_file())
        self.assertFalse((codex_home / '.codex').exists())
        checked = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                                  '--host-version', '0.160.0', '--check'], env=env,
                                 capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_owned_legacy_role_upgrade_keeps_the_exact_previous_file(self):
        role = self.project / '.codex/agents/method_worker.toml'
        role.parent.mkdir(parents=True)
        previous = ('# Generated by codex-method scripts/install; Codex 0.159.2 V2.\n'
                    'name="method_worker"\ndescription="previous owned role"\n'
                    'developer_instructions="previous instructions"\n')
        role.write_text(previous, encoding='utf-8')
        checked = self.install('--check')
        self.assertNotEqual(checked.returncode, 0)
        self.assertEqual(role.read_text(encoding='utf-8'), previous)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(role.read_text(encoding='utf-8'), previous)
        report = json.loads(result.stdout)
        backups = [Path(path) for path in report['backups']]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding='utf-8'), previous)
        self.assertNotIn(role.parent, backups[0].parents)
        # Windows chmod controls only the read-only bit; POSIX owner mode is unavailable.
        if os.name != 'nt':
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

    def test_nested_discovered_role_collision_refuses_before_any_write(self):
        role = self.project / '.codex/agents/custom/method_worker.toml'
        role.parent.mkdir(parents=True)
        role.write_text('name="method_worker"\ndescription="mine"\ndeveloper_instructions="mine"\n', encoding='utf-8')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('collision', result.stderr)
        self.assertFalse((self.project / '.codex/config.toml').exists())
        self.assertEqual(tomllib.loads(role.read_text(encoding='utf-8'))['description'], 'mine')

    def test_historical_host_is_not_a_current_package_qualification(self):
        result = self.install('--host-version', '0.159.2')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())

    def test_plugin_manifest_resolves_real_hook_consumer(self):
        self.assertTrue((ROOT / '.codex-plugin/plugin.json').is_file(), 'plugin delivery missing')
        manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        config = json.loads((ROOT / manifest['hooks']).read_text(encoding='utf-8'))
        self.assertIn('PreToolUse', config['hooks'])
