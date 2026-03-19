#!/bin/bash
set -euo pipefail

# Only run in remote/cloud environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

SKILLS_SOURCE="${CLAUDE_PROJECT_DIR}/skills"
SKILLS_TARGET="${HOME}/.claude/skills"

mkdir -p "$SKILLS_TARGET"

# Symlink all skill directories from the repo
for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"

  # Skip if already correctly linked
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill_dir" ]; then
    continue
  fi

  # Remove stale link or directory, then create symlink
  rm -rf "$target"
  ln -s "$skill_dir" "$target"
done
