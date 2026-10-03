"""Validate real release metadata and the checked-out integration object."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from tests.github_fixture import GitHubFixture, ROOT


class ReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.fx=GitHubFixture();self.addCleanup(self.fx.close)
        (self.fx.project/'.codex-plugin').mkdir()
        (self.fx.project/'codex-method.json').write_text(json.dumps({'version':'0.2.0'}))
        (self.fx.project/'.codex-plugin/plugin.json').write_text(json.dumps({'version':'0.2.0'}))

    def check(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'.github/check-release.py'),
                               '--root',str(self.fx.project),*args],text=True,capture_output=True)

    def test_equal_versions_match_the_actual_tag(self):
        result=self.check('--tag','v0.2.0')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_plugin_descriptor_mismatch_refuses_release(self):
        (self.fx.project/'.codex-plugin/plugin.json').write_text('{"version":"0.1.0"}')
        self.assertNotEqual(self.check().returncode,0)

    def test_tag_mismatch_refuses_release(self):
        self.assertNotEqual(self.check('--tag','v0.3.0').returncode,0)

    def test_missing_plugin_manifest_is_not_a_successful_single_version_check(self):
        (self.fx.project/'.codex-plugin/plugin.json').unlink()
        self.assertNotEqual(self.check().returncode,0)


class MergeCheckoutGateTest(unittest.TestCase):
    def setUp(self):
        self.fx=GitHubFixture();self.addCleanup(self.fx.close)

    def check(self,base=None,head=None):
        return subprocess.run([sys.executable,str(ROOT/'.github/check-merge-checkout.py'),
                               '--root',str(self.fx.project),'--base',base or self.fx.base,
                               '--head',head or self.fx.head],text=True,capture_output=True)

    def merge_checkout(self):
        tree=self.fx.git('rev-parse','HEAD^{tree}').strip()
        merge=self.fx.git('commit-tree',tree,'-p',self.fx.base,'-p',self.fx.head,'-m','integration').strip()
        self.fx.git('checkout','--detach',merge)

    def test_declared_identity_matches_actual_two_parent_checkout(self):
        self.merge_checkout()
        result=self.check()
        self.assertEqual(result.returncode,0,result.stderr)

    def test_branch_head_is_not_integration_evidence(self):
        self.assertNotEqual(self.check().returncode,0)

    def test_swapped_or_other_parent_identity_refuses(self):
        self.merge_checkout()
        self.assertNotEqual(self.check(base=self.fx.head,head=self.fx.base).returncode,0)
        self.assertNotEqual(self.check(base='a'*40).returncode,0)
