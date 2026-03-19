#!/bin/bash
set -euo pipefail

# Determine skills source directory
# Remote: use project dir; Local: use the repo where this hook lives
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  SKILLS_SOURCE="${CLAUDE_PROJECT_DIR}/skills"
else
  SKILLS_SOURCE="$(cd "$(dirname "$0")/../.." && pwd)/skills"
fi
SKILLS_TARGET="${HOME}/.claude/skills"

mkdir -p "$SKILLS_TARGET"

# Copy all skill directories from the repo (symlinks are not followed by Claude Code)
for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"

  # Skip if target exists and source hasn't changed
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    # Re-copy if source is newer than target
    src_mtime="$(stat -c %Y "$skill_dir" 2>/dev/null || stat -f %m "$skill_dir")"
    tgt_mtime="$(stat -c %Y "$target" 2>/dev/null || stat -f %m "$target")"
    if [ "$src_mtime" -le "$tgt_mtime" ]; then
      continue
    fi
  fi

  # Remove stale link or outdated directory, then copy
  rm -rf "$target"
  cp -R "$skill_dir" "$target"
done
