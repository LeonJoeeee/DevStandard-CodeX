# codex-method — Architecture

> Shared baseline for all parallel work. Read before any task.
> Changing anything here = touching the core: public merge + human approval + an ADR.

## Context and provenance

codex-method adapts DevStandard's GitHub collaboration method to one Codex main session and
native Codex workers, reviewers, and helpers. The adaptation source is
`/home/leon/projects/prod/devstandard` at `d593c67f6850fccca9246833c8fc7419836ce23a`.
It supplies rules, templates, craft bindings, and machinery; this repository is not source-free.
Source ADR/spec/research history stays in the source repository. This project's ADR history
starts at 0000, with the original 0001 preserved and corrected by dated amendment.

The host owns sessions, authentication, tools, model access, permissions, and native children.
The method adds the protocol linking issue → lane → evidence-bearing PR → independent judgment
→ exact-head integration → cleanup → authorized release. GitHub is the durable collaboration
record. Native handles are session observations. A local shared-git review receipt verifies the
shipped lifecycle's relationship to its public record; it is not another task tracker.

## Structure and ownership

| Component | Ownership and interface |
|---|---|
| Orchestrator role | `reference/orchestrator.md` is the complete main-session contract: human handover, responsive event loop, dispatch, design challenge, acceptance, integration, recovery, cleanup, release, and requirements craft. |
| Worker role | `reference/worker.md` plus `reference/harness-codex.md` supplies one lane's execution, evidence, escalation, and native recovery obligations. Its freshly fetched packet carries the whole ordered issue, named base, branch, worktree, inputs, output duty, language and attribution. |
| Reviewer role | The discovered typed role automatically supplies the complete canonical judging contract and harness. The native message carries the complete filled fence, workdir and a retained complete packet path plus SHA-256. The child explicitly hashes before/after and reads all numbered chunks; missing, partial, changed or inconsistent evidence fails Floor 1. The packet retains exact pins, claims, authority, diff forms, status captures and gaps. No implementation craft or publication authority. |
| Native delivery | Package hooks use `.codex-plugin/plugin.json` and the host-provided `PLUGIN_ROOT`. SessionStart covers startup/resume/clear/compact; insufficient configured parts stop rather than deliver partial context. `scripts/install` separately generates project `.codex/agents/*.toml` roles: `method_worker`, `method_reviewer`, `method_helper`, `method_review_helper`. Roles carry developer instructions only; actual native calls supply model/effort so role config cannot silently override the invocation. Hook configuration belongs to the package. |
| Dispatcher | `scripts/dispatch` creates or validates a lane and prepares native invocation data. Lane receipts, locks and retained briefs live in the Git common directory under `codex-method/lanes`; a repository-wide ownership lock prevents different checkouts from admitting overlapping writers. The caller launches, observes, records and continues the real child. A resolver remains an ordinary lane worker. |
| Review lifecycle | `scripts/review-packet`, packet assembly, and `scripts/review_state.py` use one shared parser and ledger in the common git directory: `codex-method/reviews/OWNER/REPO/PR.json`. Start qualifies installed roles and prepares the fresh six-field native instruction. Reservation id/token, issue/head/base, identity/author, packet SHA (also the retained UTF-8 bundle), instruction SHA, raw verdict SHA and exact comment SHA bind start, publish, status and guard. Short native transport avoids role duplication and large inline evidence without dropping bundle bytes. Pending intent is durable before remote mutation; status recovers only exact association, never retries an unknown outcome. |
| Integration and protection | `scripts/guard` verifies the current default branch, current-base ancestry, exact accepted receipt/head/base, and green `merged-result / BASE_SHA / HEAD_SHA` from GitHub Actions app `15368`, with no failed head checks. It re-fetches before execute and merges with `--match-head-commit`. No automatic remote-branch deletion. Protection is provisioned deliberately with explicit required check names. |
| On-demand guidance | Other `reference/` pages own document admission, placement, templates, CI upkeep, red/flaky checks and fallback design. `AGENTS.md` is commands/gotchas/copy-list/language only; `docs/maintenance.md` is this repository's maintenance authority. |

The orchestrator processes events briefly and observes outstanding lanes. Independent writable
scopes permit parallel workers; shared writable paths have one accountable writer. Task-local
helpers are below the GitHub coordination layer and return to their caller. They retain that
caller's authority bounds and explicit model/effort. Reviewer helpers retain the nonediting role.

