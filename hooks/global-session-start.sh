#!/bin/bash
# ── Global SessionStart hook ──
# Installed to ~/.claude/hooks/session-start.sh by scripts/install.sh.
# Entry point for every Claude Code session on this machine.
#
# Works in two modes:
#   1. Local: uses $CLAUDE_CONFIG_REPO (set in shell profile)
#   2. Cloud: auto-clones the repo to ~/.claude/claude-config/ as fallback
#
# Checks prerequisites, then delegates to sync-skills.sh.

set -euo pipefail

GITHUB_REPO="https://github.com/mvroeder/claude-config.git"
CLOUD_CLONE_DIR="${HOME}/.claude/claude-config"

WARNINGS=()

# ── 1. Resolve CLAUDE_CONFIG_REPO ────────────────────────────────────────────
if [ -z "${CLAUDE_CONFIG_REPO:-}" ] || [ ! -d "${CLAUDE_CONFIG_REPO}" ]; then
  # Fallback for cloud sessions: auto-clone if not available
  if [ -d "$CLOUD_CLONE_DIR/.git" ]; then
    # Already cloned — pull latest (fail silently if offline)
    timeout 10 git -C "$CLOUD_CLONE_DIR" pull --ff-only --quiet 2>/dev/null || true
  else
    # Clone fresh (shallow for speed)
    if timeout 30 git clone --depth 1 --quiet "$GITHUB_REPO" "$CLOUD_CLONE_DIR" 2>/dev/null; then
      echo "claude-config: auto-cloned to $CLOUD_CLONE_DIR" >&2
    else
      echo "claude-config: could not clone $GITHUB_REPO — skills unavailable" >&2
      exit 0
    fi
  fi
  CLAUDE_CONFIG_REPO="$CLOUD_CLONE_DIR"
fi

# ── 2. Sync script must exist and be executable ──────────────────────────────
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO}/scripts/sync-skills.sh"
if [ ! -x "${SYNC_SCRIPT}" ]; then
  echo "claude-config: sync script not found or not executable: ${SYNC_SCRIPT}" >&2
  exit 0
fi

# ── 3. Global CLAUDE.md check (non-fatal) ────────────────────────────────────
if [ ! -f "${HOME}/.claude/CLAUDE.md" ]; then
  WARNINGS+=("~/.claude/CLAUDE.md not found — will be synced now.")
fi

# ── 4. Skills directory check (non-fatal) ────────────────────────────────────
SKILLS_DIR="${HOME}/.claude/skills"
if [ ! -d "${SKILLS_DIR}" ] || [ -z "$(ls -A "${SKILLS_DIR}" 2>/dev/null)" ]; then
  WARNINGS+=("~/.claude/skills/ is missing or empty — will be synced now.")
fi

# ── Print warnings (non-fatal) ──────────────────────────────────────────────
if [ ${#WARNINGS[@]} -gt 0 ]; then
  for msg in "${WARNINGS[@]}"; do
    echo "claude-config: ${msg}" >&2
  done
fi

# ── Delegate to sync-skills.sh ──────────────────────────────────────────────
exec "${SYNC_SCRIPT}"
