# Codex project instructions — Guitar-Learning

Repository: https://github.com/mtch777/Guitar-Learning. Branch of record: main.

## Listening feedback — permanent user instruction, 2026-11-02
- Reuse the existing listening page. Repopulate it; do not rebuild a player or rerender verified audio for presentation changes.
- Always show untouched original, what changed, color-coded changed notes in the piano roll, and specific feedback questions. Keep four bars before/after by default.
- Follow `composition-lab/LISTENING_REVIEW_TEMPLATE.md` and its publisher. Keep the same serving URL when available.

## Artist scope — user instruction, 2026-11-01
- New song analysis, artist profiles and musical demonstrations must use ONLY these artists, in priority order: Invent Animate, then Currents, then ERRA.
- Use Invent Animate for the next active musical capability. Do not choose another artist because its material is easier.
- Preserve other artists' existing artifacts only as historical/regression evidence; do not expand their analysis or demonstrations.
- Fresh-song QA must freeze its eligible artist/song population before selection and retain the first result, including failures. Artist priority does not permit cherry-picking or rerolling.

## Before changing anything
- Read composition-lab/HANDOFF.md (extensive historical context), then composition-lab/CODEX_CONTEXT.md.
- Inspect current main HEAD, source, tests, and workflows. Current code supersedes older handoffs.
- This repo also hosts a guitar-learning UI: scope edits carefully; don't regress unrelated features.
- Do not publish copyrighted commercial GP source scores, private annotations, credentials, or licensed model weights.
- Store bulk song downloads and analysis outputs in draft GitHub Releases, not GitHub Actions artifacts. Actions artifact storage is a small shared allocation and must not hold the corpus. Preserve existing encryption; verify replacement size and SHA-256 before removing any stored source copy. See `.github/ARTIFACT_STORAGE_MIGRATION.md` and `.github/scripts/release_storage.py`.

## Working method
- Make an explicit, persistent checklist of subtasks with testable acceptance criteria.
- Implement, run tests, diagnose, retry, and proceed to the next independent subtask without requiring a user message saying 'next'.
- Keep a progress log with commits, commands, results, unresolved blockers, and next action. Do not mark a task complete merely because code was written or a report generated.
- Preserve baseline GP outputs for comparative listening and measurable analysis.
- Do not confuse valid GP serialization with musical quality. Real playback/listening review is required.
- Preserve rational onset/duration, original note/beat occurrences, track/voice, tuning, ties and technique metadata.
- Exact 0% similarity controls must preserve locked musical dimensions; other percentages require measurable behavior.
- Ask before destructive changes or changes that require private credentials or human musical judgments. If blocked, document and advance other independent work.

## Verification
- Run relevant Python tests and available JS tests/build; report commands and actual results.
- Do not claim remote deployment, model inference, benchmark accuracy, or audio quality without verifying each.
- Keep model checkpoints and corpus licensing separate from source-code licenses.

## Composition Lab steering (reconciled 2026-11-03)
- After HANDOFF.md and CODEX_CONTEXT.md, read composition-lab/PROJECT_COMPLETION_PLAN.md and composition-lab/DEVELOPMENT_OPERATING_RULES.md. Their current sections govern scope and order; dated experiment logs do not provide competing next actions.
- ProjectPlanner3000 follows composition-lab/PROJECTPLANNER_INSTRUCTIONS.md. Consult at start, midpoint/about ten working steps, and completion. Root remains responsible for decisions and delivery; do not revive QABot3000.
- Every subagent brief must name the current objective, requirements, owned files, counterexample, acceptance evidence and forbidden scope. Agents must challenge stale/conflicting directions before proceeding and report actual results, not implementation-only completion.
- Use composition-lab/PROJECT_COMPLETION_PLAN.md for the current tier status and ordered MVP acceptance. Use composition-lab/THEMATIC_RETURN_PROGRESS.md for the active contract and checklist. Do not restart the earlier T2 assignment from a historical handoff. MVP acceptance and full-tier completion are separate: all broader requirements remain owed. Tool and accepted bounded milestones stay closed except regressions. Root owns integration; examples supply evidence rather than redefine scope.
- Preserve all three QA gates and the approved operation's lever semantics. Zero locks the supplied current state; reverting is separate. Historical proposals grant no tier bypass. Routine safe changes within an accepted capability proceed under technical QA; publish useful comparisons promptly without inventing a new approval gate.
- Publish governing requirements and their required links coherently on main. Verify committed/published content separately from local files and CI; untracked local instructions do not establish the published contract.
