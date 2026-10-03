"""Generate and check real project-discovered agent role files, without user config writes."""
import json
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
                               str(self.project), '--host-version', '0.159.2', *args],
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
        result = self.install('--host-version', '0.160.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / '.codex').exists())
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_plugin_manifest_resolves_real_hook_consumer(self):
        self.assertTrue((ROOT / '.codex-plugin/plugin.json').is_file(), 'plugin delivery missing')
        manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())
        config = json.loads((ROOT / manifest['hooks']).read_text())
        self.assertIn('PreToolUse', config['hooks'])
