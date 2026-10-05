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

## Proposed executor accounting amendment (2026-10-05; not yet accepted)

The complete preceding contract remains the independently accepted baseline at commit
`4d1f98cc0e91c6501729daeb76ab301b7cc1798c`, blob
`3168676a6a9732c816cfe02c33910a8aed92845d`. This appended proposal does not authorize its
new runtime interface or change that baseline's observations. Independent challenge and an
explicit root choice of the route precede consumption. Preserve the preceding bytes apart
from this whole proposal's draft status; keep the prior accepted blob reachable.

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

| Route | Utility and maintained/operational cost | Remaining evidence requirement |
|---|---|---|
| Keep the original strict local route blocked | Lowest cost: no new host interface; retained/native-completed continuation still works. Cannot qualify useful missing-handle recovery or its cleanup consumer on this host. | Report separate local executor coverage refusal; never omit its group. |
| Local no-tool initialization, then discovery/enrollment | Smaller candidate: one exact no-tool native cell, one direct-child collector operation and initialization/enrollment tests (rough estimate 80–150 maintained lines); no new network endpoint or extra process beyond the ordinary lazy host. Preserves the default executable selection. | Amend the previously continuous-from-launch actor registry into a closed, non-writing initialization phase; prove unique source-correlated child, complete direct-child enumeration and exact birth/PGID registration before any admitted command. |
| Caller-owned gRPC host from launch | Recommended for the initially strict missing-handle route: caller owns both Popen/wait handles before lane work. Same process count as ordinary server plus its lazy host; a second supervisor handle, endpoint validation, and two-stop sequencing (rough estimate 120–200 maintained lines plus 6–10 focused cases). Adds an unauthenticated loopback endpoint during the task. | Actual gRPC/native role/tool semantics, both launch identities, no-detach source audit, complete owned registry, session shutdown, two waits and final empty-group proof. |

Estimates are comparative engineering judgments, not implemented counts or qualification.
The smaller local route is source-supported as an **option**, not claimed executed or selected:
`core/src/tools/code_mode/mod.rs:128–145,232–257` initializes its `OnceCell` session through
`create_session()` on execution; the process provider above establishes the lazy host.
An exact `text("codex-method-executor-enrollment-v1");` cell uses the actually advertised
`functions.exec` tool without a nested command/tool. No public initialize-host RPC is assumed.
If root selects this alternative, while writer admission is closed the observer must byte-match
that exact source and its complete output/call/turn IDs, await ordinary exact completion, and
refuse any tool, timer, extra JavaScript, hook/command activity or unknown item in this phase.
Then kernel `proc_listpids(PROC_PPID_ONLY=6, server_pid, ...)` membership-to-birth-to-membership
must find exactly the source-resolved packed host with matching executable hash, actual parent
birth, stable child birth and PID=PGID, accounting every other direct child rather than skipping
it. Qualify that collector API first; unknown, vanished, reparented, multiple matching children,
permission failure or a replaced host refuses. A later lazy reconnection/generation or new
unregistered process invalidates admission; no repeat prewarm during lane work. Closed-phase
initialization is not a zero-command positive: an actual useful gated command is still required.
This alternative explicitly changes creation-time registration into registration after a bounded
non-writing initialization; it cannot silently satisfy the previous continuous registration rule.

### Proposed gRPC interface and lifetime ordering

If accepted and chosen, add a narrowly versioned `caller-owned-grpc-v1` transport to the same
origin/closure validator and maintained lifecycle harness. The origin contains the original
app runtime identity and **one additional executor runtime identity**, each with full kernel
birth, executable hash, exact argv/cwd, boot identity, same surviving observer parent and own
PID=PGID. Bind actual endpoint and immutable original stdout selector to the executor's launch.
No caller boolean, existing unrelated listener or desktop PID substitutes for either Popen.
Both native actor threads continue to map to their real spawning app-server; code-mode host
is an executor, never a method worker/reviewer, and does not receive invented native handles.

Launch the exact packed host with argv `[host_binary, "--listen", "grpc://127.0.0.1:0"]`
through `Popen(start_new_session=True)` in the assigned lane. Immediately retain its returned
Popen/kernel origin before any gRPC session is opened. Read its single original stdout endpoint,
require exactly `http://127.0.0.1:<positive ephemeral port>` with no path/query/credentials,
and corroborate same owned birth and listener readiness. Ambiguity or non-loopback refuses.
Then launch `[app_binary, "app-server", "--strict-config", "--code-mode-host", endpoint]`
through the same observer with `start_new_session=True`; retain its origin before first thread.
`features.code_mode_host=true` belongs only to the task-private configuration. Preserve model,
effort, tier, installed roles/hook package and production/main configuration. Native V2 discovery,
explicit Sol/high dispatch and role delivery retain their ordinary gates. The first useful wrapper
must traverse this selected provider; a fallback-created local host invalidates coverage.

