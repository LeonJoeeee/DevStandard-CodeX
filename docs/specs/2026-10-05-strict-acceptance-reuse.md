# Reuse an accepted review only through an exact, published proof

Status: committed

## Problem & context

[Issue 16](https://github.com/LeonJoeeee/codex-method/issues/16) completes the safe
acceptance-reuse part of DevStandard at pinned source
`d593c67f6850fccca9246833c8fc7419836ce23a` (ADRs 0035/0046 and `compare_rebase`).
Target base: `1a9e1d386313cf784559ee0dda54723e4b88f129` (0.2.6). Diff equality
cannot establish replay or acceptance. Fresh Goal/Floor review and exact merged
CI remain default; implementation awaits independent challenge and publication
of the accepted reachable spec blob.

## Options considered

1. **Append-only accepted-review proof receipts.** Separate predicates share
   association/recovery; uncertainty returns to ordinary review. Selected.
2. **Tree/comment/attestation equality.** Loses replay, placement and acceptance
   guarantees. Rejected.
3. **Re-review everything.** Repeats unchanged judgments; retained as fallback.

## Decision

Add `scripts/acceptance_reuse.py` for deterministic proofs; extend
`scripts/review_state.py`, `scripts/review-packet` and `scripts/guard` for existing
ledger/publication consumers. Synchronize consumer tests, references, architecture,
maintenance, README and ADR amendments, preserving history. Recommend 0.3.0 for
new public interfaces; no draft release-field edits. Detailed rules use one triggered reference and
short orchestrator pointers without shortening its contract.

### Interface and common binding

`review-packet reuse PR --issue ISSUE --attempt ORIGINAL_COMMENT_ID --kind
replay|note|external --old-base O --old-head H --base B --head N --request FILE
--output DIR --project CHECKOUT` computes, retains and publishes one complete
proof. `request` is strict kind-specific JSON: replay `{}`, Note
`{"target":"PATH","start":START,"end":END,"fence_offset":OFFSET}`, external
`{"artifact":"pr-description","fence_offset":OFFSET}`. Offsets are zero-based
byte offsets: target START/END refer to H's raw blob and select [START, END);
OFFSET refers to the first byte of the opening fence line, including indentation,
in the raw returned verdict, excluding its publication envelope. Reject extra
fields, noninteger/invalid offsets and split UTF-8 characters; target bounds satisfy
0 <= START <= END <= blob byte length. `guard merge --reuse REUSE_COMMENT_ID`
selects a proof; omission selects ordinary acceptance, including the context check below.
`guard compare` stays diagnostic.

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

New packets and receipts bind `context-v1`: issue body, ordered issue/PR comments,
PR title/body and base/head repository/ref identities. Retain full API captures;
compare ordered comment (id, author-login, raw UTF-8 body) tuples and exact text/
identity fields, excluding volatile reactions, not substantive bytes. Preserve
original history; allow only the exactly associated anchor-attempt/proof PR
comments and the native issue record below. Unknown, edited, reordered or duplicate
comments refuse. Author identity or a method-looking envelope alone grants no allowance.

After actual spawn, `review-packet record-native PR --issue I --attempt ID
--native-handle HANDLE --observation FILE` replaces handwritten handle recording.
Under the same lock, retain the complete observed return and publish one exact
single-line `<!-- codex-method-native-v1 {JSON} -->` issue comment, with
compact sorted-key JSON and terminal LF, binding repo/PR/issue,
original attempt token/id, head/base, instruction SHA256, supplied handle and
observation SHA256. Retain comment id/author/raw bytes/hash in that attempt.
Its author must equal the original attempt author. Only that associated comment
may follow its issue snapshot; extra prose or another id/author/body/record
refuses. Pending intent/recovery applies before POST to the issue. This records
the caller's observed handle, not native authentication or task authority; it neither authorizes a second spawn nor alters
history. Unknown publication blocks all dependent review/integration operations.

Every ordinary guard of a new context-bound receipt compares current context to
its accepted snapshot under those exact allowances, then repeats comparison at
verification end. Changed PR body needs the selected external proof or fresh
review; replay/Note selection and omitted `--reuse` cannot evade it. Legacy
receipts retain only their existing exact-head guarantee, never qualify for reuse
and are not advertised as context enforcement.

`start` may review an already accepted same head only when it verifies actual
context drift against the latest bound snapshot under the same allowances; it
retains that diff in the new packet/receipt. Notes, changed CI observation or an
allowed handle/proof record alone cannot trigger a round. Explicit
`start --refresh-context --attempt ID` admits one context-binding upgrade of an
exact accepted legacy attempt lacking `context-v1`, with its intact original
association/carriers; absent or corrupted evidence is not an upgrade. A fresh
attempt preserves earlier verdicts and invalidates their reuse selections.
All pending-publication, active-reservation and Floor-2-stop blocks still apply.

Fetch immutable objects only from the API-verified destination repository, verify
checkout origin and PR repository/ref identities, and match fetched objects to
API pins. Hold the lock through proof publication or guard verification; re-read
local ledger/bundle/request and remote original/proof comments, context and head/
base at the end. Refuse changes. Guard recomputes the predicate from retained
inputs; a stored `pass` is insufficient. Every route requires current-base
ancestry, Actions-app success for `merged-result / B / N`, no failed head checks, final identity/context rechecks
and server protection with `--match-head-commit`. Locks coordinate method actors,
not hostile same-credential isolation or an atomic server-side base lock.

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
bytes, valid complete JSON without duplicate keys, equal versions across both
descriptors at each endpoint, and strict numeric `major.minor.patch` increase
without leading zeros. Both descriptors change in lockstep; N's version exceeds
H's and the replay's whenever an exemption is used. A stopped replay may resolve only a conflict whose stage-1/2/3 descriptor
blobs independently differ solely in that same synchronized version value;
resolve to B's side and continue. Other conflicts refuse. No empty PR delta,
descriptor deletion/symlink, arbitrary JSON edit or silent version revert qualifies.

**Optional raw Note grammar:** the reviewer may prescribe one replacement inside
`### Notes` using this exact top-level block; ordinary Notes need no structure.

~~~~text
<!-- codex-method-note-v1 -->
Replacement: {"target":"a.md","start":0,"end":4}
```replacement
Corrected text.
```
<!-- /codex-method-note-v1 -->
~~~~

Require exactly one such block outside all other fences/blockquotes, wholly within
the unique raw `### Notes` section. Wrapper lines end in LF; delimiter/metadata
lines begin at column zero; strict JSON metadata has exactly the target/start/end keys above or solely
`{"artifact":"pr-description"}`. Its next line opens a fence: zero to three spaces,
three or more identical backticks or tildes, and literal `replacement`; closure
uses identical indentation/marker, with no suffix. No intervening prose or blank
lines; the closing delimiter immediately follows closure. Duplicate/nested blocks,
extra fences/metadata, markers inside content, unclosed fences, alternative
blocks, examples inside enclosing fences and unsupported forms refuse. Using this optional block
declares prescription; ordinary free-form discussion never does. Update reviewer
guidance with this qualifying example without requiring it of ordinary reviews.

**Note:** B equals O; N is one new commit whose sole parent is H. Locator fields
must equal the request, and OFFSET must identify that block's opening fence.
Extract its original raw content; strip only the common leading-whitespace prefix
of nonblank lines, preserving blank lines, line endings and trailing whitespace.
Substitute into H's UTF-8 regular-file blob at the reviewed half-open range;
require the entire N tree equals this sole nonempty substitution with unchanged
mode. Amend/rebase/extra commits, adapted text and Goal/Floor grounds refuse.

**External:** H equals N and O equals B as exact commits, not merely equal trees.
The same accepted raw Note block uses artifact-only metadata; require the entire
current PR body equals its extracted replacement. Retain complete before/after
bodies/hashes; other accepted context fields stay fixed. Originally failing
Goal/Floor or general artifact-only closure needs fresh actual judgment; SHA
equality cannot manufacture acceptance. Other artifacts remain unsupported.

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
crashes and races. Include normal/forged/duplicate handle records, omitted or
wrong-kind `--reuse`, same-head drift re-review, Notes-only refusal and legacy
upgrade. Retain original outputs, PREWRITE/DELIVERY and whole challenge/verdicts.

Qualify changed installed-candidate native bytes; rehearse actual packet/guard
reuse on an authorized protected disposable GitHub lane. Distinguish native,
live and fixture evidence; root owns protection and irreversible operations.
Full suite, routing/release/ADR checks, exact merged CI and whole independent
Goal/Floor review precede human product-merge approval. No product
merge, protection change, release, production install, CI-outage route, broader
threat model, Claude executor or resume deduplication is authorized here.
