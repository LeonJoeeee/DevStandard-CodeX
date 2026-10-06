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
  the generated root `AGENTS.md` template suggests operational facts and record language while preserving project instructions.

The single Shared collaboration agreements section in the orchestrator applies to ordinary
research and document tasks as well as repository lanes. The hook delivers it to main; the
installer inlines it once into each complete native role. Helpers keep their caller's task
contract without inventing an issue, worktree or PR. General rules need no permanent user-level
AGENTS bootstrap. Preserve useful project-specific AGENTS files.

Start with [the orchestrator](reference/orchestrator.md). Workers receive
[their contract](reference/worker.md) and [native Codex mechanics](reference/harness-codex.md).
The [reviewer contract](reference/code-review-prompt.md) is the sole judging contract.

## Requirements and settings

The qualified hosts are Codex **0.160.0** and **0.160.1**, native V2, with captured Linux
controlled-provider mechanics. The current Windows 0.160.1 installation also has authenticated
startup/role-policy evidence; its isolated workspace-write probe remains blocked as described below.
`scripts/host_contract.py` is the shared exact-version boundary; missing or unknown observations refuse.
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

For safe lane cleanup on Linux, Git must preserve an existing dangling symbolic ref during
create-only `update-ref --no-deref` transactions. **Git 2.52.0 is the tested fixed stable
release.** System Git 2.43.0 failed the existing archive safety regression: a symbolic ref whose
target is missing was treated as absent when checking an expected zero object ID, allowing the
transaction to replace the symbolic archive ref. The [official Git fix](https://github.com/git/git/commit/450fc2bace48ce7ba07a2431175923bf2d610635)
distinguishes that existing ref and refuses the write; the [2.52.0 release notes](https://github.com/git/git/blob/v2.52.0/Documentation/RelNotes/2.52.0.adoc)
describe the related dangling-symbolic-ref fetch fix. With Git 2.52.0, the Linux regression and
all 302 tests passed without implementation or test changes. This is a tested compatibility
point, not an exhaustive minimum for vendor backports or every platform.

The lifecycle commands also require an authenticated GitHub CLI whose `gh api` supports
`--paginate --slurp` for collecting complete ordered API records. System gh 2.45.0 rejected
`--slurp`; [gh 2.102.0](https://github.com/cli/cli/releases/tag/v2.102.0) is the tested Linux
compatibility point, not an exhaustive minimum for other versions or platforms. The
[official `gh api` manual](https://cli.github.com/manual/gh_api) describes these options.

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

Before accepting a Linux installation, run these from the source checkout in the same
environment used to launch method commands:

```sh
command -v git
git --version
python3 -m unittest -v tests.test_dispatch_native.DispatchNativeTest.test_cleanup_cas_refuses_dangling_symbolic_winner_at_transaction
python3 -m unittest discover -s tests -t .
```

Both test commands must exit 0. The targeted regression verifies refusal and preservation when
a dangling symbolic archive ref wins the transaction race. Select a complete fixed Git
installation through the launcher's `PATH`; a shell alias does not select subprocess Git.
Verify the behavior for other versions or vendor backports rather than relying on the version
number alone. These Linux checks do not extend the native host or platform qualification below.

Verify GitHub CLI capability in that same launcher environment, replacing `OWNER`, `REPO`
and `ISSUE` with an existing issue accessible to the authenticated account:

```sh
command -v gh
gh --version
gh api --paginate --slurp repos/OWNER/REPO/issues/ISSUE/comments
```

The API command must exit 0 and return an outer JSON array of pages. Select the verified CLI
through the launcher's `PATH` so method subprocesses use it too.

The repository includes a local native marketplace. For common rules in new chats, register
and install it in the user config layer, then review and trust its current hook hashes:

```sh
codex plugin marketplace add /absolute/path/to/DevStandard-CodeX --json
codex plugin add codex-method@codex-method --json
```

On Windows, Python 3.11+ must be available through `py -3`; hooks use `commandWindows`
with explicit UTF-8 input/output. Invoke method scripts with `py -3`, for example
`py -3 C:\path\to\DevStandard-CodeX\scripts\install --user --host-version 0.160.1`.
Unix hook entry points retain Bash/Python. Installation enables the plugin but does not grant
hook trust. Inspect the native engine's `hooks/list` in the intended chat directories for
both enabled, trusted hooks; inspect the actual new-session context and typed role discovery.
The shipped installer handles role/config files separately. A cache directory or success
message alone proves neither trust nor delivery.

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
Formal roles retain their complete worker/reviewer sources and native harness. Task-local helpers
receive [their bounded contract](reference/task-helper.md), shared agreements and only the relevant
native mechanics; ordinary material work does not inherit a formal PR workflow.
Project installation preserves unrelated settings and user configuration. Explicit `--user`
installs roles under `$CODEX_HOME/agents` (default `~/.codex/agents`); active configuration layers still govern discovery in a
new chat. User-level installation is not automatic registration for every project and does not
change the main session's model or service tier.
Both paths refuse unowned collisions; neither installs the plugin or craft dependency. Restart
the trusted target session to discover the roles. The native schema exposes `agent_type` when
roles are loaded; its absence before discovery is not permission to substitute task-name routing.
Verify whole orchestrator delivery and continuation to the actual handle as well as discovery.
Configured bytes do not prove an existing chat has switched. Before retiring a user-level
collaboration file, retain a stable backup and migration map and qualify the new shared bytes
in fresh main/worker/reviewer/helper requests without that file. Check applicable overrides and
configuration layers. Disabled/untrusted plugins or another host/profile do not automatically
load these rules; use a supported method entry or explicit task carrier. Inspect the actual
native schema: an admitted ordinary helper interface without `agent_type` requires the exact
shared section and assigned role contract explicitly in its message, without typed-discovery
or hook-enforcement claims. Formal gating review retains its qualified typed route.

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

Dispatch carries the dynamic task binding; the discovered role supplies its static contract once.
Dispatch and review start prepare native invocation data; the main session must call the real
native tool with `fork_turns="none"`, record the returned handle, and publish the reviewer's
unedited whole return. For review, the discovered typed role automatically supplies the complete
static contract and harness. For ordinary `review-packet start`, the short native message binds
issue, head, base, reviewer identity and workdir to one absolute retained bundle path and SHA-256.
The bundle alone carries the complete filled contract and evidence. The reviewer must hash it
before and after, read every numbered chunk, and match its contract to those immutable bindings. A missing, changed
or partially read bundle fails Floor 1. This uses ordinary read tools; the host does not follow
file references or read the bundle automatically. Its UTF-8 digest is the existing packet SHA;
`status` validates new file carriers while retaining historical inline recovery. Publish a returned
Floor-failing verdict whole even when its bundle is missing. The shared-git local review receipt
binds exact head, base, packet, verdict,
and published comment. Remote metadata alone never authorizes acceptance. Add `--execute` to the
guard only within existing merge authorization. Review start requires current installed roles
and returns the exact native JSON at its `instruction` path; recovery follows the orchestrator's
**Review packets** section. Use each command's `--help` for its full contract.

Safe already-authorized temporary self-hosted Actions for hosted allowance/capacity refusal
keep ordinary review and CI gates; [the CI guidance](reference/ci-pipelines.md) owns diagnosis,
trust/isolation, equivalence, retained logs and cleanup. The separate degraded local merge-waiver
design remains documented, but its CLI route refuses as unqualified. Rebase
comparison is diagnostic patch/tree equality and does not authorize acceptance reuse; changed
heads need fresh check 1. Version-only review waivers are source principles, not implemented guard
exemptions. See [the architecture](docs/architecture.md) for these dispositions.

## Evidence and layout

The Windows installation work is recorded in [the accepted design](docs/specs/2026-10-06-windows-native-subscription.md)
and [implementation plan](docs/plans/2026-10-06-windows-native-subscription.md), under
[Issue 21](https://github.com/LeonJoeeee/DevStandard-CodeX/issues/21). Full regression and
controlled-provider native CI run on Linux; Windows/macOS CI exercise critical portable
entry points. Critical macOS script checks do not claim a real macOS native session.
On the current Windows 0.160.1 host a fresh authenticated ChatGPT session completed all four
typed roles, allowed cwd reads, and real worker-merge/reviewer-PowerShell-write refusals.
Requested GPT/high routing is distinguished from unavailable independent provider telemetry.
The isolated Windows controlled-provider probe reaches whole context and native role completion
but its workspace-write subprocess execution is blocked by host policy; that probe is not a pass.
Startup evidence does not qualify resume, clear, compact, restart recovery or the full remote lifecycle.

Codex 0.160.0 target probes captured loaded native role discovery, complete worker/reviewer
context bytes, explicit `gpt-6.1-sol`/`high`, `fork_turns="none"`, allowed `pwd`, and ordinary
worker-merge, reviewer-write and reviewer-cross-role refusals. Those mechanics probes used a
controlled provider. A separate production call with an explicitly
active role-config layer ran a typed fresh reviewer at `gpt-6.1-sol`/`high`, retained the supplied prompt
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
instructions live in `docs/maintenance.md`; project `AGENTS.md` preserves native project instructions
and useful operational facts.
The source-to-target routing in the architecture explains retained content, replacements,
intentional historical omissions, and deferred capabilities.

MIT; source and superpowers attribution are retained. See [LICENSE](LICENSE).
