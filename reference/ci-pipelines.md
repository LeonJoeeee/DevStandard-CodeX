# CI, the release pipeline, and keeping them current

Read this at project start, after the skeleton exists. Two robots, generated once — then they age with GitHub, not with the project:

- **CI** — runs the tests on every push/PR. The rule it enforces: *nothing merges to main unless tests are green.* With parallel sessions sharing main as their foundation, this gate cannot rely on anyone remembering to run tests.
- **Release (CD)** — every project must ANSWER the release question: *what does "shipping" mean here?* A service → deploy; a tool/library → publish a package; a plugin → publish to its marketplace/repo. Default trigger: **a version tag** — pushing `vX.Y.Z` releases automatically; the human decides when to tag. Fully-automatic release-on-merge is a per-project opt-in, not the default.

Adapt the templates to the project's language/toolchain (swap the test command and the release steps). Keep each file minimal — these are gates, not build systems.

## CI template (`.github/workflows/ci.yml`)

```yaml
name: CI
permissions:
  contents: read
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - name: Bind this checkout to the advertised PR merge result
        if: github.event_name == 'pull_request'
        env:
          EXPECTED_BASE: ${{ github.event.pull_request.base.sha }}
          EXPECTED_HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          test "$(git rev-parse HEAD^1)" = "$EXPECTED_BASE"
          test "$(git rev-parse HEAD^2)" = "$EXPECTED_HEAD"
      # <language setup step here, e.g. actions/setup-node / setup-python>
      - name: Install
        run: <install command>
      - name: Test
        run: <test command>

  merged-result:
    name: merged-result / ${{ github.event.pull_request.base.sha }} / ${{ github.event.pull_request.head.sha }}
    if: github.event_name == 'pull_request'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "this exact merge of base and head passed the test job"
```

The CI token only needs to read the code; a job that must write (like the release template) escalates its own permissions per-job.

