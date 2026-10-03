# codex-method in native Codex

This page is the Codex mechanics delivered with `reference/worker.md` to a worker. The
orchestrator reads it when installing, dispatching, continuing, or recovering native roles.
The worker page owns the task contract; the filled review packet owns a reviewer's judgment.

## Qualified host and role delivery

The version-specific baseline is Codex **rust-v0.159.2**. Source qualification established
`gpt-6.1-sol` with `high` effort in its model metadata and V2 as its default collaboration
protocol. Metadata presence does not establish an account's access or a successful production
model call. Installation and live behavior must be demonstrated for the actual target.

The legacy `.codex-plugin/plugin.json` package delivers hooks and skills. Project role files
under `.codex/agents/*.toml` are discovered separately; `scripts/install` generates the
`method_worker`, `method_reviewer`, `method_helper`, and `method_review_helper` roles for an
explicit target. Installing a plugin does not itself install those project roles. Role files
carry `developer_instructions` only. The native call supplies model and effort explicitly;
Codex applies role settings after call overrides, so fixing them in TOML would silently undo
arbitration or helper routing. Role files do not supply effective per-role `cwd`, sandbox,
or hook settings. Child permissions and cwd are inherited from the
parent. The package-level hook uses the actual `agent_type` payload and a structured deny.

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
`method_review_helper` and the caller's nonediting restriction. Choose helper model and effort
from the supplied `Helpers:` binding. Do not add `cwd`, `hook_settings`, `prompt`,
`subagent_type`, or `run_in_background` to this V2 call.

A prepared receipt is not a launched child. Record the actual returned native handle with its
issue and lane; observe native completion before reuse or cleanup. Read the child's full
return. The dispatcher cannot attest a handle it did not observe. A live or uncertain child
blocks a second writer. If a requested model, effort, role, or native tool is unavailable,
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
`dispatch ISSUE --record-status <actual-list-agents-capture> --host-version 0.159.2`.
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

Source inspection qualifies the schema and inheritance statements above. It does not prove
installed hook delivery, whole-context arrival, native continuation after restart, live GitHub
review publication, protected integration, clear/compaction behavior, or uncoached compliance.
Validate those properties on the explicit target; keep captured evidence distinct from fixtures
and from DevStandard's historical cross-host probes. See `docs/architecture.md` for source
routing and deferred capabilities. General host guidance is in the
[official OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents);
the pinned source qualification governs the version-specific contract here.
