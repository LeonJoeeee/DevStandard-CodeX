# The repository's operational memory

`AGENTS.md` at a repository root is that project's operational memory: what a later session needs in
order to work there without rediscovering it. It is the one file a reader opens before touching the
tree.

**It accepts only these four kinds of content.** Anything else belongs on a shipped page, in an
issue, or in a PR description:

1. **Commands** — how to build, test, lint, and run this project's own gates.
2. **Environment gotchas** — the facts a session would otherwise burn a turn discovering.
3. **Worktree copy-list entries** — untracked inputs a new worktree may copy, named explicitly. A
   missing list means no copy.
4. **Record-language declarations** — when a record is not in English, and which.

Nothing method-shaped lives here. A rule about how work is organized is a method rule and goes on a
shipped page; `AGENTS.md` is a project's memory, and a project is not a method.

**Naming.** The file is `AGENTS.md`, because Codex reads that name. A project that keeps both a
`CLAUDE.md` and an `AGENTS.md` has two memories that drift; keep one.

## What it is for

A worker arrives to a checkout with a brief and a role. It reads this file first, then the method
pages its brief names. This file answers "how does *this* repository work", never "how does the
method work".

## Placement

Every reference-page rule about where a file goes still applies; see `reference/where-it-goes.md`.
This file goes at the repository root, and its presence is optional: a project with nothing to put
in it omits the file rather than shipping an empty one.
