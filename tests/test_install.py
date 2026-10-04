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
                              capture_output=True, text=True)

    def test_install_preserves_unrelated_config_and_roles(self):
        config = self.project / '.codex/config.toml'
        config.parent.mkdir()
        prior = '# keep this\nmodel = "some-other-model"\n[features]\nweb_search = true\n'
        config.write_text(prior)
        agents = config.parent / 'agents'
        agents.mkdir()
        other = agents / 'other.toml'
        other.write_text('name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(config.read_text().startswith(prior))
        parsed = tomllib.loads(config.read_text())
        self.assertTrue(parsed['features']['multi_agent_v2']['enabled'])
        self.assertTrue(parsed['features']['multi_agent_v2']['expose_spawn_agent_model_overrides'])
        self.assertEqual(other.read_text(), 'name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        for role in ('method_worker', 'method_reviewer', 'method_helper', 'method_review_helper'):
            parsed = tomllib.loads((agents / (role + '.toml')).read_text())
            self.assertEqual(parsed['name'], role)
            # Native role config wins over spawn overrides; keep model/effort in the call.
            for forbidden in ('model', 'model_reasoning_effort', 'cwd', 'sandbox_mode', 'approval_policy', 'hooks'):
                self.assertNotIn(forbidden, parsed)
            instructions = parsed['developer_instructions']
            source = 'code-review-prompt.md' if 'review' in role else 'worker.md'
            self.assertIn((ROOT / 'reference' / source).read_text(), instructions)
            self.assertIn('method_review_helper', instructions)
            self.assertIn('fork_turns', instructions)
        first = config.read_bytes()
        self.assertEqual(self.install('--check').returncode, 0)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(config.read_bytes(), first)

    def test_shared_agreements_reach_each_role_once_without_promoting_children(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        source = (ROOT / 'reference/orchestrator.md').read_text()
        start = '<!-- BEGIN SHARED COLLABORATION AGREEMENTS -->'
        end = '<!-- END SHARED COLLABORATION AGREEMENTS -->'
        self.assertIn(start, source, 'shared instructions have no extractable source')
        shared = source.split(start, 1)[1].split(end, 1)[0].strip()
        self.assertTrue(shared)
        for role in ('method_worker', 'method_reviewer', 'method_helper', 'method_review_helper'):
            with self.subTest(role=role):
                instructions = tomllib.loads((self.project / '.codex/agents' / (role + '.toml')).read_text())['developer_instructions']
                self.assertEqual(instructions.count(shared), 1)
                self.assertNotIn('# Orchestrator\n', instructions)
                if role.endswith('helper'):
                    self.assertTrue(instructions.startswith('# Task-local helper contract\n'))
                    self.assertIn('Lane receipt and PR judging requirements apply only', instructions)

    def test_missing_ambiguous_or_empty_shared_source_refuses_before_any_write(self):
        package = self.project / 'package'
        (package / 'scripts').mkdir(parents=True)
        shutil.copy2(ROOT / 'scripts/install', package / 'scripts/install')
        shutil.copy2(ROOT / 'scripts/hard_edges.py', package / 'scripts/hard_edges.py')
        shutil.copytree(ROOT / 'reference', package / 'reference')
        page = package / 'reference/orchestrator.md'
        start = '<!-- BEGIN SHARED COLLABORATION AGREEMENTS -->'
        end = '<!-- END SHARED COLLABORATION AGREEMENTS -->'
        for text in ('# No shared section\n', start + '\n' + end,
                     start + '\nx\n' + end + '\n' + start + '\ny\n' + end):
            with self.subTest(text=text):
                page.write_text(text)
                target = self.project / 'target'
                target.mkdir(exist_ok=True)
                result = subprocess.run([sys.executable, str(package / 'scripts/install'), '--project',
                                         str(target), '--host-version', '0.160.0'], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('shared collaboration', result.stderr)
                self.assertFalse((target / '.codex').exists())

    def test_check_detects_missing_install_and_drift_without_writing(self):
        result = self.install('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())
        self.assertEqual(self.install().returncode, 0)
        path = self.project / '.codex/agents/method_worker.toml'
        path.write_text(path.read_text().replace('Return the PR', 'Changed return the PR'))
        # A valid but different generated role must be detected too.
        path.write_text(path.read_text() + '\nmodel_verbosity="low"\n')
        before = path.read_bytes()
        self.assertNotEqual(self.install('--check').returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_role_collision_refuses_before_any_write(self):
        path = self.project / '.codex/agents/method_worker.toml'
        path.parent.mkdir(parents=True)
        path.write_text('name="method_worker"\ndescription="mine"\ndeveloper_instructions="mine"\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex/config.toml').exists())
        self.assertIn('mine', path.read_text())

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
        config.write_text('# preserve user settings\nmodel="keep-model"\n')
        agents = codex_home / 'agents'
        agents.mkdir()
        other = agents / 'other.toml'
        other.write_text('name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        env = dict(os.environ, CODEX_HOME=str(codex_home))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                                 '--host-version', '0.160.0'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['scope'], 'user')
        self.assertEqual(report['codex_home'], str(codex_home))
        self.assertEqual(tomllib.loads(config.read_text())['model'], 'keep-model')
        self.assertEqual(other.read_text(), 'name="other"\ndescription="keep"\ndeveloper_instructions="keep"\n')
        self.assertTrue((agents / 'method_reviewer.toml').is_file())
        self.assertFalse((codex_home / '.codex').exists())
        checked = subprocess.run([sys.executable, str(ROOT / 'scripts/install'), '--user',
                                  '--host-version', '0.160.0', '--check'], env=env,
                                 capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_owned_legacy_role_upgrade_keeps_the_exact_previous_file(self):
        role = self.project / '.codex/agents/method_worker.toml'
        role.parent.mkdir(parents=True)
        previous = ('# Generated by codex-method scripts/install; Codex 0.159.2 V2.\n'
                    'name="method_worker"\ndescription="previous owned role"\n'
                    'developer_instructions="previous instructions"\n')
        role.write_text(previous)
        checked = self.install('--check')
        self.assertNotEqual(checked.returncode, 0)
        self.assertEqual(role.read_text(), previous)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(role.read_text(), previous)
        report = json.loads(result.stdout)
        backups = [Path(path) for path in report['backups']]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), previous)
        self.assertNotIn(role.parent, backups[0].parents)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

    def test_nested_discovered_role_collision_refuses_before_any_write(self):
        role = self.project / '.codex/agents/custom/method_worker.toml'
        role.parent.mkdir(parents=True)
        role.write_text('name="method_worker"\ndescription="mine"\ndeveloper_instructions="mine"\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('collision', result.stderr)
        self.assertFalse((self.project / '.codex/config.toml').exists())
        self.assertEqual(tomllib.loads(role.read_text())['description'], 'mine')

    def test_historical_host_is_not_a_current_package_qualification(self):
        result = self.install('--host-version', '0.159.2')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())

    def test_plugin_manifest_resolves_real_hook_consumer(self):
        self.assertTrue((ROOT / '.codex-plugin/plugin.json').is_file(), 'plugin delivery missing')
        manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())
        config = json.loads((ROOT / manifest['hooks']).read_text())
        self.assertIn('PreToolUse', config['hooks'])
