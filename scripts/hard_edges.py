"""codex-method's fixed helpers, shared by `dispatch`, `review-packet`, `guard` and `hooks`.

A rule's model and effort live in one place — `reference/orchestrator.md`'s Model and effort
section. Everything here reads those cells; a reworded or dropped row refuses loudly instead of
dispatching on a stale model name.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ANCHOR_ROW = re.compile(r'^\|\s*(worker|reviewer)\s*\|\s*`([^`]+)`\s+at\s+`([^`]+)`\s*\|$', re.M)
HELPER_ROW = re.compile(
    r'^\|\s*(.+?)\s*\|\s*`([^`]+)`\s+at\s+`([^`]+)`\s*\|$', re.M)


class Refusal(Exception):
    """A condition the method refuses rather than working around."""


def require(condition, message):
    if not condition:
        raise Refusal(message)
    return condition


def refusing(read, *args):
    """Run `read(*args)` and refuse on a named failure instead of guessing."""
    return read(*args)


def run(*args, cwd=None, env=None, input=None):
    """Run a command; a non-zero exit is a refusal carrying the command's own output."""
    proc = subprocess.run([str(a) for a in args], cwd=cwd, env=env, input=input,
                          text=True, capture_output=True, encoding='utf-8')
    if proc.returncode != 0:
        raise Refusal(f'{args[0]} exited {proc.returncode}: {proc.stderr or proc.stdout}')
    return proc.stdout


def ascending(pair):
    """A monotonic `(major, minor)` comparison key for version strings."""
    return tuple(int(part) for part in pair)


def page(root=None):
    """The one page that states a model and effort, read whole."""
    base = Path(root) if root else ROOT
    target = base if base.suffix == '.md' else base / 'reference/orchestrator.md'
    return target.read_text(encoding='utf-8')


def anchored_roles(root=None):
    """Every (role, model, effort) row `dispatch` reads to configure a role."""
    text = page(root)
    rows = [(m.group(1), m.group(2), m.group(3)) for m in ANCHOR_ROW.finditer(text)]
    require(rows, 'the dispatch page states no anchored role row')
    require({row[0] for row in rows} == {'worker', 'reviewer'},
            f'expected worker and reviewer rows, got {[r[0] for r in rows]}')
    return rows


def helper_rows(root=None):
    """The helper table's rows as (work, model, effort)."""
    text = page(root)
    require("Helpers' work" in text, 'the dispatch page states no helper table header')
    rows = HELPER_ROW.findall(text.split("Helpers' work", 1)[1])
    require(rows, 'the dispatch page states no helper table')
    return [(work.strip(), model, effort) for work, model, effort in rows]


def ordinary_judgment_setting(root=None):
    """Codex's default subagent: the helper row an ordinary judgment takes."""
    rows = [row for row in helper_rows(root) if row[0].startswith('Ordinary judgment')]
    require(len(rows) == 1, 'the dispatch page states no ordinary-judgment helper setting')
    return rows[0][1], rows[0][2]


def helper_line(root=None):
    """The packet line that tells a role its own helpers' routing."""
    return ("Helpers: your own subagents go through Codex's native subagent tool, never a process "
            "on another host, and each takes the model and effort its work needs — "
            + '; '.join(f'{work}: `{model}` at `{effort}`'
                        for work, model, effort in helper_rows(root)) + '.')


def hook_config(root=None, role=None):
    """Parent-session TOML fragment for the qualified V2 host, never spawn arguments.

    Codex role configs do not apply hooks. The parent hook infers a child's role from the native
    payload, and the legacy plugin supplies the same hook without this optional inline fragment.
    """
    root_path = Path(root) if root else ROOT
    require(role in ('worker', 'reviewer'), 'executor role required')
    command = shlex.join([str(root_path / 'hooks/pre-tool-use')])
    model, effort = ordinary_judgment_setting(root)
    return '\n'.join([
        'hooks.PreToolUse=[{matcher=".*",hooks=[{type="command",command='
        + json.dumps(command) + ',timeout=30}]}]',
        'agents.default_subagent_model=' + json.dumps(model),
        'agents.default_subagent_reasoning_effort=' + json.dumps(effort),
        'features.multi_agent_v2.enabled=true',
        'features.multi_agent_v2.expose_spawn_agent_model_overrides=true',
    ])


def arbitration_settings(root=None):
    """(model, effort) for an arbitration: a genuine dilemma, an irreversible judgment."""
    text = page(root)
    match = re.search(r'Arbitration.*?`([^`]+)`\s+at\s+`([^`]+)`', text, re.S)
    require(match, 'the dispatch page states no arbitration setting')
    return match.group(1), match.group(2)


# --- GitHub ---------------------------------------------------------------

def api(endpoint, *args):
    """Read from the GitHub API through `gh`; a refusal carries the failing endpoint."""
    out = run('gh', 'api', endpoint, *args)
    return json.loads(out) if out.strip() else None


def merged_result(base, head):
    """The identity CI must cover to admit a merge."""
    return f'merged-result / {base} / {head}'


def protection_check(repo, branch):
    """Delegate GitHub's protection and active-rules inspection to the one boundary."""
    from protection import protection_check as check
    return check(repo, branch)


def filled(value, name):
    """A required, non-blank field."""
    require(isinstance(value, str) and value.strip(), f'{name} is required')
    return value.strip()


def resolved(path, what):
    """A path resolved once, for identity comparison."""
    path = Path(path)
    return Path(os.path.realpath(path)) if path.exists() else path.resolve()


def same_path(one, other):
    return resolved(one, 'path') == resolved(other, 'path')


def inside(child, ancestor):
    """True when `child` lies under `ancestor`, after resolving both."""
    try:
        resolved(child, 'child').relative_to(resolved(ancestor, 'ancestor'))
        return True
    except ValueError:
        return False


def base_advanced(repo, base_ref, head):
    """True when the base moved ahead of the head's recorded base."""
    out = run('gh', 'api', f'repos/{repo}/compare/{base_ref}...{head}')
    return bool(out) and json.loads(out).get('behind_by', 0) > 0


def round_check(comments, head):
    """The latest whole verdict attached to `head`, or None."""
    from review_packet import decisions
    latest = None
    for comment in comments:
        body = comment.get('body') or ''
        if head in body and 'Ready to merge:' in decisions(body):
            latest = comment
    return latest
