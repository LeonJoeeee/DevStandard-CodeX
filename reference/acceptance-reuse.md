# Reuse an accepted review through its exact proof

Read this only when a merging session proposes acceptance reuse or must refresh
an accepted same-head review after its substantive context changed. Fresh
Goal/Floor review remains the default. `guard compare` is diagnostic and never
acceptance authority. The existing original verdict stays immutable.

## Original receipt and context

Only the latest original, locally receipted whole Goal Yes / both Floors Pass /
Ready Yes verdict can anchor reuse. Its original comment id/author/raw bytes,
packet, native instruction and SHA-256 bindings must remain intact. A reserved,
failed, invalid, missing or partial original cannot qualify. Proofs never chain,
consume a round or supply a new verdict. A subsequent original attempt invalidates
all earlier proof selections.

New reservations bind `context-v1` in their envelope, receipt and digest-bound
packet: full issue/PR API captures, issue body, PR title/body, base/head repository
and ref identities, and ordered comment (id, author-login, raw body) tuples.
Volatile reactions grant no substantive authority. Preserve original history;
only exactly associated original-attempt/proof PR comments and the original's
single native issue record may follow. Owner authorship and method-looking text
alone never qualify. Unknown, edited, reordered or duplicate comments refuse.

After actual native spawn, retain its whole observed return and use:

```sh
<plugin>/scripts/review-packet record-native PR --issue ISSUE --attempt ORIGINAL_ID --native-handle ACTUAL_HANDLE --observation /durable/native-return.json --project CHECKOUT
```

This publishes one exact `codex-method-native-v1` issue comment binding original
attempt, head/base, instruction hash, supplied handle and observation hash. Its
author must equal the original attempt author. Extra prose or another id/body/
author refuses. The supplied observation is caller evidence, not native
authentication, a completion verdict, permission to spawn again or task authority.

Ordinary guard checks the accepted context even without `--reuse`; it repeats
context and original evidence checks at verification end. Changed PR body needs
the selected external proof or fresh review. Another proof kind cannot authorize
that change. Legacy receipts keep only their existing exact-head/base guarantee
and cannot reuse acceptance. Do not advertise retrospective context enforcement.

For an accepted same head, `start` admits a fresh original review only for actual
verified context drift and retains the drift in the new packet/receipt. Notes,
changed CI observations and associated lifecycle/proof records alone cannot
trigger a round. `start --refresh-context --attempt ORIGINAL_ID` admits one
explicit upgrade of an intact accepted legacy file carrier lacking context;
missing/corrupt evidence is not an upgrade. Pending publication, active reviewer
and Floor-2-stop blocks still apply. Earlier verdicts remain unchanged.

## Compute and select one of three proofs

```sh
<plugin>/scripts/review-packet reuse PR --issue ISSUE --attempt ORIGINAL_ID --kind replay --old-base O --old-head H --base B --head N --request /durable/request.json --output /durable/reuse --project CHECKOUT
<plugin>/scripts/guard merge --repo OWNER/REPO --pr PR --reuse PROOF_COMMENT_ID --project CHECKOUT
```

Use full immutable commit SHAs. The checkout origin, API destination and PR
repository/ref identities must agree; reuse currently supports same-repository
PRs only. Fetch verified objects without moving caller refs/index/worktree. The
per-PR ledger lock covers computation/publication or guard verification. Requests
are strict complete JSON without duplicate/extra keys, NaN or ambiguous offsets.

| Kind | Request | Exact predicate |
|---|---|---|
| `replay` | `{}` | O ancestor of H and B, B ancestor of N, B differs from O, nonempty PR delta, no merges or gitlinks. Replay O..H onto B in a disposable sanitized repository, reapply cherry-picks, retain empty commits, disable hooks/rerere/signing. Union old/new PR-changed paths uses literal NUL-delimited names and no renames. H/N entries match object type, mode and blob bytes, including symlinks/deletions; full replay tree equals N apart from the descriptor rule below. |
| `note` | `{"target":"PATH","start":START,"end":END,"fence_offset":OFFSET}` | B equals O. N is one new commit with sole parent H. The accepted raw Note's reviewed locator and fence offset match the request. Apply its exact extracted replacement at [START, END) in H's UTF-8 regular-file blob. Entire N tree equals this sole nonempty substitution with unchanged mode. No adaptation, amend, rebase or extra commits. |
| `external` | `{"artifact":"pr-description","fence_offset":OFFSET}` | H equals N and O equals B as exact commits. The entire current raw PR body equals the accepted raw Note's prescribed artifact replacement; retain complete before/after bodies and hashes. Every other context field stays fixed. Other artifacts and closure of an originally failing verdict require fresh judgment. |

