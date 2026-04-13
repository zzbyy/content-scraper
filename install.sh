#!/usr/bin/env bash
set -euo pipefail

# Content Scraper Skill — remote installer (works with private repos via gh CLI)
# Usage:
#   gh repo clone zzbyy/content-scraper /tmp/cs && /tmp/cs/install.sh && rm -rf /tmp/cs
#   ... install.sh claude      # Claude Code only
#   ... install.sh openclaw    # OpenClaw only

MODE="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[!!]${NC} %s\n" "$1"; }
fail() { printf "${RED}[ERR]${NC} %s\n" "$1"; exit 1; }

# ── Python dependencies ─────────────────────────────────────────────
install_deps() {
  echo "Installing Python dependencies..."
  if   pip  install requests beautifulsoup4 --break-system-packages -q 2>/dev/null; then :
  elif pip  install requests beautifulsoup4 -q 2>/dev/null; then :
  elif pip3 install requests beautifulsoup4 --break-system-packages -q 2>/dev/null; then :
  elif pip3 install requests beautifulsoup4 -q 2>/dev/null; then :
  else fail "Could not install Python deps. Run: pip install requests beautifulsoup4"
  fi
  ok "requests + beautifulsoup4"

  if command -v playwright &>/dev/null; then
    ok "playwright already installed"
  else
    warn "playwright not installed (needed only for Douyin). Install later: pip install playwright && playwright install chromium"
  fi
}

# ── Claude Code ──────────────────────────────────────────────────────
install_claude() {
  local src="$SCRIPT_DIR/claude-code"
  local dest="$HOME/.claude/skills/content-scraper-skill"

  [ -d "$src" ] || fail "claude-code/ dir not found. Run from the repo root."

  echo "Installing Claude Code skill -> $dest"
  mkdir -p "$dest/references" "$dest/scripts"

  cp "$src/SKILL.md"                          "$dest/SKILL.md"
  cp "$src/scripts/content_scraper_agent.py"  "$dest/scripts/content_scraper_agent.py"
  for ref in "$src"/references/*.md; do
    cp "$ref" "$dest/references/"
  done
  chmod +x "$dest/scripts/content_scraper_agent.py"
  ok "Claude Code skill installed"
}

# ── OpenClaw ─────────────────────────────────────────────────────────
install_openclaw() {
  local src="$SCRIPT_DIR/openclaw"
  local dest="$HOME/.openclaw/skills/content-scraper"

  [ -d "$src" ] || fail "openclaw/ dir not found. Run from the repo root."

  echo "Installing OpenClaw skill -> $dest"
  mkdir -p "$dest/scripts"

  cp "$src/SKILL.md"                          "$dest/SKILL.md"
  cp "$src/scripts/content_scraper_agent.py"  "$dest/scripts/content_scraper_agent.py"
  chmod +x "$dest/scripts/content_scraper_agent.py"
  ok "OpenClaw skill installed"
}

# ── Main ─────────────────────────────────────────────────────────────
echo "Content Scraper Skill Installer"
echo "================================"

case "$MODE" in
  all)      install_deps; echo; install_claude; echo; install_openclaw ;;
  claude)   install_deps; echo; install_claude ;;
  openclaw) install_deps; echo; install_openclaw ;;
  *)
    echo "Usage: ./install.sh [all|claude|openclaw]"
    exit 1 ;;
esac

echo ""
ok "Done! Platforms: X/Twitter, WeChat, Xiaohongshu, Jike, Douyin"
