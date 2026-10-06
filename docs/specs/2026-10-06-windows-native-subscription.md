# Windows native-subscription installation and qualification

Status: accepted by the human on 2026-10-06

## Goal and authorization

Continue DevStandard-CodeX development and install it on the user's Windows computer with substantial repeatable testing. The user chose the GitHub mainline gpt-6.1-sol/high native child route and clarified that the previous DeepSeek changes were an abandoned experiment. Keep the user's main-session model and service tier. The user explicitly authorized all project operations, including issues, PRs, and merges, and selected global common rules for all Codex chats. Ordinary tasks still use their task contract; the GitHub lifecycle applies when the task calls for repository collaboration. Windows is temporary and the intended long-term environments are Linux and macOS. Preliminary research and discussion are complete; the human explicitly requested installation, adaptation, debugging, tests and fixes. Existing quality and review gates still apply.

## Current evidence

The desktop uses Codex 0.160.1. Existing scripts only admit 0.160.0. Four user roles are discovered, but the plugin is absent from the installed/enabled inventory and actual hooks/list returns zero hooks in both the current chat and source checkout. The existing Windows prototype has portable locks and hook entry points, but also stale DeepSeek anchors. Nine routing checks and six manual hook probes pass. The first Windows suite log records 271 test methods, 123 failures and 144 errors (including subtest outcomes); fixture executable resolution selects the real gh rather than the intended test double. Further whole-suite runs are held until that boundary is repaired. Script-only probes also show git.exe merge/commit and PowerShell Set-Content are admitted where the corresponding worker/reviewer operations should be denied. These probes do not execute the represented commands or establish actual host enforcement. Strict-config startup accepts both legacy V2 and native agents declarations on 0.160.1; the exact-version refusal alone does not prove broad API incompatibility.

## Options

1. Qualify and support the actual Windows desktop version, preserve Unix behavior, restore GPT routing, and install through the real plugin facility. Selected recommendation: addresses the environment the user actually uses.
2. Pin a separate old 0.160.0 CLI. This would leave the current desktop entry unresolved and split the installation target.
3. Install cached files without qualification. Rejected because cache presence does not establish enabled hooks, role settings, or usable commands.

## Platform-priority discussion update

Use a shared portable core with Linux as the full-suite CI baseline, macOS qualification before making support claims, and necessary Windows runtime/installation and role-policy coverage for the temporary host. Global context delivery needs neither an Actions runner nor a port of every Unix test fixture. Comprehensive testing remains required for changed core behavior. Windows tests must fail closed at the fake GitHub boundary; do not claim that unexecuted Unix fixtures passed on Windows.

## Design

Retain the current Windows prototype as recoverable Git history and work on a new development branch in the existing checkout. Restore only the abandoned DeepSeek routing edits to the mainline model/effort; retain useful Windows changes. Consolidate exact supported host versions in one shared definition; add 0.160.1 only with captured native qualification and reject unknown versions. Observe actual versions rather than reporting 0.160.0 for the new host. Use the actual supported configuration schema, preserving unrelated user settings.

Keep the synchronous whole-context SessionStart handler and the role-specific PreToolUse policy. Windows selects the Python entry and correct native executable invocation; Unix keeps its existing behavior. Do not loosen review, scope, merge, or hook gates to make tests pass. Standardize explicit UTF-8 boundaries and platform-specific process/pipe handling where failures demonstrate the need.

Repair test consumers so fixture commands cannot reach real GitHub. Fail closed if the intended executable is not selected. Existing lifecycle tests continue to use their stateful GitHub double and real local Git. Add Windows coverage for delivery, role refusal, file locks, executable selection, settings preservation, collisions, and host-version refusal. No remote fixture metadata may stand in for a real production result.

Before installation, retain a timestamped user-config/role backup and hashes. Register the local plugin through codex plugin marketplace add and codex plugin add; inspect the real engine's hook definitions and persist trust for their exact current hashes through the supported host path after reviewing the scripts. Install current roles, confirm plugin inventory and trusted hook discovery, and leave main settings intact. Do not claim the existing chat's model-visible context reloaded merely because files changed.

## Validation and completion checks

- The full existing unit/lifecycle suite passes on Linux CI. Windows critical tests cover the installed entry points, complete UTF-8 delivery, refusal paths, ordinary role boundaries, locks, host versions, configuration preservation and installation collisions. Fixture executable selection never falls through to real GitHub; targeted failures reproduce before repairs.
- Release descriptors, routing, ADR checks, and documentation links pass; Unix coverage remains via the existing Linux CI path and any locally available compatible environment.
- Actual Codex 0.160.1 native controlled-provider qualification captures full root context, native typed role discovery, explicit GPT/high settings, fresh children, allowed reads, ordinary worker/reviewer denials, completion, and retained-handle continuation. Synthetic provider evidence is labeled as mechanics qualification.
- A fresh authenticated native-subscription smoke test separately captures real GPT operation and method role behavior, without an API key, DeepSeek provider, or silently substituted settings.
- A clean installation/check and repeated installation preserve unrelated configuration; the engine lists the enabled plugin and trusted hooks in the intended directories.
- Independent review checks the final diff and evidence. Prepare reviewable commits and PRs and integrate only after the project's exact acceptance and CI gates pass, within the user's explicit project authorization and the discussed scope.

## Records and limits

Use this repository's docs/specs and existing architecture/ADR conventions, not a competing handoff hierarchy. Retain complete logs in task work and concise reports in task outputs. Report failed, blocked, and unexecuted checks explicitly. A broad ongoing development request does not define every future product feature; this first deliverable is the native Windows installation and qualification baseline.
