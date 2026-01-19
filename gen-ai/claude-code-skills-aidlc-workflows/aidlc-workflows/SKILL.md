---
name: aidlc-workflows
description: AI-DLC workflow execution that loads and follows external aidlc-workflows rules to plan, design, and generate code with approval gates and aidlc-docs artifacts. Use when a user wants to run AI-DLC, needs adaptive inception/construction phases, or needs rule-driven requirements, design, and code generation from aidlc-workflows.
---

# AIDLC Workflow Skill

## Core behavior

- Locate the `aidlc-workflows/` repository and read rules from it on demand.
- Follow AI-DLC phases (inception, construction, operations) with explicit approval gates.
- Write artifacts to `aidlc-docs/` and preserve audit/state across phases.
- Never modify rule files under `aidlc-workflows/aidlc-rules/`.

## Locate aidlc-workflows

Use this lookup order:

1. `AIDLC_WORKFLOWS_DIR` environment variable, if set.
2. `aidlc-workflows/` in the current workspace.
3. `~/aidlc-workflows`.

If none are found, ask the user in English using this exact prompt:

"I couldn't find the aidlc-workflows directory. Please provide the absolute path to your aidlc-workflows repository (for example: /Users/yourname/path/to/aidlc-workflows)."

## Rule loading

- Read `aidlc-workflows/skills/ai-dlc/SKILL.md` for baseline workflow intent.
- Use `aidlc-workflows/skills/ai-dlc/loader.md` as the source of truth for dynamic rule loading.
- Load only the specific rule files required for the current stage.
- Prefer common rules first, then phase-specific rules, then stage-specific rules.

See `references/loader.md` for the loading sequence summary and key rule files.

## Execution flow

1. Confirm workspace state (greenfield vs brownfield) and initialize `aidlc-docs/`.
2. Run INCEPTION stages per rules (always/conditional) and request approval after each stage.
3. Run CONSTRUCTION per unit, including design, code generation, and build/test stages.
4. If OPERATIONS is requested, follow the operations rule file when present.
5. Keep a clear audit trail in `aidlc-docs/audit.md` and state in `aidlc-docs/aidlc-state.md`.

## Output rules

- Use the question/answer format required by the rule files when asking clarifying questions.
- If a stage is skipped, document the skip reason in the audit trail.
- Never copy rule content into the skill; only reference and load it as needed.

## Example trigger phrases

- "Using AI-DLC, build a user authentication service with OAuth 2.0"
- "/aidlc-workflows Add a password reset feature"
