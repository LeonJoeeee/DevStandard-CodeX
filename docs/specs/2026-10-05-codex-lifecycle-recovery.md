# Actual Codex lifecycle and safe same-lane recovery

Status: draft

## Problem & context

[Issue 18](https://github.com/LeonJoeeee/codex-method/issues/18) requires actual lifecycle
qualification on installed 0.2.6 (`1a9e1d386313cf784559ee0dda54723e4b88f129`) and Codex
0.160.0. Current production startup/helper evidence qualifies those transitions only. Historical
0.2.4 compact/new-process resume and failed 0.2.3 TUI-clear attempts remain evidence for their
own bytes, including failures. A matcher, hook acknowledgement, cached thread lookup, or
controlled provider cannot establish production post-transition behavior.

`scripts/dispatch` currently requires a fresh `list_agents` entry for the original handle before
`--continue`. A genuinely terminated spawning runtime may make that handle unavailable in a
new process. Absence alone proves no stopped lifetime. We need a conservative continuation
route that proves runtime termination independently, retains the old native observations, and
prepares a fresh child on the same issue/branch/worktree without asserting task success.

## Options considered

1. Keep only fresh completed-handle evidence: simplest, but cannot recover a lane whose
   session-local handle disappeared after proven old-process termination.
2. Admit absent/not-found handles or a caller's stopped flag: available, but permits concurrent
   writers when the old process or its command descendants remain alive; rejected.
3. Add separately validated runtime-origin/closure evidence: selected. More evidence is needed,
   but uncertainty still refuses and existing retained-handle continuation remains preferred.

## Decision

### One recovery contract, two kinds of observation

Add optional `--record-runtime-origin FILE` and `--record-runtime-closure FILE` actions to
`scripts/dispatch`. Neither launches/stops a child. The existing shared ownership lock covers
validation and receipt mutation. Original spawn/status observations remain unchanged. An
origin is immutable once bound; a matching replay is idempotent and conflicting data refuses.
Closure appends a separate `runtime_closure` observation and records `status=runtime-ended`;
it never sets native `finished=true`, invents `completed`, or grants review/cleanup acceptance.

The versioned `codex-runtime-origin-v1` carrier binds repository, issue, purpose, original run
`lane_id`, branch, resolved worktree, base, requested/canonical native handles, parent/child
thread IDs, and the spawning runtime. Runtime identity contains host/boot identity, PID, precise
OS birth identity, executable path/hash, process group, launch cwd/argv, host version, and
launch/observation times. It includes absolute retained capture paths and SHA-256 digests for
the raw launch, spawn, thread binding, native status and OS observations. Origin collection
starts when the owned runtime launches; handle binding follows the actual spawn, before that
runtime ends. A retrospective PID guess cannot qualify an old unbound run.

The `codex-runtime-closure-v1` carrier references that exact origin digest/run and retains raw
pre-stop native/thread/command accounting, complete observed process ancestry and birth
identities, the exact stop method/result, wait/reap evidence, and post-stop OS observations.
Before stopping, require no unresolved turn, command execution, or unaccounted background
work and identify every owned descendant, including detached/reparented processes already
observed. Bound process identities must still match immediately before any signal. Only the
task-owned runtime and proved descendants may be stopped. Missing accounting, unknown
ownership, reused PIDs, incomplete observation, or a surviving descendant refuses closure.
EOF, a deadline, failed RPC, interrupted native status, empty new-session agent list, and
`kill(pid, 0)` failure alone are insufficient. Abrupt termination is recorded as such; it cannot
be relabeled graceful shutdown. Unobserved/crashed runtimes without this proof remain blocked.

Both carrier validators check every referenced original and hash, chronology and identity,
plus fresh direct OS observations. Use platform-qualified precise process birth identity;
unsupported platforms/collectors refuse rather than approximate it with PID alone. Captures
are caller-supplied evidence, not cryptographic runtime attestation; the method retains its
ordinary cooperative host boundary and does not defend against fabricated same-credential
evidence or hostile process hiding. A summary's booleans do not replace source observations.

### Preparing the next writer

Retained-handle recovery stays native `followup_task` after actual stopped status and a fresh
self-contained binding. If the original handle remains usable, prefer it. Fresh replacement
requires either the existing fresh finished-native route or `runtime-ended` with its original
closure carrier freshly revalidated by the dispatcher at `--continue`. For the closure route,
also capture the new runtime's actual native lookup result showing the old handle unavailable;
an ambiguous lookup or contradictory live status refuses. No fake old-handle entry is supplied.

The closure route uses the existing `--continue --brief FILE` preparation path, with a new
`--runtime-closure FILE` argument mutually exclusive with `--native-status`. It verifies the
same repository/issue/branch/worktree/base/purpose and no pending cleanup, refreshes the whole
ordered issue record and authorized continuation, requalifies current typed-role bytes, and
appends one fresh run identity. The original runtime version/evidence stays historical; current
qualification is required separately. The new child receives exact role, goal, Bounds,
Done-check, working location and unfinished state. Preparing is not spawning or accepting work.
Rejection changes neither ownership nor run history. Closure does not broaden `--cleanup`.

### Lifecycle qualification harness

Maintain `.github/test-native-lifecycle.py`, with deterministic parser/negative tests in
`tests/test_native_lifecycle_fixture.py` and dispatch regressions in
`tests/test_dispatch_native.py`. Use actual production Sol/high for behavioral claims and a
separate controlled-provider mode for host mechanics/request-input capture. Retain the exact
schema, command/settings, provider class, hook/role/package hashes, trust/config baseline,
thread/turn/item/native identities and all original streams. Completion waits correlate exact
returned thread and turn IDs: another child/compaction completion cannot finish the awaited turn.

Execute these separately on frozen installed bytes, then repeat affected checks on candidate
bytes in an isolated explicitly configured target:

| Transition | Required actual sequence and evidence |
|---|---|
| Startup | Fresh runtime, ordinary turn, one complete actual method block and final behavior. |
| Genuine resume | Record old origins; finish actors; stop/reap the actual old server/descendants; launch a distinct runtime; minimal same-ID `thread/resume`; ordinary turn, fresh whole delivery, and exact authorized task-state recovery. Cached same-process resume is a separate negative. |
| Compact | Actual `thread/compact/start`; correlate real compaction completion; next ordinary turn without resume; fresh complete method and explicit recovered task binding before work. Acknowledgement alone fails. |
| API clear | Actual `thread/start` with `sessionStartSource=clear`, then ordinary turn. Label as API-route evidence; Codex 0.160.0 has no `thread/clear` RPC. |
| TUI clear | Actual owned PTY session and `/clear` input; retain terminal bytes, changed session identity, actual clear hook and subsequent production model turn. API-source-clear is insufficient. |
| Retained child | Actual typed Sol/high child returns/stops; observe original handle; `followup_task` carries refreshed binding; observe the same handle's subsequent work/return. |
| Same-lane replacement | Record actual origin and lane; prove old-runtime closure; show absent old handle in new runtime; run real dispatcher closure/continue; launch one freshly rebound typed child in the identical lane and verify its bounded outcome. |

For each claimed delivery, compare the entire UTF-8 method/header bytes and ending, not marker
presence. Establish exactly one fresh method delivery in the bounded transition/first subsequent
turn; do not count all earlier history as duplicate delivery. Retain production host model-input
records correlated to that exact turn plus observed response/tool behavior. A hook output or a
persisted developer message without evidence that it reached the model is not enough. If
production input visibility is unavailable, report that dimension unverified; controlled input
captures prove mechanics only. Typed child captures compare the complete generated role/shared
section once, inspect actual role/schema and rollout model/effort, and disclose unavailable live
metadata. No independent child-speed claim is made.

The caller assigns one authorized disposable probe lane and its exact write surface before
production worker recovery tests; never reuse this live implementation lane or another writer.
Main model/effort/tier and package stability stay unchanged. Use only task-owned isolated runtime
config/trust, preserving exact before/after bytes/modes; do not broaden global trust or add a
global AGENTS file. Every launched process gets an origin and final OS accounting. Existing
uncertain experiments are untouched. Durable private originals live at the caller-authorized
`outputs/migration-completion/recovery` workspace path (0700/0600); disposable adapters/state
live at `work/migration-completion/recovery`. Publish only secret-free indexes on issue 18.

### Documentation and ownership

Update owned `reference/harness-codex.md` and `reference/worker.md` recovery wording with the
new evidence route and its limits. Root coordinates synchronized changes to the parallel-owned
orchestrator/architecture/README and a dated ADR 0001 amendment; do not edit historical bodies.
The added interface suggests a minor version bump, assigned by root alongside other lanes.
This draft authorizes no implementation before its independent challenge and accepted blob.

## Out of scope

Persistent native handles across process restart, force cleanup, retrospective origin creation,
acceptance or CI exemptions, hostile-peer isolation, another host/executor, main settings
changes, and product integration/release/production upgrade are excluded.

## Verification

Run the existing full suite and routing/release/ADR checks on the final combined bytes. Real-Git
dispatch regressions must prove matching closure permits one same-lane preparation and that
live/uncertain/missing-origin/hash-drift/identity-mismatch/stale/reused-PID/active-command and
surviving-descendant inputs refuse without receipt or ownership mutation. Preserve ordinary
finished-handle continuation, historical-version bounds, legacy receipt handling, lock refusal,
pending-cleanup blocking and no closure-as-cleanup behavior. Fixtures are labeled fixtures.

The native harness emits a machine-checked matrix per source hash: executed/supported,
safely blocked, or unverified, with original evidence references, all failed/no-op attempts and
actual final process/config accounting. No pending/timed-out check is passing. Independent
Goal/Floor review inspects candidate changes and original captures before any human merge
decision. Evidence-only conclusions remain issue comments; product changes become a PR.

## Failure detection & rollback

Capture identity/hash/active-work failures before mutating the lane. Durable origin/closure
records append without erasing prior observations; interrupted receipt writes use the existing
atomic durable writer and ownership lock. An ambiguous partial record blocks replacement and
retains all evidence for caller inspection. Do not reset a receipt, kill uncertain processes,
restore stale global config, or retry a failed transition into an unqualified passing claim.
Stop only proved owned probe processes; remove only task-owned temporary trust/config changes
after comparing current bytes and preserving unrelated concurrent edits. Failure to prove final
teardown/config restoration is an unfinished result. Revert candidate code through ordinary
review if needed; installed 0.2.6 stays the stable subject throughout this lane.
