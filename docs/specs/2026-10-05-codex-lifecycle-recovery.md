# Actual Codex lifecycle and safe same-lane recovery

Status: draft

## Problem & context

[Issue 18](https://github.com/LeonJoeeee/codex-method/issues/18) qualifies installed 0.2.6
(`1a9e1d386313cf784559ee0dda54723e4b88f129`), Codex 0.160.0 and separately candidate bytes.
Current production evidence covers startup/helper; 0.2.4 resume/compact and failed 0.2.3 clear
remain historical. Dispatch needs a fresh old-handle entry, stranding ended session-local handles.
Absence alone proves no stopped lifetime.

## Options considered

1. Completed-handle evidence only: simple, but ended sessions strand lanes.
2. Absent handles/stopped flags: rejected; old processes or commands can survive.
3. Bounded validated runtime evidence: selected. Preserve native observations, prove termination
   separately and block unaccounted work. Desktop/crash recovery needs another accounting mechanism.

## Decision

### Initially admitted runtime and command surface

Support **macOS only**, initially through a caller-owned Python observer launching actual Codex
0.160.0 `app-server --strict-config` with `subprocess.Popen(start_new_session=True)`. The observer
owns the returned `Popen`/wait handle and remains alive across the planned server restart. This
is not a desktop PID-discovery route. Legacy/desktop runs without contemporaneous origin refuse.

The unprivileged collector uses `libproc` `proc_pidinfo(PROC_PIDTBSDINFO)` for PID, PPID, PGID
and `pbi_start_tvsec/pbi_start_tvusec`; `proc_pidpath` for executable identity; and
`sysctlbyname("kern.bootsessionuuid")` for boot identity. Bind executable bytes by SHA-256.
The initially accepted whole-system `proc_listallpids` plus birth-read census is **blocked on
this host**: actual PID 1 birth reads return 0/EPERM. Retain that failure; never silently skip
an inaccessible process or describe a partial system census as complete.

Proposed amendment: obtain complete membership of **every registered owned process group**
directly from `proc_listpids(PROC_PGRP_ONLY=2, pgid, ...)`, then birth-read every returned member.
This is an alternative coverage predicate, not a successful whole-system census. The upfront
registry and audited no-detach execution surface below must establish that every owned actor,
hook, launcher, command and host executor belongs to a registered group throughout its lifetime.
An unknown/detaching execution surface or missing registration still refuses, even if every
queried group is empty. A group's number never identifies a process birth or authorizes a signal.

Qualify the exact APIs/136-byte `proc_bsdinfo` structure on this host, retaining repeated stable
owned-child identities, repeated live membership, empty exited-group reads, a reparented surviving
member and a detached-live-child negative. `proc_listpids` returns **bytes**; its null-buffer sizing
may estimate systemwide capacity rather than group membership. Allocate spare capacity, reject
negative/nonmultiple/at-capacity results and nonzero errno; retain exact size/return/errno values.
Read membership, every member's birth identity and membership again. A changed set, missing,
short, inconsistent or permission-denied member read refuses that observation. Preserve each
failed/racing observation; a later newly captured stable observation is distinct evidence.
Unknown members and group reuse block closure; never signal them. Before final admission every
registered group must return no members, and every recorded birth must be absent. A temporary
exited member still enumerated blocks until a separately retained fresh empty observation.

`ps lstart` and native command `processId` remain insufficient identities. No privileged install
or Linux/cgroup claim is introduced. Qualification captures and collector source hashes travel
with evidence. This draft amendment requires independent acceptance before product consumption.

Useful synchronous commands are admitted through the harness's **owned-command launcher**.
Every command invocation carries a unique ticket in its actual native `exec_command` arguments.
The launcher records its own kernel PID/birth, ancestry to the recorded server, actual PGID,
exact argv/cwd and direct `Popen` child identity before execution, then waits synchronously.
Correlate ticket to native function call/output, `commandExecution` item/thread/turn and logical
PTY/session ID. A PTY `processId` is never converted to an OS PID. Missing/ambiguous correlation
refuses. If the host cannot expose this mapping, this supported route is unavailable.

The actual advertised transport may expose `exec_command` only inside `functions.exec`.
Admit this exact frozen JavaScript template, with one literal canonical JSON argument object:

```javascript
const r = await tools.exec_command(<literal JSON arguments>); text(r);
```

The harness generates `cmd` as the exact shell-quoted catalog argv invoking the owned launcher
and ticket, with assigned `workdir`, `login:false`, fixed shell and bounded yield/output options.
Reject extra argument keys. Reconstruct and byte-compare the actual wrapper from the frozen
template and validated literal arguments; retain template/source hashes, structured arguments,
outer call ID/output and nested actual result, including exit/session fields. Join outer call,
native command item/session and launcher ticket without treating a PTY ID as PID. Additional
JavaScript/comments, other tools, dynamic arguments, changed wrappers or extra asynchronous/unawaited
work invalidate coverage. Account for the admitted host executor's process identities/groups;
unknown executor backgrounds refuse. Qualify this wrapper with useful nonzero commands on
the actual target; never assume standalone command exposure or alter main settings to obtain it.

The command catalog binds exact argv templates, executables, program/dependency source hashes
and the reviewed source locations establishing **no daemonization, setsid/setpgid, detached or
untracked background children**. Initially qualify local Git operations with hooks/helpers
accounted for, and an inspected synchronous unittest program; arbitrary shell/interpreter bodies,
unknown Git hooks/credential helpers, code-mode beyond this inspected wrapper, MCP execution
and unreviewed dependencies refuse.
Changed tested source requires re-audit, not a stale catalog entry. This is a bounded cooperative
command contract, not enforcement against hostile code. Each command's actual group may differ
from the server's PTY group; register it and every observed descendant's birth identity. Known
source behavior preserves those groups through completion, so a complete registered-group census finds surviving
or reparented nondetaching children even after their direct parent exits. Synchronous wait alone
is insufficient. An unaudited detachment capability invalidates coverage even if later snapshots
are empty. Snapshots do not prove that no process escaped between them.

An isolated target disables unaccounted external servers/background features and permits only
hashed synchronous method hooks, whose source/launch chain is audited for the same no-detach
property. Hook start/completion IDs and idle group censuses must reconcile. All native actors,
command tickets/groups and hook invocations enter the observer's append-only registry from
launch. Gaps, unregistered actors/processes or unknown item/tool kinds invalidate coverage.
Zero-command-only success cannot qualify normal workers. Unavailable useful accounting yields
an explicit capability limit, never weaker coverage or a new general supervisor.

### Strict evidence carriers and phase rules

Add `--record-runtime-origin FILE` and `--record-runtime-closure FILE` to `scripts/dispatch`.
Neither stops/launches children. Validate and mutate under the shared ownership lock. The new
versioned JSON objects reject absent, mistyped or unknown fields; source records remain immutable.
Each phase seals byte-for-byte cuts of actual raw streams before hashing; later append activity
cannot change an origin's source file. Retain the complete final streams as well as every sealed cut.

| Carrier/group | Required fields and types |
|---|---|
| Both | `schema` string; `lane` object: repo/branch/resolved worktree/base/purpose/run lane_id strings and positive issue integer; `runtime_id` string; `sources` array. |
| Each source | Absolute `path` string, 64-hex `sha256`, selector object: positive JSONL `line` plus JSON Pointer string (or whole-JSON pointer). Hash complete original file bytes; selector must resolve uniquely to the asserted actual record. |
| Origin | `runtime` object: host string, boot UUID string, PID/PPID/PGID positive integers, birth seconds/microseconds integers, executable path/hash and cwd strings, argv string array, host version string; supervisor identity with identical process fields; collector/catalog/config/hook hashes; `actors` array of requested/canonical handle and parent/child thread ID strings plus spawn call/item IDs. |
| Closure | `origin_sha256` string; `mode="planned-quiescent"`; pre-stop registry/census/native/command/hook source selectors; exact stop argv/action and wait exit result; final census selectors; process identities/command tickets/groups retained from origin onward. |
| Each observation | Supervisor sequence positive integer, monotonic nanoseconds integer, UTC timestamp string; native thread/turn/item/call IDs where applicable. No caller boolean replaces raw observations. |

Launch captures `Popen` return and kernel identity before first thread/turn. After actual spawn,
join canonical handle from the original function output to the same call ID; join parent/child
IDs from that call's `collabAgentToolCall.senderThreadId/receiverThreadIds` and child rollout
metadata. Require exactly one child mapping. `--record-runtime-origin` binds this upfront
history while the original runtime is still live; matching replay is idempotent, conflict refuses.
No later origin reconstruction qualifies an already-ended run.

The same observer's sequence/monotonic values must increase across launch, spawn, registration,
last activity, quiescence, stop, wait and final census; boot and supervisor birth must stay equal.
Before stop, close observer admission of new turns/followups, reconcile every actor's actual idle/
returned state and every hook/command completion, then census all registered groups/identities.
Quiescence and identity checks must be at most five seconds old when stopping. Identity-check
only owned processes; close server stdin, wait up to five seconds, then record failure if alive.
A separately recorded identity-checked SIGTERM is permissible owned teardown, labeled SIGTERM,
never graceful-exit evidence. No SIGKILL fallback qualifies planned closure.

Closure requires actual wait/reap plus absence of every recorded process birth and no remaining
member of any registered group in a complete kernel group census. PID reuse, unresolved sessions, live or
unaccounted descendants refuse. Before each closure record and `--continue`, the dispatcher
rechecks immutable originals, identities, coverage and a direct census taken within five seconds
of receipt mutation. Unreadable census/stale evidence refuses. Caller captures are not authenticated
runtime attestations; original bytes and correlations remain inspectable under the ordinary boundary.

**Unexpected exit is blocked**, including active-turn/command crashes. Preserve unfinished native
state and surviving identities; never reconstruct quiescence or stop/wait success from root death.
Missing origin/coverage/lifetime blocks. Crash recovery needs separate design/qualification.

### One next writer; distinct lifetime and acceptance

Closure appends `runtime_closure`, sets `status=runtime-ended`, and does not change old native
spawn/status observations or native `finished`, invent completion, or accept work. Prefer usable
retained handles with refreshed binding and native `followup_task` after actual stopped status.
Otherwise `--continue --brief FILE --runtime-closure FILE` (exclusive with `--native-status`)
revalidates the latest run's closure plus the new runtime's actual absent/not-found lookup;
ambiguous or live old-handle results refuse. Under the same lock, require unchanged lane identities,
no pending cleanup, current typed-role qualification and freshly fetched whole ordered issue/
authorized continuation. Append one prepared identity in the same lane and bind its predecessor
run ID and admitted closure digest; rejection leaves it unchanged. The existing fresh-finished-native
route remains. Lifetime proof never grants task success, accepted review or integration authority.

### Narrow cleanup consumer of the same proof

Add repeatable `--cleanup-runtime-closure FILE` with required `--cleanup --pr N --native-status FILE`.
Only unavailable **historical worker runs** already superseded by this lane's closure-based
continuation qualify. Each original carrier's origin/digest/run must match the successor's
recorded predecessor binding; duplicate, extra, changed or never-used carriers refuse. Live or
unfinished old handles contradict closure; usable finished handles use ordinary native evidence.
The latest worker requires fresh actual `completed`; borrowing reviewers retain fresh native
lifetime gates without closure exemptions.

Under the shared lock, reuse the same validator/source/coverage checks at admission and within
five seconds before each destructive removal, with fresh direct OS absence/group census.
Recheck the lifetime inventory for late activity or receipt drift. Retain per-run proof kind and
origin/closure digests in cleanup intent/final receipt; never rewrite old native observations or
set old `finished` true. Retry requires the same carriers plus fresh native/OS evidence.

Preserve every existing merged-PR/repository/exact-head/integration/tree, clean/ignored/sole-copy,
archive CAS/ownership, occupancy/configuration, durable marker and final verification gate.
Ambiguous present paths still refuse; closure cannot authorize a retry. Latest missing handles,
reviewer gaps, legacy/no-origin and uncertain crashes remain blocked. `cleaned` records verified
removal, never task success, accepted review or a CI exemption. This limited consumer prevents
qualified recovered lanes from being permanently stranded without admitting general crash cleanup.

### Maintained harness, qualification and ownership

Maintain `.github/test-native-lifecycle.py` including collector/launcher subcommands and focused
`tests/test_native_lifecycle_fixture.py` / `tests/test_dispatch_native.py` coverage. Ordinary
turn waits require exact thread and returned turn ID. `thread/compact/start` returns no turn ID:
serialize it while the target is idle, retain request/ack cursor, correlate the unique subsequent
`contextCompaction` item ID on that thread and its notification turn ID through completion,
then start the ordinary follow-up; missing/ambiguous events refuse without consuming other turns.

| Probe row | Required observation |
|---|---|
| Frozen 0.2.6 | Fresh startup; genuine resume after actual old-server reap; compact without resume; API `sessionStartSource=clear`; separate actual PTY `/clear` and subsequent model turn; retained typed-child continuation. |
| Candidate only | Upfront origin, useful audited synchronous command, planned closure, unavailable old handle, actual dispatcher same-lane replacement, completed successor, authorized exact merged head and cleanup consuming the same retired-run proof. Frozen 0.2.6 lacks new actions. |
| Negatives | Cached resume; real surviving command descendant; deliberate detachment/accounting gap; active-turn/active-command crash; missing origin, stale/hash/identity/actor mismatch, unqualified collector and pending cleanup. |

Use production Sol/high for behavioral claims; controlled provider input captures prove mechanics
only. Compare complete method/header/ending bytes once in the bounded first post-transition turn;
compare complete typed role/shared section and actual model/effort metadata. Production wire-input
visibility stays a separate unverified dimension if unsupported, even with matching rollout context
and correct behavior. Each matrix row retains actual executed/supported/safely blocked/unverified
status, failures/no-ops, settings/trust/config before/after and complete original streams.

Root assigns a separate authorized probe lane. Preserve main settings, installed 0.2.6, absent global
AGENTS and prior experiments. Durable private captures use caller-authorized workspace
`outputs/migration-completion/recovery` (0700/0600); disposable adapters use
`work/migration-completion/recovery`. Reap only owned processes with final OS proof; publish only
secret-free indexes. This lane proposes dispatcher/tests, this cleanup consumer and worker/harness guidance.
Root coordinates shared O/architecture/README/ADR/version changes with Issue 16. Minor bump
suggested only; independent accepted reachable spec precedes implementation/probes.

## Out of scope

General desktop/crash supervision, Linux privileged environment setup, persistent handles,
retrospective origins, cleanup exemptions beyond retired qualified worker lifetimes, force cleanup,
merge/release/production upgrade and main setting changes.

## Verification and failure detection

Regression checks bind actual Git lane mutation and prove valid continuation prepares once;
all refused carriers preserve original ownership/run history. Prove recovered-lane cleanup retains
the exact archive/head/ancestry and observes both removals while old native `finished` stays false.
Negatives cover missing/current-worker completion, changed/extra/unused closure, late live actor/
descendant, unavailable reviewer, expired census, changed wrappers/extra JS/tool calls/unawaited
work and every existing removal gate. Preserve all
cleanup interruption/ambiguous-present-path regressions; closure does not clear them.
Preserve retained/native-finished paths, legacy receipt/version behavior and locks. Real native negatives include surviving and
detached children with exact owned cleanup evidence, not fabricated census JSON. Run final full
suite plus routing/ADR/release checks after implementation; draft revisions need static checks only.
Independent Goal/Floor review examines candidate bytes and original captures before human merge.

Use existing atomic durable receipt writes; ambiguous partial records block and retain evidence.
Never reset history or retry failures into an unqualified pass. Remove only proved owned temporary
settings against current bytes, preserving concurrent changes. Teardown/restoration failure remains
unfinished. Stable installed 0.2.6 is the rollback subject; candidate reversion uses ordinary review.

## Proposed executor accounting amendment (2026-10-05; revised, not yet accepted)

The complete preceding contract remains the independently accepted baseline at commit
`4d1f98cc0e91c6501729daeb76ab301b7cc1798c`, blob
`3168676a6a9732c816cfe02c33910a8aed92845d`. Preserve those preceding bytes except the draft
status and separating newline. The earlier appended proposal remains reachable at commit
`29f8f94c8bf68a3a1956d7df330dd88cadb92fe8`, blob
`7e0ebb94b697336ca0c95e5b82e0f03cd37ed8dc`; its recommendation of route C was independently
challenged and is superseded here. This revision addresses the whole retained challenge with
SHA-256 `c641a3cd50b861e6c9479273e132c245cd10e8387d792368578e1a0c154f6efa`.
Root selected route B for revision, not implementation acceptance. A fresh independent acceptance
and explicit root handoff must precede new marker/host experiments or consumption of this interface.

### Actual capability and provenance

Official `openai/codex` tag `rust-v0.160.0` resolves annotated tag
`79b1b666f2e8551f8abbbca34957227f67f3f553` to commit
`a956835d020762cb2b570053af06f643a11c0ecc`. In that source,
`code-mode/src/remote_session.rs:35–84,105–171` uses one lazily created local process host;
`remote_session/connection.rs:157–173` spawns it with `process_group(0)`. Its separate PGID
is outside a server-and-command-only group registry. The actual native `commandExecution`
item's `processId` still does not expose this host's OS PID. Captured transport attempt 2
therefore establishes a useful command and its correlations, never complete executor coverage.

`install-context/src/lib.rs:176–212` chooses the packed resource/adjacent host executable.
The public `with_host_program` Rust constructor is not a CLI/config executable override.
No launcher insertion, executable replacement, relocation or inferred override is admitted.
`app-server/src/code_mode_host.rs:12–39` instead exposes the supported HTTP gRPC host selector;
`app-server/src/lib.rs:596–612` requires `features.code_mode_host=true` for that route.
`code-mode-host/src/main.rs:19–36` exposes `--listen grpc://IP:PORT`;
`grpc_transport.rs:24–40` publishes the actual bound HTTP endpoint on stdout and serves gRPC.
The actual two binaries' `--help` commands both exited 0 and confirm these argument surfaces.
No gRPC runtime or new initialization experiment has been started by this proposal.

Actual app binary SHA-256 is
`6b582e8813ce7e8ed4c52814ee5cf230dba647bf2292df747a4003f2657ef201`, observed
`codex-cli 0.160.0`. Actual packed host at
`/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex-code-mode-host` has SHA-256
`680a24a8aa7f0d7f9ab06c1416d465fd30a50fe40f46d2073c9d123f1f227328`.
The host help exposes no version flag. The original adjacent `codex-package.json` reports
version `0.160.0`, target `aarch64-apple-darwin`, with SHA-256
`404c4c935bf9b7a57fc02b6f0d09ba6b7bbbf15cf14286fc017de2a6c01cab47`.
This ties both selected files to an inspected same-version package, while package metadata and
source tag remain distinct from a reproducible source-to-binary build attestation. Before any supported qualification,
root must bind both actual packaged binary hashes to this source-audited candidate, disclose
that limit, and requalify changed package/source bytes. An unknown host package refuses.
Whole official source originals and capability outputs are privately retained under the
already authorized `outputs/migration-completion/recovery`; evidence indexes supplement them.

### Bounded alternatives and recommendation

| Route | Utility and maintained/operational cost | Capability limit or next evidence |
|---|---|---|
| A: retain strict refusal | Currently admitted behavior; no new interface or operations. Retained completed-handle continuation remains useful. | Useful local missing-handle recovery and its historical cleanup consumer remain blocked by incomplete executor coverage. |
| B: bounded local initialization and enrollment | Selected revision candidate. Preserve default local executable selection and ordinary server plus lazy host; add exact marker correlation, qualified direct-child collection and lifetime checks. Rough estimate 150–250 maintained lines and 8–12 focused cases beyond the existing barrier, excluding shared hook accounting needed by every useful route. No listener or second caller-owned runtime. | Actual complete PPID collection, exact marker, synchronous hooks, useful gated commands, same-host continuity and planned closure all remain unqualified. |
| C: caller-owned gRPC host | Historical alternative with real CLI support; caller could own both launch/wait handles. Rough estimate 120–200 maintained lines plus endpoint/two-stop operations, before addressing missing session accounting. | Public protocol has no host-wide session/peer inventory or complete audit stream. Selected route cannot reconcile every session before stop; safely blocked and no longer recommended as usable recovery. |

Estimates are engineering judgments, not measured implementation counts. Route C's supported
argv remains `[host_binary, "--listen", "grpc://127.0.0.1:0"]`, then
`[app_binary, "app-server", "--strict-config", "--code-mode-host", endpoint]` with task-private
`features.code_mode_host=true`. These arguments do not authorize starting it. The whole public
`code-mode-protocol/src/grpc/codex.code_mode.v1.proto` exposes `OpenSession`, subscriptions and
cell operations scoped to a known session, without global enumeration. Host stdout supplies the
endpoint; neither it, health, owned Popen handles nor empty groups establishes full session
accounting. The unauthenticated loopback listener permits other local clients. Do not add a proxy,
patched host, OTEL listener or supervisor merely to manufacture a positive. B keeps the existing
local stdio provider and adds no network endpoint; it does not claim hostile-process containment.

### Proposed B phase and immutable carrier

Name the transport `local-initialized-executor-v1`. Keep the existing owned app-server origin,
observer, native actor handles/thread IDs, lane and provenance unchanged. Append one immutable
initialization/enrollment carrier to that origin; old receipts without this carrier remain blocked.
The carrier binds original-byte hashes and unique selectors for admission closure, marker request,
actual provider Custom call, complete output, exact native thread/turn completion, collector cuts,
executor enrollment and command-admission release. It records monotonic and UTC chronology, boot
identity, parent app birth, packed path/hash and actual child PID/birth/PPID/PGID. No caller boolean,
retrospective desktop PID, elapsed sleep or PTY logical process ID substitutes for these originals.

Use the source-supported execution chain in `core/src/tools/code_mode/mod.rs:128–145,232–257`
through `create_session()` and the local process provider. There is no invented initialize-host RPC
or host executable override. Start with writer/command admission closed and all startup hooks
fully accounted for. The named `executor-initialization` phase permits exactly one advertised
`functions.exec` **Custom** input with these UTF-8 bytes, without a trailing newline:

```javascript
text("codex-method-executor-enrollment-v1");
```

Bind the actual request, call ID, source, thread ID and exact turn ID; retain the complete native
items/notifications and raw provider request/output. Require one successful terminal cell with the
single marker text and exact successful turn completion. No nested tool, command, timer, extra
JavaScript, yielded/unawaited cell, other model activity or unknown item is admitted in this phase.
The observer must distinguish the cell result from turn completion and wait for both; a completed
unrelated turn does not release admission. Any unexpected activity permanently invalidates this
attempt and remains captured. Gate release has a retained observer acknowledgement only after
all initialization and OS checks succeed. Unsupported correlation or gate enforcement refuses.

`CodeModeExecuteHandler` accepts `ToolPayload::Custom` and does not override the default
`pre_tool_use_payload`; `core/src/tools/registry.rs:134–142` returns `None` for non-Function
payloads. Thus even matcher `.*` does not establish a marker PreToolUse invocation. Do not invent
one or count its absence as missing hook completion. Unexpected actual marker-time hook activity
still refuses; startup and the later nested Function `exec_command` hooks have separate accounting.

### Qualified complete direct-child enrollment

Before consuming B, qualify macOS `proc_listpids(PROC_PPID_ONLY=6, app_pid, ...)` against actual
owned children, including simultaneous children, growth/race, exited/reparented members and errors.
Retain each raw API selector/argument, sizing return, buffer capacity, returned byte count, errno,
full PID vector and every birth/path read. Require valid integral sizes, spare capacity and stable
complete membership, applying the accepted registered-group collector's truncation/unknown/reuse
rules. Sizing is not proof of a complete later read. Permission, ambiguous zero/error, malformed
bytes, duplicate IDs, truncation or unstable membership refuses; no skipped child or PID1 bypass
becomes a passing full-system census. This is a separately qualified direct-child API, not a new
claim that the retained full-system EPERM cut passed.

While admission stays closed, after exact marker completion perform complete membership → births
and executable paths/hashes → membership validation, bracketed by the same live app birth. The
source-audited local provider must explain exactly one newly created packed host, directly parented
to that app with stable birth and PID=PGID. Every other actual direct child needs its own complete
known origin/registration; none may be ignored to make uniqueness pass. Bind the host's birth to
this exact initialization phase, current package/source selectors and actual app parent. Vanished,
reparented, multiple matching, unknown or mismatched executable/parent/group observations refuse.
Short-lived unobserved children cannot be excluded by snapshots: the bounded marker's full source
and hook audit must exclude such creation; if it cannot, coverage remains unsupported.

Label enrollment **after bounded initialization**, never registration from launch or command
pre-exec enrollment. The exception permits only this non-writing actor creation; it does not
license initialization commands. After sealing that carrier, directly recheck host birth/path/hash,
parent and full known-child/group coverage before every command gate release, at quiescence and
immediately before the planned stop. Public connection/generation errors, host disappearance,
replacement/reconnection, changed birth/path/hash or unknown child permanently invalidate this
runtime's qualification. Do not rerun the marker or borrow the old proof for a new host. Preserve
the failed lifetime and require a separately authorized new runtime with a fresh origin instead.
No unsupported private generation metadata or assumed error-free reconnection is evidence.

### Separate hook and useful-command accounting

`hooks/src/engine/command_runner.rs:384–437` selects `ProcessMode::NewSession`: startup and
nested-command hook shells therefore create groups outside the app and local-host groups. Retain
each actual hook event/handler identity, input, source/config digest, shell argv/initialization,
PID/birth/PPID/PGID, enrollment barrier, full stdout/stderr, completion and actual descendant/wait
correlations. Require audited synchronous hooks only, with no unknown login-shell startup, detached
helper, async hook, arbitrary MCP or unaccounted subprocess. A hook wrapper must register its
own shell/script group and any audited descendant before task work is released, without changing
hook results or omitting actual native originals. A completed hook response alone is not proof of
OS reaping. If the actual public surface cannot correlate and gate that full chain, B is blocked.

Startup hooks run and finish under their own gate before the marker. Later nested `exec_command`
PreToolUse/PostToolUse hooks receive the same accounting independently of the Custom wrapper.
Keep the accepted exact single awaited `tools.exec_command` wrapper, structured argv, full outer
call/output and native command item/launcher ticket correlations. The separately maintained command
barrier enrolls the child before bootstrap-to-command exec, with allowed executable transition,
exact assets and explicit observer release. Retain useful nonzero synchronous Git and test commands;
a marker-only or zero-command run cannot qualify practical lane recovery. Complete hooks, launcher,
executor, command descendants and actual waits form one registry; empty sampled groups alone do
not establish its completeness. Native actors remain discovered typed roles with actual Sol/high
settings and ordinary whole shared-role delivery, not invented executor-role handles.

### Actual local-host stop and closure evidence

The observer owns the app-server Popen; the lazy host Child handle belongs to the SDK. In
`remote_session/connection.rs:533–569,606–609`, dropping the connection cancels its supervisor;
`kill_and_reap` calls `start_kill()` and `wait()` but discards both results, and spawn also sets
`kill_on_drop(true)`. Expected SDK-owned **hard termination** is distinct from an observed graceful
host exit or an observer-owned host wait. The carrier records this source-defined mechanism and
its evidence limit; never invent a host exit code, successful SDK wait, or proof no SIGKILL occurred.
Caller SIGKILL fallback remains prohibited as qualifying closure. Unexpected active host/app
crashes remain blocked even if every group later becomes empty.

Close writer and ordinary command admission before planned stop. Reconcile every actual native
thread/turn and cell terminal result, callback result/cancellation, hook and command against the
complete original stream. No outstanding/yielded cell, unresolved callback, unknown activity or
missing completion may become idle merely because a thread is reported completed. Require a fresh
same registered host birth still live, exact app identity, and complete known group census within
the accepted five-second freshness bound immediately before initiating the preplanned app stop.
Keep all shutdown requests/events, provider/native outputs and stdout/stderr through actual app
wait/reap; never truncate warnings or assume logging supplies a nonexistent global inventory.

`core/src/session/handlers.rs:287–325,338–371` warns on code-mode shutdown failure and continues
toward `ShutdownComplete`. `app-server/src/request_processors/thread_processor.rs:1283–1293`
warns about bounded submit failures/timeouts. Neither that marker nor app exit 0 proves successful
session closure. Retain and reconcile these originals: shutdown submission failure, timeout,
unresolved cancellation or session error refuses planned closure. Expected source-owned connection
cancellation after reconciled terminal sessions is labeled separately, with no invented success
status. If the public originals cannot distinguish it from an unresolved session failure, refuse.

Any source-audited SessionEnd/shutdown hook is an explicit shutdown-only exception to closed
ordinary command admission: enroll/gate it before its work, correlate its native handler and finish
all descendants, retaining its separate group. No new model turn, ordinary command, callback work
or host replacement is permitted. Missing shutdown-hook observation invalidates coverage. This
exception cannot retroactively register earlier hooks or commands or hide an active pre-stop task.

Close app-server stdin and retain the observer's actual bounded Popen wait/reap and result; a
teardown failure stays failure under the original identity-checked owned-cleanup rules. Then
freshly verify the exact registered host birth is absent and its complete recorded group is empty,
as well as every app/hook/launcher/command birth/group. Do not signal the SDK host or claim a caller
host wait. Survivor, reused PID/group, unknown member, ambiguous read or inability to observe
absence blocks qualification and is retained. Only the reconciled preplanned lifetime plus actual
app reap and fresh kernel absence can supply B's stopped-lifetime evidence. Revalidate immutable
sources and directly check all recorded births/groups at every ownership mutation/removal as before.

Same-lane successor admission and historical-worker cleanup consume this one complete proof. Keep
all origin/predecessor/digest bindings, latest actual-completed requirements for current runs,
reviewer lifetime evidence, merged-PR/exact-head/integration/archive/clean-tree/sole-copy gates and
ambiguous-removal refusals. Runtime-ended never means task success, accepted review or permission
to remove a still-uncertain lane. Legacy/no-origin and unexpected-crash experiments stay untouched.
Ordinary unsupervised default-local/desktop missing-handle recovery remains unsupported; only a
separately accepted and actually qualified B harness can claim this subset. Refusal names the
missing initialization/host/hook/callback observation and preserves owned work and original receipts.

### Required qualification, boundaries and rollback

After independent acceptance and explicit root route binding, qualify the PPID API first, then the
exact closed marker and unique same-host enrollment, all synchronous hooks, useful gated Git/test
commands and complete native wrapper/item/ticket correlations. Demonstrate actual planned app
reap and all registered births/groups absent, retained-handle preference, fresh same-lane successor
admission and historical-worker cleanup with current-run native completion. Negative cases include
unknown or reparented direct children, surviving/detached command descendants, incomplete hooks,
changed marker/wrapper/assets, stale cuts, host replacement/reconnect, live host after app reap,
shutdown warning/failure and unexpected active exits. No negative cut is retried into a pass.

These are proposed checks, not executed B evidence. Preserve the global PID1 EPERM, initial exit
lag, denied child-file write and incomplete executor transport cuts as their original failures or
limits. Existing barrier/strict parser unit tests are mechanism evidence only. Controlled providers
qualify host mechanics; actual production Sol/high whole-method startup, real-process resume,
TUI clear with next actual turn, compact/state recovery and live GitHub workflow still need root's
self-contained probe-lane handoff and current candidate originals. An unavailable observation blocks
its matrix row; no constructed fixture or hook-only result substitutes for that behavior.

Root coordinates shared documentation/ADR0004/version0.5.0 ownership as before. No new B interface
code, marker/host experiment, installation, production/auth/config change, live GitHub probe, merge,
protection change or release is authorized by this draft. Already accepted independent strict
validation/consumers and the existing barrier may proceed. Rollback retains receipts and captures,
returns to route A's strict refusal, preserves installed 0.2.6 and unrelated work, reaps only proved
owned processes and restores task-private settings against exact current bytes. Teardown/restoration
failure remains unfinished. Original GitHub 401 refusals remain retained; human reauthentication
and root's byte-verified publication restored ordinary task publication, without expanding route
acceptance, production or irreversible authority. No worker authentication change or alternate
transport is part of this revision.
