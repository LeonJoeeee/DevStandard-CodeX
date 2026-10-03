# How to write a design spec

Read this when a task is substantial enough to need one (rule below). The design spec is the middle layer between `docs/architecture.md` (the system view) and the code: **one document that settles how a substantial change will be built, before it is built** — and it doubles as the handoff a context-free worker executes.

## When one is required (and when not)

Required when any of these holds — the gate is the significance of the **change**, never the size of the project:

- it changes a shared or public interface (API, schema, on-disk format, a cross-module contract);
- it is a real feature whose design could reasonably go more than one way;
- getting it wrong is expensive to undo.

Explicitly exempt — write nothing: refactors that don't change meaning, objective improvements (speed, fewer warnings), changes invisible to users, and anything the task's issue already fully specifies (unless the change independently triggers one of the three conditions above — for those, a spec and its challenge run regardless of how detailed the issue is). Founding setup owes no separate spec either; its design and challenge are the architecture settling itself (`reference/prd.md`). The exemption list is what keeps this lean — when in doubt on a borderline case, a half-page spec beats a wrong build, but never write one for the exempt categories.

## What it contains (1–3 pages, never more)

1. **Problem & context** — what this changes and why now; link the issue.
2. **Options considered** — 2–3 real options with the tradeoffs that matter; one line each on what was rejected and why. This section is the document's reason to exist: the chosen design without the rejected alternatives is just code in prose.
3. **Decision** — the chosen design, concretely: the files and interfaces it touches.
4. **Out of scope** — what this deliberately does not do.
5. **Verification** — the end-to-end check that proves it works; the task's done-check derives from this; the verification must be something a machine can judge.
6. **Failure detection & rollback** *(conditional)* — required only when the change touches a shared or public interface, a schema, or anything expensive to undo; state how a partial failure is detected and how to return safely to the previous state.

The orchestrator uses its centralized design craft binding in `reference/orchestrator.md` to
settle the design and brief its writer. A worker writes the repository artifact in its assigned
lane; return here for admission, contents and accepted-design handoff.

**Pin detail in proportion to the cost of getting it wrong.** Spell out exact interfaces, commands, and step order where a mistake is expensive or the sequence is fragile — a migration, a shared contract, a destructive step. Where several implementations would all be fine, give the direction and the boundary and leave the code to the worker (the code is the worker's call). Rigor goes to the fragile parts, not uniformly: over-specifying a low-risk part burns the pre-code challenge on minutiae and boxes out the worker; under-specifying a fragile sequence invites a data-losing reorder.

## Mechanics

- **File by default**: `docs/specs/YYYY-MM-DD-<kebab-title>.md` in the target repo; an adopted repository's established convention may supply another location. The date prefix keeps parallel branches from colliding over sequence numbers (the problem ADR numbering solves with a verify-then-claim check — specs avoid it entirely).
- **Status header**, first line under the title: `Status: draft | accepted | committed | abandoned`. Accepted = survived the pre-code challenge; committed = implemented and merged; abandoned = decided against. **Specs are never deleted** — an abandoned spec is a road not taken, worth remembering; the corpus is a second decision log alongside the repository's ADR log.
- **Review = the existing pre-code challenge, run by the main session before implementation**: a clean reviewer that did not write the spec tries to poke holes in it before any implementation starts. `reference/orchestrator.md`'s Dispatching to an executor section owns what clean requires and how to dispatch it. Nothing new is added on top.
- **Flow**: the main session commissions the draft in the task's worker lane and runs the pre-code challenge BEFORE authorizing implementation — the header flips to `Status: accepted` when nothing blocking remains. Before the implementation continuation, ensure that accepted blob is reachable in the repository, publish its blob SHA on the issue, and link the accepted spec as the worker's handoff. The spec file travels in the worker's implementation PR, which sets `Status: committed` before check 1 — the status describes the state at merge (no post-merge edit of a protected main). A spec whose decision must be settled long before building starts can instead merge alone in its own small PR at `accepted`; the implementation PR later flips it to `committed` as part of its reviewed diff.
- **Relation to ADRs**: an architecture-touching change still gets its ADR — the ADR records *the decision and its why* (one page, forever); the spec records *the design* (options, interfaces, verification). Link them; neither replaces the other.

## Template

```markdown
# <change, in one line>

Status: draft

## Problem & context
<what this changes and why now; link the issue>

## Options considered
1. <option> — <the tradeoff that matters>
2. <option> — <why rejected, one line>

## Decision
<the chosen design; the files and interfaces it touches>

## Out of scope
- <what this deliberately does not do>

## Verification
<the end-to-end check that proves it works>

## Failure detection & rollback (when required)
<for a shared/public interface, schema, or expensive-to-undo change: how a partial failure is detected and how to return safely to the previous state>
```

Lands in the target repo under `docs/specs/` by default; an adopted repository's established convention
may supply another location, which `docs/architecture.md` declares (`reference/in-repo-writes.md`).
