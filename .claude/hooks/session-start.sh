#!/bin/bash
set -euo pipefail

# Only run in remote/cloud environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR}"

# ---- Load .env if present ----
ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

# ---- Detect exe.dev environment ----
if [ -f /etc/exe-dev-release ] || hostname -f 2>/dev/null | grep -q 'exe\.dev'; then
  export EXE_DEV=true
fi

# ---- Symlink skills ----
SKILLS_SOURCE="${PROJECT_DIR}/skills"
SKILLS_TARGET="${HOME}/.claude/skills"

mkdir -p "$SKILLS_TARGET"

for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"

  # Skip if already correctly linked
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill_dir" ]; then
    continue
  fi

  # Remove stale link or directory, then create symlink
  rm -rf "$target"
  ln -s "$skill_dir" "$target"
done

# ---- Ensure agent directories exist ----
mkdir -p "$HOME/agent/"{workspace,state,logs,scripts}
