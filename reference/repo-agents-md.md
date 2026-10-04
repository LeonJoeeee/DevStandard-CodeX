# A lean repo-root `AGENTS.md` template

CI settles the project's commands — capture useful operational facts while they are fresh.
Generate a repo-root `AGENTS.md` when useful project instructions are admitted under
`reference/in-repo-writes.md`. Codex discovers this root entry natively; every worker also
reads it explicitly before task work. The operational template below aims to keep routine notes brief.

`AGENTS.md` is the Codex operational entry point. Preserve an adopted repository's existing
instructions and established operational sources: consolidate or point to an established fact,
never maintain competing copies. Repository-maintenance practices belong in the established
maintenance document, linked here when needed; they are not another agent-host entry point.
General collaboration is maintained in the method and delivered through hooks and native roles;
no permanent user-level `AGENTS.md` bootstrap is required. This project's generated operational
template suggests commands, environment gotchas, copy-list entries and record language. It is
not a universal host content restriction: preserve adopted instructions, human-authorized
project rules and established workflows, and do not delete them to satisfy this template.

- **Commands** — install, test, run (the same ones CI just encoded);
- **Environment gotchas** — ports in use, services that must be up, local-vs-CI differences;
- **Untracked files a new worktree must copy** — the allowlist `reference/orchestrator.md`'s Worktree lifecycle section copies from (nonconfidential local configuration only). Secret material is not copied into lanes;
  its established destination and access remain subject to `reference/where-it-goes.md`.

A cache or deploy root outside the tree is an environment gotcha of exactly this kind only when the
root itself already existed as an authority for this project's files or the human chose it. Recording
that place relays the authority so a clean-context worker does not invent another
(`reference/where-it-goes.md`); an `AGENTS.md` line added in the same change never authorises a root the
change invented. It belongs under Gotchas, not as a new kind of content.

One conditional fourth template item: a `## Record language` line, when the repo's durable record is not English. It sits here because a clean-context worker must see it natively; the reasoning behind the choice goes in that repo's ADR log, not here. Its absence means English.

A repo-wide language declaration in root `AGENTS.md` overrides the method's English default for the whole record,
never per file or per agent. State one language explicitly under `## Record language`, such as
`Chinese is canonical for code, documentation, commits, and GitHub records` or `记录语言：中文`.
An established non-English record earns that declaration: write it and follow the existing record,
never start a mixed record. A human-facing translation is a marked
mirror naming its canonical file and changes in the same diff as that file.

Generate it only when the project actually has some of that to say. A file that merely transcribes what CI already encodes, or that would stand empty under every heading with no record language to declare, is noise every later session pays to read — skip it, and let the first real command, gotcha, copy-list line or record-language declaration create it through the same write-back lane.

Write back useful operational facts through the project's normal change path. Aim for roughly
30 lines for newly generated operational notes; consolidate duplicate or obsolete facts as useful,
never drop effective project instructions merely to fit a number. Link architecture, decisions
and existing task records rather than duplicating them. Explicitly authorized project instructions
may need more space; the template is a suggestion, not an admission or review Floor.

```markdown
# <Project> — repo notes for agents

## Commands
- install: <command>
- test: <command>
- run: <command>

## Gotchas
- <port / service / local-vs-CI difference worth one line>
- <cache or deploy root already assigned to this project or chosen by the human, e.g. ~/.cache/foo or /srv/app — this line relays that place; it does not authorise a root this change invented>

## New worktree: copy these untracked files
- <path>   (or: none — everything load-bearing is tracked)

Architecture: see docs/architecture.md — never duplicated here. Decisions: docs/adr/ unless the architecture doc points elsewhere. Tasks: GitHub issues.
```
