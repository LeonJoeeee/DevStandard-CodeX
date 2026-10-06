# codex-method in native Codex

This page is the Codex mechanics delivered with `reference/worker.md` to a worker. The
orchestrator reads it when installing, dispatching, continuing, or recovering native roles.
The shared agreements own general collaboration; the worker page owns its lane contract and
the filled review packet owns formal PR judgment. Task-local helpers keep their caller's contract.

## Qualified host and role delivery

The supported host is Codex **0.160.0**, native V2; the probes below qualify its mechanics.
Target probes
captured loaded role discovery, full worker/reviewer role bytes, explicit `deepseek-v4.1-flash`/`max`,
`fork_turns="none"`, allowed `pwd`, and ordinary worker merge, reviewer write and reviewer
cross-role refusals. A controlled provider establishes host mechanics rather than production
worker execution or uncoached compliance. A separate production `gpt-6.1-sol`/`high` typed reviewer call with
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
default `deepseek-v4.1-flash`/`max` explicitly in every native child call, unless a direct, specific human
instruction overrides its named dispatch. Role files do not supply effective per-role `cwd`, sandbox,
or hook settings. Child permissions and cwd are inherited from the
parent. The package hook resolves from the host-provided `PLUGIN_ROOT` and uses actual `agent_type`
with a structured deny. Native role files cannot install hooks. SessionStart matches startup,
resume, clear and compact. One synchronous handler uses `additionalContextLimit: 0` to carry
the whole orchestrator inline. Its fixed 64,000 UTF-8 byte budget includes the complete
additionalContext header and page. Missing, empty, invalid UTF-8 or oversized pages return
`continue: false` without partial context. The budget belongs to the method, not Codex. Capture
live context and actual stopping behavior for each claim rather than inferring them from JSON or matchers.

The installer extracts the single marked Shared collaboration agreements section from
`reference/orchestrator.md` and inlines it once into all four roles. Children receive that section,
not the whole orchestrator, and do not reread its main-session duties. Helper roles receive
`reference/task-helper.md`, a role-specific boundary and the single marked Native helper mechanics
excerpt: the caller retains lane ownership and publication, and ordinary
non-PR work does not inherit Issue/lane/fence requirements. The worker role's instructions carry
this page and `reference/worker.md`; its spawn message
carries the freshly assembled task packet without a second static role copy. Installation drift
and missing roles refuse before a lane is prepared. Helpers receive their narrower task and applicable
role boundary. Reviewer roles automatically deliver the complete nonediting contract and native mechanics,
with no implementation skills. Their short native message binds the issue, review base, head,
reviewer identity, workdir
and full retained evidence bundle by absolute path and SHA-256. The bundle supplies the complete
filled judging contract. The reviewer explicitly reads and verifies that complete bundle before judging; a path is not automatic
delivery. A child receives neither the main session's conversation nor
an assumed startup delivery of the orchestrator page.

## Native V2 invocation

Prepare the worker receipt with `scripts/dispatch`, or the gating-review receipt with
`scripts/review-packet start` under the orchestrator's **Review packets** section. Pass the
returned instruction's message and exact settings unchanged to the native tool. This is the
qualified argument shape, shown as data:

```json
{
  "task_name": "issue_123_worker",
  "message": "<complete dispatcher brief>",
  "agent_type": "method_worker",
  "fork_turns": "none",
  "model": "deepseek-v4.1-flash",
  "reasoning_effort": "max"
}
```

For gating review, the short native message binds `Issue`, `Review base`, `Head`, `Reviewer
identity`, explicit workdir, method root and the token-directory `review-brief.md` absolute path
with SHA-256. The bundle begins with the complete filled judging contract and retains all material;
the message does not duplicate static role text or the filled contract. Hash the bundle before
reading, read every sequential numbered chunk with no omitted or truncated output, then hash it
again after reading/review. Both hashes must match the supplied digest, and the receipt pins and
identity must agree with the filled contract. Disclose path, digest and full coverage in Floor 1
grounds. Missing access, drift, mismatches or partial reads fail Floor 1; do not rule readiness
from receipt pins or an evidence summary alone. A supported inline packet must be read completely;
a supplied file carrier still requires exact hashing, full reads and inline/bundle agreement.
Native schema and role fields stay unchanged. This route uses normal native calls and ordinary
read tools, with no code-mode flag or file-reference API required; the host does not read the path
for you. Original bundle bytes and instruction hashes remain retained for acceptance and recovery.

