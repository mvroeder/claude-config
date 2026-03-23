#!/bin/bash
set -euo pipefail

# ── Sync skills and CLAUDE.md from claude-config repo to ~/.claude/ ──
# Called by the SessionStart hook in settings.json.
# Expects to be run from the cloned repo at ~/.claude/claude-config/.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SOURCE="${REPO_ROOT}/skills"
SKILLS_TARGET="${HOME}/.claude/skills"
CLAUDE_MD_SOURCE="${REPO_ROOT}/CLAUDE.md"
CLAUDE_MD_TARGET="${HOME}/.claude/CLAUDE.md"

# ── Sync CLAUDE.md (only if source is newer) ──
if [ -f "$CLAUDE_MD_SOURCE" ]; then
  if [ ! -f "$CLAUDE_MD_TARGET" ]; then
    cp "$CLAUDE_MD_SOURCE" "$CLAUDE_MD_TARGET"
  else
    src_mtime="$(stat -c %Y "$CLAUDE_MD_SOURCE" 2>/dev/null || stat -f %m "$CLAUDE_MD_SOURCE")"
    tgt_mtime="$(stat -c %Y "$CLAUDE_MD_TARGET" 2>/dev/null || stat -f %m "$CLAUDE_MD_TARGET")"
    if [ "$src_mtime" -gt "$tgt_mtime" ]; then
      cp "$CLAUDE_MD_SOURCE" "$CLAUDE_MD_TARGET"
    fi
  fi
fi

[ -d "$SKILLS_SOURCE" ] || exit 0

mkdir -p "$SKILLS_TARGET"

# ── Copy skill directories (smart: skip unchanged) ──
for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"

  # Skip if target exists and source hasn't changed
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    src_mtime="$(stat -c %Y "$skill_dir" 2>/dev/null || stat -f %m "$skill_dir")"
    tgt_mtime="$(stat -c %Y "$target" 2>/dev/null || stat -f %m "$target")"
    if [ "$src_mtime" -le "$tgt_mtime" ]; then
      continue
    fi
  fi

  rm -rf "$target"
  cp -R "$skill_dir" "$target"
done
