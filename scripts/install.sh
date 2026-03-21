#!/bin/bash
set -euo pipefail

# ── Install claude-config: register user-level SessionStart hook ──
# Run once per machine. Requires $CLAUDE_CONFIG_REPO to be set.
#
# What it does:
#   1. Checks that CLAUDE_CONFIG_REPO is set and valid
#   2. Installs hooks/global-session-start.sh to ~/.claude/hooks/session-start.sh
#   3. Adds a user-level SessionStart hook to ~/.claude/settings.json
#   4. Runs an initial skill sync

SETTINGS_FILE="${HOME}/.claude/settings.json"
SETTINGS_SOURCE="${CLAUDE_CONFIG_REPO:-}/settings.json"
HOOK_INSTALL_DIR="${HOME}/.claude/hooks"
HOOK_INSTALL_PATH="${HOOK_INSTALL_DIR}/session-start.sh"
HOOK_SOURCE="${CLAUDE_CONFIG_REPO:-}/hooks/global-session-start.sh"
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO:-}/scripts/sync-skills.sh"

# ── Pre-flight checks ──────────────────────────────────────────────────────────
if [ -z "${CLAUDE_CONFIG_REPO:-}" ]; then
  echo "ERROR: CLAUDE_CONFIG_REPO is not set."
  echo ""
  echo "Add this to your ~/.zshrc (or ~/.bashrc):"
  echo ""
  echo "  export CLAUDE_CONFIG_REPO=\"\$HOME/dev/claude-config\""
  echo ""
  echo "Then reload your shell and run this script again."
  exit 1
fi

if [ ! -d "$CLAUDE_CONFIG_REPO" ]; then
  echo "ERROR: Directory not found: $CLAUDE_CONFIG_REPO"
  echo "Clone the repo first, then run this script again."
  exit 1
fi

if [ ! -x "$SYNC_SCRIPT" ]; then
  echo "ERROR: Sync script not found or not executable: $SYNC_SCRIPT"
  exit 1
fi

if [ ! -f "$HOOK_SOURCE" ]; then
  echo "ERROR: Hook source not found: $HOOK_SOURCE"
  exit 1
fi

# ── Install hook script to ~/.claude/hooks/ ───────────────────────────────────
mkdir -p "$HOOK_INSTALL_DIR"
cp "$HOOK_SOURCE" "$HOOK_INSTALL_PATH"
chmod +x "$HOOK_INSTALL_PATH"
echo "Installed hook: $HOOK_INSTALL_PATH"

# ── Ensure ~/.claude/ exists ──────────────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"

# ── Install settings.json (merge repo version with existing user settings) ───
if [ ! -f "$SETTINGS_SOURCE" ]; then
  echo "ERROR: Settings source not found: $SETTINGS_SOURCE"
  exit 1
fi

if [ -f "$SETTINGS_FILE" ]; then
  if command -v jq >/dev/null 2>&1; then
    # Deep-merge: repo settings as base, user settings on top, then repo hooks win
    TMP="$(mktemp)"
    jq -s '.[0] * .[1] * { hooks: .[0].hooks }' \
      "$SETTINGS_SOURCE" "$SETTINGS_FILE" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"
    echo "Merged repo settings into $SETTINGS_FILE (hooks from repo, other settings preserved)."
  else
    echo "WARNING: jq not installed. Replacing $SETTINGS_FILE with repo version."
    echo "  Any custom permissions will need to be re-added."
    cp "$SETTINGS_SOURCE" "$SETTINGS_FILE"
  fi
else
  cp "$SETTINGS_SOURCE" "$SETTINGS_FILE"
  echo "Created $SETTINGS_FILE from repo version."
fi

# ── Initial sync ──────────────────────────────────────────────────────────────
echo ""
echo "Running initial skill sync..."
"$SYNC_SCRIPT"
echo "Done! Skills synced to ~/.claude/skills/"

echo ""
echo "Setup complete. Every new Claude Code session will now auto-sync skills."
echo "To add a new skill: commit it to $CLAUDE_CONFIG_REPO/skills/ and push."
