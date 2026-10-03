"""The actual ADR gate rejects an amendment its status block does not announce."""
from pathlib import Path
import subprocess
import sys
import unittest
from tests.github_fixture import GitHubFixture, ROOT


class ADRGateTest(unittest.TestCase):
    def setUp(self):
        self.fx=GitHubFixture();self.addCleanup(self.fx.close)
        directory=self.fx.project/'docs/adr';directory.mkdir(parents=True)
        self.adr=directory/'0001-decision.md'

    def check(self, text):
        self.adr.write_text(text)
        return subprocess.run([sys.executable,str(ROOT/'.github/check-adr-index.py')],
                              cwd=self.fx.project,text=True,capture_output=True)

    def test_announced_date_and_wrapped_status_pass(self):
        result=self.check('# Decision\nStatus: Accepted;\nAmended (2026-10-03)\n\n'
                          '**Amendment (2026-10-03):**\nA correction.\n')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_missing_announcement_fails(self):
        result=self.check('# Decision\nStatus: Accepted\n\n'
                          '**Amendment (2026-10-03):**\nA correction.\n')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('no `Amended (2026-10-03)`',result.stdout)

    def test_cited_amending_adr_requires_the_matching_status_form(self):
        wrong=self.check('Status: Accepted; Amended (2026-10-03)\n\n'
                         '**Amendment (2026-10-03, see 0002):**\nCorrection.\n')
        self.assertNotEqual(wrong.returncode,0)
        right=self.check('Status: Accepted; Amended by 0002 (2026-10-03)\n\n'
                         '**Amendment (2026-10-03, see 0002):**\nCorrection.\n')
        self.assertEqual(right.returncode,0,right.stdout+right.stderr)

    def test_closed_template_fence_is_not_an_amendment(self):
        result=self.check('Status: Accepted\n\n```md\n'
                          '**Amendment (2026-10-03):**\nExample.\n```\n')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_unclosed_fence_cannot_hide_an_actual_amendment(self):
        result=self.check('Status: Accepted\n\n```md\n'
                          '**Amendment (2026-10-03):**\nCorrection.\n')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('no `Amended (2026-10-03)`',result.stdout)
