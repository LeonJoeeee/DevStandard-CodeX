# codex-method in native Codex

This page is the Codex mechanics delivered with `reference/worker.md` to a worker. The
orchestrator reads it when installing, dispatching, continuing, or recovering native roles.
The worker page owns the task contract; the filled review packet owns a reviewer's judgment.

## Qualified host and role delivery

The supported host is Codex **0.160.0**, native V2; the probes below qualify its mechanics.
Target probes
captured loaded role discovery, full worker/reviewer role bytes, explicit `gpt-6.1-sol`/`high`,
`fork_turns="none"`, allowed `pwd`, and ordinary worker merge, reviewer write and reviewer
cross-role refusals. A controlled provider establishes host mechanics rather than production
worker execution or uncoached compliance. A separate production Sol/high typed reviewer call with
an explicitly active role-config layer retained prompt heading/end marker and omitted a parent-only
token; an earlier inactive-config discovery block remains recorded. This establishes that call
rather than universal account access or user-level installation. The earlier 0.159.2 source
qualification is
historical evidence, not current support. Unknown versions refuse until explicitly qualified.

The legacy `.codex-plugin/plugin.json` package delivers hooks and skills. Project role files
under `.codex/agents/*.toml` are discovered separately; `scripts/install` generates the
`method_worker`, `method_reviewer`, `method_helper`, and `method_review_helper` roles for an
explicit project, or under `$CODEX_HOME/agents` (default `~/.codex/agents`) only with explicit `--user`. Installing a plugin
does not itself install those roles. User-level files do not guarantee discovery in every project;
verify the active role-config layer and target session. Role discovery precedes dispatch: native
V2 exposes
`agent_type` only when agent roles are loaded, and a new trusted session discovers installed
roles. Role files
carry `developer_instructions` only. The native call supplies model and effort explicitly;
Codex applies role settings after call overrides; omit model settings from TOML and state the
default `gpt-6.1-sol`/`high` explicitly in every native child call, unless a direct, specific human
instruction overrides its named dispatch. Role files do not supply effective per-role `cwd`, sandbox,
or hook settings. Child permissions and cwd are inherited from the
parent. The package hook resolves from the host-provided `PLUGIN_ROOT` and uses actual `agent_type`
with a structured deny. Native role files cannot install hooks. SessionStart matches startup,
resume, clear and compact; too few configured handlers stop before delivering a partial page.
Capture live context for each lifecycle claim rather than inferring it from those matchers.

The worker role's instructions carry this page and `reference/worker.md`; its spawn message
carries the freshly assembled task packet. Helpers receive their narrower task and applicable
role boundary. Reviewer roles receive a nonediting contract and the complete current packet,
with no implementation skills. A child receives neither the main session's conversation nor
an assumed startup delivery of the orchestrator page.

## Native V2 invocation

Prepare the worker receipt with `scripts/dispatch`, or the gating-review receipt with
`scripts/review-packet start` under the orchestrator's **Review packets** section. Pass the
returned instruction's complete message and exact settings to the native tool. This is the
qualified argument shape, shown as data:

```json
{
  "task_name": "issue_123_worker",
  "message": "<complete dispatcher brief>",
  "agent_type": "method_worker",
  "fork_turns": "none",
  "model": "gpt-6.1-sol",
  "reasoning_effort": "high"
}
```

Gating review uses `method_reviewer`; a fresh design challenge or pre-PR arbitration uses
`method_review_helper`. Ordinary task helpers use `method_helper`; a reviewer's helpers keep
`method_review_helper` and the caller's nonediting restriction. Every helper uses explicit `gpt-6.1-sol` at `high`
under the supplied `Helpers:` binding. Do not add `cwd`, `hook_settings`, `prompt`,
`subagent_type`, or `run_in_background` to this V2 call.

A prepared receipt is not a launched child. Record the actual returned native handle with its
issue and lane; observe native completion before reuse or cleanup. Read the child's full
return. The dispatcher cannot attest a handle it did not observe. A live or uncertain child
blocks a second writer. Lane receipts and retained briefs are shared across checkouts in the Git
common directory under `codex-method/lanes`. An older run keeps its observed version; preparing a
current-version child requires fresh actual completion evidence for the old handle and current
host qualification. Conflicting legacy receipts are preserved and refused, not overwritten. If a requested model, effort, role, or native tool is unavailable,
report the limitation; model availability and quota never silently change the setting or gate.

## Worktree and permission boundary

A child starts in the parent's directory. Its worktree path is an instruction, **not cwd
isolation or a new OS sandbox**. Before any task write, validate the exact recorded branch,
linked-worktree identity, and named base under the worker page; run commands with that
worktree explicitly selected. Parent permission grants may reach other lanes and shared git
metadata; the assigned-lane restriction remains a role obligation.

An independent native reviewer means a fresh context (`fork_turns="none"`), a nonediting
contract, and the ordinary-path role hook. It does **not** mean an OS-enforced read-only child.
The host's inherited sandbox still applies. The hook's full rules and exclusions live in
`reference/orchestrator.md`'s The role hook section. Do not describe same-credential malicious
agent containment or arbitrary MCP-write isolation as a property of this arrangement.

## Continuation and binding recovery

The native handle lives in its spawning session's agent tree. `dispatch --continue` prepares a
fresh child identity in the existing lane; it is not a native handle-resume command. For a retained
child, freshly fetch the issue/ordered comments and current authorized continuation, deliver that
self-contained brief yourself, and keep observing the original recorded handle with
`dispatch ISSUE --record-status <actual-list-agents-capture> --host-version 0.160.0`.
Continue a stopped child with
`followup_task` on that actual handle, carrying the newly fetched continuation brief. Inspect
native status first; messages to a live child steer that child and do not license another writer.
A retained stopped handle is preferred because it retains context. With no recoverable handle,
first establish that the old child cannot still write, then create a fresh child for the same
lane with the full role and refreshed packet. An uncertain lifetime remains blocked.

After compaction or loss of binding, stop task writes. Ask the orchestrator on the actual
native channel to resend the exact original packet and current authorized continuation,
including issue, branch, worktree, named base, Bounds, Done-check, and method root. Match all
identities to the recorded lane and reread the role sources. A caller's cwd, a guessed issue,
a partial checkout summary, or a different lane's receipt does not recover this binding.
If that exact carrier cannot be recovered, return the gap; do not reconstruct authority from
memory. This route makes no promise about persistence across restarted sessions.

For a required refused action, return the exact refusal, act, target, next step, and clean-point
snapshot under `reference/worker.md`'s Required tools and refusals. The orchestrator performs
an authorized act only through its own admitted path, then sends its result and continuation
to the retained child. If its own path is refused, it reports the limitation to the human.
Neither role loosens permissions, bypasses a hook, or copies secrets to make the action work.

## Qualification limits

The 0.160.0 target probes qualify loaded role discovery, native schema, child role context and
ordinary-path denials described above. The separately captured production reviewer call qualifies
that call only. These probes do not prove universal account access, user-level installation, main
startup/resume/clear/compaction delivery, persistent native continuation after restart, live GitHub
review publication, protected integration, or uncoached compliance.
Validate those properties on the explicit target; keep captured evidence distinct from fixtures
and from DevStandard's historical cross-host probes. See `docs/architecture.md` for source
routing and deferred capabilities. General host guidance is in the
[official OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents);
the version-specific target qualification governs the contract here.
