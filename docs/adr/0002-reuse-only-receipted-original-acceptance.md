# 0002 — Reuse only a receipted original acceptance with an exact proof

Status: Accepted (2026-10-05); Amends 0001 (accepted-review reuse and native review recording).

## Context

The human authorized the remaining DevStandard acceptance-reuse migration under
[Issue 16](https://github.com/LeonJoeeee/codex-method/issues/16), while retaining
separate merge approval. Diff/tree equality cannot establish actual replay or
associate a favorable review with changed context. Same-head metadata changes
also expose a gap when acceptance checks only commit identity. Original verdict
bytes and the exact merged-result CI guarantee must survive reuse and crashes.

Root accepted the independently challenged [strict reuse spec](../specs/2026-10-05-strict-acceptance-reuse.md)
at blob `6fad995f600bb04c3329e6536a2a63a7356c02a4` before implementation. The
public proof interfaces and durable receipt association make this a consequential
cross-consumer decision. Root reserved this number before parallel 0003/0004 claims.

## Decision

Append one proof receipt to the existing per-PR ledger and publish it separately,
anchored only to the latest actually accepted original Goal/Floor verdict. Replay,
raw prescribed Note substitution and exact same-head PR-description correction
have independent deterministic predicates. Guard recomputes selected proofs;
original attempts/verdict bytes remain immutable, proofs do not chain or consume
a review round, and ordinary fresh review remains the default.

New original packets/receipts bind substantive context and exact ordered history.
Ordinary guard checks that accepted context even without reuse. `record-native`
retains the caller's actual observed return and exactly associates one post-start
issue record; author identity or method-looking text alone is never an allowance.
Verified substantive context drift permits fresh same-head judgment; Notes alone
do not. Legacy receipts keep their old exact-head guarantee and cannot reuse.
Durable exact pending intent precedes publication; unknown outcomes refuse
without retry/reset. Every route keeps ordinary exact Actions-produced merged CI,
current destination/pin/race checks and server-side protection.

The real alternatives were equality/attestation shortcuts, rejected for losing
review association and replay guarantees, and mandatory re-review of every input,
retained as the safe fallback but unnecessarily repeating proven judgments.

## Consequences

Supported inputs can retain actual acceptance without manufacturing another
verdict. More exact evidence must be retained; unknown publication, unsupported
forms and missing/corrupt carriers deliberately sacrifice availability. The
source bare-version path without a verdict remains a separate unapproved policy
choice and is unimplemented. Fixtures, controlled native runtime and protected
live GitHub rehearsal establish distinct properties. This decision grants no
product merge, protection change, production install or release authorization.
