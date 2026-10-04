# Working on codex-method itself

Repo ops for this repository only. Nothing in `reference/` points here, and no seeded project
receives it. The line that decides what belongs here: a method this project *ships* goes in the
shipped pages; a practice useful only for maintaining *this* project goes here.

**Never write the page total.** A change may state what it cost; it may not state what a page
measures afterwards. The CI-enforced ceiling is the only current figure a reader needs.

## Rewording a rule: search twice

Our product is prose, so nothing mechanical catches a stale statement. When you change wording that
exists in more than one place:

1. **Every other statement of the clause** — `reference/`, `docs/architecture.md`, and the ADR that
   recorded it.
2. **Every site that cites or paraphrases it**, found by *its pointer to the rule* — never by the
   words you just added. That half is the one that keeps being skipped.

Reconcile each in the same diff, or say in the PR description why it needs none. **Cite the rule,
not the line:** a `reference/orchestrator.md:NN` pointer is staled the moment anything above it
moves. **Record the ruling, not the tally.**

## Commands

```sh
python3 -m unittest discover -s tests -t .
python3 .github/check-routing.py
python3 .github/check-adr-index.py
python3 .github/check-release.py
rg -n '@[a-zA-Z0-9_-]*/' reference/ --glob '*.md'
# Native runtime gate: use an explicitly writable scratch root; local bind refusals are blockers.
python3 .github/test-native-runtime.py --installer scripts/install --scratch-root "$TMPDIR" --log-dir "$TMPDIR/native-evidence"
```

## Version bumps

Fold the lockstep bump into the change PR and put the semver call in its description. Every shipped merge, including a bare version bump, requires an exact accepted check-1
receipt and merged-result CI through `scripts/guard merge`. The source-only bare-bump waiver
is not implemented in this target.
