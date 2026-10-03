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

The qualified source baseline is Codex **0.159.2**, native V2. `gpt-6.1-sol` at `high` is the
default for the main session, worker, and reviewer. [Model and effort](reference/orchestrator.md)
states explicit helper and arbitration settings. A requested model's absence or quota exhaustion
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
installed or runtime-tested that dependency path on 0.159.2. Inspect the target host's plugin
help and resulting skill discovery before relying on it. No Claude frontmatter or role label
installs a Codex skill. Missing required skills stop the dependent task with an explicit gap.

## Install and verify

The `.codex-plugin/plugin.json` package carries method hooks. Load that package through the
qualified host's plugin facility and establish host trust. Project agent definitions are a
separate discovery path; generate them only in the explicitly selected project:

```sh
/path/to/codex-method/scripts/install --project /path/to/project --host-version 0.159.2
/path/to/codex-method/scripts/install --project /path/to/project --host-version 0.159.2 --check
```

The installer preserves unrelated project settings and refuses role collisions. It generates
`method_worker`, `method_reviewer`, `method_helper`, and `method_review_helper`, with V2 settings.
It does not edit user configuration or install the plugin/dependency. Restart the trusted target
session, verify role discovery, whole orchestrator delivery, a fresh native child with explicit
model/effort, its allowed command and actual role refusal, and continuation to its real handle.
An installer success or fixture is not evidence of that live qualification.

## Commands and lifecycle

Settle the result and bounds with the human, prepare an issue, dispatch a lane, drive its PR to
green, review the final head, then return it for the human's merge decision. Explicit delegation
may extend the orchestrator's authority through merge; releases need their own authorization.
Existing projects adopt documents when their triggers fire; a small task does not invent a PRD.

```sh
scripts/dispatch 123 --purpose worker --base origin/main --host-version 0.159.2 --project /path/to/project
scripts/review-packet start 124 --issue 123 --architecture-level no --output /path/to/scratch --host-version 0.159.2 --project /path/to/project
scripts/review-packet publish 124 --issue 123 --attempt COMMENT_ID --verdict /path/to/scratch/verdict.md --project /path/to/project
scripts/review-packet status 124 --issue 123 --project /path/to/project
scripts/guard merge --repo OWNER/REPO --pr 124 --project /path/to/project
```

Dispatch and review start prepare native invocation data; the main session must call the real
native tool with `fork_turns="none"`, record the returned handle, and publish the reviewer's
unedited whole return. The shared-git local review receipt binds exact head, base, packet, verdict,
and published comment. Remote metadata alone never authorizes acceptance. Add `--execute` to the
guard only within existing merge authorization. Review start requires current installed roles
and returns the exact native JSON at its `instruction` path; recovery follows the orchestrator's
**Review packets** section. Use each command's `--help` for its full contract.

The CI-fallback design remains documented, but its CLI route refuses as unqualified. Rebase
comparison is diagnostic patch/tree equality and does not authorize acceptance reuse; changed
heads need fresh check 1. Version-only review waivers are source principles, not implemented guard
exemptions. See [the architecture](docs/architecture.md) for these dispositions.

## Evidence and layout

This checkout is an adaptation deliverable, not a claim that the package has been installed or
that the complete live worker/PR/review/merge lifecycle has passed. Source qualification for
0.159.2 establishes interface and inheritance behavior; production account access, installed
hook behavior, clear/compaction, and end-to-end integration need captured target evidence.
DevStandard's historical probes are not inherited runtime evidence.

```sh
python3 -m unittest discover -s tests -t .
python3 .github/check-routing.py
```

`reference/` holds operative roles, templates, and procedures. `scripts/` and `hooks/` carry the
mechanical lifecycle and ordinary-path restrictions; `.codex-plugin/` is the host package;
`docs/` holds this project's PRD, architecture, and fresh ADR log. Repository-maintenance
instructions remain in existing `CLAUDE.md`; `AGENTS.md` is the narrow Codex operational entry.
The source-to-target routing in the architecture explains retained content, replacements,
intentional historical omissions, and deferred capabilities.

MIT; source and superpowers attribution are retained. See [LICENSE](LICENSE).
