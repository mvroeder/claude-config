#!/bin/bash
set -euo pipefail

# ============================================================
# exe.dev VM Setup Script
# Run once after creating a new exe.dev box:
#   ssh exe.dev new
#   # then inside the VM:
#   git clone <this-repo> ~/claude-config
#   bash ~/claude-config/.claude/hooks/exe-dev-setup.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "==> exe.dev setup for claude-config"

# ---- 1. System packages ----
echo "==> Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  git \
  curl \
  jq \
  python3 \
  python3-venv \
  cron \
  2>/dev/null

# ---- 2. Install uv (Python package manager) ----
if ! command -v uv &>/dev/null; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# ---- 3. Install pyenv ----
if ! command -v pyenv &>/dev/null; then
  echo "==> Installing pyenv..."
  curl https://pyenv.run | bash

  # Add pyenv to shell profile
  SHELL_RC="$HOME/.bashrc"
  if ! grep -q 'pyenv' "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << 'PYENV_INIT'

# pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
PYENV_INIT
  fi
fi

# ---- 4. Create directory structure ----
echo "==> Creating directory structure..."
mkdir -p "$HOME/.claude/skills"
mkdir -p "$HOME/agent/{workspace,state,logs,scripts}"

# ---- 5. Load .env if present ----
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  echo "==> Loading environment from .env..."
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
else
  echo "==> WARNING: No .env file found at $ENV_FILE"
  echo "   Copy .env.example and fill in your keys:"
  echo "   cp $PROJECT_DIR/.env.example $ENV_FILE"
  echo "   chmod 600 $ENV_FILE"
fi

# ---- 6. Symlink skills (same as session-start) ----
echo "==> Symlinking skills..."
SKILLS_SOURCE="$PROJECT_DIR/skills"
SKILLS_TARGET="$HOME/.claude/skills"

for skill_dir in "$SKILLS_SOURCE"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_TARGET/$skill_name"

  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill_dir" ]; then
    continue
  fi

  rm -rf "$target"
  ln -s "$skill_dir" "$target"
  echo "   Linked: $skill_name"
done

# ---- 7. Install Python dependencies for research skill ----
RESEARCH_DIR="$PROJECT_DIR/skills/research-last30days"
if [ -d "$RESEARCH_DIR" ] && [ -f "$RESEARCH_DIR/requirements.txt" ]; then
  echo "==> Installing research skill dependencies..."
  uv pip install --system -r "$RESEARCH_DIR/requirements.txt" 2>/dev/null || true
fi

# ---- 8. Set up cron for scheduled tasks ----
echo "==> Configuring cron..."
CRON_MARKER="# claude-config-managed"
SCRIPTS_DIR="$HOME/agent/scripts"

# Create morning briefing script placeholder
if [ ! -f "$SCRIPTS_DIR/morning-briefing.sh" ]; then
  cat > "$SCRIPTS_DIR/morning-briefing.sh" << 'BRIEFING'
#!/bin/bash
# Morning briefing — customize this script
# Triggered daily via cron

set -euo pipefail

LOG_DIR="$HOME/agent/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/briefing-$(date +%Y-%m-%d).log"

echo "[$(date)] Starting morning briefing..." >> "$LOG_FILE"

# Uncomment and configure when integrations are ready:
# claude --print "Create my morning briefing..." >> "$LOG_FILE" 2>&1

echo "[$(date)] Briefing complete." >> "$LOG_FILE"
BRIEFING
  chmod +x "$SCRIPTS_DIR/morning-briefing.sh"
fi

# Add cron job if not already present
if ! crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
  (
    crontab -l 2>/dev/null || true
    echo "0 6 * * * $SCRIPTS_DIR/morning-briefing.sh $CRON_MARKER"
  ) | crontab -
  echo "   Cron job added: daily briefing at 06:00"
fi

# ---- 9. Shell profile integration ----
SHELL_RC="$HOME/.bashrc"
MARKER="# claude-config-env"
if ! grep -q "$MARKER" "$SHELL_RC" 2>/dev/null; then
  cat >> "$SHELL_RC" << SHELL_BLOCK

$MARKER
# Load claude-config environment
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a; source "$PROJECT_DIR/.env"; set +a
fi
export PATH="\$HOME/.local/bin:\$PATH"
SHELL_BLOCK
  echo "==> Shell profile updated."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy and fill in your API keys:"
echo "     cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"
echo "     chmod 600 $PROJECT_DIR/.env"
echo "  2. Source your profile:  source ~/.bashrc"
echo "  3. Start Claude Code:   claude"
echo ""
