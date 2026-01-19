#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_name="aidlc-workflows"
source_dir="$script_dir/$skill_name"
target_root="$HOME/.claude/skills"
target_dir="$target_root/$skill_name"

if [[ ! -d "$source_dir" ]]; then
  echo "Error: skill directory not found at $source_dir" >&2
  exit 1
fi

mkdir -p "$target_root"
rm -rf "$target_dir"
cp -R "$source_dir" "$target_dir"

echo "Installed $skill_name to $target_dir"
echo "If aidlc-workflows is not in your workspace, set AIDLC_WORKFLOWS_DIR to its path."
