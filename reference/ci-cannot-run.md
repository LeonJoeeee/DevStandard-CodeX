# When CI cannot start: evidence while integration waits

Green ordinary CI and independent Goal/Floor review remain separate merge gates.
`scripts/ci-evidence` preserves useful local evidence; it grants no waiver and always
reports `merge_permitted: false`. `review-packet start --ci-fallback` and
`guard merge --ci-fallback` still refuse. A comment, successful collector or helper
audit cannot manufacture an Actions-app check or ordinary review admission.

The original DevStandard fallback required the merging main session's exact
synthetic merge, every CI job, public evidence and independent audit, with a human
owning any protected-branch exception and immediate restoration. The evidence
subset is migrated here. That historical degraded integration policy is still
unapproved: agents never lower protection, bypass required checks, push the default
branch directly or release under this route. The main session returns the precise
policy choice to the human before any dependent implementation.

First read `reference/ci-pipelines.md`'s **When hosted CI cannot start** section.
Safe, explicitly authorized repo-scoped self-hosted Actions produce ordinary checks
and are a separate route. They still need a functioning Actions service and reviewed
runner routing; `runs-on: ubuntu-latest` does not select a self-hosted runner.

## The cause and the waiting decision

Waiting preserves ordinary CI. Even a real outage rarely justifies the cost of a
full equivalent run and audit. Before collecting, explain concretely why waiting
was ruled out. Two source causes may qualify: a proven provider incident, or a
private account's exhausted hosted allowance **with a proven block on further
usage**. The cause must be external to this repository and prevent every otherwise
eligible push in the affected provider/account scope. An absent run is no proof.

