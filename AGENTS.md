# Shared work rules

Read docs/team/README.md, run-contract.md and the assigned worker prompt first.
Use separate clean worktrees/clones from the same pinned HANDOFF_SHA. Worker PRs
target codex/import-quantum-duet while the import PR remains unmerged. No force pushes,
main pushes, merges, automatic worker sessions or publication without human direction.

Coordinator owns root config/dependencies/licences, shared contract/fixtures, packaging
tools and final integration. A owns the backend Python files listed in its prompt;
B owns its new adapter/example/test files; C owns web/dev/UI test files. Treat prompt
allowlists as exact scope. Record cross-owner needs instead of editing their files.
Edit canonical sources only; deployment build directories/manifests are generated
and ignored. Keep original experiments, weights and local musical mapping unchanged.
No held-out motifs, new training, paid API calls or physical QPU use.

Verify existing and assigned tests; run the rules-only CLI without native audio.
Report local/mocked/browser/Qollab/IonQ checks separately, with actual timestamps and
failures. Preserve paired run/round IDs, recorded/live labels and explicit errors.
Raw musical coordination bypasses central arrangement. Preserve immutable raw source
and source lineage after arrangement. CHSH is not musical-quality or speedup evidence.
No browser credentials, silent simulator substitution or guessed provider counts.
