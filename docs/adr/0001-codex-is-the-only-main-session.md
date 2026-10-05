# 0001 — Codex is the only main session, and every worker is its own built-in subagent

Status: Accepted (2026-09-29); Amended (2026-10-03); Amended (2026-10-04); Amended (2026-10-05).

*This ADR decides what this method ships. A reader in any seeded project should take it as method.*

## Context

The human's ruling, 2026-09-29: build a method that a Codex main session runs end to end, and do not
carry a cross-host executor into it. Two earlier positions shaped the ruling. A sibling method had
just removed Codex hosting because, as a main session on shared rules, Codex followed its own harness
logic instead. And the same discussion settled that a helper a role spawns uses its own harness's
built-in subagent — never another host's process — because cross-harness nesting solves nothing and
costs a whole layer of machinery.

The method starts from zero: its decision log is this file, and no other project's pages are its
source.

## Decision

Codex is the only main session. Dispatched work and gating review both go to Codex's own built-in
subagent; there is no `--implementation` selector and no second vendor's agent anywhere in the
shipped commands. The dispatcher prepares a native-worker receipt (model, effort, brief) and the
caller hands it to Codex's native spawn with conversation-history forking disabled, then records the
returned handle on the issue — the dispatcher observes no handle, so that record is the evidence one
finished.

Model and effort are stated once, on `reference/orchestrator.md`'s Model and effort section, and
every reader takes them from there: `scripts/dispatch` for the anchored rows, the packet's `Helpers:`
line for a role's own subagents, `review-packet` for an arbitration. A row that cannot be read
refuses rather than dispatching on a stale name.

## Consequences

The shipped commands are `dispatch`, `review-packet` and `guard`. The role hook refuses a worker's
merge, the orchestrator's `gh pr merge`, and a reviewer's write flags — four words, because a word
stays only where the act is irreversible and no other layer stops it.

SessionStart delivers `reference/orchestrator.md` whole, in ordered parts when one output cannot
carry it; the parts concatenate to the file's exact bytes and are tested that way.


**Amendment (2026-10-03, adaptation audit and human runtime qualification):** The original body
incorrectly says no other project's pages are the source. codex-method is a port and adaptation
of `/home/leon/projects/prod/devstandard`, including its role pages, reference rules, templates,
and collaboration machinery. Starting from zero refers only to this project's ADR history,
seeded by ADR 0000; it does not deny those sources. The original September acceptance date and
source-free wording are retained as historical text, not asserted as verified facts: this
adaptation instruction and correction are dated 2026-10-03. Source history is routed in
`docs/architecture.md`, rather than copied as this project's decision log.

The Codex-only main-session and native-subagent decision stands. Codex rust-v0.159.2 source
qualification establishes V2 spawn fields, `gpt-6.1-sol`/`high` metadata, inherited cwd and
permissions, package-level hooks selected by `agent_type`, and separate project-role discovery.
A native nonediting reviewer is a fresh-context contract plus ordinary-path hook, not a per-child
OS read-only sandbox. Native arbitration before a PR follows the same boundary. Model and effort
are explicit; unavailable models and quota never silently substitute.

The original claims about shipped role-hook breadth and tested whole startup delivery are not
runtime evidence for this adaptation. `reference/harness-codex.md` and `docs/architecture.md`
state the qualification limits. Review acceptance uses a shared-git local receipt and the exact
published raw verdict; remote metadata is not authorization. Fallback and rebase-proof reuse
remain documented source capabilities that the shipped guard does not qualify. Installation,
production calls, and a complete remote lifecycle need captured evidence before they are claimed.


**Amendment (2026-10-04, human-approved Codex-only cleanup):** Every worker, reviewer,
helper and arbitration uses explicit `gpt-6.1-sol` at `high`. The earlier model-tier routing and
model/effort escalation are historical settings; unavailable settings are reported rather than
substituted. This does not change the main session's selected model or service tier.

The target no longer uses a second host's maintenance entry: applicable repository-only practices
move from the old target `CLAUDE.md` to `docs/maintenance.md`, with one pointer in `AGENTS.md`.
Operative pages and routing checks use only native Codex roles. Source filenames, old carrier
choices and provenance remain historical facts in the reconciliation, not execution instructions.
Host compatibility is qualified on explicit versions with actual role discovery, tool schema,
hook/context delivery and continuation evidence; an unknown version or a configured role is not
proof of runtime readiness. Session resume must recover complete operating context before task
actions. The exact qualified versions and remaining evidence limits belong in the harness and
architecture rather than being inferred from this amendment.


**Amendment (2026-10-04, target host qualification):** Current native role support is Codex
0.160.0 V2. Loaded roles expose the six-field spawn schema including `agent_type`; target probes
captured full worker/reviewer context bytes, explicit Sol/high, no conversation-history fork,
allowed `pwd`, worker merge refusal, reviewer write refusal and reviewer cross-role refusal.
The probe used a controlled provider and does not qualify production calls or a remote lifecycle.
The original 0.159.2 source record remains history rather than current support. Unknown versions
are not admitted by inference.

