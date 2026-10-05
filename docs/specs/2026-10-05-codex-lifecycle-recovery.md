# Actual Codex lifecycle and safe same-lane recovery

Status: accepted

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
