# 0001 — Codex is the only main session, and every worker is its own built-in subagent

Status: Accepted (2026-09-29); Amended (2026-10-03).

*This ADR decides what this method ships. A reader in any seeded project should take it as method.*

## Context

The human's ruling, 2026-09-29: build a method that a Codex main session runs end to end, and do not
carry a cross-host executor into it. Two earlier positions shaped the ruling. A sibling method had
just removed Codex hosting because, as a main session on shared rules, Codex followed its own harness
logic instead. And the same discussion settled that a helper a role spawns uses its own harness's
built-in subagent — never another host's process — because cross-harness nesting solves nothing and
costs a whole layer of machinery.

The method starts from zero: its decision log is this file, and no other project's pages are its
source.

## Decision

Codex is the only main session. Dispatched work and gating review both go to Codex's own built-in
subagent; there is no `--implementation` selector and no second vendor's agent anywhere in the
shipped commands. The dispatcher prepares a native-worker receipt (model, effort, brief) and the
caller hands it to Codex's native spawn with conversation-history forking disabled, then records the
returned handle on the issue — the dispatcher observes no handle, so that record is the evidence one
finished.

Model and effort are stated once, on `reference/orchestrator.md`'s Model and effort section, and
every reader takes them from there: `scripts/dispatch` for the anchored rows, the packet's `Helpers:`
line for a role's own subagents, `review-packet` for an arbitration. A row that cannot be read
refuses rather than dispatching on a stale name.

## Consequences

The shipped commands are `dispatch`, `review-packet` and `guard`. The role hook refuses a worker's
merge, the orchestrator's `gh pr merge`, and a reviewer's write flags — four words, because a word
stays only where the act is irreversible and no other layer stops it.

SessionStart delivers `reference/orchestrator.md` whole, in ordered parts when one output cannot
carry it; the parts concatenate to the file's exact bytes and are tested that way.


**Amendment (2026-10-03, adaptation audit and human runtime qualification):** The original body
incorrectly says no other project's pages are the source. codex-method is a port and adaptation
of `/home/leon/projects/prod/devstandard`, including its role pages, reference rules, templates,
and collaboration machinery. Starting from zero refers only to this project's ADR history,
seeded by ADR 0000; it does not deny those sources. The original September acceptance date and
source-free wording are retained as historical text, not asserted as verified facts: this
adaptation instruction and correction are dated 2026-10-03. Source history is routed in
`docs/architecture.md`, rather than copied as this project's decision log.

The Codex-only main-session and native-subagent decision stands. Codex rust-v0.159.2 source
qualification establishes V2 spawn fields, `gpt-6.1-sol`/`high` metadata, inherited cwd and
permissions, package-level hooks selected by `agent_type`, and separate project-role discovery.
A native nonediting reviewer is a fresh-context contract plus ordinary-path hook, not a per-child
OS read-only sandbox. Native arbitration before a PR follows the same boundary. Model and effort
are explicit; unavailable models and quota never silently substitute.

The original claims about shipped role-hook breadth and tested whole startup delivery are not
runtime evidence for this adaptation. `reference/harness-codex.md` and `docs/architecture.md`
state the qualification limits. Review acceptance uses a shared-git local receipt and the exact
published raw verdict; remote metadata is not authorization. Fallback and rebase-proof reuse
remain documented source capabilities that the shipped guard does not qualify. Installation,
production calls, and a complete remote lifecycle need captured evidence before they are claimed.