The project installer remains explicitly scoped by default. `--user` is a deliberate opt-in to
native roles in `~/.codex/agents` for new chats; unrelated settings and main-session choices are
preserved, and unowned collisions refuse. Native role discovery must precede dispatch. No
fallback registry keyed on `task_name` replaces the host's role identity. Resume, clear and
compaction claims require their own actual host evidence.


**Amendment (2026-10-04, explicit settings and production reviewer evidence):** Sol/high is
fixed for every child by default. A direct, specific human instruction overrides the global
setting only for its named dispatch; no automatic model/effort escalation or quota fallback is
introduced. Main-session settings remain untouched.

A production typed fresh reviewer call with its role-config layer explicitly active retained the
supplied prompt heading/end marker and omitted a parent-only token. The first discovery attempt
was blocked because that layer was inactive; it remains recorded rather than erased by the
successful call. This evidence does not establish user-scope discovery in all projects, worker
execution or a complete remote lifecycle. The current Codex loader supplies `PLUGIN_ROOT`;
package hooks consume that host key without the removed second-host compatibility fallback.


**Amendment (2026-10-04, native hook and shared-lane correction):** Lane receipts, ownership
locks and retained briefs are shared in the Git common directory across checkouts. Legacy local
receipts are imported only when uniquely consistent, with originals and hashes preserved; unknown
children and conflicting records still block reuse. Initial and continuation briefs remain raw,
and root record-language declarations are resolved before ownership changes.

SessionStart covers startup, resume, clear and compact, refuses insufficient configured part
capacity rather than delivering a partial page, and uses the Codex loader's plugin root. The role
hook recognizes actual native spawn aliases and command argv, including wrappers and absolute
paths, without scanning inert search prose as a command. Worker pushes require explicit remote
and branch targets. These are ordinary-path checks; arbitrary MCP/script writes, interactive stdin
and inherited parent permissions retain the declared limits. Live lifecycle qualification remains
separate from matcher and fixture checks.


**Amendment (2026-10-04, ordinary native review transport):** A formal review of 0.2.0 was
blocked before child launch because its roughly 224 KB native message repeated the typed role
and complete evidence packet. Earlier role/runtime probes and green CI remain their actual
historical evidence, not proof of that default desktop caller path.

The typed role still automatically delivers the complete static contract and native mechanics.
The ordinary native message now carries the complete filled judging fence, workdir and an absolute
retained complete-bundle path plus SHA-256; it does not duplicate role text or inline the large
bundle. The child explicitly verifies the digest before and after reading every numbered chunk,
checks inline/bundle contract agreement, and fails Floor 1 on missing access, drift, mismatch or
partial reads. Original bundle bytes are retained for acceptance and recovery. This changes the
carrier, not the judging contract, role schema or host API: no automatic file loading, special
code-mode-only prerequisite or new dispatcher is introduced. Fresh qualification must use the
updated role bytes and normal caller route; no old green result is claimed as that evidence.


**Amendment (2026-10-04, one whole inline SessionStart output):** The earlier ordered-part
carrier and insufficient-handler rules above remain historical facts and are superseded. Codex
0.160.0 supports `additionalContextLimit: 0`, which forwards the complete additionalContext
inline without a spill-file preview. The handler now runs once synchronously for startup,
resume, clear or compact and emits the entire original UTF-8 page, preceded by a stable whole
context marker and actual plugin-root/path header. It has no numbered-part reconstruction,
per-part arguments or configurable `CODEX_METHOD_CAP_BYTES`.

A fixed 64,000 UTF-8 byte budget applies to the **complete additionalContext**, including the
header. This conservatively reuses the former eight-times-8,000 aggregate budget; it is a
method safety limit, not a Codex cap. Missing, empty, invalid UTF-8 or oversized pages return
`continue: false` with a stop reason and no partial context. No body trimming or spill retrieval
replaces delivery. Ordinary PreToolUse checks, role contracts and integration policy stand.

