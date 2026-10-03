# codex-method

A development method for a **Codex main session**. It adds the three things an agent harness
doesn't do by itself:

1. **A durable task record** — a GitHub issue with `## Goal`, `## Bounds` and `## Done-check`, so
   the work is judged against what was asked.
2. **An isolated lane** — one task, one branch, one worktree, one accountable writer, with a PR
   that carries the evidence.
3. **Two gates before integration** — an independent read-only review (Goal and two Floors), and
   green CI for the exact merge result. `scripts/guard` is the only merge entry point.

The orchestrator page is the complete instruction: [`reference/orchestrator.md`](reference/orchestrator.md).
The worker's contract is [`reference/worker.md`](reference/worker.md); the review contract is
[`reference/code-review-prompt.md`](reference/code-review-prompt.md).

## What it is not

This is not a port of another method's files and not a second host for one. It is its own method,
written for Codex from the first line. There is no cross-host executor: every dispatched worker is
Codex's own built-in subagent, and a helper a role spawns is one too.

## Requirements

- **Codex**, with plugin and SessionStart-hook support. It is the only main session.
- **[superpowers](https://github.com/obra/superpowers)** — the craft layer. The role pages point at
  its requirements, debugging, TDD and planning skills; install it into Codex.
- **Python 3.9+, `git`, and an authenticated [`gh`](https://cli.github.com/)** for the shipped
  commands.
- On Linux, Codex's [sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing#prerequisites)
  (`bubblewrap`, and where required its scoped AppArmor profile).

## Model and effort

Anchored for the two roles, routed for helpers, one statement on the dispatch page:

| Role | Model at effort |
|---|---|
| worker | `gpt-6.1-sol` at `high` |
| reviewer | `gpt-6.1-sol` at `high` |
| arbitration (a genuine dilemma, an irreversible judgment, an architecture-level acceptance) | `gpt-6-astra` at `max` |
| helper — decides a merge or a design | `gpt-6-astra` at `high` |
| helper — ordinary judgment | `gpt-6.1-sol` at `high` |
| helper — mechanical work | `gpt-6-luna` at `max` |

## Commands

```sh
scripts/dispatch 123 --purpose worker --base origin/main
scripts/review-packet start 124 --issue 123 --architecture-level no --output <scratch>
scripts/guard merge --repo OWNER/REPO --pr 124 --project CHECKOUT
```

`--help` on each carries its full contract and refuses rather than guessing.

## Checks

```sh
python3 -m unittest discover -s tests -t .
python3 .github/check-routing.py
```
