# codex-method — repo notes for agents

## Commands
- test: `python3 -m unittest discover -s tests -t .`
- routing check: `python3 .github/check-routing.py`
- command contracts: `scripts/dispatch --help`, `scripts/review-packet --help`, `scripts/guard --help`
- release lockstep: `python3 .github/check-release.py`
- ADR amendment check: `python3 .github/check-adr-index.py`

## Gotchas
- Python tests use the repository root as their import root (`-t .`); choose an explicitly writable scratch root for native runtime probes.
- Native roles are discovered from target `.codex/agents/`; plugin hooks and skills use a separate package path.
- `docs/maintenance.md` is the repository-maintenance authority; consult it for wording sweeps and record practices.

## New worktree: copy these untracked files
- None. Do not copy untracked local inputs or secrets into a new lane.

## Record language
- English is canonical for code, comments, documentation, commits, and GitHub records. Conversation follows the human; product text follows its audience.
