#!/bin/bash
# Install code-review agents to Kiro global configuration

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIRO_AGENTS_DIR="$HOME/.kiro/agents"
KIRO_PROMPTS_DIR="$HOME/.kiro/prompts"

mkdir -p "$KIRO_AGENTS_DIR" "$KIRO_PROMPTS_DIR"

cp "$SCRIPT_DIR"/agents/code-review-*.json "$KIRO_AGENTS_DIR/"
cp "$SCRIPT_DIR"/prompts/code-review-*.md "$KIRO_PROMPTS_DIR/"

echo "Installed code-review agents to ~/.kiro/"
echo "Agents: $(ls "$KIRO_AGENTS_DIR"/code-review-*.json 2>/dev/null | wc -l | tr -d ' ') files"
echo "Prompts: $(ls "$KIRO_PROMPTS_DIR"/code-review-*.md 2>/dev/null | wc -l | tr -d ' ') files"
