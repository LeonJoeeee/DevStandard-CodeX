# Actual Codex lifecycle and safe same-lane recovery

Status: draft

## Problem & context

[Issue 18](https://github.com/LeonJoeeee/codex-method/issues/18) requires actual lifecycle
qualification on installed 0.2.6 (`1a9e1d386313cf784559ee0dda54723e4b88f129`) and Codex
0.160.0, followed by separate qualification of candidate bytes. Current production evidence
covers startup/helper only; 0.2.4 resume/compact and failed 0.2.3 TUI-clear attempts remain
historical. Current dispatch cannot replace a session-local handle after its spawning runtime
ends, because it requires a fresh old-handle entry. Absence alone proves no stopped lifetime.

## Options considered

1. Keep completed-handle evidence only: simple, but a genuinely ended session can strand a lane.
2. Accept absent handles/stopped flags: rejected because old processes or commands can survive.
3. Add bounded, independently checked runtime evidence: selected. Preserve native observations,
   prove termination separately, and block unaccounted work. Unrestricted desktop/crash recovery
   would need another process-accounting mechanism; neither PID guesses nor snapshot claims suffice.

## Decision

### Initially admitted runtime and command surface

Support **macOS only**, initially through a caller-owned Python observer launching actual Codex
0.160.0 `app-server --strict-config` with `subprocess.Popen(start_new_session=True)`. The observer
owns the returned `Popen`/wait handle and remains alive across the planned server restart. This
is not a desktop PID-discovery route. Legacy/desktop runs without contemporaneous origin refuse.

The unprivileged collector uses `libproc` `proc_pidinfo(PROC_PIDTBSDINFO)` for PID, PPID, PGID
and `pbi_start_tvsec/pbi_start_tvusec`; `proc_pidpath` for executable identity; `proc_listallpids`
for a full census; and `sysctlbyname("kern.bootsessionuuid")` for boot identity. Bind executable
bytes by SHA-256. `ps lstart`, native command `processId` and process-group numbers are not
process birth identities. Before admitting any closure, qualify these exact APIs/structure sizes
on this host with an owned live child, repeated stable reads, and exited-child observations.
Unavailable, short, inconsistent or permission-denied reads refuse; no privileged install or
Linux/cgroup claim is introduced. Qualification captures and collector source hashes travel with evidence.

Useful synchronous commands are admitted through the harness's **owned-command launcher**.
Every command invocation carries a unique ticket in its actual native `exec_command` arguments.
The launcher records its own kernel PID/birth, ancestry to the recorded server, actual PGID,
exact argv/cwd and direct `Popen` child identity before execution, then waits synchronously.
Correlate ticket to native function call/output, `commandExecution` item/thread/turn and logical
PTY/session ID. A PTY `processId` is never converted to an OS PID. Missing/ambiguous correlation
refuses. If the host cannot expose this mapping, this supported route is unavailable.

The command catalog binds exact argv templates, executables, program/dependency source hashes
and the reviewed source locations establishing **no daemonization, setsid/setpgid, detached or
untracked background children**. Initially qualify local Git operations with hooks/helpers
accounted for, and an inspected synchronous unittest program; arbitrary shell/interpreter bodies,
unknown Git hooks/credential helpers, code-mode/MCP execution and unreviewed dependencies refuse.
Changed tested source requires re-audit, not a stale catalog entry. This is a bounded cooperative
command contract, not enforcement against hostile code. Each command's actual group may differ
from the server's PTY group; register it and every observed descendant's birth identity. Known
source behavior preserves those groups through completion, so a full final census finds surviving
or reparented nondetaching children even after their direct parent exits. Synchronous wait alone
is insufficient. An unaudited detachment capability invalidates coverage even if later snapshots
are empty. Snapshots do not prove that no process escaped between them.

An isolated target disables unaccounted external servers/background features and permits only
hashed synchronous method hooks, whose source/launch chain is audited for the same no-detach
property. Hook start/completion IDs and idle group censuses must reconcile. All native actors,
command tickets/groups and hook invocations enter the observer's append-only registry from
launch. Gaps, unregistered actors/processes or unknown item/tool kinds invalidate coverage.
No normal-worker positive is claimed from a zero-command-only child. If this host cannot supply
useful audited command accounting, report the precise capability limit and retain this proposal;
do not manufacture a positive by weakening coverage or building a general supervisor.

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
member of any registered group in a complete census. PID reuse, unresolved sessions, live or
unaccounted descendants refuse. Before each closure record and `--continue`, the dispatcher
rechecks immutable originals, identities, coverage and a direct census taken within five seconds
of receipt mutation. Unreadable census/stale evidence refuses. Caller captures are not authenticated
runtime attestations; original bytes and correlations remain inspectable under the ordinary boundary.

**Unexpected exit is a separate blocked case**, including a crash during an active turn or
command. Preserve unfinished/interrupted native state and any surviving identities. Even a
known root death is insufficient without admitted descendant coverage; this first route never
reconstructs pre-stop quiescence or stop/wait success. Missing origin/coverage/lifetime is safely
blocked. Supporting crash recovery later requires independent design/qualification.

### One next writer; unchanged acceptance and cleanup

Closure appends `runtime_closure`, sets `status=runtime-ended`, and does not change old native
spawn/status observations or native `finished`, invent completion, or accept work. Prefer usable
retained handles with refreshed binding and native `followup_task` after actual stopped status.
Otherwise `--continue --brief FILE --runtime-closure FILE` (exclusive with `--native-status`)
revalidates the latest run's closure plus the new runtime's actual absent/not-found lookup;
ambiguous or live old-handle results refuse. Under the same lock, require unchanged lane identities,
no pending cleanup, current typed-role qualification and freshly fetched whole ordered issue/
authorized continuation. Append one prepared identity in the same lane; rejection leaves it unchanged.
The existing fresh-finished-native route remains. **Cleanup remains unchanged**: unavailable
historical handles can still block automatic teardown after replacement. Retain that lane/receipt;
recovery is not fully cleaned delivery, integration authority or an acceptance/CI exemption.

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
| Candidate only | Upfront origin, useful audited synchronous command, planned closure, unavailable old handle, actual dispatcher same-lane replacement and bounded outcome. Frozen 0.2.6 lacks new actions; record this limitation. |
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
secret-free indexes. This lane owns dispatcher/tests and worker/harness recovery guidance. Root
coordinates shared O/architecture/README/ADR amendment/version fields with Issue 16. A minor
bump is suggested only. Independent accepted reachable spec precedes implementation/probes.

## Out of scope

General desktop/crash supervision, Linux privileged environment setup, persistent handles,
retrospective origins, force cleanup, merge/release/production upgrade and main setting changes.

## Verification and failure detection

Regression checks bind actual Git lane mutation and prove valid continuation prepares once;
all refused carriers preserve original ownership/run history. Preserve retained/native-finished
paths, legacy receipt/version behavior and locks. Real native negatives include surviving and
detached children with exact owned cleanup evidence, not fabricated census JSON. Run final full
suite plus routing/ADR/release checks after implementation; draft revisions need static checks only.
Independent Goal/Floor review examines candidate bytes and original captures before human merge.

Use existing atomic durable receipt writes; ambiguous partial records block and retain evidence.
Never reset history or retry failures into an unqualified pass. Remove only proved owned temporary
settings against current bytes, preserving concurrent changes. Teardown/restoration failure remains
unfinished. Stable installed 0.2.6 is the rollback subject; candidate reversion uses ordinary review.
