# CI-outage evidence and the protected integration boundary

Status: draft

## Problem & context

[Issue 17](https://github.com/LeonJoeeee/codex-method/issues/17) migrates the useful
evidence, independent audit and return obligations of DevStandard's fallback without
inventing authority to merge. Source: `d593c67f6850fccca9246833c8fc7419836ce23a`,
`reference/ci-cannot-run.md` and ADR 0025, including its dated amendments. The source
requires the merging main session's full synthetic-merge run and assigns a protected
branch's waiver to the **human**, followed by same-session protection restoration.
The target at `1a9e1d386313cf784559ee0dda54723e4b88f129` has neither qualified
fallback admission nor a platform-compatible degraded integration route.

Fresh discovery at 2026-10-05T05:31:41–43Z found product `main` unprotected,
protection HTTP 404 `Branch not protected`, and active branch rules `[]`. The
validation repository separately has strict `test` from Actions app `15368`, admin
enforcement, required PRs and no force pushes/deletion. Original argv, timestamps,
exit codes, stdout and stderr are retained in the root-authorized evidence directory's
`discovery/captures.json` and `0.json`–`3.json`; no cause of product protection state
is inferred. An unprotected repository cannot prove protected integration.

GitHub requires checks from their configured app and applies the bypass ban to
administrators: [protection documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
Local evidence cannot report a genuine Actions-app check. Current CI is working;
rehearsal outage inputs must be visibly labeled simulated.

## Options and human decision

1. **Preserve protection; qualify evidence/audit; await ordinary CI.** Recommended
   implementable scope: retain exact local evidence and an independent audit while
   every degraded merge still refuses. This completes the evidence subsystem only;
   it does **not** finish the historical merge-waiver migration.
2. **Temporary repo-scoped self-hosted Actions.** Prefer this ordinary route when
   the Actions service works and a safe equivalent environment exists. It produces
   normal checks. Current `runs-on: ubuntu-latest` does not select a self-hosted
   runner; changing routing needs a reviewed workflow interface, isolated ephemeral
   environments, credential disposal and retained logs. This is not an outage waiver.
   [Runner routing documentation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow).
3. **Historical human manual waiver. UNAPPROVED and outside current bounds.** The
   human would explicitly name one repository/PR/base/head, accept the audited
   degradation, personally perform any platform-required temporary exception and
   merge, and restore/verify the captured protection in the same session. The source
   allowed this; current bounds prohibit protection weakening and required-check
   bypass. No agent implementation, permission inference or retrospective receipt
   can reconcile those constraints.

The concrete direction question is: retain option 1's protected refusal and record
the remaining migration gap, or explicitly amend the bounds to permit option 3's
human-owned, one-PR exception? Restoring product protection is a separate human
decision, not permission implied by this spec. No option-3 implementation starts
without written human direction and a corresponding ADR. No policy choice is
represented as settled by the draft or its pre-code challenge.

## Proposed safe interfaces

After independent challenge and authorized continuation, add `scripts/ci-evidence`
with `prepare`, `run`, `publish`, `audit-packet`, `record-audit`, `status`, and
`return-sweep`. Require explicit project, repository, PR and evidence destination.
One accountable integrating main session operates these commands; workers may return
ordinary done-check evidence but cannot run fallback check 2 or integrate. A
`codex-method-ci-evidence-v1` receipt in the Git common directory under
`codex-method/ci-evidence/OWNER/REPO/PR/TOKEN.json` owns immutable associations and
bounded progress. It is evidence state, not a second task tracker or outage mode.

`prepare` captures provider incident or private-account hosted-minutes exhaustion,
its affected scope, and a concrete reason waiting is ruled out. Both named causes
must be external to this repository and prevent CI starting for every otherwise
eligible push in the affected provider/account scope, as clarified on the issue.
Retain cause proof and current run/workflow/auth/configuration diagnostics; absence
of a run alone proves nothing. Queued, slow, flaky, red, disabled/mis-scoped workflow,
org disablement, no CI, unreadable/auth/network state and offline runners refuse.
An unresolved incident, quota document or observed startup refusal must actually
establish the named cause; a user-supplied assertion or fixture is not production
proof. Simulation is accepted only in explicit rehearsal state and can never create
an operationally qualifying receipt.

Fetch and cross-check current default branch, remote base and PR head using API
captures and explicit fetches. Retain full SHAs, successful `merge-tree --write-tree`
output, `commit-tree` with ordered parents `[base, head]`, and checked-out
`HEAD`, `HEAD^1`, `HEAD^2`, tree. Verify exactly two parents and independently
recompute the tree. Refuse conflicts or identity movement before and after preparation,
run, publication and audit. Base/head/workflow/job-map changes require a new receipt
and complete run; historical evidence is retained. The synthetic object is held by
a create-only direct archival ref until durable export has been verified.

`run` consumes a manually reviewed, workflow-blob-bound job map: every enabled
workflow for this exact PR event, every matrix member, job dependency/condition,
step, action/setup, toolchain, shell, working directory, environment, service,
secret requirement and artifact behavior. No automatic YAML guessing, test filtering
or user-selected job subset. Reusable/composite actions and environment expressions
must be resolved and pinned; unsupported semantics or unavailable requirements
refuse complete coverage. Run all eligible jobs unfiltered to completion, retaining
failures and `always()` cleanup/artifact obligations. Legitimately event-ineligible
jobs need an explicit predicate and supplied event proof; skipped eligible jobs fail.

For this base, map all four CI jobs: `suite` (checkout, merge check, full suite and
release/path/routing/ADR checks), `native` (Linux apt/AppArmor/bwrap preparation, Codex 0.160.0
installation, native probe and artifact retention), `test` (both dependency results),
and `merged-result` (exact checkout/parent check). A Mac native probe cannot replace
the Linux job. Local retained native artifacts preserve evidence but cannot claim
the unavailable GitHub upload action actually ran. A mapped equivalent requires
reviewed justification for that transport difference; missing original logs or any
incapable substantive step refuses full-job equivalence. Release is never run here.

Capture UTC start/end, exact argv/cwd/environment identities, toolchain versions,
whole stdout/stderr and exit codes for each step. The before/after records include
both clean tracked diffs, identical `git status --porcelain -uall`, permitted
untracked inputs from the prior baseline and root copy-list, and every ignored
input used with byte hashes/modes. Snapshot environment and dependency inputs before
and after; enumerate owned generated outputs separately and preserve them. Unknown
or changed inputs fail, even when status appears unchanged. Never expose secrets:
an unpublishable required input returns a containment decision instead of silently
redacting away audit evidence or copying credentials into the lane.

`publish` posts `CI-FALLBACK EVIDENCE — integration blocked` with the original four
audit questions and complete evidence. This marker is evidence, never a check or
waiver. Large evidence uses ordered numbered comments with exact-byte digests and
a manifest binding all parts; no output-tail substitution or inaccessible local-only
sole copy. Before each POST save/fsync pending exact outbound bytes/token and prior
receipt. Record repository/PR/comment id, author, URL, full body hash and timestamps;
refetch exact bodies. `status` recovers only a unique exact author/body/token match.
Unknown, missing, duplicate or edited outcomes refuse; never blindly retry a POST.

`audit-packet` retains the whole issue, accepted spec, pinned diff forms, original
evidence, publication parts/receipts and full source audit checklist. Bind token,
base/head/tree, packet path/digest and fresh independent `method_review_helper`
identity, explicitly Sol/high. The helper hashes, reads all numbered chunks and
hashes again; it audits cause, synthetic identity, fresh clean inputs and complete
coverage, returning the whole itemized findings and limitations. `record-audit`
binds that raw return and native handle to the packet/publication bytes; publish the
whole return through the same pending-intent discipline. Missing carrier, malformed
audit, tampering or movement refuses. This bounded audit is not formal Goal/Floor
acceptance; ordinary review admission and merge authorization remain unchanged.

`status` reports `incomplete`, `incapable`, `publication-pending`, `audit-pending`,
`audit-failed`, `audited-integration-blocked`, `stale`, or `return-verified`, always
with `merge_permitted: false`. `scripts/guard --ci-fallback` remains a hard refusal.
No synthetic check, default-branch mutation, worker merge or release interface exists.

## Return, failure and rollback

The interval ends as soon as ordinary CI can start. Re-read provider cause, exact
current main and protection; `return-sweep` binds the first ordinary main CI begun
after return, its run/attempt/workflow/head identities and every required job result.
Require main still matches that verified head, and protection matches the approved
baseline rather than inferring restoration. Green closes evidence records; red
returns the full affected-PR list to ordinary red-main recovery; pending/unreported
jobs keep the sweep open and releases blocked. A newer main needs its own verification.
Do not merge on a stale outage receipt after service return.

Current CI lacks `workflow_dispatch`. Rerunning a historical run is insufficient
unless its workflow and head exactly match current main. Otherwise report a blocked
trigger or use a separately reviewed ordinary PR adding a main dispatch interface;
no empty direct push or invented API trigger. Manual dispatch requires the configured
default-branch workflow: [GitHub documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Interrupted preparation/run retains failed commands, partial outputs, archival ref
and exact worktree identity. No operation resumes unknown execution as a successful
run. Partial publication/audit recovers exact receipts only. Rollback abandons the
new receipt without erasing prior evidence or changing protection. Cleanup follows
verified durable export and ordinary nonforced worktree removal; dirty, occupied,
ambiguous or sole-copy paths remain for caller disposition. Never port source
`remove --force || true` or recursive deletion of uncertain paths.

## Verification and ownership

Table-driven tests cover both genuine cause shapes and all excluded triggers,
simulated-state refusal, parent order/count/tree, full matrix/setup/action coverage,
incapable jobs, dirty/changed/ignored inputs, base/head movement, receipt/comment
tampering, unknown/duplicate POST outcomes and interruption at each durable boundary.
A disposable live rehearsal must prove real comment publication/refetch/recovery,
independent whole audit and protection inspection, and show the protected missing-
check refusal without changing protection. Label simulated outage proof throughout;
test platform blocking only in a specifically authorized disposable repository.

Rehearse an ordinary exact-main CI return, stale-main/red/pending sweep failures and
release blocking. Product PR verification still requires current-source full suite,
routing/release/ADR checks, native qualification, exact-head ordinary CI and final
independent Goal/Floor review. No safe-evidence success closes Issue 17's full goal
while the true degraded integration policy remains unresolved.

Current phase owns only this draft. After Issue 16 releases overlapping writes,
proposed implementation owns new evidence script/module/tests and coordinated
updates to fallback guidance, role hook, review guidance, README/architecture and
decision records; shared guard/review APIs need a fresh base/interface reconciliation.
No version fields, shared code, native OS probes or repository provisioning change
in this phase. Task evidence stays in the root-authorized durable
`outputs/migration-completion/fallback`; disposable execution stays in
`work/migration-completion/fallback`, with no sole durable copy there.
