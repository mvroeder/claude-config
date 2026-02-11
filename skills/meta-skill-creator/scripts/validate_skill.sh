#!/usr/bin/env bash
# Validate a Claude Code skill directory against the specification.
# Usage: validate_skill.sh <path-to-skill-directory>
#
# Exit code 0 = all checks passed
# Exit code 1 = one or more checks failed

set -euo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)) || true; }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)) || true; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; ((WARN++)) || true; }

# --- Argument check ---
if [ $# -lt 1 ]; then
    echo "Usage: validate_skill.sh <path-to-skill-directory>"
    exit 1
fi

SKILL_DIR="$1"

if [ ! -d "$SKILL_DIR" ]; then
    echo "Error: '$SKILL_DIR' is not a directory"
    exit 1
fi

SKILL_NAME=$(basename "$SKILL_DIR")
echo ""
echo "Validating skill: $SKILL_NAME"
echo "Path: $SKILL_DIR"
echo ""

# --- Structure checks ---
echo "Structure:"

if [ -f "$SKILL_DIR/SKILL.md" ]; then
    pass "SKILL.md exists"
else
    fail "SKILL.md missing (required)"
fi

if [ -f "$SKILL_DIR/IMPROVEMENTS.md" ]; then
    pass "IMPROVEMENTS.md exists"
else
    fail "IMPROVEMENTS.md missing (required by convention)"
fi

for antipattern in README.md CHANGELOG.md INSTALLATION_GUIDE.md QUICK_REFERENCE.md; do
    if [ -f "$SKILL_DIR/$antipattern" ]; then
        fail "$antipattern exists (anti-pattern — remove it)"
    fi
done

# Check for empty directories
for dir in "$SKILL_DIR"/*/; do
    [ ! -d "$dir" ] && continue
    count=$(find "$dir" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -eq 0 ]; then
        fail "Empty directory: $(basename "$dir")/ (remove or populate)"
    fi
done

echo ""

# --- Frontmatter checks ---
echo "YAML Frontmatter:"

if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    fail "Cannot check frontmatter — SKILL.md missing"
    echo ""
    echo "Results: $PASS passed, $FAIL failed, $WARN warnings"
    exit 1
fi

# Extract frontmatter (between first two --- lines)
FRONTMATTER=$(awk '/^---$/{n++; next} n==1{print} n>=2{exit}' "$SKILL_DIR/SKILL.md")

if [ -z "$FRONTMATTER" ]; then
    fail "No YAML frontmatter found (must start with --- on line 1)"
else
    pass "YAML frontmatter present"
fi

# Check name field
NAME_VALUE=$(echo "$FRONTMATTER" | awk -F': ' '/^name:/{print $2}' | tr -d ' ')
if [ -n "$NAME_VALUE" ]; then
    # Validate format: lowercase + hyphens + numbers only
    if echo "$NAME_VALUE" | grep -qE '^[a-z0-9-]+$'; then
        pass "name: '$NAME_VALUE' (valid format)"
    else
        fail "name: '$NAME_VALUE' (must be lowercase, numbers, hyphens only)"
    fi
    # Validate length
    NAME_LEN=${#NAME_VALUE}
    if [ "$NAME_LEN" -le 64 ]; then
        pass "name length: $NAME_LEN chars (max 64)"
    else
        fail "name length: $NAME_LEN chars (exceeds max 64)"
    fi
else
    warn "name field missing (will default to directory name: $SKILL_NAME)"
fi

# Check description field
DESC_VALUE=$(echo "$FRONTMATTER" | awk '/^description:/{sub(/^description: */, ""); print}')
if [ -n "$DESC_VALUE" ]; then
    pass "description present"
    DESC_LEN=${#DESC_VALUE}
    if [ "$DESC_LEN" -le 200 ]; then
        pass "description length: $DESC_LEN chars (max 200)"
    else
        fail "description length: $DESC_LEN chars (exceeds max 200)"
    fi
else
    fail "description missing (strongly recommended — Claude uses this for auto-activation)"
fi

# Check allowed-tools
TOOLS_VALUE=$(echo "$FRONTMATTER" | awk '/^allowed-tools:/{sub(/^allowed-tools: */, ""); print}')
if [ -n "$TOOLS_VALUE" ]; then
    pass "allowed-tools set: $TOOLS_VALUE"
else
    warn "allowed-tools not set (consider restricting for least privilege)"
fi

echo ""

# --- Body checks ---
echo "Body:"

TOTAL_LINES=$(wc -l < "$SKILL_DIR/SKILL.md" | tr -d ' ')
if [ "$TOTAL_LINES" -le 500 ]; then
    pass "Total lines: $TOTAL_LINES (max 500)"
else
    fail "Total lines: $TOTAL_LINES (exceeds max 500)"
fi

# Check for "When to Use" section in body (anti-pattern)
BODY=$(awk '/^---$/{n++; next} n>=2{print}' "$SKILL_DIR/SKILL.md")
if echo "$BODY" | grep -qi "when to use"; then
    warn "'When to Use' found in body (this belongs in the description field)"
fi

# Check for Self-Improvement Protocol
if echo "$BODY" | grep -qi "self-improvement\|improvements\.md"; then
    pass "Self-Improvement Protocol referenced"
else
    warn "No Self-Improvement Protocol found in body"
fi

echo ""

# --- Summary ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -gt 0 ]; then
    exit 1
else
    exit 0
fi