The official [large hook output guide](https://learn.chatgpt.com/docs/hooks#large-hook-output)
and pinned [0.160.0 spiller](https://github.com/openai/codex/blob/a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/hooks/src/output_spill.rs)
provide the host-setting basis. Actual provider captures must prove full inline bytes and one
invocation; a script stop response alone is not evidence that the host stopped a turn. Native
qualification and lifecycle captures remain distinct from unit/configuration checks.


**Amendment (2026-10-04, Issue 8 shared collaboration migration):** General collaboration is
maintained once in the marked Shared collaboration agreements section of the orchestrator.
SessionStart already delivers that complete page; the installer extracts the section and inlines
it once into every self-contained worker/reviewer/helper role, without giving children main-session
operations or requiring them to reload a second shared core. This adapts the source role-self-
containment and contract/mechanics separation principles rather than restoring competing rule copies.
The qualified dispatch message now carries only the dynamic task; installed-role drift refusal and
lane identity remain. Formal judging, original evidence and whole unedited verdict publication stand.

Explicit human task instructions or prior confirmation authorize work within bounds without a
second handover approval. Method defaults, including skill menus and paths, yield to that authority
and established project workflow; they do not waive explicit integration/review gates. Ordinary
helper contracts do not own a lane or formal PR gate. Unsupported wakeups are not promised,
and settings reports distinguish requested/configured values from observable live metadata.
The generated operational AGENTS template is a suggestion, not a universal host content fence;
useful project instructions remain. Architecture prose edits use ordinary authorization while
consequential structural decisions retain ADR admission and human direction.

For hosted allowance/capacity refusal, safe already-authorized temporary repo-only self-hosted
Actions run equivalent workflows with retained logs and cleanup, maintaining normal checks.
This is separate from the unqualified degraded local merge waiver. This amendment records the
source contract; installation, fresh no-global-AGENTS role delivery and lifecycle captures must
qualify these new bytes before retiring the global file. A stable backup precedes retirement;
no permanent duplicate bootstrap is required. The original ADR bodies and prior runtime facts
remain historical evidence, not proof of the new runtime.


**Amendment (2026-10-04, human-authorized review and helper payload refinement):** Ordinary
`review-packet start` now keeps the complete filled judging contract and original evidence in
one retained digest-bound bundle. Its short native request carries the exact issue/head/base,
reviewer identity, workdir, absolute bundle path and digest, without a second filled render.
Hash-before/hash-after, complete numbered reading, failure disclosure, original whole-verdict
publication and exact acceptance remain. Only the canonical fence's transport wording changes;
Goal/Floor/Notes judgment and output rules do not. Existing inline dispatcher consumers and
already-prepared file or inline receipts retain their original bytes and validation semantics.

Task-local helpers receive one dedicated bounded-subtask source and a validated native-helper
excerpt rather than complete formal worker/reviewer pages behind a disclaimer. The exact shared
agreements still reach each role once; formal roles remain complete. Caller ownership, explicit
default settings, helper no-merge, reviewer-helper nonediting and review-helper-only nesting
remain. New payload bytes require actual target-role delivery and refusal checks before they
are called qualified; static composition alone is not behavioral evidence.

The human explicitly excluded short-core orchestrator loading and lifecycle injection dedup.
Whole startup/resume/clear/compact injection and necessary diff/failure evidence remain. This
refinement grants no merge or release permission; optimization integration still awaits the
human's explicit approval of the resulting PR.


**Amendment (2026-10-05, Issue 14 guarded squash lane cleanup):** The shared Git lane
receipt now owns bounded post-integration cleanup intent and observed removal progress. The
existing guarded squash policy remains; safe cleanup no longer depends on stale local main or
original commit ancestry alone. Actual repository/API/fetched-object bindings and integration
reachability on current base precede removal. Ancestor admission requires head reachability;
nonancestor admission additionally requires immutable integration/head tree equality.

Both routes create one deterministic direct Git archive with non-dereferencing create-only/CAS
ownership, retaining the exact head and reachable ancestry indefinitely. This small ref cost
permits one teardown/recovery path and preserves original history independently of later base
movement. Builtin nonforced branch deletion uses the exact archive as a command-local qualified
upstream; inherited ambiguity and logical-remote collisions refuse. Normal owned branch
configuration/reflog deletion remains, with no historical rewritten/reflog-only draft retention
promise, pruning policy or remote deletion. Refreshing local main alone cannot solve squash
non-ancestry; changing guard merge policy or raw branch-ref deletion was rejected.

Durable intent and archive verification precede removals. The same receipt plus actual state
recovers interruption after either removal, including before progress writes; fresh native and
integration evidence still gate retry. A durable pre-command `worktree-removing` marker denotes
may-have-begun, not execution/completion. Absence permits verified continuation; any present
path refuses automatic retry, even an original after a pre-command crash/removal failure. This
conservative availability cost preserves ambiguous files for caller-led inspection/disposition,
without resetting intent or forcing deletion; failure to save the marker prevents removal.
Actual phase/archive/branch/path observations remain distinct from completion claims.
Unexplained missing worktrees, reappeared files, moved
identities and occupied branches remain preserved. This adds no second tracker, general recovery
engine, forced cleanup or hostile-peer isolation. The design was independently challenged and
root accepted the reachable spec blob before implementation; its canonical detail lives in
`docs/specs/2026-10-05-squash-lane-cleanup.md`. Implementation, native qualification, hosted CI,
formal judging, product merge approval and live rehearsal remain distinct evidence obligations.
