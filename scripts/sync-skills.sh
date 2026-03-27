#!/bin/bash
set -euo pipefail

# ── Sync skills and CLAUDE.md from claude-config repo to ~/.claude/ ──
# Called by:
#   1. User-level SessionStart hook (any project, uses $CLAUDE_CONFIG_REPO)
#   2. Project-level session-start.sh (inside the repo itself)
#
# Env: CLAUDE_CONFIG_REPO  – path to local clone of claude-config
#       SKILLS_SOURCE_OVERRIDE – if set, skip git pull and use this path

SKILLS_TARGET="${HOME}/.claude/skills"
CLAUDE_MD_TARGET="${HOME}/.claude/CLAUDE.md"

# ── Determine source ──
if [ -n "${SKILLS_SOURCE_OVERRIDE:-}" ]; then
  SKILLS_SOURCE="$SKILLS_SOURCE_OVERRIDE"
elif [ -n "${CLAUDE_CONFIG_REPO:-}" ] && [ -d "${CLAUDE_CONFIG_REPO}" ]; then
  SKILLS_SOURCE="${CLAUDE_CONFIG_REPO}/skills"

  # Quick git pull (timeout 10s, fail silently if offline)
  if git -C "$CLAUDE_CONFIG_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    timeout 10 git -C "$CLAUDE_CONFIG_REPO" pull --ff-only --quiet 2>/dev/null || true
  fi
else
  exit 0
fi

# ── Determine repo root for CLAUDE.md sync ──
if [ -n "${SKILLS_SOURCE_OVERRIDE:-}" ]; then
  REPO_ROOT="$(cd "$SKILLS_SOURCE_OVERRIDE/.." && pwd)"
else
  REPO_ROOT="${CLAUDE_CONFIG_REPO}"
fi

# ── Sync CLAUDE.md ──
CLAUDE_MD_SOURCE="${REPO_ROOT}/CLAUDE.md"
if [ -f "$CLAUDE_MD_SOURCE" ]; then
  cp "$CLAUDE_MD_SOURCE" "$CLAUDE_MD_TARGET"
fi

[ -d "$SKILLS_SOURCE" ] || exit 0

mkdir -p "$SKILLS_TARGET"

# ── Copy skill directories ──
for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"
  rm -rf "$target"
  cp -R "$skill_dir" "$target"
done

# ── Remove orphaned skill directories ──
for installed_dir in "$SKILLS_TARGET"/*/; do
  [ -d "$installed_dir" ] || continue
  skill_name="$(basename "$installed_dir")"
  if [ ! -d "$SKILLS_SOURCE/$skill_name" ]; then
    rm -rf "$installed_dir"
  fi
done
