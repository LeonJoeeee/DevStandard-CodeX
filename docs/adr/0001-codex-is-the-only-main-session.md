# 0001 — Codex is the only main session, and every worker is its own built-in subagent

Status: Accepted (2026-09-29); Amended (2026-10-03); Amended (2026-10-04).

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


**Amendment (2026-10-04, human-approved Codex-only cleanup):** Every worker, reviewer,
helper and arbitration uses explicit `gpt-6.1-sol` at `high`. The earlier model-tier routing and
model/effort escalation are historical settings; unavailable settings are reported rather than
substituted. This does not change the main session's selected model or service tier.

The target no longer uses a second host's maintenance entry: applicable repository-only practices
move from the old target `CLAUDE.md` to `docs/maintenance.md`, with one pointer in `AGENTS.md`.
Operative pages and routing checks use only native Codex roles. Source filenames, old carrier
choices and provenance remain historical facts in the reconciliation, not execution instructions.
Host compatibility is qualified on explicit versions with actual role discovery, tool schema,
hook/context delivery and continuation evidence; an unknown version or a configured role is not
proof of runtime readiness. Session resume must recover complete operating context before task
actions. The exact qualified versions and remaining evidence limits belong in the harness and
architecture rather than being inferred from this amendment.


**Amendment (2026-10-04, target host qualification):** Current native role support is Codex
0.160.0 V2. Loaded roles expose the six-field spawn schema including `agent_type`; target probes
captured full worker/reviewer context bytes, explicit Sol/high, no conversation-history fork,
allowed `pwd`, worker merge refusal, reviewer write refusal and reviewer cross-role refusal.
The probe used a controlled provider and does not qualify production calls or a remote lifecycle.
The original 0.159.2 source record remains history rather than current support. Unknown versions
are not admitted by inference.

The project installer remains explicitly scoped by default. `--user` is a deliberate opt-in to
native roles in `~/.codex/agents` for new chats; unrelated settings and main-session choices are
preserved, and unowned collisions refuse. Native role discovery must precede dispatch. No
fallback registry keyed on `task_name` replaces the host's role identity. Resume, clear and
compaction claims require their own actual host evidence.


**Amendment (2026-10-04, explicit settings and production reviewer evidence):** Sol/high is
fixed for every child by default. A direct, specific human instruction overrides the global
setting only for its named dispatch; no automatic model/effort escalation or quota fallback is
introduced. Main-session settings remain untouched.

A production typed fresh reviewer call with its role-config layer explicitly active retained the
supplied prompt heading/end marker and omitted a parent-only token. The first discovery attempt
was blocked because that layer was inactive; it remains recorded rather than erased by the
successful call. This evidence does not establish user-scope discovery in all projects, worker
execution or a complete remote lifecycle. The current Codex loader supplies `PLUGIN_ROOT`;
package hooks consume that host key without the removed second-host compatibility fallback.


**Amendment (2026-10-04, native hook and shared-lane correction):** Lane receipts, ownership
locks and retained briefs are shared in the Git common directory across checkouts. Legacy local
receipts are imported only when uniquely consistent, with originals and hashes preserved; unknown
children and conflicting records still block reuse. Initial and continuation briefs remain raw,
and root record-language declarations are resolved before ownership changes.

SessionStart covers startup, resume, clear and compact, refuses insufficient configured part
capacity rather than delivering a partial page, and uses the Codex loader's plugin root. The role
hook recognizes actual native spawn aliases and command argv, including wrappers and absolute
paths, without scanning inert search prose as a command. Worker pushes require explicit remote
and branch targets. These are ordinary-path checks; arbitrary MCP/script writes, interactive stdin
and inherited parent permissions retain the declared limits. Live lifecycle qualification remains
separate from matcher and fixture checks.