Gating review uses `method_reviewer`; its native message follows the formal transport above.

<!-- BEGIN NATIVE HELPER MECHANICS -->
## Native helper mechanics

Inspect the actual native schema before invoking it. Qualified Codex 0.160.0 V2 accepts
`task_name`, `message`, `agent_type`, `fork_turns="none"`, `model` and `reasoning_effort`.
Ordinary task helpers use `method_helper`; fresh design challenge and pre-PR arbitration use
`method_review_helper`. A reviewer's helpers keep `method_review_helper` and its nonediting
restriction; use only fresh review-helper descendants for authorized review help, never a generic
writer. Every helper passes model and effort explicitly under the delivered `Helpers:` binding.
If a requested setting, role or native tool is unavailable, return the limitation; availability and
quota never silently change the setting or gate. Do not add unsupported `cwd`, `sandbox`,
`hook_settings`, `prompt`, `subagent_type`, `fork_context` or `run_in_background` spawn fields.

Children inherit the parent's cwd and permissions. Run every command with the supplied working
directory explicitly selected; a task path is an instruction, not cwd isolation or an OS sandbox.
Fresh context and a nonediting contract plus the trusted ordinary-path role hook are not OS-enforced
read-only isolation. The hook does not contain arbitrary MCP writes or hostile same-credential code.

Where an admitted native interface lacks `agent_type`, an ordinary task-local helper's message must
explicitly carry the exact shared section (the installer's `shared_agreements()` output) and the
complete assigned helper role/task contract with applicable write or nonediting bounds. Use only
supported fields. This carrier is not typed role discovery or proof of role-hook enforcement;
formal gating review still needs its qualified typed route and identity. Return interface/hook
refusals under the shared rule rather than bypassing them. Do not infer universal desktop
compatibility from app-server probes.

A prepared task is not a launched child. Record its actual returned native handle; observe native
status/completion and read the full return before reuse or cleanup. A live or uncertain child blocks
an overlapping writer. Inspect status before task-local continuation on the actual retained handle,
and supply the refreshed self-contained task. Before replacing it, establish that the old child
cannot still write. After lost context, stop dependent work and recover the exact role, goal, bounds,
checks, working directory and observed task status from the caller; invent no lane fields. This route
makes no promise about persistence across restarted sessions. Refusals and retained state return
under the shared agreements while independent authorized work continues.
<!-- END NATIVE HELPER MECHANICS -->

For a dispatched repository lane, record the actual native handle with its issue and lane. The
dispatcher cannot attest a handle it did not observe. Lane receipts and retained briefs are shared
across checkouts in the Git common directory under `codex-method/lanes`. An older run keeps its
observed version; preparing a current-version child requires fresh actual completion evidence for
the old handle and current host qualification. Conflicting legacy receipts are preserved and
refused, not overwritten.

## Worktree and permission boundary

Before any lane write, validate the exact recorded branch, linked-worktree identity and named
base under the worker page; run commands with that worktree explicitly selected. Parent permission grants may reach other lanes and shared git
metadata; the assigned-lane restriction remains a role obligation.

An independent gating reviewer follows the same fresh-context, nonediting and ordinary-path
boundary described above; the host's inherited sandbox still applies. The hook's full rules and
exclusions live in `reference/orchestrator.md`'s The role hook section.

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

After compaction or loss of a repository lane binding, stop dependent task writes. Ask the
orchestrator on the actual native channel to resend the exact original packet and current authorized continuation,
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
