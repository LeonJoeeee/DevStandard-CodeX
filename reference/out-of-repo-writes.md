# Writing outside the repository

Most work ends in the tree. Some work must not: secrets, live application state, and release
deliverables. This page owns where those go, what the declaring root requires, and what must be
disclosed when they are written.

## The three expensive kinds

1. **Secrets and credentials** — never in the tree, never in a commit message, never in an issue or
   PR body. They go to the destination the human authorized in words. Without one, the work stops
   and reports the missing destination; it does not invent one.
2. **Application and service state** — a database, a bucket, a queue, a running service. Writes here
   change what other people see. They need the same authorization as a production change, and a
   declared root: the one directory or namespace this task may write, named before the first write.
3. **Release deliverables** — tags, published artifacts, package registry pushes. These are
   irreversible and outward-facing. Release is the human's call unless they delegated it in words.

## The cache arm

A cache is neither of the first two: it can be rebuilt from the repository. Writing to one needs no
authorization, but it needs a declared root like everything else here, so a task cannot scatter
caches across a home directory.

## Retention

Anything written outside the repository is either (a) durable state the human owns — say where it
is and how to undo it — or (b) disposable. Disposable artifacts are removed when the task ends and
their ownership and disposability are established. A sole durable copy is never deleted.

## Disclosure

Every out-of-repository write is named in the PR description: what was written, where, under whose
authorization, and how to undo it. Silence about an out-of-tree write is a defect the reviewer
raises under Floor 2, because the next session cannot see it and cannot clean it up.

## Where a rule lives

Placement for anything in the tree is `reference/where-it-goes.md`. Task-state that belongs on an
issue or PR is never an invented handoff file.
