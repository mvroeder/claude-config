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
HOOK_INSTALL_DIR="${HOME}/.claude/hooks"
HOOK_INSTALL_PATH="${HOOK_INSTALL_DIR}/session-start.sh"
HOOK_SOURCE="${CLAUDE_CONFIG_REPO:-}/hooks/global-session-start.sh"
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO:-}/scripts/sync-skills.sh"

# Hook command uses $HOME so it works across machines without absolute paths
HOOK_CMD="\$HOME/.claude/hooks/session-start.sh"

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

# ── Merge hook into user-level settings.json ─────────────────────────────────
if [ -f "$SETTINGS_FILE" ]; then
  # Check if hook is already registered (either old or new path)
  if grep -q "session-start.sh\|sync-skills.sh" "$SETTINGS_FILE" 2>/dev/null; then
    echo "Hook already registered in $SETTINGS_FILE"
    # Update old hook command to new path if needed
    if grep -q "sync-skills.sh" "$SETTINGS_FILE" 2>/dev/null; then
      if command -v jq >/dev/null 2>&1; then
        TMP="$(mktemp)"
        jq --arg old "\$CLAUDE_CONFIG_REPO/scripts/sync-skills.sh" \
           --arg new "$HOOK_CMD" '
          walk(if type == "string" and . == $old then $new else . end)
        ' "$SETTINGS_FILE" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"
        echo "Updated hook command to new stable path."
      else
        echo "WARNING: jq not installed. Please update the hook command manually in $SETTINGS_FILE"
        echo "  Old: \$CLAUDE_CONFIG_REPO/scripts/sync-skills.sh"
        echo "  New: $HOOK_CMD"
      fi
    fi
  else
    # Merge: add SessionStart hook to existing settings
    if command -v jq >/dev/null 2>&1; then
      TMP="$(mktemp)"
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
            "command": "${HOOK_CMD}"
          }
        ]
      }
    ]
  }
}
EOF
  echo "Created $SETTINGS_FILE with SessionStart hook."
fi

# ── Initial sync ──────────────────────────────────────────────────────────────
echo ""
echo "Running initial skill sync..."
"$SYNC_SCRIPT"
echo "Done! Skills synced to ~/.claude/skills/"

echo ""
echo "Setup complete. Every new Claude Code session will now auto-sync skills."
echo "To add a new skill: commit it to $CLAUDE_CONFIG_REPO/skills/ and push."