**The `merged-result` job is not optional, is not a protection context, and is not renameable.** `scripts/guard merge` requires it by that exact name on the PR head, so a project without it cannot merge through the guard at all (`reference/orchestrator.md`'s Guarded operations section). Its name changes with every base and head, and the guard verifies the check producer is GitHub Actions app id `15368`,
so it can never be a required status check — protection requires `test`, and the guard requires this. `needs: test` is what makes it report only for a merge result whose tests passed; `fetch-depth: 2` is what lets the binding step read the merge commit's two parents. Ship the job under the name the template gives it.

Third-party (non-`actions/*`) actions: pin to a full commit SHA, not a tag — a tag can be rewritten under you (the 2025 tj-actions compromise; SHA-pinned repos were immune). First-party `actions/*` at a version tag is fine. A SHA never updates itself — that is exactly what the Dependabot file below keeps current.

Artifacts: upload one only when a later step or a person actually consumes it, and always set `retention-days:` — the default keeps every copy for 90 days, and on a private repo the 500 MB storage quota fills in days of routine pushes, after which uploads start failing. CI output is not an archive: actual release deliverables ship through the release pipeline; a report worth retaining goes where `reference/where-it-goes.md` sends it rather than being published merely to keep it, and any build can be reproduced from its commit.

Minutes are the other finite quota, and the one that stops everything: on a private repo an exhausted monthly balance runs *no* workflow at all — CI, release and Dependabot alike — so the merge gate goes absent rather than red (a public repo's standard runners are free, so this cannot happen there). Treat exhaustion as a pipeline-spend bug before an allowance problem; the usual causes are cheap to fix — a job triggering on every push to every branch when `pull_request` alone would do, a matrix kept wide out of habit, no dependency cache so every run re-downloads the world, no `paths:` filter so a docs typo rebuilds everything, no `concurrency:` group canceling superseded branch runs, and the default 6-hour `timeout-minutes` letting a hung job burn an afternoon. Fix the spend, and tell the human the balance is out — topping it up, or making the repo public, is theirs. `reference/ci-cannot-run.md` preserves a separate degraded local merge-waiver design; its CLI
route is unqualified. Use the safe self-hosted Actions route below before waiting when authorized.

The minimal template above includes none of these controls; add the language setup action's `cache:` input, job-level `timeout-minutes:`, `on: pull_request: paths:`, `strategy: matrix:`, and a top-level `concurrency:` group.

## When hosted CI cannot start

When hosted CI fails before workflow steps, first inspect the check annotations or provider
status. Distinguish quota, billing, spending-limit and runner-capacity refusal from code or test
failure. A workflow that began and failed, a queued run and a platform startup refusal need
different remedies; never label infrastructure refusal a test failure.

If GitHub Actions cannot run because hosted allowance or paid capacity is unavailable, and the
already-authorized local machine can safely execute the workflow, run equivalent CI using
temporary self-hosted runners rather than stopping at the hosted error. Existing authorization
suffices within its bounds. Self-hosted Actions still produce ordinary Actions checks and keep
review, protection and exact merged-result gates; this is not `guard --ci-fallback` or its
unqualified degraded local merge waiver. Provisioning outside existing authorization returns
the concrete action and impact to the human.

Prefer registration only to the current repository and ephemeral runners, one job then exit,
with isolated work directories, least permissions and only necessary credentials. Supply fresh
runners for each required job or matrix member. Retain logs; afterward remove registrations,
credentials and disposable work directories, preserving retained evidence first. Keep a
persistent runner only when the human explicitly requests it, with its state risk disclosed.

Never execute untrusted fork or PR code on a local runner that can reach personal files,
LAN services, credentials or production systems. Use an isolated disposable environment for
untrusted code; if one is unavailable, explain why self-hosting is unsafe. A different working
directory is not OS or network isolation. Judge code trust and reachable resources for both
public and private repositories; repository visibility alone does not establish safety.

Match the original workflow's toolchain, dependencies, commands, environmental constraints and
build/test matrix wherever possible, including the exact merge-result identity. Record
unavoidable differences. Attach results and retained logs to the PR or established handoff
record, preserve hosted infrastructure-failure records, and label this fallback validation.
Do not relabel it as the degraded `CI-FALLBACK` merge waiver.

If safe self-hosting is unavailable, complete every safe feasible equivalent local check and
record the exact blocked jobs, environment and reason. Those results do not establish green CI.
Do not weaken protection or merge without explicit human acceptance of remaining risk and an
integration path that actually permits it; this shipped guard still refuses the unqualified
waiver. A self-hosted job queued behind an offline runner is still a run, not a provider outage;
inspect actual runner/job status and restore the authorized runner path or report the blockage.

Branch protection is the LAST founding step: `guard protection --apply --check test` names the contexts on the command line, repeating `--check` once per name, and refuses with none rather than PUT an empty list. The role hook does not gate it (`reference/orchestrator.md`'s Guarded operations section); it is the human's or the main session's command by role instruction and by who holds admin credentials. `reference/prd.md`'s setup sequence has the order; `reference/orchestrator.md`'s Branch protection section has the payload. Enabling it turns the rule into a hard gate, and three settings make that gate real:

- **"Require branches to be up to date before merging"** — green on a stale base is not green on main. Guard binds CI to the current base/head and requires fresh check 1 by default. `reference/orchestrator.md`'s Merge and rebase proof section and `reference/acceptance-reuse.md` define explicit actual-replay proof of unchanged reviewed substance; diagnostic `compare` grants no acceptance. Every selected reuse still requires fresh exact merged-result CI. **Leave GitHub's merge queue off** — all of it, not only the kinds that rebase; `reference/orchestrator.md`'s Branch protection section says why, and `guard protection` reports an enabled one.
- **"Do not allow bypassing the above settings"** — without it, admins are exempt, and in a solo setup every agent session runs on the owner's admin credentials.
- Know your plan: protection may be unavailable on free-plan **private** repositories. The shipped guard has no plan-limit waiver and refuses unreadable protection or active rules. Report the exact platform limitation; `reference/orchestrator.md`'s Branch protection section owns the refusal and provisioning boundary.

Protection changes only who enforces the ceremony, not the ceremony itself. Use your role page's two-checks paragraph for review and CI, and the documented source-exception limits; the shipped guard has no bare-version waiver. Required status protection makes GitHub enforce the CI portion and nothing else — what it leaves open, and the role guards and reviewed-head merge route that cover it, are in `reference/orchestrator.md`'s Guarded operations section.

## Pipeline pin upkeep (`.github/dependabot.yml`, generated in the same setup step)

The pipeline's own parts — the `uses:` pins in these workflows — rot on GitHub's clock, not the project's: actions age out of support and a SHA pin never updates itself. Generate this file in the same setup step; a bot then opens PRs bumping those pins as new versions land, and each rides the normal two checks like any other change. This keeps the pipeline's own actions current only — the project's own dependencies stay out of the method's scope (that ruling stands, now narrowed to say so explicitly).

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

## Release template (`.github/workflows/release.yml`)

```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      # <language setup + install + build steps>
      - name: Test
        run: <test command>          # green tests gate the release too
      - name: Publish
        run: <publish/deploy step>   # gh release create / npm publish / deploy ...
```

If the project genuinely has no release form yet, generate CI only and record the open release question in the PRD's constraints — don't invent ceremony.

Both files land in the target repo under `.github/workflows/`.

The same setup step also generates the repo-root `AGENTS.md`, when the project has anything to put in it — `reference/repo-agents-md.md` (the Codex operational entry point). The same founding commit also seeds the in-repo worktree root into `.gitignore` (`/.codex-method/worktrees/`) — the line every later worktree creation checks for (`reference/orchestrator.md`'s Worktree lifecycle section, Birth).

## When CI goes red with no change of yours

A green run means the code passed today, not that the pipeline is current. GitHub ends-of-life the runtimes its actions run on, on its own cutoff dates — so a pipeline with zero project changes can go from green to red, usually after months of deprecation-warning annotations inside still-green runs. If a gate goes red mid-task with no relevant change of yours, suspect a vendor deprecation before your own code; when a task already touches a workflow file, bump any `uses:` the run flags as deprecated in the same diff.

Provisioning/check commands and the exact protection payload live in `reference/orchestrator.md`'s Guarded operations section.
