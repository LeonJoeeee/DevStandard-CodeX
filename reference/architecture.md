# How to write the architecture doc

Read this at project start, after the PRD. The architecture doc is the **shared baseline every parallel session works against** — it must stay correct, because people coordinate through it. It answers *how the project is structured*; the *why* behind each decision lives in ADRs. 1–3 pages, no more.

Use the requirements binding in `reference/orchestrator.md` for the design dialogue;
return here for this document's content and location.

## Sections

1. **Header rule** (verbatim): "Shared baseline for all parallel work. Read before any task. Changing anything here = touching the core: public merge + human approval + an ADR."
2. **Context** — what this system is and what it talks to (a paragraph; a simple diagram only if it pays for itself).
3. **Structure** — the level-1 picture: the main components/modules, what each owns, and the interfaces/boundaries between them. This is the map parallel tasks navigate by.
4. **Key quality goals** — the 3–5 properties that drive structural choices (e.g. latency, simplicity, portability). These are tie-breakers for future decisions.
5. **Document-location footer** — one line naming the ADR-log location this repository uses, by
   default: "Decisions and their reasons: `docs/adr/`." If an adopted repository's established
   convention keeps any method kind off its default path, declare that mapping in this same footer.
   This is the single pointer every canonical-path consumer follows.

## Rules

- **Altitude discipline** — the #1 staleness trap is detail creep. The architecture doc holds what is *slow-changing and cross-cutting*. Per-task design detail does not belong here; volatile reasoning goes to ADRs (append-only); implementation detail stays in code.
- **Update-in-same-change**: any merge that changes the structure updates this doc in the same merge (plus an ADR). A baseline that drifts from reality is worse than none — people build against it.
- **The doc states the stable present** — not history (that lives in ADRs and git), and not future promises or time-relative hedges ("currently", "for now", "temporarily", "until the migration lands"). Such lines read as true but go stale with no signal, misleading the parallel workers who build against this doc. A change that's coming becomes an ADR when it lands — never a promise written here.

## When the project outgrows one page: split on zoom

The overview stays THE single 1–3-page doc — it never grows past that. When one subsystem can no longer be explained legibly at the overview's altitude, extract **that subsystem only** into a child doc:

- `docs/architecture/<subsystem>.md` by default, or the established location an adopted repository uses, scoped to that subsystem and carrying the same header rule; the overview keeps a one-paragraph summary plus a link.
- Split along domain seams (a bounded context, a service, a business area) — never on a size threshold; zoom only the blocks that need it, never every subsystem to equal depth.
- Stop above the code: no class- or file-level docs — agents read the source on demand, and docs at that altitude are stale the week they're written.

## Template

```markdown
# <Project> — Architecture

> Shared baseline for all parallel work. Read before any task.
> Changing anything here = touching the core: public merge + human approval + an ADR.

## Context
<what this is, what it talks to>

## Structure
<components, ownership, interfaces/boundaries — the level-1 map>

## Key quality goals
1. <property> — <why it matters here>
2. <property> — <why it matters here>

Decisions and their reasons: `<decision-log-path>` (default: `docs/adr/`).
Other established method-document locations: `<kind>: <path>` (omit when every default applies).
```

Lands in the target repo as canonical `docs/architecture.md`; it is the entry point that declares any
established off-canonical locations, so its own path never yields (`reference/in-repo-writes.md`).
