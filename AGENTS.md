# codex-method — repo notes for agents

## Commands
- test: `python3 -m unittest discover -s tests -t .`
- routing check: `python3 .github/check-routing.py`
- command contracts: `scripts/dispatch --help`, `scripts/review-packet --help`, `scripts/guard --help`
- release lockstep: `python3 .github/check-release.py`
- ADR amendment check: `python3 .github/check-adr-index.py`

## Gotchas
- Python tests use the repository root as their import root (`-t .`); if inherited `CLAUDE_JOB_DIR` points outside writable roots, use `env -u CLAUDE_JOB_DIR TMPDIR=/tmp` for the test command.
- Native roles are discovered from target `.codex/agents/`; plugin hooks and skills use a separate package path.
- Existing `CLAUDE.md` holds repository-maintenance guidance; consult it for the wording-sweep command and record practices.

## New worktree: copy these untracked files
- None. Do not copy untracked local inputs or secrets into a new lane.

## Record language
- English is canonical for code, comments, documentation, commits, and GitHub records. Conversation follows the human; product text follows its audience.
