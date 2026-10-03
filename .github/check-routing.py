"""The dispatch page is the only statement of a model and effort: check its cell form."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hard_edges import (anchored_roles, arbitration_settings, helper_rows,  # noqa: E402
                        ordinary_judgment_setting)

rows = anchored_roles(ROOT)
helpers = helper_rows(ROOT)
arb = arbitration_settings(ROOT)
assert {r[0] for r in rows} == {'worker', 'reviewer'}, rows
assert arb == ('gpt-6-astra', 'max'), arb
assert ordinary_judgment_setting(ROOT) == ('gpt-6.1-sol', 'high')
assert len(helpers) >= 3, helpers
names = sorted({r[1] for r in rows} | {r[1] for r in helpers} | {arb[0]})
assert names == ['gpt-6-astra', 'gpt-6-luna', 'gpt-6.1-sol'], names
print('static assertions OK; models', names)
