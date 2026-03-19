#!/bin/bash
# ── Global SessionStart hook ──
# Installed to ~/.claude/hooks/session-start.sh by scripts/install.sh.
# Entry point for every Claude Code session on this machine.
#
# Checks all prerequisites loudly so missing setup is caught immediately,
# then delegates to sync-skills.sh.

set -euo pipefail

ERRORS=()
WARNINGS=()

# ── 1. CLAUDE_CONFIG_REPO must be set ────────────────────────────────────────
if [ -z "${CLAUDE_CONFIG_REPO:-}" ]; then
  ERRORS+=("CLAUDE_CONFIG_REPO is not set. Add this to your ~/.zshrc (or ~/.bashrc):")
  ERRORS+=("  export CLAUDE_CONFIG_REPO=\"\$HOME/dev/claude-config\"")
fi

# ── 2. Repo directory must exist ─────────────────────────────────────────────
if [ -n "${CLAUDE_CONFIG_REPO:-}" ] && [ ! -d "${CLAUDE_CONFIG_REPO}" ]; then
  ERRORS+=("CLAUDE_CONFIG_REPO points to a non-existent directory: ${CLAUDE_CONFIG_REPO}")
fi

# ── 3. Sync script must exist and be executable ───────────────────────────────
SYNC_SCRIPT="${CLAUDE_CONFIG_REPO:-}/scripts/sync-skills.sh"
if [ -n "${CLAUDE_CONFIG_REPO:-}" ] && [ -d "${CLAUDE_CONFIG_REPO}" ] && [ ! -x "${SYNC_SCRIPT}" ]; then
  ERRORS+=("Sync script not found or not executable: ${SYNC_SCRIPT}")
fi

# ── 4. Global CLAUDE.md must exist ────────────────────────────────────────────
if [ ! -f "${HOME}/.claude/CLAUDE.md" ]; then
  WARNINGS+=("~/.claude/CLAUDE.md not found — global instructions are missing.")
  if [ -n "${CLAUDE_CONFIG_REPO:-}" ]; then
    WARNINGS+=("  Fix: cp \"${CLAUDE_CONFIG_REPO}/CLAUDE.md\" ~/.claude/CLAUDE.md")
  fi
fi

# ── 5. Skills directory must exist and not be empty ───────────────────────────
SKILLS_DIR="${HOME}/.claude/skills"
if [ ! -d "${SKILLS_DIR}" ] || [ -z "$(ls -A "${SKILLS_DIR}" 2>/dev/null)" ]; then
  WARNINGS+=("~/.claude/skills/ is missing or empty — skills have not been synced yet.")
fi

# ── Print errors and abort ────────────────────────────────────────────────────
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "" >&2
  echo "╔══════════════════════════════════════════════════════════════╗" >&2
  echo "║  Claude Code setup is incomplete — session may not work!    ║" >&2
  echo "╚══════════════════════════════════════════════════════════════╝" >&2
  for msg in "${ERRORS[@]}"; do
    echo "  ✗ ${msg}" >&2
  done
  echo "" >&2
  exit 1
fi

# ── Print warnings (non-fatal) ────────────────────────────────────────────────
if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo "" >&2
  echo "⚠  Claude Code: setup warnings" >&2
  for msg in "${WARNINGS[@]}"; do
    echo "  ${msg}" >&2
  done
  echo "" >&2
fi

# ── Delegate to sync-skills.sh ───────────────────────────────────────────────
exec "${SYNC_SCRIPT}"
