# codex-method

A Codex-only adaptation of [DevStandard](https://github.com/LeonJoeeee/devstandard): one
responsive Codex main session coordinates its own native workers, reviewers, and helpers through
the GitHub flow. DevStandard supplied the role contracts, documentation templates, placement
rules, and collaboration machinery. This project's ADR history starts at zero; the source history
is reconciled in [the architecture](docs/architecture.md).

The method adds:

- An issue with Goal, Bounds, and Done-check, carrying the human's settled direction.
- One task, branch, worktree, and accountable writer; an evidence-bearing PR and clean handback.
- Fresh independent Goal/Floor review and green CI for the exact merge result before guarded
  integration. Notes remain useful observations and never create review rounds.
- Durable product, architecture, decision, and substantial-design records at their triggers;
  root `AGENTS.md` holds only operational facts and record language.

Start with [the orchestrator](reference/orchestrator.md). Workers receive
[their contract](reference/worker.md) and [native Codex mechanics](reference/harness-codex.md).
The [reviewer contract](reference/code-review-prompt.md) is the sole judging contract.

## Requirements and settings

The supported host is Codex **0.160.0**, native V2; target probes qualify the mechanics below.
Every worker, reviewer, helper and
arbitration uses explicit `gpt-6.1-sol` at `high`. The main session retains the human's model and
service tier. [Model and effort](reference/orchestrator.md) states those role settings.
A direct, specific human instruction may override a child setting for
that dispatch; there is no automatic model or effort escalation. A requested model's absence or
quota exhaustion
is reported; neither silently substitutes another model or lowers a gate. All agents and helpers
use Codex's built-in tools.

The commands need git, an authenticated `gh`, and a GitHub repository for the full lifecycle.
Native dispatch, review start, and project-role installation need Python 3.11+ (`tomllib`);
review assembly/publication and guard need Python 3.9+.
The native host owns authentication, trust, permissions, and sandbox prerequisites. A child
inherits parent cwd and permissions; the assigned worktree is a role instruction. Independent
nonediting review has a fresh context and ordinary-path hook, with no per-child OS read-only
promise. The [harness page](reference/harness-codex.md) states the complete limits.

[Superpowers](https://github.com/obra/superpowers) is the upstream craft dependency. Install it
into Codex using its plugin marketplace path, then verify that `superpowers:brainstorming`,
`superpowers:writing-plans`, `superpowers:test-driven-development`, and
`superpowers:systematic-debugging` resolve to readable skills:

```sh
codex plugin marketplace add https://github.com/obra/superpowers.git
codex plugin add superpowers@superpowers-dev
```

The source project recorded these command forms on Codex 0.153.4; this adaptation has not
installed or runtime-tested that dependency path on 0.160.0. Inspect the target host's plugin
help and resulting skill discovery before relying on it. A role label alone does not install a
Codex skill. Missing required skills stop the dependent task with an explicit gap.

## Install and verify

The `.codex-plugin/plugin.json` package carries method hooks. Load that package through the
qualified host's plugin facility and establish host trust. SessionStart uses one synchronous handler to deliver the whole orchestrator inline;
`additionalContextLimit: 0` disables host spilling. A fixed 64,000 UTF-8 byte safety budget
covers the entire additionalContext, including its root/path header. Missing, empty, invalid
UTF-8 or oversized pages return a stop response without partial rules. This is the method's
budget, not a Codex limit. Native role definitions are a separate discovery path. Install into the explicitly selected
project by default, or explicitly install user-level roles:

```sh
/path/to/codex-method/scripts/install --project /path/to/project --host-version 0.160.0
/path/to/codex-method/scripts/install --project /path/to/project --host-version 0.160.0 --check
# Explicit opt-in: install user-level roles; verify active discovery in the target session
/path/to/codex-method/scripts/install --user --host-version 0.160.0
```

The installer preserves unrelated project settings and refuses role collisions. It generates
`method_worker`, `method_reviewer`, `method_helper`, and `method_review_helper`, with V2 settings.
Project installation preserves unrelated settings and user configuration. Explicit `--user`
installs roles under `$CODEX_HOME/agents` (default `~/.codex/agents`); active configuration layers still govern discovery in a
new chat. User-level installation is not automatic registration for every project and does not
change the main session's model or service tier.
Both paths refuse unowned collisions; neither installs the plugin or craft dependency. Restart
the trusted target session to discover the roles. The native schema exposes `agent_type` when
roles are loaded; its absence before discovery is not permission to substitute task-name routing.
Verify whole orchestrator delivery and continuation to the actual handle as well as discovery.

## Commands and lifecycle

Settle the result and bounds with the human, prepare an issue, dispatch a lane, drive its PR to
green, review the final head, then return it for the human's merge decision. Explicit delegation
may extend the orchestrator's authority through merge; releases need their own authorization.
Existing projects adopt documents when their triggers fire; a small task does not invent a PRD.

```sh
scripts/dispatch 123 --purpose worker --base origin/main --host-version 0.160.0 --project /path/to/project
scripts/review-packet start 124 --issue 123 --architecture-level no --output /path/to/scratch --host-version 0.160.0 --project /path/to/project
scripts/review-packet publish 124 --issue 123 --attempt COMMENT_ID --verdict /path/to/scratch/verdict.md --project /path/to/project
scripts/review-packet status 124 --issue 123 --project /path/to/project
scripts/guard merge --repo OWNER/REPO --pr 124 --project /path/to/project
```

Dispatch and review start prepare native invocation data; the main session must call the real
native tool with `fork_turns="none"`, record the returned handle, and publish the reviewer's
unedited whole return. For review, the discovered typed role automatically supplies the complete
static contract and harness. The ordinary native message carries the complete filled judging
fence plus workdir, an absolute retained evidence-bundle path and its SHA-256; it does not repeat
that role or inline the whole large bundle. The reviewer must hash the bundle before and after,
read every numbered chunk, and match the filled fence to its pinned packet. A missing, changed
or partially read bundle fails Floor 1. This uses ordinary read tools; the host does not follow
file references or read the bundle automatically. Its UTF-8 digest is the existing packet SHA;
`status` validates new file carriers while retaining historical inline recovery. Publish a returned
Floor-failing verdict whole even when its bundle is missing. The shared-git local review receipt
binds exact head, base, packet, verdict,
and published comment. Remote metadata alone never authorizes acceptance. Add `--execute` to the
guard only within existing merge authorization. Review start requires current installed roles
and returns the exact native JSON at its `instruction` path; recovery follows the orchestrator's
**Review packets** section. Use each command's `--help` for its full contract.

The CI-fallback design remains documented, but its CLI route refuses as unqualified. Rebase
comparison is diagnostic patch/tree equality and does not authorize acceptance reuse; changed
heads need fresh check 1. Version-only review waivers are source principles, not implemented guard
exemptions. See [the architecture](docs/architecture.md) for these dispositions.

## Evidence and layout

Codex 0.160.0 target probes captured loaded native role discovery, complete worker/reviewer
context bytes, explicit `gpt-6.1-sol`/`high`, `fork_turns="none"`, allowed `pwd`, and ordinary
worker-merge, reviewer-write and reviewer-cross-role refusals. Those mechanics probes used a
controlled provider. A separate production call with an explicitly
active role-config layer ran a typed fresh reviewer at Sol/high, retained the supplied prompt
heading and end marker, and omitted a parent-only token; an earlier inactive-config discovery
block remains recorded. This qualifies that reviewer call, not every account, worker execution,
uncoached behavior, user-scope installation or the remote worker/PR/review/merge lifecycle.
Resume, clear/compaction and persistent handle recovery need
separate captured evidence. Codex 0.159.2 source qualification and DevStandard's earlier probes
are historical evidence, not current host support.

```sh
python3 -m unittest discover -s tests -t .
python3 .github/check-routing.py
```

`reference/` holds operative roles, templates, and procedures. `scripts/` and `hooks/` carry the
mechanical lifecycle and ordinary-path restrictions; `.codex-plugin/` is the host package;
`docs/` holds this project's PRD, architecture, and fresh ADR log. Repository-maintenance
instructions live in `docs/maintenance.md`; `AGENTS.md` is the narrow Codex operational entry.
The source-to-target routing in the architecture explains retained content, replacements,
intentional historical omissions, and deferred capabilities.

MIT; source and superpowers attribution are retained. See [LICENSE](LICENSE).
