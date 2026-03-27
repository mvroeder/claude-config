#!/bin/bash
# ── Global SessionStart hook ──
# Installed to ~/.claude/hooks/session-start.sh by scripts/install.sh.
# Entry point for every Claude Code session on this machine.
#
# Local: uses $CLAUDE_CONFIG_REPO (set in shell profile)
# Cloud: auto-clones the repo to ~/.claude/claude-config/ as fallback

set -euo pipefail

GITHUB_REPO="https://github.com/mvroeder/claude-config.git"
CLOUD_CLONE_DIR="${HOME}/.claude/claude-config"

# ── 1. Resolve CLAUDE_CONFIG_REPO ──
if [ -z "${CLAUDE_CONFIG_REPO:-}" ] || [ ! -d "${CLAUDE_CONFIG_REPO}" ]; then
  if [ -d "$CLOUD_CLONE_DIR/.git" ]; then
    timeout 10 git -C "$CLOUD_CLONE_DIR" pull --ff-only --quiet 2>/dev/null || true
  else
    if timeout 30 git clone --depth 1 --quiet "$GITHUB_REPO" "$CLOUD_CLONE_DIR" 2>/dev/null; then
      echo "claude-config: auto-cloned to $CLOUD_CLONE_DIR" >&2
    else
      echo "claude-config: could not clone $GITHUB_REPO — skills unavailable" >&2
      exit 0
    fi
  fi
  CLAUDE_CONFIG_REPO="$CLOUD_CLONE_DIR"
fi

# ── 2. Installation health check ──
HOOK_SELF="$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
REPO_HOOK="${CLAUDE_CONFIG_REPO}/hooks/global-session-start.sh"
if [ -f "$REPO_HOOK" ] && [ -f "$HOOK_SELF" ]; then
  if ! cmp -s "$REPO_HOOK" "$HOOK_SELF"; then
    echo "claude-config: hook outdated — run: \$CLAUDE_CONFIG_REPO/scripts/install.sh" >&2
  fi
fi

# ── 3. Sync Reminders (macOS only, non-blocking) ──
if [ "$(uname)" = "Darwin" ]; then
  REMINDERS_SYNC="${HOME}/.claude/tools/sync-reminders.py"
  if [ -x "$REMINDERS_SYNC" ]; then
    python3 "$REMINDERS_SYNC" &>/dev/null &
  fi
fi

# ── 4. Delegate to sync-skills.sh ──
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO}/scripts/sync-skills.sh"
if [ -x "$SYNC_SCRIPT" ]; then
  exec "$SYNC_SCRIPT"
else
  echo "claude-config: sync script not found: $SYNC_SCRIPT" >&2
  exit 0
fi
