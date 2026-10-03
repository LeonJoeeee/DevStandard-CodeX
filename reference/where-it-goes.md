# Where every file goes

Read this before choosing a destination for a file the work will write. This page is the entry point
for placement: **it does not classify files and is not a decision procedure.** It states one rule,
closes the ordinary case with a default, and names only the cases where that default is expensive.

## Why there is no taxonomy

Three taxonomies were built and each failed in a way the next reproduced. An ordered list put its
catch-all before a specific row, so model weights took the catch-all. Two questions with no precedence
let the output question overlap every other kind, so a service's data could take the project-local
default and die with a worktree. Roles that bind broke when a release archive containing a private key
matched both *release: publish* and *secret: never publish*; a file cannot be forced to have only one
role. Their common cause was trying to build a complete decision procedure over an open-ended set —
the shape issue #173 records and the human ruled out on 2026-08-29. The rule below instead decides the
common case, closes with a default, and names only the three kinds where taking it is expensive.

## The placement rule

<!-- BEGIN PLACEMENT RULE -->
**Put every file where something that ALREADY EXISTED puts it** — code or configuration that writes
there, a tool's documented default, the repo's own docs relaying one of those, or a place the human
chose.

**This rule is about where YOU write while doing the work.** It is not about where the software you are
building writes for its users: a product's own output paths — a CLI's `--output`, an app's export
directory, a service's configured data root — are part of its interface, designed and reviewed as
design, and the same-change code that defines them is the authority for them. Do not route a product's
user-facing output into the development repository.

**The boundary is the interface, not the run.** Designing a CLI's `--output` is product design;
**exercising it while you work — choosing the concrete path you actually write to, or the host
directory a Compose volume lands in — is your own write and takes this rule**, including its ask-kinds.
A same-change Compose file naming `./data` authorises the design, never the host destination you point
it at.

**What must already exist is an authority that puts THIS project's files there, not merely the
directory**: a `/srv/app` that happens to exist authorises nothing — it may be another service's, and
a second one writing into it intermingles or overwrites durable state. What this same change added names nothing: a config file, workflow or Compose
file this diff introduces cannot authorise its own destination. **A document relays authority, never
originates it** — a design spec, an issue or a note counts when it repeats a destination the human
chose or one that already existed; a destination it invents counts for nothing, including in a spec
written for this very task. **Neither does a handoff or session-state document** — inherited,
tracked, or admitted at a human's request: such an artifact never names a destination, whatever its
own standing. (`reference/in-repo-writes.md` governs whether it may exist at all; this governs
whether it may point anywhere, and the answer is no.)

**Nothing names a place? Put it inside the project** — in a gitignored directory when it is not
material the repo maintains — and **never invent a place outside it**: not under `$HOME`, not on the
Desktop, not an absolute path like `/opt/x`. Judge it yourself; you do not need a rule for every kind
of file, and a file that dies with the task belongs in your session's scratch or one `mktemp -d`.

**Three never take that default**, because a wrong answer costs more than a stray file. Where nothing
already names a place for one of these, ASK — a worker stops and tells the main session, the main
session asks the human:
- **a secret or confidential data** — a key, a token, a credential, including one your task
  generates; and data that must not spread: a production export, personal data, a licensed corpus.
  Never committed, never published, **whatever else is true of the file it sits in** — and note that
  the project-local default is not containment: `.gitignore` is not `.dockerignore`, and an ignored
  path is still copied by an image build or an archive;
- **application state, persistent or operational** — a service's, and equally a desktop app's or a
  CLI's autosave, history or local database; and the runtime files a program must be able to create
  to run at all: a socket, a PID file, a lock file, a spool — **for a program that outlives your task.
  A test daemon's socket, thrown away with the task, is not this: that dies with the task and belongs
  in scratch.** A project-local gitignored path dies with
  the worktree, a package replacement or a read-only install loses the first kind, and a read-only
  installation cannot create the second at all;
- **a release deliverable** — never committed as a by-product, never merely attached to an issue.

**Say where it went.** This is about artifacts, not about your work: a file you committed is safe in
the branch. **"Inside the project" means the repository you are working in — a disposable worktree is
not a durable place**: a worktree is deleted when its task ends, and a gitignored path in one is
invisible to `git status --porcelain -uall`. A kept file whose only durable copy is inside the
worktree is disclosed and resolved before teardown under your role page's The tree you hand back section, and every
durable write outside the repo is disclosed under `reference/out-of-repo-writes.md`; those pages own
what the disclosure says and when. What this rule decides is the case they cannot: if it must
outlive the task and the only place you have is a worktree — **or any other destination that does not
promise to keep it, an evictable tool cache included** — you have nowhere to move it to: stop and tell
the main session (a worker), or ask the human (the main session), before teardown rather than after.
A downloaded corpus that must be kept is the standing example: the tool's cache is the right place for
a re-fetchable copy, and the wrong place for the only one.
<!-- END PLACEMENT RULE -->

For the declared-root requirement for service state, the cache arm, retention, and disclosure details
of the three expensive kinds, continue to `reference/out-of-repo-writes.md`.

## Worked examples

- Committing a generated `results.json` does not make it material the repo maintains; deciding to
  commit it cannot authorise the repository as its destination.
- A coverage report shown once dies with the task and belongs in scratch. The same report, when it
  must be retained, does not belong in scratch and takes the durability rule above.
- Model weights use the tool's documented cache whenever one exists, whether they serve many tasks or
  one. With no documented cache, weights fetched for one task go to scratch; weights that must be kept
  take the durability rule and its ask.
- Generated prose a human can read is still documentation, so `reference/in-repo-writes.md` governs
  whether it may be added to the repository.