Bind only IPv4 loopback, ephemeral port and the one task lifetime. Do not enable OTEL listeners,
exporters, remote addresses, public tunnels or an additional daemon. This API has no authentication
in the inspected listener path; it is admissible only under the already stated cooperative,
non-hostile local boundary. It is not containment from arbitrary local clients. Unknown sessions,
peer activity, uncorrelated callbacks or registry gaps refuse; inability to observe/reconcile
those events is a capability block, never assumed exclusivity. Close the endpoint on owned host
termination and corroborate its listener is gone. Neither an HTTP health check nor an empty
process group authenticates endpoint ownership or proves complete session accounting.

Enroll both runtime groups, every source-audited synchronous hook, the owned-command launcher
and gated child birth **before command execution**. Audit code-mode-host session/runtime globals,
app-server callback/tool routing, sandbox/PTY launch chain and exact command dependencies; native
Rust tasks/threads must be distinguished from OS subprocesses. No arbitrary MCP, unknown Git
hook/helper, detached program, additional executor or unknown source chain is covered. Hash
all inspected originals and target binary/package provenance. Changed bytes refuse until audited.
Gated bootstrap-to-command exec preserves the enrolled PID/birth/group; the registry retains the
allowed executable transition and exact target argv/assets, never infers a second OS birth.
Actual callback/native command item/wrapper/ticket/source selectors and idle censuses remain mandatory.

Before stop, close admission and reconcile all actual app threads, cells, callbacks, hooks and
command waits against the complete original stream; bind executor session close/idle evidence.
Unexpected app or executor crash, active cell/command, missing close event or unresolved callback
blocks planned closure. Freshly census all registered groups and identity-check both owned runtime
births within five seconds. Close app-server stdin, wait/reap up to five seconds and retain the
actual result; any failure remains labeled failure, with only the previously permitted separately
recorded identity-checked SIGTERM teardown. Confirm app-native sessions/callbacks cannot remain
live before stopping the executor. A gRPC listener runs independently of stdin: its closure is
an explicit identity-checked **SIGTERM** followed by actual wait/reap, never graceful-stdin evidence.
If source/actual observations cannot prove quiescence, terminate only as owned cleanup and refuse
recovery qualification. Do not invent a global gRPC shutdown RPC. No SIGKILL fallback qualifies.
Final closure needs every recorded app/executor/command/hook birth absent, every registered group
empty and listener absent, with direct fresh checks at each receipt mutation/removal as before.
A reused/live/unknown process or open endpoint refuses without signals to unknown owners.

Same-lane continuation and historical-worker cleanup consume that one complete two-runtime proof;
all predecessor/origin/digest, latest actual-completed, reviewer, integration/archive/exact-head,
clean-tree/sole-copy and ambiguous-removal rules remain. No route means task success or acceptance.
Keep ordinary default local and desktop missing-handle recovery **unsupported** until a separately
chosen, accepted and actually qualified registration route exists. Refusal names the missing
executor origin/group rather than claiming a usable lane or silently switching transport.

### Amendment verification and failure handling

After acceptance and explicit route binding, retain a fresh controlled mechanics run with actual
selected provider, discovered typed worker/shared role bytes, useful gated Git and synchronous test
commands, whole wrapper/native/registry correlations and actual two-runtime closure. Negative runs
include a live executor after app reap, surviving/reparented command child, deliberate detachment,
unknown callback/client, host restart/replacement, stale/hash/endpoint identity changes and unexpected
active exit; none may admit continuation or cleanup. Preserve original failures and no-op cuts.
The actual production Sol/high/full-method/lifecycle/GitHub checks still require root's concrete
probe-lane handoff and separate current-candidate evidence. Source reading and help output establish
an available interface, not those end-to-end claims. A required observation absent on the actual
host blocks the affected row; do not broaden into a generic supervisor to manufacture completion.

Before integration, root coordinates shared documentation/ADR0004/version0.5.0 ownership as before.
This proposal holds all new interface code/probes until independently accepted; already accepted
strict validation and the command barrier may proceed independently. Rollback is to the original
strict fail-closed contract: preserve receipts/captures and owned work, leave main/installed 0.2.6
unchanged, reap only identified owned processes and restore task-private settings against exact
current bytes. A teardown/restoration failure stays unfinished; never retry it into passing proof.
