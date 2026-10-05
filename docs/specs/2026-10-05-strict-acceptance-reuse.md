# Reuse an accepted review only through an exact, published proof

Status: draft

## Problem & context

[Issue 16](https://github.com/LeonJoeeee/codex-method/issues/16) completes the safe
acceptance-reuse part of DevStandard at pinned source
`d593c67f6850fccca9246833c8fc7419836ce23a`, principally ADRs 0035/0046 and
`scripts/hard_edges.py:compare_rebase`. Target base is
`1a9e1d386313cf784559ee0dda54723e4b88f129` (0.2.6). Diagnostic diff equality does
not establish replay, receipt association or acceptance. The default remains a
fresh Goal/Floor review and exact merged-result CI. This spec settles the new
proof/publication interface; implementation waits for root's independent challenge
and publication of this spec's accepted reachable blob.

## Options considered

1. **Explicit append-only proof receipts anchored to actual acceptance.** Separate
   replay, Note and same-head artifact predicates share association/recovery;
   every uncertain case returns to ordinary review. Selected.
2. **Treat matching trees, comments or caller attestations as acceptance.** Cheap,
   but loses parent, placement, evidence and actual-verdict guarantees. Rejected.
3. **Re-review everything.** Safe existing fallback, but repeats judgments of
   proven unchanged substance. Retained for unsupported inputs, not the sole route.

## Decision

Add `scripts/acceptance_reuse.py` for deterministic proofs; extend
`scripts/review_state.py`, `scripts/review-packet` and `scripts/guard` for existing
ledger/publication consumers. Add real-consumer tests and synchronize operative
references, architecture, maintenance, README and ADR amendments while preserving
historical bodies. Recommend 0.3.0: this adds public commands and a receipt schema;
no release fields change in the draft phase. Put detailed exception rules in one
triggered reference, with short pointers in the complete orchestrator; do not
shorten its contract to make budget room.

### Interface and common binding

`review-packet reuse PR --issue ISSUE --attempt ORIGINAL_COMMENT_ID --kind
replay|note|external --old-base O --old-head H --base B --head N --request FILE
--output DIR --project CHECKOUT` computes, retains and publishes one complete
proof. `request` is strict kind-specific JSON: replay `{}`, Note
`{"target":"PATH","start":START,"end":END,"fence_offset":OFFSET}`, external
`{"artifact":"pr-description","fence_offset":OFFSET}`. Offsets are zero-based
UTF-8 byte offsets; reject extra fields, ambiguity and invalid offsets.
`guard merge --reuse REUSE_COMMENT_ID` explicitly selects that proof; without it,
the existing exact-head route remains. `guard compare` stays diagnostic.

Use the same per-PR lock and durable shared-git ledger, retaining original attempt
objects/verdict bytes and appending `reuses`. Each `codex-method-reuse-v1` record
binds repository/PR/issue, unique token, kind, original attempt token/comment id,
old/new base/head, original packet/instruction/verdict/comment SHA256 values,
request SHA256, complete proof bundle SHA256 and exact published comment id,
author and SHA256. It consumes no review round and supplies no new verdict.
No chaining: each proof independently anchors to the latest original attempt;
a subsequent attempt invalidates selection of earlier reuse. Verify original
association, valid complete returned Goal Yes / both Floors Pass / Ready Yes,
retained packet and instruction hashes, and absence of pending publication or
reserved reviewer. Failed, partial, malformed or missing evidence never qualifies.

New original packets retain a structured context capture in their hashed bundle
and receipt: complete ordered issue body/comments and PR comments, PR title/body
and base/head repository/ref identities, with raw-byte hashes. Require this binding for reuse;
older receipts lacking it keep ordinary workflow. Issue authority, PR title and
repository/ref identities must remain identical. PR body remains identical except
for the external predicate below. Permit only the exactly associated anchor-attempt
and proof comments after that PR-comment snapshot; changed historical comments or any other new comment require
fresh review. These method envelopes never become new substantive authority.

Fetch immutable objects only from the API-verified destination repository, verify
checkout origin and PR repository/ref identities, and match fetched objects to
API pins. Hold the lock through proof publication or guard verification; re-read
local ledger/bundle/request and remote original/proof comments, context and head/
base at the end. Refuse changes. Guard recomputes the predicate from retained
inputs; a stored `pass` is insufficient. Every route still needs current default
base ancestry, ordinary successful Actions-app `merged-result / B / N`, no failed
head checks, final head/base/context rechecks and server-side protection with
`--match-head-commit`. Locks coordinate method actors; they add no hostile
same-credential isolation or atomic server-side base lock.

### Three independent proof predicates

**Replay:** require full immutable commit SHAs, O ancestor of H and B, B ancestor
of N, B different from O, nonempty PR delta, and no merge commits or gitlinks in
either PR range. In a disposable clone with sanitized Git environment/config,
hooks/rerere disabled and no signing, replay O..H onto B with cherry-picks
reapplied and empty commits retained. Compare the union of O..H and B..N changed
paths using NUL-delimited literal names and no rename inference. Each H/N entry
must match exact object type, mode and blob bytes, including absent/deleted entries;
the complete replay tree must equal N's tree except the descriptor adjustment
below. Caller refs/index/worktree never move.

The sole exemption is the top-level `version` value in both
`codex-method.json` and `.codex-plugin/plugin.json`: regular files with unchanged
mode, exactly one value-only line change per descriptor, unchanged surrounding
bytes, valid complete JSON without duplicate keys, equal old/new versions, and
strict numeric `major.minor.patch` ordering without leading zeros. Both descriptors must change in
lockstep; N's version must exceed H's and the replay's whenever an exemption is
used. A stopped replay may resolve only a conflict whose stage-1/2/3 descriptor
blobs independently differ solely in that same synchronized version value;
resolve to B's side and continue. Other conflicts refuse. No empty PR delta,
descriptor deletion/symlink, arbitrary JSON edit or silent version revert qualifies.

**Note:** B equals O and N is one new commit whose only parent is H; an amend,
rebase, extra commit or merged parent refuses. The selected accepted raw verdict
must have one uniquely delimited Note containing the exact optional locator
`Replacement target: PATH@START:END` immediately followed by its own fenced
replacement, whose opening starts at OFFSET. The locator is reviewed authority
for placement; the caller cannot select a different occurrence. Extract raw
fenced content, strip only the common leading-whitespace prefix shared by
nonblank lines, and preserve blank lines, line endings and trailing whitespace.
Substitute it into H's regular-file blob at the reviewed byte range; require the
entire N tree equals this sole substitution with unchanged mode. Ambiguous,
unstructured, adapted or Goal/Floor-ground replacements use fresh review.

**External:** H equals N and O equals B, with exact commit equality rather than
just equal trees. Support PR-description corrections already prescribed in an
accepted Note using `Replacement artifact: pr-description` followed immediately
by one own raw fence at OFFSET. Apply the same exact extraction; require the
entire current raw PR body equals the quoted replacement and retain complete
before/after bodies and hashes. All other reviewed inputs remain fixed. This
strict subset avoids self-certifying arbitrary prose as harmless. An originally
failing Goal/Floor or general artifact-only closure needs fresh actual judgment;
SHA equality cannot manufacture acceptance. Other artifact types are unsupported.

### Distinct source policy option: bare version without a verdict

The source also admits a bare version bump with no review at all. That is a
separate gate choice, not accepted-receipt reuse, and is **not authorized for
implementation or use by this spec**. A concrete option for human decision is
`review-packet version-proof` plus explicit `guard merge --version-proof ID`:
require B as N's sole parent, an entire nonempty delta confined to both declared
version-value lines with the same strict monotonic/mode/JSON predicate above,
retain a separately labeled no-review proof receipt and normal exact merged CI,
association/publication recovery and races. It would honestly report no check-1
verdict and never synthesize Yes. Until specific human approval, absence of an
accepted receipt refuses even this input. This outstanding source case must be
reported as a policy decision, not as completed migration.

## Failure detection & rollback

Before POST, durably store exact proof-comment bytes, token and original-source
association in the existing ledger's pending intent. Append proof comments; never
PATCH an original verdict. An unknown POST outcome blocks reuse, review start,
replacement publication and integration. `review-packet status` may recover only
one exact token/body/author/id association; missing, altered or duplicate evidence
remains pending without retry or automatic reset. Crash before POST still follows
this rule. Partial local artifacts are retained and cannot qualify. A lock/write
failure before publication prevents mutation; a later failure never reports success.
Rollback uses ordinary fresh review or restores software to the prior version;
unknown-version receipts refuse without deleting ledger history. No automatic
revocation/deletion, receipt reconstruction from comments or force bypass.

## Verification and out of scope

Exercise reservation -> whole publication -> reuse -> status -> actual guard with
real Git histories, observing admitted merge argv only in consumer fixtures.
Positive cases cover disjoint replay, deletions/symlinks with preserved entry
identity, exact Note substitution, same-head prescribed metadata and strict
version-exempt replay. Negative cases cover every byte/mode/type/parent/head/base/
receipt/evidence/context drift, conflicts, ambiguous placement, malformed or
nonmonotonic versions, failure/partial evidence, missing/duplicate publication,
crashes at pending/save boundaries and local/remote races. Preserve original failed
and passing outputs, PREWRITE/DELIVERY and whole challenge/verdicts.

Qualify the final installed candidate's changed native role/hook bytes and rehearse
reuse through actual packet/guard commands on a specifically authorized protected
disposable GitHub lane. Native, live and fixture evidence remain distinct; root
owns protected-repository provisioning and irreversible rehearsal operations.
Full suite, routing, release, ADR and exact merged-result hosted CI plus whole
independent Goal/Floor review precede human product-merge approval. No product
merge, protection change, release, production install, CI-outage route, broader
threat model, Claude executor or resume deduplication is authorized here.
