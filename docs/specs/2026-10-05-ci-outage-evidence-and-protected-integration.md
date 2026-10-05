# CI-outage evidence and the protected integration boundary

Status: accepted

## Problem & context

[Issue 17](https://github.com/LeonJoeeee/codex-method/issues/17) migrates fallback
evidence, independent audit and return obligations. Source commit
`d593c67f6850fccca9246833c8fc7419836ce23a`, `reference/ci-cannot-run.md` and
ADR 0025 with amendments require the merging main session's full synthetic-merge
run and assign waiver to the **human**, followed by same-session protection
restoration. Target `1a9e1d386313cf784559ee0dda54723e4b88f129` has no qualified
fallback admission or protected degraded integration route.

Fresh discovery at 2026-10-05T05:31:41–43Z found product `main` unprotected,
protection HTTP 404 `Branch not protected`, and active branch rules `[]`. The
validation repository separately has strict `test` from Actions app `15368`, admin
enforcement, required PRs and no force pushes/deletion. Original argv, timestamps,
exit codes and outputs remain in the authorized evidence directory's
`discovery/captures.json` and `0.json`–`3.json`. No cause is inferred;
unprotected product main cannot prove protected integration.

GitHub requires checks from their configured app and applies the bypass ban to
administrators: [protection documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
Local evidence cannot report a genuine Actions-app check. Current CI is working;
rehearsal outage inputs must be visibly labeled simulated.

## Options and human decision

1. **Preserve protection; qualify evidence/audit; await ordinary CI.** Recommended
   scope: retain exact evidence and an independent audit; degraded merge refuses.
   This is a partial migration, **not** the historical merge-waiver feature.
2. **Temporary repo-scoped self-hosted Actions.** Prefer this ordinary route when
   the Actions service works and a safe equivalent environment exists. It produces
   normal checks. Current `runs-on: ubuntu-latest` does not select a self-hosted
   runner; routing requires a reviewed interface, isolated ephemeral environments,
   credential disposal and retained logs. This is not an outage waiver.
   [Runner routing documentation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow).
3. **Historical human manual waiver. UNAPPROVED and outside current bounds.** The
   human would explicitly name one repository/PR/base/head, accept the audited
   degradation, personally perform the platform-required exception/merge, and
   restore/verify protection in the same session. Current bounds prohibit weakening
   and required-check bypass; no agent implementation can reconcile those constraints.

The concrete direction question is: retain option 1's protected refusal and record
the remaining migration gap, or explicitly amend the bounds to permit option 3's
human-owned, one-PR exception? Restoring product protection is a separate human
decision, not permission implied by this spec. No option-3 implementation starts
without written human direction and a corresponding ADR. No policy choice is
represented as settled by the draft or its pre-code challenge.

## Proposed guide and focused collector

After challenge and authorized continuation, extend fallback guidance and add one
focused `scripts/ci-evidence` collector. Require explicit
project/repository/PR, reviewed workflow map, cause proof and durable output directory;
`--rehearsal` marks every artifact simulated, and `--verify` checks a retained bundle
without rerunning commands. The integrating main session operates the collector;
workers return ordinary done-check evidence, never fallback check 2 or integration.
Its digest-bound bundle contains original captures, a coverage manifest and gaps.
No lifecycle-command family, common-directory outage ledger or task tracker.
Reuse existing digest/carrier and durable-save/publication utilities where needed;
do not reuse formal acceptance records or their verdict parser.

Capture provider incident or private-account hosted-minutes exhaustion, affected
scope, and why waiting is ruled out. Require an external cause preventing every
otherwise eligible push in the affected provider/account scope, with original
cause/run/workflow/auth/configuration diagnostics. Missing runs alone are no proof.
Queued/slow/flaky/red, disabled/mis-scoped workflows, org disablement, absent CI,
unreadable/auth/network state and offline runners refuse. Assertions and fixtures
are not production proof; rehearsal simulation never qualifies operationally.

Fetch and cross-check current default branch, remote base and PR head using API
captures and explicit fetches. Retain full SHAs, successful `merge-tree --write-tree`
output, `commit-tree` with ordered parents `[base, head]`, and checked-out
`HEAD`, `HEAD^1`, `HEAD^2`, tree. Verify exactly two parents and independently
recompute the tree. Refuse conflicts and movement before/after collection,
publication and audit. Base/head/workflow/map changes require a new bundle
and complete run; historical evidence is retained. The synthetic object is held by
a create-only direct archival ref until durable export has been verified.

The initial supported map is this pinned CI workflow's PR event and all four jobs:
`suite` (checkout, merge check, full suite and release/path/routing/ADR checks),
`native` (Linux apt/AppArmor/bwrap setup, Codex 0.160.0 installation, native probe
and artifact retention), `test` (both dependency results), and `merged-result`
(exact checkout/parent check). Pin workflow/map bytes, event inputs, action versions,
setup, shell/cwd/env, toolchain and dependency conditions. Record every enabled
workflow/job/step and gap. A new workflow, matrix, reusable/composite
action, service, secret or expression outside that concrete map blocks complete
coverage pending a reviewed map change; no general Actions evaluator or YAML guessing.
Run every eligible mapped job unfiltered to completion, preserving failures and
`always()` cleanup/artifact obligations. Event-ineligible steps require event proof;
an eligible skipped step fails. Release is never run here.

A Mac probe cannot replace Linux. Local artifacts do not claim GitHub upload;
the map audits this transport difference.
Any incapable substantive step or missing original logs refuses full equivalence.

Capture UTC start/end, exact argv/cwd/environment identities, toolchain versions,
whole stdout/stderr and exit codes for each step. The before/after records include
both clean tracked diffs, identical `git status --porcelain -uall`, permitted
untracked inputs from the prior baseline and root copy-list, and every ignored
input used with byte hashes/modes. Account for setup-generated dependencies/outputs
at step boundaries: pre-setup state, full setup results and
post-setup versions/hashes before dependent steps. The reviewed map declares allowed
generated paths/changes; package and Codex installation are not unexplained drift.
Changed source or undeclared input changes fail even when status looks unchanged.
Retain owned generated outputs separately. Never expose secrets:
an unpublishable required input returns a containment decision instead of silently
redacting away audit evidence or copying credentials into the lane.

Publish `CI-FALLBACK EVIDENCE — integration blocked` with the original four
audit questions and complete evidence. This marker is evidence, never a check or
waiver. Large evidence uses ordered numbered comments with exact-byte digests and
a manifest binding all parts; no output-tail substitution or inaccessible local-only
sole copy. Before each POST save/fsync pending exact outbound bytes/token and prior
receipt. Record repository/PR/comment id, author, URL, full body hash and timestamps;
refetch exact bodies. Recovery requires a unique exact author/body/token match.
Unknown, missing, duplicate or edited outcomes refuse; never blindly retry a POST.

The audit bundle retains the whole issue/spec/diff evidence, original captures,
publication parts/receipts and source checklist. Bind token/base/head/tree,
path/digest and fresh independent `method_review_helper`, explicitly Sol/high.
The helper hashes, fully reads numbered chunks and hashes again; audit cause,
synthetic identity, clean fresh inputs and full coverage. Retain raw whole findings,
limitations and native handle bound to bundle/publication bytes; publish unchanged
with pending intent. Missing/malformed carriers, tampering and movement refuse.
Helper audit is not formal Goal/Floor acceptance or ordinary review admission.

Report cause qualification, simulation, per-step results, gaps and
`merge_permitted: false`; attached audit/publication receipts are not formal
acceptance. `scripts/guard --ci-fallback` stays a hard
refusal. No synthetic check, default-branch mutation or release command is added.

## Return, failure and rollback

**Evidence-only return (option 1).** When ordinary CI can start, re-read cause,
end outage eligibility, retain/mark historical evidence, and resume ordinary CI
and formal review for the PR's exact current base/head. The bundle/audit replaces
neither gate. Green main never verifies an unmerged PR; red main cannot make it a
regression suspect. Main checks below serve release verification only.

**Future degraded merges (option 3, unapproved).** Retain actual integrated
commit/tree and exact merged-PR set, human authority and before/after protection.
Bind the first ordinary post-return main CI to current main containing those
integrations, run/attempt/workflow/head and all required jobs. Green closes that
set; red makes those actually degraded merges suspects. Verify same-session
protection restoration and the return baseline. This phase implements no such
integration policy, creates no fictional merged set and grants no waiver.

**Release hold: integrating-session obligation.** Before creating/pushing any tag
or invoking any release action, the integrating main session must inspect the
repository's issue/PR outage records, current provider/account cause, current main
CI and protection. Retain these captures and a `release withheld` or `hold cleared`
decision on the existing issue; unreadable or incomplete evidence means withhold.
The hold begins with a qualifying degraded interval and clears only after cause
return, the first ordinary post-return CI covering exact current main is complete
and green, and protection matches the approved baseline. A newer main needs fresh
verification. Under option 1 this says nothing about unmerged PR acceptance; under
future option 3, the actual merged-set sweep must also be complete. Pending/red
CI, uncertain policy/protection or absent supported trigger keeps the hold.

The proposed consumer is Release hold inspection in `reference/ci-cannot-run.md`,
linked from `reference/orchestrator.md`'s Cleanup and release section.
`scripts/guard`, the role hook and `release.yml` do not enforce an
outage-aware release gate today. No machine enforcement is claimed. Rehearsal
records the actual inspection, the withheld decision, and unchanged local/remote
tag and release inventory; it clears the decision only against matching post-return
main CI/protection captures. It never creates a product tag or release to prove a hold.

Current CI lacks `workflow_dispatch`. Rerunning a historical run is insufficient
unless its workflow and head exactly match current main. Otherwise report a blocked
trigger or use a separately reviewed ordinary PR adding a main dispatch interface;
no empty direct push or invented API trigger. Manual dispatch requires the configured
default-branch workflow: [GitHub documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Interrupted preparation/run retains failed commands, partial outputs, archival ref
and exact worktree identity. No operation resumes unknown execution as a successful
run. Partial publication/audit recovers exact receipts only. Rollback abandons the
bundle without erasing prior evidence or changing protection. Cleanup follows
verified durable export and ordinary nonforced worktree removal; dirty, occupied,
ambiguous or sole-copy paths remain for caller disposition. Never port source
`remove --force || true` or recursive deletion of uncertain paths.

## Verification and ownership

Collector tests cover both genuine causes and excluded triggers, simulated refusal,
parent order/count/tree, supported-map coverage and unsupported-step refusal,
incapable jobs, dirty/changed/ignored inputs, base/head movement, receipt/comment
tampering, unknown/duplicate POST outcomes and interruption at each durable boundary.
A disposable live rehearsal must prove real comment publication/refetch/recovery,
independent whole audit and protection inspection, and show the protected missing-
check refusal without changing protection. Label simulated outage proof throughout;
test platform blocking only in a specifically authorized disposable repository.

Rehearse evidence-only return followed by ordinary exact-PR CI/review; explicitly
show main success does not certify that PR and main failure does not implicate it.
Exercise the documented release inspection with active cause, stale/red/pending main
and verified post-return main/protection, recording withhold/clear decisions and
unchanged tags/releases. Future merged-set recovery remains a conditional design
check, not a claim of rehearsed degraded integration. Product PR verification requires full suite,
routing/release/ADR checks, native qualification, exact-head ordinary CI and final
independent Goal/Floor review. No safe-evidence success closes Issue 17's full goal
while the true degraded integration policy remains unresolved.

Current phase owns only this draft. After Issue 16 releases overlapping writes,
proposed implementation owns the focused collector/map/tests and coordinated
updates to fallback and release-inspection guidance, README/architecture and
decision records; shared guard/review APIs need a fresh base/interface reconciliation.
No version fields, shared code, native OS probes or repository provisioning change
in this phase. Task evidence stays in the root-authorized durable
`outputs/migration-completion/fallback`; disposable execution stays in
`work/migration-completion/fallback`, with no sole durable copy there.
