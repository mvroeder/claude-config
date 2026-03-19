#!/bin/bash
set -euo pipefail

# ── Install claude-config: register user-level SessionStart hook ──
# Run once per machine. Requires $CLAUDE_CONFIG_REPO to be set.
#
# What it does:
#   1. Checks that CLAUDE_CONFIG_REPO is set and valid
#   2. Adds a user-level SessionStart hook to ~/.claude/settings.json
#   3. Runs an initial skill sync

SETTINGS_FILE="${HOME}/.claude/settings.json"
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO:-}/scripts/sync-skills.sh"

# ── Pre-flight checks ──
if [ -z "${CLAUDE_CONFIG_REPO:-}" ]; then
  echo "ERROR: CLAUDE_CONFIG_REPO is not set."
  echo ""
  echo "Add this to your ~/.zshrc (or ~/.bashrc):"
  echo ""
  echo "  export CLAUDE_CONFIG_REPO=\"\$HOME/Projects/claude-config\""
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
  echo "ERROR: Sync script not found: $SYNC_SCRIPT"
  exit 1
fi

# ── Ensure ~/.claude/ exists ──
mkdir -p "$(dirname "$SETTINGS_FILE")"

# ── Hook command (uses env var so no absolute paths in config) ──
HOOK_CMD="\$CLAUDE_CONFIG_REPO/scripts/sync-skills.sh"

# ── Merge hook into user-level settings.json ──
if [ -f "$SETTINGS_FILE" ]; then
  # Check if hook is already registered
  if grep -q "sync-skills.sh" "$SETTINGS_FILE" 2>/dev/null; then
    echo "Hook already registered in $SETTINGS_FILE"
  else
    # Merge: add SessionStart hook to existing settings
    # Use a temp file for safe in-place update
    TMP="$(mktemp)"
    if command -v jq >/dev/null 2>&1; then
      jq --arg cmd "$HOOK_CMD" '
        .hooks //= {} |
        .hooks.SessionStart //= [] |
        .hooks.SessionStart += [{"hooks": [{"type": "command", "command": $cmd}]}]
      ' "$SETTINGS_FILE" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"
      echo "Hook added to existing $SETTINGS_FILE"
    else
      echo "WARNING: jq not installed. Please add the hook manually."
      echo ""
      echo "Add this to $SETTINGS_FILE under \"hooks\".\"SessionStart\":"
      echo ""
      echo "  {\"hooks\": [{\"type\": \"command\", \"command\": \"$HOOK_CMD\"}]}"
      rm -f "$TMP"
      exit 1
    fi
  fi
else
  # Create fresh settings file
  cat > "$SETTINGS_FILE" <<EOF
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOOK_CMD"
          }
        ]
      }
    ]
  }
}
EOF
  echo "Created $SETTINGS_FILE with SessionStart hook."
fi

# ── Initial sync ──
echo ""
echo "Running initial skill sync..."
"$SYNC_SCRIPT"
echo "Done! Skills synced to ~/.claude/skills/"

echo ""
echo "Setup complete. Every new Claude Code session will now auto-sync skills."
echo "To add a new skill: commit it to $CLAUDE_CONFIG_REPO/skills/ and push."
