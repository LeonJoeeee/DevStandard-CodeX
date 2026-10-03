# 0001 — Codex is the only main session, and every worker is its own built-in subagent

Status: Accepted (2026-09-29).

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
