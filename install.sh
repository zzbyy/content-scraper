#!/usr/bin/env bash
set -euo pipefail

# Content Scraper Skill Installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/zzbyy/content-scraper/main/install.sh | bash
#   curl -fsSL ... | bash -s -- claude      # Claude Code only
#   curl -fsSL ... | bash -s -- openclaw    # OpenClaw only

REPO="zzbyy/content-scraper"
BRANCH="main"
BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
MODE="${1:-all}"

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[!!]${NC} %s\n" "$1"; }
fail() { printf "${RED}[ERR]${NC} %s\n" "$1"; exit 1; }

fetch() { curl -fsSL "$1" || fail "Failed to download $1"; }

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
  local dest="$HOME/.claude/skills/content-scraper-skill"
  echo "Installing Claude Code skill -> $dest"
  mkdir -p "$dest/references" "$dest/scripts"

  fetch "${BASE}/claude-code/SKILL.md"                          > "$dest/SKILL.md"
  fetch "${BASE}/claude-code/scripts/content_scraper_agent.py"  > "$dest/scripts/content_scraper_agent.py"
  for ref in douyin jike wechat x-twitter xiaohongshu; do
    fetch "${BASE}/claude-code/references/${ref}.md"            > "$dest/references/${ref}.md"
  done
  chmod +x "$dest/scripts/content_scraper_agent.py"
  ok "Claude Code skill installed"
}

# ── OpenClaw ─────────────────────────────────────────────────────────
install_openclaw() {
  local dest="$HOME/.openclaw/skills/content-scraper"
  echo "Installing OpenClaw skill -> $dest"
  mkdir -p "$dest/scripts"

  fetch "${BASE}/openclaw/SKILL.md"                             > "$dest/SKILL.md"
  fetch "${BASE}/openclaw/scripts/content_scraper_agent.py"     > "$dest/scripts/content_scraper_agent.py"
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
    echo "Usage: curl -fsSL <url>/install.sh | bash -s -- [all|claude|openclaw]"
    exit 1 ;;
esac

echo ""
ok "Done! Platforms: X/Twitter, WeChat, Xiaohongshu, Jike, Douyin"
