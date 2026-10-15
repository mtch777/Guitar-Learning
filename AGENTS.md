# Codex project instructions — Guitar-Learning

Repository: https://github.com/mtch777/Guitar-Learning. Branch of record: main.

## Before changing anything
- Read composition-lab/HANDOFF.md (extensive historical context), then composition-lab/CODEX_CONTEXT.md.
- Inspect current main HEAD, source, tests, and workflows. Current code supersedes older handoffs.
- This repo also hosts a guitar-learning UI: scope edits carefully; don't regress unrelated features.
- Do not publish copyrighted commercial GP source scores, private annotations, credentials, or licensed model weights.

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
