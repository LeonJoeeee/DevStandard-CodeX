# 0000 — Record consequential architecture decisions

Status: Accepted (2026-10-03).

## Context

This repository adapts DevStandard into a Codex-only method. Its source decisions explain the
origin of the rules but are another project's history. This project's decisions need a separate
log that records what was actually accepted here.

## Decision

Start this project's ADR sequence at 0000. Record one decision and its real reasons when it touches
top-level design, scatters across the codebase, or is costly to reverse. Skip trivial, temporary,
or already-recorded choices. Claim the next number above every claim, including open work, and
record the claim in the PR. Never reuse a number or invent alternatives absent from the discussion.

Accepted bodies are immutable. Supersede a changed decision with a new ADR and update the old
status. Factual corrections or partial changes append dated amendments and update the status so
every amendment is discoverable. `reference/adr.md` owns the complete mechanics and template.
DevStandard's historical ADR files are not copied into this log; `docs/architecture.md` routes
source decisions to their operative Codex rules and records intentional departures.

## Consequences

Readers can distinguish adaptation sources from this repository's decision history. Existing
ADR 0001 is retained with a dated correction rather than rewritten; future changes receive new
numbers when this admission test fires.
