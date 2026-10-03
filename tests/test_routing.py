"""The model and effort the method routes to: one page, every reader."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hard_edges import (anchored_roles, arbitration_settings, helper_line, helper_rows,  # noqa: E402
                        hook_config, ordinary_judgment_setting, Refusal)


class RoutingTest(unittest.TestCase):
    def test_worker_and_reviewer_share_the_anchored_tier(self):
        rows = {role: (model, effort) for role, model, effort in anchored_roles(ROOT)}
        self.assertEqual(rows['worker'], ('gpt-6.1-sol', 'high'))
        self.assertEqual(rows['reviewer'], ('gpt-6.1-sol', 'high'))

    def test_arbitration_is_astra_at_max(self):
        self.assertEqual(arbitration_settings(ROOT), ('gpt-6-astra', 'max'))

    def test_helpers_take_three_tiers(self):
        rows = {work: (model, effort) for work, model, effort in helper_rows(ROOT)}
        self.assertEqual(rows['Its conclusion directly decides a merge or a design '
                              '(checking a worker\'s diff, challenging a design)'],
                         ('gpt-6-astra', 'high'))
        self.assertEqual(rows['Ordinary judgment (research, checking)'],
                         ('gpt-6.1-sol', 'high'))
        self.assertEqual(rows['Mechanical (scans, first-pass triage, evidence gathering, '
                              'fixed-field extraction, lists, format conversion)'],
                         ('gpt-6-luna', 'max'))

    def test_the_default_subagent_is_the_ordinary_judgment_row(self):
        self.assertEqual(ordinary_judgment_setting(ROOT), ('gpt-6.1-sol', 'high'))

    def test_the_helper_line_names_every_row(self):
        line = helper_line(ROOT)
        for model in ('gpt-6-astra', 'gpt-6.1-sol', 'gpt-6-luna'):
            self.assertIn(model, line)

    def test_hook_config_carries_the_default_helper_tier(self):
        config = hook_config(ROOT, 'worker')
        self.assertIn('gpt-6.1-sol', config)
        self.assertIn('hooks.PreToolUse', config)

    def test_a_reworded_row_refuses_instead_of_stale_routing(self):
        scratch = ROOT / 'tests' / '.scratch-page'
        scratch.mkdir(exist_ok=True)
        page = scratch / 'reference'
        page.mkdir(exist_ok=True)
        (page / 'orchestrator.md').write_text('# No table at all\n')
        with self.assertRaises(Refusal):
            helper_rows(scratch)


class NoClaudeTest(unittest.TestCase):
    def test_the_shipped_pages_never_route_to_claude(self):
        hits = []
        for path in (ROOT / 'reference').glob('*.md'):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if re.search(r'\b(Claude Code|claude-cli|--implementation claude|fable)\b', line):
                    hits.append(f'{path.name}:{number}: {line.strip()[:80]}')
        self.assertEqual(hits, [])


if __name__ == '__main__':
    unittest.main()
