# Team handoff

Import branch: codex/import-quantum-duet; default target: main.
Reviewed code: `e9f02aecfcd973dbe8e235d74265515b65aca348`; freshly inspected team base: `7b9b6b0f6a27425645c01389ccbcd7d63b4a3982`.
All initial workers start from one HANDOFF_SHA: the final commit adding these three
prompt files. Resolve it with `git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-a.md` and verify B/C prompt commits equal it.
The coordinator's final report prints the exact SHA after committing and confirms
its presence on the pushed branch. This avoids putting a circular self-hash in files.

Read repository-map.md, run-contract.md, verification.md. Copy the entire appropriate
prompt in prompts/ into a new session. No worker session has been launched.

| Role | Ownership / dependency |
|---|---|
| A: backend (highest priority) | Exact single-circuit real bridge diagnosis first; Python probe/run/backend integration + backend_a tests. B/C do not wait |
| B: adapter | New paired adapter, examples and adapter_b tests. Uses frozen fixture and contract now; later consumes A's unchanged take API |
| C: interface | Existing web/dev UI plus ui_c tests. Uses same fixture now; arranged production hookup after B's output review |
| Coordinator | Shared contract/fixture/config/lock/build/licences, final validation, explicit integration and PR-base updates. Does not implement A/B/C here |

Generated build directories/ZIP/manifests are not canonical or committed. Source
ownership is disjoint, including tests. Necessary cross-owner changes are dependencies,
not permission to edit. No new training or paid execution. No merges in this session.

Worker draft PRs target the import branch while its draft PR is unmerged. This is a
temporary stacked arrangement: review workers against the same imported foundation.
Human approval/merge comes first; coordinator explicitly updates bases and retargets
afterwards. Do not silently rebase or combine teammate branches.

Example separate worktrees, from a clean coordinator checkout after fetching:
```powershell
git fetch origin
$handoffSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-a.md
git worktree add ../OxfordQ-worker-a -b codex/duet-backend-20261010 $handoffSha
git worktree add ../OxfordQ-worker-b -b codex/duet-adapter-20261010 $handoffSha
git worktree add ../OxfordQ-worker-c -b codex/duet-interface-20261010 $handoffSha
```
Use fresh names if any path/branch exists. Verify every initial HEAD equals the exact
printed HANDOFF_SHA. Their prompts also provide independent clone commands.

Human actions: review import/scientific notices, choose and launch separate sessions,
approve any integration and merges, authorize platform maintainer contact if needed,
resolve free IonQ/platform constraints, approve publication/video/submission separately.
The original Qollab draft remains private; nothing was published in this import.
