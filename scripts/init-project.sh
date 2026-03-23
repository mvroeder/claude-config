#!/bin/bash
set -euo pipefail

# ── init-project.sh ──────────────────────────────────────────────────────────
# Interactive setup for new projects with Claude Code integration.
# Creates: git repo, GitHub remote, CLAUDE.md, .gitignore, .env
#
# Usage:
#   init-project.sh                       # interactive
#   init-project.sh ~/dev/my-project      # with path, rest interactive

CLAUDE_CONFIG_REPO="${CLAUDE_CONFIG_REPO:-}"

# ── Colors & helpers ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}▸${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*" >&2; }

ask() {
  local prompt="$1" default="${2:-}" reply
  if [ -n "$default" ]; then
    echo -en "${BOLD}${prompt}${NC} [${default}]: " >/dev/tty
  else
    echo -en "${BOLD}${prompt}${NC}: " >/dev/tty
  fi
  read -r reply </dev/tty
  echo "${reply:-$default}"
}

ask_choice() {
  local prompt="$1"
  shift
  local options=("$@")
  echo -e "\n${BOLD}${prompt}${NC}" >/dev/tty
  for i in "${!options[@]}"; do
    echo "  $((i+1))) ${options[$i]}" >/dev/tty
  done
  local choice
  while true; do
    echo -en "${BOLD}Auswahl${NC} [1]: " >/dev/tty
    read -r choice </dev/tty
    choice="${choice:-1}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
      echo "${options[$((choice-1))]}"
      return
    fi
    error "Bitte 1-${#options[@]} eingeben."
  done
}

confirm() {
  local prompt="$1" default="${2:-y}"
  local hint="Y/n"
  [ "$default" = "n" ] && hint="y/N"
  echo -en "${BOLD}${prompt}${NC} [${hint}]: " >/dev/tty
  local reply
  read -r reply </dev/tty
  reply="${reply:-$default}"
  [[ "$reply" =~ ^[Yy] ]]
}

# ── Pre-flight checks ────────────────────────────────────────────────────────
if [ -z "$CLAUDE_CONFIG_REPO" ] || [ ! -d "$CLAUDE_CONFIG_REPO" ]; then
  error "CLAUDE_CONFIG_REPO is not set or directory doesn't exist."
  error "Run: export CLAUDE_CONFIG_REPO=\"\$HOME/dev/claude-config\""
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  error "GitHub CLI (gh) ist nicht installiert."
  error "Run: brew install gh"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  error "GitHub CLI ist nicht eingeloggt."
  error "Run: gh auth login"
  exit 1
fi

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  Claude Code – Neues Projekt Setup   ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Project path ──────────────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
  PROJECT_DIR="$(cd "$(dirname "$1")" 2>/dev/null && pwd)/$(basename "$1")" 2>/dev/null || PROJECT_DIR="$1"
else
  PROJECT_DIR="$(ask "Projektpfad" "$HOME/dev/")"
fi

PROJECT_NAME="$(basename "$PROJECT_DIR")"
PROJECT_NAME="$(ask "Projektname" "$PROJECT_NAME")"

# ── 2. Project type ──────────────────────────────────────────────────────────
PROJECT_TYPE="$(ask_choice "Projekttyp?" "Coding / Architektur" "Writing (PRDs, Whitepapers, Docs)" "Beides (Coding + Writing)")"

case "$PROJECT_TYPE" in
  "Coding"*) TEMPLATE_TYPE="coding" ;;
  "Writing"*) TEMPLATE_TYPE="writing" ;;
  "Beides"*) TEMPLATE_TYPE="both" ;;
esac

# ── 3. Visibility ────────────────────────────────────────────────────────────
VISIBILITY="$(ask_choice "GitHub Repository Sichtbarkeit?" "Private" "Public")"
case "$VISIBILITY" in
  "Private") GH_VISIBILITY="--private" ;;
  "Public")  GH_VISIBILITY="--public" ;;
esac

# ── 4. Description ────────────────────────────────────────────────────────────
DESCRIPTION="$(ask "Kurzbeschreibung (für GitHub)" "")"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Zusammenfassung ──${NC}"
info "Pfad:        $PROJECT_DIR"
info "Name:        $PROJECT_NAME"
info "Typ:         $PROJECT_TYPE"
info "Sichtbar:    $VISIBILITY"
[ -n "$DESCRIPTION" ] && info "Beschreibung: $DESCRIPTION"
echo ""

if ! confirm "Projekt erstellen?"; then
  echo "Abgebrochen."
  exit 0
fi

echo ""

# ── Create directory ──────────────────────────────────────────────────────────
if [ -d "$PROJECT_DIR" ]; then
  warn "Verzeichnis existiert bereits: $PROJECT_DIR"
  if [ -d "$PROJECT_DIR/.git" ]; then
    warn "Git-Repository existiert bereits — überspringe git init."
    GIT_EXISTS=true
  else
    GIT_EXISTS=false
  fi
else
  mkdir -p "$PROJECT_DIR"
  success "Verzeichnis erstellt: $PROJECT_DIR"
  GIT_EXISTS=false
fi

# ── Git init ──────────────────────────────────────────────────────────────────
if [ "$GIT_EXISTS" = false ]; then
  git -C "$PROJECT_DIR" init --quiet
  success "Git-Repository initialisiert"
fi

