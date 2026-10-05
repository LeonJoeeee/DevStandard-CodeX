# Preserve original history during squash-merged lane cleanup

Status: draft

## Problem & context

[Issue 14](https://github.com/LeonJoeeee/codex-method/issues/14) repairs the mismatch
between guarded squash integration and cleanup's local-main ancestry requirement.
At initial base `890ee873cacfda018505f58ac2b1c08260bd473a`, successfully merged
lanes remain because squash preserves content without preserving original commit
ancestry; stale local main is a separate source of refusal. Cleanup must remove
only the exact owned clean worktree and local branch while retaining recoverable
original commits. Product integration still requires separate human approval.

This spec is admitted by the substantial cleanup/retention interface and costly
destructive sequence. Root's preliminary challenge found no blocking directional
flaw; acceptance requires challenge of this exact reachable spec blob. The two
real-Git upstream probes establish feasibility, not product acceptance.

## Options considered

1. **Archive the exact head, verify integration, use qualified `branch -d`.**
   Retains original ancestry and Git's occupied-worktree/config/reflog behavior;
   adds one retained ref and bounded receipt recovery. Selected for this draft.
2. **Refresh local main or change guard to ordinary merge.** Refreshing alone
   cannot repair squash non-ancestry; changing merge policy alters integration and
   leaves existing squash lanes unresolved. Rejected.
3. **Delete the branch ref directly after PR checks.** Raw `update-ref -d` would
   require replacing builtin branch-deletion checks and config/reflog cleanup;
   merged state alone supplies no content proof. Rejected.

## Decision

Extend `scripts/dispatch --cleanup` and `tests/test_dispatch_native.py`; keep the
existing shared Git lane receipt, ownership lock, native observation requirements
and durable `write_json` mechanism. Synchronize cleanup guidance in
`reference/orchestrator.md`, source `docs/architecture.md`, affected references
and paraphrases, and relevant ADR decisions by dated amendment with original
bodies preserved. Fold the synchronized 0.2.6 patch bump into the implementation
PR: this repairs existing cleanup behavior without changing integration policy.

Use a uniform archive and removal sequence for both admission routes. This draft
refinement avoids duplicate interruption handling at the cost of one retained Git
ref per cleaned lane, including ancestral integration. Retention covers the exact
current head and its reachable history, not historical rewritten or reflog-only
drafts. Ordinary `branch -d` removes the owned branch config section and reflog;
sole-copy inspection and explicit disposition of other work remain prerequisites.

### Proof and ordered removal

1. Under the existing lock, validate receipt repository, issue, current recorded
   lane id, branch, worktree and exact recorded PR URL/number. Require fresh
   finished evidence for every retained worker handle and every borrowing
   reviewer handle. Unknown, missing, active or uncertain children refuse. Check
   the exact linked worktree/common Git identity, branch and head; require empty
   tracked, untracked and ignored status and no other worktree using the branch.
2. Read the actual merged PR from the verified repository. Require closed/merged
   state, matching PR/head/base repositories, branch and exact head `H`, and an
   immutable integration commit `I`. Resolve the actual PR base ref and freshly
   observed current base commit `B` through repository API evidence. Fetch from
   that verified repository; verify fetched commit identities against the API
   observations. Do not trust caller HEAD, local main or an unverified tracking
   ref. Unavailable, ambiguous or changed evidence refuses. Require `I` reachable
   from `B`. Admit ancestry when `H` is reachable from `B`; otherwise additionally
   require exact Git tree equality `I^{tree} == H^{tree}`. Compare integration
   content, not the later base tree: current base may have advanced.
3. Define deterministic `refs/codex-method/archive/<issue>/<recorded-lane-id>`
   in the common Git repository. Durably save bound cleanup intent in the
   existing lane receipt before mutations: repository/PR, branch/worktree/lane,
   `H`, `I`, base ref/`B`, proof route/tree identities and archive ref/head.
   Create the direct archive ref with
   `git update-ref --no-deref <ref> H <zero-oid>`: enforce non-dereferencing,
   create-only/CAS semantics at the transaction itself, not merely by precheck.
   An existing direct ref is reusable only with the same owning intent/lane
   identity and exact `H`; symbolic refs, including dangling ones, conflicting
   refs and moved refs refuse without following, redirecting or overwriting them
   or their targets. Verify that the archive itself is a direct ref at exact `H`,
   then durably save the archive confirmation before worktree removal.
   No pending cleanup can be redispatched
   as a fresh lane or have its bound intent silently replaced.
4. Inspect effective Git configuration, including inherited settings. Require
   zero or one branch merge source; multiple values are ambiguous and refuse.
   Use a deterministic lane-specific logical remote absent from effective
   configuration, with command-local URL `.` and a fetch mapping from the sole
   existing merge source to the archive. With no merge source, supply one
   command-local source. Override the branch remote command-locally; never append
   another merge value to an existing one. Reject logical-remote collisions and
   unsupported effective settings. One identical argument list must verify
   `branch@{upstream}` as the full archive ref and exact `H`, and later execute
   deletion. Persist no override or logical remote; perform no network operation
   through that logical remote.
5. Immediately before removal, recheck relevant receipt/PR/object, worktree,
   cleanliness, branch-head, archive and occupancy identities. Refuse detected
   changes. Remove only the exact owned worktree with ordinary `git worktree
   remove`; durably record observed removal. Before branch deletion, verify the
   remaining branch still equals `H`, no worktree occupies it, the archive still
   equals `H`, and the identical effective upstream configuration still resolves
   correctly. Delete only that local branch with qualified ordinary `branch -d`.
6. Observe both removals, prune ordinary worktree metadata, and verify the archive
   still retains `H`. Only then durably publish `status: cleaned` with proof and
   archive identity. Output the archive and a recovery example such as
   `git show <archive-ref>`; explain Git's expected archive-versus-HEAD warning.
   The remote task branch and unrelated persistent configuration remain intact.

## Failure detection & recovery

Keep bounded intent and observed progress in the existing receipt; no second
journal or general transaction engine. Refusal reports the exact phase, retained
archive/branch/files and next safe action. A receipt write failure before removal
prevents removal; a later failure must not claim `cleaned`.

On restart, acquire the same lock and revalidate fixed intent, current remote
proof, fresh native lifetimes, archive and worktree/branch inventory. A newly
verified current base may advance while the bound repository/base ref, `H`, `I`
and archive identity remain fixed; rerun reachability against that current base
and retain the new proof observation without replacing the original intent.
Before any removal, use the normal linked-worktree and cleanliness checks. A missing worktree
without bound prior intent and verified archive refuses. With that evidence,
inspect actual state: an absent worktree with branch still at `H` permits only
the remaining verified branch deletion; absent worktree and branch after a crash
before final receipt publication permits finalization after the final checks.
This includes a crash after removal but before its progress write. A reappeared
path/files, changed branch, occupied branch, moved/conflicting archive or changed
integration evidence refuses. Never delete a reappeared path or infer completion
from command return alone. A create-only CAS race may leave the intent pending;
revalidate the actual archive before retry, never overwrite the winner.

Recovery can reconstruct original committed work in a separately chosen safe
lane from the archive; it does not silently recreate or overwrite the removed
path. Archival refs remain indefinitely with no automated pruning. The lock
coordinates method actors; rechecks detect observed races, but neither supplies
OS isolation or an atomic guarantee against a hostile same-credential actor.

## Out of scope

No forced deletion, remote deletion, archive pruning, arbitrary edited/partial
squash acceptance, broad replay proof, merge/review/CI gate changes, installation
of an unmerged candidate, release/tag, settings hierarchy or provider route.
Real retained source/validation lanes wait for the approved installed version.

## Verification

Capture an original failing regression through the actual dispatcher with real
Git squash commits and linked worktrees before implementation. Then prove exact
head cleanup with stale local main, advancing current base, tracked/untracked
branch configuration and ancestral integration. Assert both local removals,
archive recovery of original head/ancestors, retained remote branch, truthful
receipt state and unrelated configuration equality; expected owned branch
config/reflog deletion is allowed.

Negative cases assert retained refs/files and receipt status for uncertain native
handles, all dirty/ignored states, PR/repository/base/head mismatch, extra commits,
unequal trees, unavailable/unreachable/moved integration proof, archive ownership
conflict/CAS race, inherited config ambiguity/collision, moved branch/archive and
another occupied worktree. Inject interruption after each removal and before its
progress/final receipt write; test absent worktree without intent and reappeared
files. Real Git must qualify non-dereferencing create-only/CAS at the actual
archive transaction boundary, asserting refusal and unchanged symbolic archive
refs and targets, including dangling targets, as well as ordinary conflicting
refs. A symbolic precheck alone does not establish that boundary. The mechanical
probes do not replace these product regressions.

Final source suite, routing, release lockstep, ADR and diff checks must pass on
final bytes; exact-head merged-result hosted CI and whole independent Goal/Floor
review precede human merge approval. Root owns the candidate-only live rehearsal
on an authorized disposable fixture. Report actual changed role/hook paths and
qualify changed native bytes only; disclose unqualified behavior and retain
original failed checks, complete challenge, PREWRITE and DELIVERY evidence.