## Enforcement and qualification

The full safety rules and hook scope live in `reference/orchestrator.md`'s The role hook section;
other pages point there. Structural lane ownership, native role instructions, and fresh packets
carry obligations; the ordinary-path hook denies its listed acts; GitHub protection and exact
review/CI identity checks gate integration. Evidence truth, goal fulfillment, design choices,
irreversible authorization and nonconvergence still require judgment. A hard gate is not lowered
because its tool or model is unavailable.

Codex **0.160.0**, native V2 is the supported host; target probes qualify the mechanics below. Native roles
must be discovered before dispatch: the schema exposes `agent_type` only when roles are loaded.
Project installation remains explicitly scoped; `scripts/install --user` opts into roles under
`~/.codex/agents`. Active configuration layers still govern discovery; user files alone do not
register roles for every project. Both paths preserve unrelated settings and refuse unowned
collisions. No installer changes the main session's chosen model or service tier. Default children are all
Sol/high; only a direct, specific human instruction overrides its named dispatch, never an
automatic escalation or quota fallback.

Target probes captured complete worker/reviewer role bytes, explicit `gpt-6.1-sol`/`high`,
`fork_turns="none"`, an allowed `pwd`, and worker merge, reviewer write and reviewer cross-role
refusals. The hook normalizes the actual native spawn alias before role checks. Ordinary command checks
use executable argv segments, including assignment/wrapper/absolute-path normalization, without
interpreting search prose as a command. Worker pushes need an explicit remote and branch refspec;
implicit/default targets refuse. Interactive stdin and arbitrary MCP/script writes remain outside
this ordinary-path boundary. These mechanics captures use the actual host with a controlled provider. A separate production
Sol/high typed fresh-reviewer call, with its role-config layer explicitly active, retained the
prompt heading/end marker and omitted a parent-only token. Its earlier inactive-config discovery
block remains evidence. That production call does not establish universal account access,
user-scope installation, uncoached adherence or a complete remote PR lifecycle. Source/schema qualification on
0.159.2 remains historical evidence; it does not extend the current support boundary.

Children inherit parent cwd and permissions. A child worktree instruction is not OS isolation;
fresh native nonediting review is a context/contract/hook property, not per-child OS read-only
enforcement. Same-credential hostile filesystem edits, obfuscation/interpreters, a compromised
host and arbitrary MCP writes remain outside the threat model. Main startup/resume delivery,
clear/compaction, persistent handles and remote protected integration need distinct captured
evidence. Local constructed checks and target runtime captures are reported separately.

A pending local review reservation blocks another start. Every returned verdict burns a round,
including malformed responses; a failed attempt with no verdict burns none. Raw publication and
its exact comment receipt precede action. Remote `codex-method-attempt-v2` metadata alone is not
authentication; missing local receipts block. A Notes-only accepted head does not get another
review round. Actual PREWRITE/DELIVERY captures travel as supplied; a missing historical baseline
remains disclosed even when a prospective repair baseline is captured.

## Source-to-target reconciliation

These routes cover the source corpus, including historical material. “Retained” means its live
rules remain at the target; “replaced” names the native carrier for the same duty; “history” keeps
provenance at the pinned source rather than misrepresenting old decisions or probes as this
project's history; “deferred” preserves a source capability and states the implementation gap.
No route imports another host, quotas as routing authority, or a weaker gate.