The sole replay exemption changes the top-level `version` value in both
`codex-method.json` and `.codex-plugin/plugin.json`: regular files, identical
mode/surrounding bytes, one value-only line change, valid JSON without duplicate
keys, synchronized numeric major.minor.patch versions without leading zeros,
strictly increasing. N exceeds both H and actual replay versions. A conflict may
resolve only when stage-1/2/3 descriptor sides independently differ solely in
those synchronized monotonic values; choose B's side and continue. Other conflicts,
descriptor deletion/symlink, arbitrary JSON edits or silent version reverts refuse.

The optional raw replacement grammar is one block wholly within the unique raw
`### Notes` section, outside other fences/blockquotes:

~~~~text
<!-- codex-method-note-v1 -->
Replacement: {"target":"a.md","start":0,"end":4}
```replacement
Corrected text.
```
<!-- /codex-method-note-v1 -->
~~~~

External metadata is solely `{"artifact":"pr-description"}`. Delimiter/metadata
lines begin in column zero and end LF. Metadata is immediately followed by a
fence with zero to three spaces, at least three identical backticks or tildes and
literal `replacement`; closing indentation/marker is identical without a suffix.
The closing delimiter follows immediately. Reject extra/nested/duplicate blocks,
extra fences/metadata, markers in content, unclosed fences, quoted examples or
alternatives. Ordinary free-form Notes need no structure.

OFFSET is the first byte of the physical opening-fence line, including indentation,
in the raw returned verdict, excluding its envelope. START/END are nonnegative
exact integer byte offsets in H's blob, selecting [START, END); reject UTF-8 split
boundaries, booleans and floats. Extraction strips only the common leading
whitespace prefix shared by nonblank lines, preserving blank lines, raw line
endings and trailing whitespace. Never normalize the returned verdict.

## Retention, recovery and integration

The shared ledger appends `reuses`, retaining original attempts. A unique output
subdirectory retains exact `request.json` and complete `proof.json`: source pins/
evidence hashes, raw request/verdict, full current API context and computed result.
The published `codex-method-reuse-v1` comment includes the exact request locator
and computed result, binds the retained bytes and their source,
then acquires exact id/author/comment hash association. Keep these files in a
durable home through acceptance/recovery; hashes cannot replace missing bytes.
Guard recomputes the predicate from retained inputs; a stored `pass` never admits.

Before any POST, durably retain exact outbound comment bytes and original source
association in the existing pending intent. Proofs append, never PATCH original
verdicts. Unknown outcomes block start, reuse, native recording, verdict changes
and integration. `status` recovers only one exact token/body/author/id association;
missing, edited or duplicate outcomes remain pending without retry/reset. Crash
before POST still follows that conservative rule. Partial artifacts remain
retained and cannot qualify. Later races refuse without reporting success.

Every route retains current-base ancestry, ordinary successful GitHub Actions app
15368 evidence for `merged-result / B / N`, no failed head check, final local/
remote identity/context checks, server protection and `--match-head-commit`.
Locks coordinate method actors, not hostile same-credential writes or an atomic
server-side base lock. Rollback uses fresh ordinary review or prior software;
unknown receipts refuse without deleting history or reconstructing authority.

The source bare-version exception without any verdict remains a separate,
unapproved gate choice. No `version-proof` admission or fake favorable review is
implemented. CI-outage waivers, production installation, merge and release still
need their own established authorization and gates. Consumer fixtures, controlled
native runtime and protected live GitHub rehearsal prove different properties;
report their actual evidence and remaining limits separately.