# ── CLAUDE.md ─────────────────────────────────────────────────────────────────
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  warn "CLAUDE.md existiert bereits — überspringe."
else
  case "$TEMPLATE_TYPE" in
    coding)
      cp "$CLAUDE_CONFIG_REPO/templates/CLAUDE-coding.md" "$CLAUDE_MD"
      # Replace project name placeholder
      sed -i '' "s/<PROJEKTNAME>/${PROJECT_NAME}/" "$CLAUDE_MD" 2>/dev/null || \
        sed -i "s/<PROJEKTNAME>/${PROJECT_NAME}/" "$CLAUDE_MD"
      success "CLAUDE.md erstellt (Coding-Template)"
      ;;
    writing)
      cp "$CLAUDE_CONFIG_REPO/templates/CLAUDE-writing.md" "$CLAUDE_MD"
      sed -i '' "s/<PROJEKTNAME>/${PROJECT_NAME}/" "$CLAUDE_MD" 2>/dev/null || \
        sed -i "s/<PROJEKTNAME>/${PROJECT_NAME}/" "$CLAUDE_MD"
      success "CLAUDE.md erstellt (Writing-Template)"
      ;;
    both)
      {
        cat "$CLAUDE_CONFIG_REPO/templates/CLAUDE-coding.md"
        echo ""
        echo "---"
        echo ""
        echo "# Writing & Documentation"
        echo ""
        # Append writing template without the first header line
        tail -n +1 "$CLAUDE_CONFIG_REPO/templates/CLAUDE-writing.md" | sed '1,/^# /{ /^# /d; }'
      } > "$CLAUDE_MD"
      sed -i '' "s/<PROJEKTNAME>/${PROJECT_NAME}/g" "$CLAUDE_MD" 2>/dev/null || \
        sed -i "s/<PROJEKTNAME>/${PROJECT_NAME}/g" "$CLAUDE_MD"
      success "CLAUDE.md erstellt (Coding + Writing kombiniert)"
      ;;
  esac
fi

# ── .gitignore ────────────────────────────────────────────────────────────────
GITIGNORE="$PROJECT_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
  # Append .env rule if not present
  if ! grep -q "^\.env" "$GITIGNORE" 2>/dev/null; then
    echo "" >> "$GITIGNORE"
    echo "# Secrets" >> "$GITIGNORE"
    echo ".env" >> "$GITIGNORE"
    echo ".env.*" >> "$GITIGNORE"
    echo "!.env.example" >> "$GITIGNORE"
    success ".env-Regeln zu bestehender .gitignore hinzugefügt"
  else
    warn ".gitignore existiert bereits mit .env-Regel — überspringe."
  fi
else
  cat > "$GITIGNORE" <<'GITIGNORE_EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/

# Secrets
.env
.env.*
!.env.example

# Build
dist/
build/
.next/
out/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Claude Code
.claude/settings.local.json
CLAUDE.local.md
GITIGNORE_EOF
  success ".gitignore erstellt"
fi

# ── .env.example ──────────────────────────────────────────────────────────────
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
if [ ! -f "$ENV_EXAMPLE" ]; then
  cat > "$ENV_EXAMPLE" <<'ENV_EOF'
# Copy this file to .env and fill in the values
# cp .env.example .env

# Example:
# API_KEY=
# DATABASE_URL=
ENV_EOF
  success ".env.example erstellt"
fi

# ── README.md ─────────────────────────────────────────────────────────────────
README="$PROJECT_DIR/README.md"
if [ ! -f "$README" ]; then
  {
    echo "# ${PROJECT_NAME}"
    echo ""
    if [ -n "$DESCRIPTION" ]; then
      echo "$DESCRIPTION"
      echo ""
    fi
  } > "$README"
  success "README.md erstellt"
fi

# ── Initial commit ────────────────────────────────────────────────────────────
if [ "$GIT_EXISTS" = false ]; then
  git -C "$PROJECT_DIR" add -A
  git -C "$PROJECT_DIR" commit --quiet -m "chore: initial project setup

Created with claude-config/scripts/init-project.sh"
  success "Initialer Commit erstellt"
fi

# ── GitHub repo ───────────────────────────────────────────────────────────────
GH_ARGS=(
  --source "$PROJECT_DIR"
  $GH_VISIBILITY
)

if [ -n "$DESCRIPTION" ]; then
  GH_ARGS+=(--description "$DESCRIPTION")
fi

# Check if remote already exists
if git -C "$PROJECT_DIR" remote get-url origin >/dev/null 2>&1; then
  warn "GitHub Remote existiert bereits — überspringe."
else
  info "Erstelle GitHub Repository..."
  if gh repo create "$PROJECT_NAME" "${GH_ARGS[@]}" --push 2>/dev/null; then
    success "GitHub Repository erstellt und gepusht"
  else
    # Repo might already exist — try to add remote and push
    warn "gh repo create fehlgeschlagen — versuche existierendes Repo zu verknüpfen..."
    GH_USER="$(gh api user --jq .login 2>/dev/null || echo "mvroeder")"
    git -C "$PROJECT_DIR" remote add origin "git@github.com:${GH_USER}/${PROJECT_NAME}.git" 2>/dev/null || true
    git -C "$PROJECT_DIR" push -u origin main 2>/dev/null && \
      success "Mit bestehendem GitHub-Repo verknüpft und gepusht" || \
      warn "Push fehlgeschlagen — bitte manuell verknüpfen."
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  Projekt ${PROJECT_NAME} ist bereit!${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
info "Nächste Schritte:"
echo "  1. cd $PROJECT_DIR"
echo "  2. CLAUDE.md anpassen (Platzhalter ausfüllen)"
echo "  3. claude  ← Claude Code starten"
echo ""
