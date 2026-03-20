#!/bin/bash
set -euo pipefail

# ── Project-level SessionStart hook ──
# Delegates to sync-skills.sh with the local repo as source.
# This runs when Claude Code is started inside the claude-config repo itself.

# Determine repo root (works for both local and cloud/remote)
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

SYNC_SCRIPT="${REPO_ROOT}/scripts/sync-skills.sh"

if [ -x "$SYNC_SCRIPT" ]; then
  SKILLS_SOURCE_OVERRIDE="${REPO_ROOT}/skills" exec "$SYNC_SCRIPT"
else
  echo "Warning: sync-skills.sh not found, skipping skill sync" >&2
fi
