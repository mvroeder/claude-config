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
INTERESTS_MD_TARGET="${HOME}/.claude/INTERESTS.md"
KNOWLEDGE_TARGET="${HOME}/.claude/knowledge"

# ── Determine source ──
if [ -n "${SKILLS_SOURCE_OVERRIDE:-}" ]; then
  # Called from project-level hook — source is already local, no pull needed
  SKILLS_SOURCE="$SKILLS_SOURCE_OVERRIDE"
elif [ -n "${CLAUDE_CONFIG_REPO:-}" ] && [ -d "${CLAUDE_CONFIG_REPO}" ]; then
  # Called from user-level hook — pull latest changes first
  SKILLS_SOURCE="${CLAUDE_CONFIG_REPO}/skills"

  # Quick git pull (timeout 10s, fail silently if offline)
  if git -C "$CLAUDE_CONFIG_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    timeout 10 git -C "$CLAUDE_CONFIG_REPO" pull --ff-only --quiet 2>/dev/null || true
  fi
else
  # No repo configured — nothing to do
  exit 0
fi

# ── Determine repo root for CLAUDE.md sync ──
if [ -n "${SKILLS_SOURCE_OVERRIDE:-}" ]; then
  REPO_ROOT="$(cd "$SKILLS_SOURCE_OVERRIDE/.." && pwd)"
else
  REPO_ROOT="${CLAUDE_CONFIG_REPO}"
fi

# ── Sync CLAUDE.md (only if source is newer) ──
CLAUDE_MD_SOURCE="${REPO_ROOT}/CLAUDE.md"
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

# ── Sync INTERESTS.md (only if source is newer) ──
INTERESTS_MD_SOURCE="${REPO_ROOT}/INTERESTS.md"
if [ -f "$INTERESTS_MD_SOURCE" ]; then
  if [ ! -f "$INTERESTS_MD_TARGET" ]; then
    cp "$INTERESTS_MD_SOURCE" "$INTERESTS_MD_TARGET"
  else
    src_mtime="$(stat -c %Y "$INTERESTS_MD_SOURCE" 2>/dev/null || stat -f %m "$INTERESTS_MD_SOURCE")"
    tgt_mtime="$(stat -c %Y "$INTERESTS_MD_TARGET" 2>/dev/null || stat -f %m "$INTERESTS_MD_TARGET")"
    if [ "$src_mtime" -gt "$tgt_mtime" ]; then
      cp "$INTERESTS_MD_SOURCE" "$INTERESTS_MD_TARGET"
    fi
  fi
fi

# ── Sync knowledge directory (smart: skip unchanged) ──
KNOWLEDGE_SOURCE="${REPO_ROOT}/knowledge"
if [ -d "$KNOWLEDGE_SOURCE" ]; then
  mkdir -p "$KNOWLEDGE_TARGET"
  for knowledge_dir in "$KNOWLEDGE_SOURCE"/*/; do
    [ -d "$knowledge_dir" ] || continue
    dir_name="$(basename "$knowledge_dir")"
    target="$KNOWLEDGE_TARGET/$dir_name"

    if [ -d "$target" ] && [ ! -L "$target" ]; then
      src_mtime="$(stat -c %Y "$knowledge_dir" 2>/dev/null || stat -f %m "$knowledge_dir")"
      tgt_mtime="$(stat -c %Y "$target" 2>/dev/null || stat -f %m "$target")"
      if [ "$src_mtime" -le "$tgt_mtime" ]; then
        continue
      fi
    fi

    rm -rf "$target"
    cp -R "$knowledge_dir" "$target"
  done
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