| Source | Target/disposition |
|---|---|
| `README.md` | Adapted README: honest source attribution, native-only roles, dependency/install path, command lifecycle, qualification limits. Source marketplace/badges/release claims are source-project history. |
| `CLAUDE.md` (source) | Applicable repository operations moved to target `docs/maintenance.md`; the old target host entry was removed. The Codex operational entry and template are `AGENTS.md` and `reference/repo-agents-md.md`; method prose is not injected into root memory. |
| `reference/orchestrator.md` | Same target: entire handover/event/task/merge/recovery flow retained. Native invocation/continuation replaces cross-host execution. Restored bounded goals, unsettled-design challenge, brainstorming binding, refusal escalation and property-preserving unavailable-capability route. |
| `reference/worker.md` | Same target: receipt vetting, full task carrier, bounded writes/unbounded tracing, baseline/final evidence, own diff inspection, PR-green ownership, verify/refute, stop events and execution craft retained. Explicit actual status captures and native binding recovery. |
| `reference/harness-codex.md`, `reference/harness-claude.md` | Replaced by native `reference/harness-codex.md`: role delivery, inherited cwd/permissions, native handle observation/continuation and exact binding recovery. Cross-host process supervision and host-specific persistence recipes are inapplicable history. |
| `reference/code-review-prompt.md` | Same target judging fence and superpowers attribution. Native start/unedited publication and local receipts replace external execution. Goal/Floor/Notes, integrity, accepted-spec authority, bounded goals and nonconvergence retained. |
| `reference/prd.md`, `reference/architecture.md` | Same targets: founding/task-scoped triggers, altitude, split-on-zoom, shared baseline, established-path mapping, lean setup and protection order. Requirements pointers resolve to orchestrator craft. |
| `reference/adr.md` | Same target: significant-cost admission, concurrent claim discipline, immutable bodies, discoverable dated amendments. Target ADR log starts at 0000. |
| `reference/design-spec.md` | Same target: significance/exemptions, real options, proportional detail, conditional rollback, independent pre-code challenge, accepted reachable blob published before continuation, implementation status and permanent abandoned records. Craft pointer corrected to orchestrator. |
| `reference/in-repo-writes.md` | Same target predicate, including exact count delimiter: method trigger, established base convention, requested authority, edit exceptions, no competing authorities or invented handoffs. Root memory renamed to AGENTS. |
| `reference/where-it-goes.md` | Same target: pre-existing project-specific authority, product-interface versus actual development write, project-local default, expensive kinds, secret containment and sole-copy durability. Source incident numbers are provenance, not target issue authority. |
| `reference/out-of-repo-writes.md` | Same target: documented cache precedence, authorized cache-root relay, must-keep exception, declared runtime root and retention, task scratch and durable external-write disclosure. Native brief retention replaces process-specific scratch mechanics. No invented Floor rule added. |
| `reference/repo-claude-md.md` | `reference/repo-agents-md.md`: commands/gotchas/copy-list/conditional language fence, authorized-root relay, meaningful creation, short-branch writeback and subtract-to-fit cap, established record language and canonical translation mirrors. Existing operational sources are respected. |
| `reference/ci-pipelines.md` | Same target templates: exact merged-result binding, least privilege, action pins/Dependabot, retention, spend diagnosis, ephemeral runner constraints, maintenance, protection and release. Provider minutes diagnosis is retained; agent model quota balancing is absent. |
| `reference/red-check.md` | Same target: own regression, deliberately staled assumption and unrelated failure routes; visible reviewed quarantine, no retry-to-green. Gate changes require independent scrutiny while both checks still run. |
| `reference/ci-cannot-run.md` | Same target fallback design: proven external platform trigger, wait default, exact two-parent synthetic merge and fresh full-job evidence, review audit, protection/return sweep, no fallback release. CLI fallback is blocked as unqualified; no marker-based waiver or gate lowering. |
| `agents/worker.md`, `agents/reviewer.md` | Generated project native TOML roles use canonical worker/harness/reviewer instructions. Claude frontmatter, tool-denial and hooks fields are not transplanted as effective Codex role fields. |
| `scripts/dispatch`, `scripts/review-packet`, `scripts/review_packet.py`, `scripts/guard`, `scripts/hard_edges.py` | Corresponding target command responsibilities; native receipt/lane observation and common local review ledger replace external lifecycle. Exact receipt/head/base and Actions-app CI producer checks strengthen the ordinary shipped route. |
| `hooks/session-start`, `hooks/hooks.json`, `hooks/pre-tool-use` | Corresponding target hooks: whole-role delivery, actual native role identity, structured denial and ordinary-path enforcement. Source host matcher/cap/runtime claims require new qualification. |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Replaced host packaging by `.codex-plugin/plugin.json` and explicit project-role installer. Source marketplace coordinates/version history are not a claimed target release. |
| `.github/check-core-budget.py`, `.github/check-agents.py`, `.github/check-adr-index.py`, `.github/test-session-start.py`, `.github/test-agents.py`, `.github/test-dispatch.py`, `.github/test-review-packet.py`, `.github/test-hard-edges.py` | Their invariant/check duties route to target routing, delivery, native-hook/install, lane/command, review lifecycle/evidence, and protection/release checks. Source green results are not target evidence. |
| `.github/test-claude-runtime.py`, `.github/test-codex-runtime.py` | Source runtime evidence remains history. Native V2 target qualification must exercise installed hooks, discovery, model/effort, native spawn/continuation and limits rather than port vendor-process fixtures. |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/dependabot.yml` | Target CI/package verification and `reference/ci-pipelines.md` setup templates own the duties. Source workflow/version/release history is not asserted as a shipped target pipeline; target release qualification is owed separately. |
| `docs/PRD.md`, `docs/architecture.md` | Adapted target definition and architecture: preserve problems, GitHub/craft reuse, all three workflows, role-context separation, delivery/enforcement/observability and convergence; revise native mechanics and make evidence limits explicit. Source acceptance records remain source history. |
| `LICENSE`, `.gitignore`, source repository-only configuration | Retain license attribution and route worktree-ignore/packaging duties to corresponding target files. Source repository-specific host settings are not installed into the target. Generated `scripts/__pycache__` is disposable source runtime output, not product content. |

### Historical research and design routes

Research reports remain non-normative provenance at the pinned source. Retained findings are
operative in the named targets; superseded drafts, empirical tallies, and another host's controls
are not copied as target claims.

| Source research/spec | Retained result and explicit departure |
|---|---|
| `_source/doc-layering-research.md` | ADR cost-of-change admission, substantial design/exemptions, permanent status-marked specs, and split-by-domain architecture zoom → the four documentation templates. No spec kit hierarchy or new journal. |
| `_source/devstandard-optimization-sweep.md` | PR-only edits after protection, spec-status ownership, merge-queue exclusion, useful operational memory/writeback → orchestrator/design-spec/repo-agents/CI. Old plugin survey and tallies remain history. |
| `_source/full-audit-v090.md` | Rebase before final evidence, explicit challenge owner, synchronized invalidated guidance, honest outward claims, immutable history → worker/design-spec/README/ADR. No copied source release/changelog assertions. |
| `_source/ci-maintenance-industry-alignment.md` | Vendor-clock rot, least privilege, independent gate-change review, flakes/quarantine, revert-first, action pins and Dependabot → CI/red-check/reviewer/orchestrator. Source research metrics are not target measurements. |
| `_source/superpowers-porting-plan.md` | Role-scoped craft dependency and absorbed worktree/review/evidence/escalation principles → orchestrator/worker/reviewer. Copying whole craft skills, old controller choreography and source host-specific workflows are declined. |
| `_source/superpowers-coupling-map.md` | Central requirements versus execution bindings, no duplicate craft prose, return-to-method conflict fence → orchestrator/worker and template pointers. Its historical skill version and earlier writing-plans placement do not override the final source role binding. |
| `_source/superpowers-absorption-quarry.md` | Cold receipt vetting, final evidence, self-review, verify/refute, disclose doubt, escalation, worktree detection/base-relative inventory, proportional design detail → worker/orchestrator/design-spec/architecture. Empirically corrected submodule rationale is not revived. |
| `_source/workflow-feature-research.md` | Sole writer, fresh judging context, real evidence, missing judge cannot pass, human decisions outside unattended execution → native role/lifecycle contract. Source Workflow APIs, numeric budgets, quota routing and speculative loader capabilities are outside Codex-native scope. |
| `_source/workflow-deep-dive-report.md` | Decision-free bounded task slices, clear human gates, observable results, resource coordination → orchestrator/worker. Old host capacity, timing/cost/resume claims and budget-reserve machinery remain source history. |
| `docs/specs/2026-08-25-devstandard-codex-adapter.md` | Abandoned source adapter remains history. Reliable native entry/delivery and explicit mapping duties → AGENTS/harness/install; checkout pointer/adoption scheme is replaced by native package plus project roles. |
| `docs/specs/2026-08-26-claude-leads-codex-executes.md` | Source host hierarchy intentionally replaced by Codex-only native hierarchy. Whole role delivery, version-qualified hooks and rollback/verification discipline survive in harness/installer qualification. |
| `docs/specs/2026-08-26-codex-gets-the-full-method.md` | Static/dynamic role separation, complete context, method source path and worker authority binding → native worker/harness. Old cross-host identity and branching startup implementation remain history. |
| `docs/specs/2026-08-26-when-a-subagent-when-codex.md` | Explicit role model/effort and same-harness helpers → orchestrator/native spawn. External-executor selection and earlier model defaults are replaced by `gpt-6.1-sol`/`high` anchors and explicit escalation. |
| `docs/specs/2026-08-27-in-repo-writes.md` | Final rule/default, expensive kinds, authority relay, document predicate and clean-tree accounting → where-it-goes/out-of-repo/in-repo/repo-agents/roles. Failed taxonomies and rejected alternatives remain history; no invented classification gate. |
| `docs/specs/2026-09-06-core-md-rule-ledger.md` | Final clauses route to complete role pages and triggered references above: per-issue weight, dispatch-first, one writer, green-before-review, evidence/scope Floors, no invented state docs, operational-memory fence, search-twice reconciliation. Earlier intermediate page names/drop proposals do not resurrect removed method hierarchies. Hook-cap/carrier observations are source evidence, not Codex qualification. |

### Source ADR routing (history is intentionally not copied)

| Source ADRs | Operative target or intentional departure |
|---|---|
| 0000 | Target 0000 and `reference/adr.md`: decision-log discipline. |
| 0001, 0007, 0019, 0031, 0049, 0059, 0060, 0061 | Role-specific whole-context delivery and one source per artifact → native harness/hooks/installer; retired skill-only/shared-core/Claude-body carriers remain history. |
| 0002, 0016, 0028 | Upstream superpowers dependency, central role craft bindings and original attribution retained; source translations retired rather than duplicated. |
| 0003, 0008, 0014, 0048 | Task-scoped document/weight triggers and dispatch boundaries retained; setup tiers, execution ladders, workflow rationing and quota balancing replaced by bounded issues/native roles. |
| 0004 | Founding sequence → PRD/CI/orchestrator templates; no automatic full ceremony for each new task. |
| 0005, 0009, 0015, 0047, 0055, 0057 | GitHub flow, independent lanes, accountable writer, responsive orchestrator, fixed dispatch, task-local native helpers → roles/commands. No second coordination engine. |
| 0006 | Native mechanics supplement the collaboration protocol; “Workflow is the whole harness” is superseded source history. |
| 0010, 0029, 0030, 0032, 0043 | Source rename/changelog/audit and repo-only guidance remain source history; target README provenance, target maintenance and architecture routing retain applicable disciplines. |
| 0011, 0022, 0026, 0044 | Both gates, universal PR path, PR-green ownership and Goal/Floor/Notes → roles/reviewer/guard. Version-only source waiver is not wired into this guard. |
| 0012, 0041 | Task-bound worktree lifecycle, adopted input discipline, baseline/clean handback → worker/orchestrator/dispatcher. |
| 0013, 0033 | Concurrent ADR numbering and discoverable amendment status → `reference/adr.md` and fresh target log. |
| 0017 | Design middle layer and substantial-change trigger → design-spec; native independent challenge before building. |
| 0018, 0023 | Operational memory and canonical record language/translation → repo-agents and root AGENTS. Source CLAUDE memory carrier adapted, existing repository operations preserved. Copy-list entries are nonconfidential only; secrets are not copied into lanes. |
| 0020, 0021 | Revert-first red-main recovery and pipeline pin upkeep → orchestrator/CI. |
| 0024, 0040, 0050 | Explicit model/effort and role/helper routes → orchestrator: every worker, reviewer, helper and arbitration uses `gpt-6.1-sol`/`high`; no model ladder, quota-balancing or silent alternatives. Source model names/tier caps are historical settings. |
| 0025 | Fallback trigger/evidence/audit/return property retained in ci-cannot-run; shipped route blocked as unqualified. |
| 0027 | Search both rule statements and pointer/paraphrase sites → retained repository maintenance discipline. ADR bodies are corrected by amendment. |
| 0034 | Whole verdict published at return before acting → review lifecycle; caller receives native return and publishes its exact raw bytes. |
| 0035, 0046 | Changed-head review default and narrow acceptance-reuse proof properties retained; `compare` is diagnostic and no automatic rebase/quoted-fix/version-field reuse is shipped. |
| 0036, 0038, 0039, 0045, 0056, 0063 | Executor/host evolution is source history. Human's Codex-only native ruling replaces cross-host selection and both removals/restorations; target 0001 amendment states provenance and actual limits. |
| 0037, 0042 | Established authority/default/expensive kinds, cache/root/retention/durability and admitted documents → placement/in-repo/out-of-repo/repo-agents. |
| 0051, 0052, 0062 | Ordinary-path role hook, no hook policy hierarchy and irreversible boundaries → orchestrator hook rules. Native reviewer ordinary write denials are explicit; no malicious isolation claim. |
| 0053, 0054 | First-principles problem research and bounded writes with unrestricted tracing → orchestrator/worker/reviewer. |
| 0058 | Human-to-orchestrator handover and interruption grounds → orchestrator. Explicit user authorization persists; no redundant approval form. |

## Deferred capabilities and verification boundary

The source acceptance-reuse design requires conflict-free replay, every PR-changed byte/mode
unchanged, only synchronized monotonic version fields exempted, then exact merged-result CI.
The shipped `compare` only diagnoses patch/tree equality. Re-review changed heads by default;
never promote its output into reuse authorization. Quoted Note replacements and bare-version
waivers likewise have no wired guard exemption. Source principle is preserved without a false
implementation claim.

The fallback design requires proven provider-wide inability to run, why waiting is ruled out,
an exact synthetic two-parent merge, all CI jobs on that tree, fresh before/after accounting,
independent audit, exact receipt association, a protected integration route and prompt return sweep.
The shipped fallback refuses; a comment substring is not a waiver. No release uses that route.
These are code/qualification follow-ups, not deleted source requirements.

The dispatcher records actual supplied native spawn/status observations but cannot authenticate
them or stop children. One shared Git lane ledger covers all checkouts. Legacy checkout-local
receipts are imported only when uniquely consistent; originals and their hashes remain retained.
Conflicts or later changes to a retained legacy record refuse rather than erase ownership. `--continue` prepares a fresh identity; retained-handle continuation uses
native `followup_task`, refreshed issue context and status observations on the original handle.
An old-version run keeps its original host identity. Preparing a current-version child requires
current qualification and fresh actual completion evidence for the old handle; no force option
disposes of an uncertain child.
Automated cleanup conservatively requires local ancestor integration and nonforced deletion;
squash/rebase merged lanes remain preserved pending explicit disposition. Extending that route
must preserve unintegrated commits and sole copies, not bypass its refusal.

The dispatcher reads the root `AGENTS.md` record-language declaration into the fresh packet;
absence means English. An explicit declaration must be singular and readable, otherwise dispatch
refuses rather than guessing or starting a mixed record. Initial input/output briefs and refreshed
continuation briefs travel verbatim; missing required input is returned before launching work.

Target 0.160.0 role discovery/context and ordinary role denials have captured evidence. Account
model availability, main-session resume/clear/compaction delivery, handle recovery after restart,
and a live remote lifecycle still need separate evidence before broader readiness claims. Test the
ordinary shipped paths against the declared threat boundary; fixtures establish only the properties
they actually reach. Do not claim the source's runtime success as the target's.

## Key quality goals

- Human time goes to direction and judgment; independent lanes make progress observable.
- Evidence and exact identity survive handoff; self-reports never replace acceptance.
- Goal substance survives review; Notes and nonconvergence do not create endless polishing.
- One source per rule and narrow operational memory keep context readable and maintainable.
- Native semantics and disclosed limits prevent packaging or permission claims the host cannot honor.

Decisions and their reasons: `docs/adr/`. Canonical product definition: `docs/PRD.md`.


## Ordinary review transport

A 0.2.0 formal review could not launch its native child from the default desktop path: the
prepared message duplicated the static role and inlined a roughly 224 KB packet. Earlier native
role probes and green CI remain evidence for their own versions and properties; they did not
qualify this large-message caller path.

The corrected route keeps the six native fields and automatic typed-role delivery. Its message
contains the complete filled judging fence, explicit workdir and an absolute retained token-directory
bundle path with SHA-256. The original complete bundle remains intact. The reviewer verifies the
digest before and after, explicitly reads all numbered chunks, and checks the inline/bundle contract
match; absent access, drift, mismatches or partial reads fail Floor 1. This is ordinary tool reading,
not automatic host file-reference loading or a special code-mode-only route. Receipt recovery
retains the bundle and instruction identities. The existing packet SHA identifies the complete
UTF-8 file bytes; the instruction SHA binds the inline fence, path and digest. New local receipts
mark `packet_carrier: file-sha256-v1` so status refuses missing or changed carrier files without
reinterpreting historical inline attempts. Raw Floor-failing verdict publication remains possible
even when its carrier is missing, so failure evidence is not lost. Updated role bytes and the
default caller route
need fresh qualification; the earlier 0.2.0 results do not prove this correction.
