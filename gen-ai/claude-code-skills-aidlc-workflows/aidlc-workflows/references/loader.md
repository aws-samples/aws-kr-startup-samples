# AI-DLC Rule Loading Summary

This skill relies on the external rule loader in:

- `aidlc-workflows/skills/ai-dlc/loader.md`

Use that file as the authoritative sequence for which rule files to load per stage.

## Minimum load order

1. `common/welcome-message.md`
2. `common/process-overview.md`
3. `common/terminology.md`
4. `common/depth-levels.md`

## Inception stages

- `inception/workspace-detection.md`
- `inception/reverse-engineering.md` (brownfield only)
- `inception/requirements-analysis.md`
- `common/question-format-guide.md` (for questions)
- `inception/user-stories.md` (conditional)
- `inception/workflow-planning.md`
- `inception/application-design.md` (conditional)
- `inception/units-generation.md` (conditional)

## Construction stages (per unit)

- `construction/functional-design.md` (conditional)
- `construction/nfr-requirements.md` (conditional)
- `construction/nfr-design.md` (conditional)
- `construction/infrastructure-design.md` (conditional)
- `construction/code-generation.md`
- `construction/build-and-test.md`

## Operations

- `operations/operations.md` (when available)

## Constraints

- Never modify any file under `aidlc-workflows/aidlc-rules/`.
- Load only what is needed for the current stage.
