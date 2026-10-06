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
assert arb == ('deepseek-v4.1-flash', 'max'), arb
assert ordinary_judgment_setting(ROOT) == ('deepseek-v4.1-flash', 'max')
assert len(helpers) >= 3, helpers
names = sorted({r[1] for r in rows} | {r[1] for r in helpers} | {arb[0]})
assert names == ['deepseek-v4.1-flash'], names
assert all((row[1], row[2]) == ('deepseek-v4.1-flash', 'max') for row in rows + helpers)
print('static assertions OK; models', names)
