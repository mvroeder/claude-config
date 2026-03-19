#!/bin/bash
set -euo pipefail

# ── Project-level SessionStart hook ──
# Delegates to sync-skills.sh with the local repo as source.
# This runs when Claude Code is started inside the claude-config repo itself.

# Determine skills source (works for both local and remote)
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  REPO_ROOT="${CLAUDE_PROJECT_DIR}"
else
  REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

SYNC_SCRIPT="${REPO_ROOT}/scripts/sync-skills.sh"

if [ -x "$SYNC_SCRIPT" ]; then
  SKILLS_SOURCE_OVERRIDE="${REPO_ROOT}/skills" exec "$SYNC_SCRIPT"
else
  # Fallback: run inline if sync script doesn't exist yet
  echo "Warning: sync-skills.sh not found, skipping skill sync" >&2
fi
