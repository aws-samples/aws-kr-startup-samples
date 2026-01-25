---
name: aidlc
description: AI-Driven Development Life Cycle workflow. Use when user says "Using AI-DLC...", "AI-DLC로...", "Start AI-DLC", "start development", "build an app", "create a project", or wants intelligent adaptive software development workflow with requirements analysis, design, and implementation phases.
disable-model-invocation: false
user-invocable: true
argument-hint: [task-description]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion, TodoWrite
---

# AI-DLC (AI-Driven Development Life Cycle) Skill

You are now operating in AI-DLC mode - an intelligent software development workflow that adapts to your needs, maintains quality standards, and keeps you in control of the process.

## User Request

$ARGUMENTS

## MANDATORY: Initialization Steps

### Step 1: Load Core Workflow Rules

**CRITICAL**: You MUST read and follow the core workflow rules:

1. Read `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rules/core-workflow.md` - This is your PRIMARY instruction set
2. Read `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/common/process-overview.md`
3. Read `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/common/session-continuity.md`
4. Read `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/common/content-validation.md`
5. Read `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/common/question-format-guide.md`

### Step 2: Session Continuity Check

Before starting any work:

1. Check if `aidlc-docs/aidlc-state.md` exists
2. **If EXISTS**:
   - Read `aidlc-docs/aidlc-state.md` to get current status
   - Read `aidlc-docs/audit.md` for interaction history
   - Follow session-continuity.md rules to present "Welcome back" prompt
   - Load all relevant artifacts from previous stages
3. **If NOT EXISTS**:
   - This is a new project
   - Display welcome message from `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/common/welcome-message.md`
   - Proceed with Workspace Detection stage

### Step 3: Execute Workflow

Follow the three-phase adaptive workflow as defined in core-workflow.md:

**INCEPTION PHASE** (WHAT to build and WHY):
- Workspace Detection (ALWAYS)
- Reverse Engineering (CONDITIONAL - Brownfield only)
- Requirements Analysis (ALWAYS - Adaptive depth)
- User Stories (CONDITIONAL)
- Workflow Planning (ALWAYS)
- Application Design (CONDITIONAL)
- Units Generation (CONDITIONAL)

**CONSTRUCTION PHASE** (HOW to build it):
- Per-Unit Loop:
  - Functional Design (CONDITIONAL)
  - NFR Requirements (CONDITIONAL)
  - NFR Design (CONDITIONAL)
  - Infrastructure Design (CONDITIONAL)
  - Code Generation (ALWAYS)
- Build and Test (ALWAYS)

**OPERATIONS PHASE** (DEPLOY and RUN - future):
- Operations (PLACEHOLDER)

## Key Principles

1. **Adaptive Execution**: Only execute stages that add value
2. **Transparent Planning**: Always show execution plan before starting
3. **User Control**: User can request stage inclusion/exclusion
4. **Progress Tracking**: Update `aidlc-docs/aidlc-state.md` with executed and skipped stages
5. **Complete Audit Trail**: Log ALL user inputs in `aidlc-docs/audit.md` with timestamps
6. **Wait for Approval**: NEVER proceed to next stage without explicit user approval

## Directory Structure

All documentation goes in `aidlc-docs/`:
```
aidlc-docs/
├── inception/
├── construction/
├── operations/
├── aidlc-state.md
└── audit.md
```

Application code goes in workspace root (NEVER in aidlc-docs/).

## IMPORTANT

- Always load the appropriate rule detail file before executing each stage
- Rule detail files are in: `.claude/skills/aidlc/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/`
- Follow the exact approval formats specified in each rule file
- Present questions in markdown files, not inline in chat
