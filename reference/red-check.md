# A red check is not a finding — it is the gate

It cannot be answered, contested, or waited out. **There are three states, not two.**

Check flakiness first: a flake is outside these three states, and the closing rule below governs it.

**1. Your diff caused it.** Fix the diff.

**2. Your change deliberately staled the check's assumption** — the case right after a structural change, where the check asserts something your change changed on purpose. Fix the check in the same PR, and name the staled assumption and why your change staled it, in both the implementer's report and the PR description. That repair is a gate change, and a diff touching CI cannot be vouched for by CI, so merge check 1 is the only check it gets (`reference/code-review-prompt.md`).

**3. Neither** — the red is not your diff's doing, and never yours to work around:

- `main` is red → the recovery is the orchestrator's (`reference/orchestrator.md`) and outranks this PR; a worker's own act is unchanged — the delivery rebase, once main is green (your role page).
- the pipeline aged out from under you → `reference/ci-pipelines.md`. Fix it in its own PR, or in this diff only if your task already touches that workflow file.
- the check can never go green at all → your role page's Driving a PR to green section.

Say what you observed on the PR and let the owning rule run. If you are a worker and the rebase cannot happen before you have to return, hand the PR back saying exactly that.

**Loosening an assertion because it is inconvenient** is the banned weakening of a done-check, applied to CI — in every one of the three states, and whoever you are.

**Never read a red run as CI being unavailable.** A run that started and failed is CI working. The check-2 fallback triggers on *no run at all*, from two named platform causes (`reference/ci-cannot-run.md`); red authorises nothing.

**A check that fails, then passes with no code change, has not gone green** — it has shown you a flake. One re-run identifies it; a second is hope, not a plan. From there the flaky-check rule governs: a tracked, reviewed quarantine, never a quiet retry loop.