Retain whole current provider/billing documents and authenticated, readable
run/workflow/event/repository/organization diagnostics. The original capture must
name its source, argv or tool input, UTC time, exit, complete stdout and stderr.
A usage total reaching the free allowance does not prove blocking: paid overage
may remain available. The old product-specific billing APIs are retired; use
current billing documents and an explicit account block, reviewed independently.
See [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
and [the API retirement](https://github.blog/changelog/2025-09-26-product-specific-billing-apis-are-closing-down/).
Unreadable or ambiguous billing state refuses; do not infer a waiver from it.

| Observation | Required action |
|---|---|
| Slow, queued, flaky, or the session is ending | Wait; a queued run exists. |
| Red run | Fix the branch or use ordinary red-main recovery. |
| Offline self-hosted runner | Repair the runner; the Actions service still queued a job. |
| Disabled, invalid, absent or event-filtered workflow | Repair CI through an ordinary PR. |
| Organization disabled Actions | Human/admin resolves it; integration waits. |
| Unauthenticated, unreadable or network-uncertain state | Establish the state or wait. |
| Unsupported billing response or ambiguous startup record | Retain the blockage; do not certify the cause. |

Assertions, simulated incident IDs and test fixtures are not operational proof.
`--rehearsal` labels the whole manifest simulated and records actual working Actions
observations separately. It never creates an operationally qualifying receipt.
The collector's cause output is an **unauthenticated candidate** requiring the
fresh independent cause audit below, even when its structural checks pass.

## The focused collector

Only the integrating main session operates this evidence path. A worker's ordinary
done-checks are never fallback check 2. Read `scripts/ci-evidence --help`; require
explicit project, repository, PR, proof, reviewed map, whole audit context and a
new durable output destination. Choose the execution environment before running:
the supported native job installs Linux packages and Codex globally. Use an
explicitly authorized disposable Ubuntu environment, never install to a production
host merely because this guide names the command.

```sh
scripts/ci-evidence --project <clean-source-clone> --repo <owner/repository> \
  --pr <number> --proof <whole-cause-proof.json> --context <audit-input-directory> \
  --map <reviewed-ci-evidence-map.json> --output <new-durable-evidence-directory>
# Add --rehearsal only for visibly simulated qualification exercises.
scripts/ci-evidence --verify <evidence-directory> \
  --expected-sha256 <externally-retained-bundle-receipt-sha256>
```

The proof JSON contains `cause` (`provider-outage` or `minutes-exhausted`), `scope`,
`why_waiting_ruled_out`, UTC `observed_at`, `external_to_repo: true`,
`prevents_all_eligible_pushes: true`, `simulated`, whole `captures`, and
`diagnostics`: authenticated/readable/workflow_enabled/event_eligible/org_enabled
booleans and `runs`. Every capture contains original `argv`, `exit_code`, UTC
`captured_at`, whole `stdout` and `stderr`. A provider candidate needs an unresolved
Actions outage response from GitHub Status. A minutes candidate additionally needs
`private_repo: true` and `blocking_capture_index` pointing at the whole current
GitHub billing-page block document. This is a carrier check, not a billing judge;
the auditor must establish actual blocking, affected account and provenance.
The supplied diagnostic assertions require their original supporting records in
the audit context; assertions alone cannot pass the audit.

The context directory contains complete `issue.json` (governing issue and ordered
comments), `accepted-spec.md` and `source-checklist.md` (the source's four audit
questions below). Symlinks or missing/empty carriers refuse. The collector retains
these bytes, the whole base-to-head binary/name-status diffs and original remote
PR/repository/default-ref responses. Supply fresh records for the actual target,
not a different repository's bundle.

The shipped map is a reviewed **byte-pinned concrete map**, not a YAML interpreter.
It covers this repository's pinned PR-event workflow: `suite`, `native`, aggregate
`test`, and `merged-result`; it records release-workflow event exclusion. Any edited
map, workflow, matrix, action, condition, service or secret requirement refuses
until a reviewed product change supplies a supported map. There is no job filter.
Linux apt/AppArmor/bwrap setup and Codex installation execute inside captured steps;
a Mac probe or silently preinstalled dependencies cannot replace them.

The collector freshly cross-checks remote default base/head through API and explicit
fetches, computes `merge-tree --write-tree`, and creates a synthetic commit with
exactly ordered `[base, head]` parents. It records the checked-out commit, parents
and tree, independently recomputes the merge tree and checks remote movement again.
A create-only direct archival ref and complete Git bundle retain the object.
No branch/default ref is advanced. A changed base/head/map/proof requires a new run.

Each command retains intent **before** execution and complete binary stdout/stderr,
exit, UTC start/end, cwd and explicit environment. Mapped jobs receive a recorded
credential-free environment, with their own home and temporary directory. Tracked
hashes/modes, clean diffs/status and ignored inputs are accounted for before/after
steps. This concrete map admits no symlink, untracked or ignored source inputs; only named
Python bytecode outputs may appear. Unsupported required inputs refuse instead of
being silently omitted. Tool versions, executable identities and Linux dependency
state are captured at step boundaries. Declared package/Codex setup changes are
expected; any other source or toolchain drift fails. Generated execution caches
remain owned disposable files; original native artifacts and evidence are retained.

A failed/incapable job remains failed/incapable; later normal steps are recorded
not-run and `always()` artifact obligations still run. Aggregate/dependent jobs
remain accounted for. No missing job becomes success. The upload action is replaced
by whole locally retained native artifacts, with that transport difference explicit;
no actual Actions upload or CI check is claimed by the collector.

## Publication and fresh independent audit

Retain `manifest.json`, complete original captures/artifacts, `merge.bundle`,
`evidence.md`, ordered `publication-part-*.md`, `publication-parts.json`, and
`bundle-receipt.json`. Keep the receipt SHA-256 outside the bundle before transporting
it; `--verify` detects changed carriers, parts, captures or interrupted commands.
Local digest files do not isolate a malicious actor holding the same credentials.

The main session publishes all ordered parts with the literal marker
`CI-FALLBACK EVIDENCE — integration blocked`, the manifest/part digests and the whole
checklist. Do not substitute output tails or inaccessible local-only evidence.
The collector performs no POST. Its `publication_intent`/`publication_recover`
utilities (load the script with Python `runpy`) reuse the existing durable-save and
digest primitives without formal acceptance records. Before each POST retain/fsync
one distinct part's exact repository/PR/author/body/token intent. Preserve the full
POST response and refetched comment list. Recover only one exact body/author/token,
positive comment ID and matching repository/PR URL; retain timestamps and receipt.
Missing, duplicate or edited outcomes refuse. An unknown POST is never blindly
retried. Check current remote base/head before and after publication and audit;
movement invalidates applicability, not the historical evidence.

Commission a fresh independent `method_review_helper`, explicit Sol/high, with a
whole digest-bound carrier: issue/spec/diff, all originals, published parts and exact
receipts, source checklist and target/base/head/tree identities. The helper hashes,
fully reads bounded numbered chunks and hashes again. Retain its actual handle,
whole raw return, limitations and bundle/publication hashes; publish the whole return
unchanged through the same pending-intent discipline. An audit finding is repaired
and rerun, never hidden. This helper audit grants neither formal Goal/Floor acceptance
nor ordinary green-head review admission.

Carry the original questions in full:

> Audit the CI-fallback evidence above against all four items:
> - Is the stated cause outside this repo (minutes exhausted, platform
>   outage) and proven — not "slow", "queued", "flaky", "red", or anything
>   this repo or its org could fix?
> - Do the merging session's timestamped fetch/ref captures identify the
>   current remote main tip and PR head, matching the published base/head
>   and this packet's pins? Does its successful merge-tree capture use
>   those exact SHAs and produce the published tree? Does the captured
>   checkout identity show a commit whose first parent is that base,
>   second parent is that head, and tree is that captured merge tree?
>   Compare the supplied captures; do not execute commands. Missing or
>   inconsistent captures cannot establish that the run tested their merge.
> - Is the run fresh (a UTC timestamp) and tracked state clean before it
>   (`git diff --quiet` and `git diff --cached --quiet`)? Are permitted
>   untracked inputs enumerated—only paths already on the pre-run baseline
>   and named by the worktree copy-list, never an invented fixture? Do
>   before/after `git status --porcelain -uall` snapshots match? Is every
>   ignored input the run depends on named?
> - Is every CI job covered, unfiltered, with commands and exit codes shown?

## Evidence-only return

As soon as ordinary CI can start, re-read the cause, end outage eligibility and mark
this evidence historical on the existing issue/PR. Resume ordinary CI and formal
review for the PR's exact **current** base/head. There is no standing outage mode.
Main green does not certify an unmerged PR, and red main cannot implicate that PR.

The source's degraded-merge return sweep is separately conditional on future human
policy: actual integrated commit/tree and exact merged-PR set, human authority,
before/after protection, and first ordinary post-return CI for exact current main
containing those integrations. Green verifies that set; red makes the actual degraded
merges suspects under normal red-main recovery. This implementation creates no
fictional merged set or degraded integration route.

## Release hold inspection

**The integrating session consumes this obligation before creating/pushing any tag
or invoking a release action.** Inspect existing outage issue/PR records, fresh
provider/account cause, exact current main CI and approved protection baseline.
Retain whole captures and a `release withheld` or `hold cleared` decision on the
existing issue. The guard, role hook and release workflow have no outage-aware
machine gate; this is a mandatory session obligation.

A hold begins with a qualifying degraded interval. Clear it only when the cause has
returned, the first ordinary post-return main CI is complete and green for exact
current main, and protection matches its approved baseline. A newer main requires
fresh verification. Under any future human-waiver policy, the actual integrated-set
sweep must also be complete. Pending/red/stale/unreadable/incomplete evidence,
uncertain protection/policy, or an unsupported trigger means **withhold**. This
release inspection grants no acceptance to an unmerged PR.

Current CI has no `workflow_dispatch`. A historical rerun is sufficient only when
workflow and head exactly match current main; otherwise report the blocked trigger
or add a dispatch interface through a separately reviewed ordinary PR. Never invent
an API trigger or make an empty direct default-branch push. Rehearse the actual
inspection and retained withhold/clear decision against matching current captures,
with unchanged local/remote tag and release inventories; do not publish a product
release to test the hold.

## Interrupted runs and safe disposal

An interrupted operation keeps its durable intent, partial originals, archival ref
and registered checkout. It cannot verify as complete or resume as a successful run.
Seal only once; retain historical failed bundles and start a new output directory.
An input change or publication/audit movement never erases prior receipts.

Before cleanup, independently verify durable export and identify the exact owned
checkout/ref. Use ordinary nonforced worktree removal only after source/input/export
accounting is complete. Dirty, occupied, ambiguous and sole-copy paths remain for
caller disposition. No automatic trap forces removal or recursively erases evidence.
The source's forced cleanup example is deliberately replaced by this retention rule.
