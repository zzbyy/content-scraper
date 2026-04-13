# content-scraper

AI agent skill for scraping content from Chinese and international social platforms.
Works with **Claude Code** and **OpenClaw**. No personal API tokens needed.

## Supported Platforms

| Platform | Content | Method |
|---|---|---|
| X/Twitter | Posts, threads, bookmarks | nitter + HTML parsing |
| WeChat (公众号) | Articles | mptext.top API |
| Xiaohongshu (小红书) | Image notes | INITIAL_STATE parsing |
| Jike (即刻) | Posts + interaction data | Jina / direct parsing |
| Douyin (抖音) | Videos (no watermark) | Playwright + API interception |

## Install

**Both Claude Code + OpenClaw:**

```bash
curl -fsSL https://raw.githubusercontent.com/zzbyy/content-scraper/main/install.sh | bash
```

**Claude Code only:**

```bash
curl -fsSL https://raw.githubusercontent.com/zzbyy/content-scraper/main/install.sh | bash -s -- claude
```

**OpenClaw only:**

```bash
curl -fsSL https://raw.githubusercontent.com/zzbyy/content-scraper/main/install.sh | bash -s -- openclaw
```

Playwright (for Douyin only) is not auto-installed. To add it:

```bash
pip install playwright && playwright install chromium
```

## What Gets Installed

| Agent | Location |
|---|---|
| Claude Code | `~/.claude/skills/content-scraper-skill/` |
| OpenClaw | `~/.openclaw/skills/content-scraper/` |

## Usage

Once installed, just ask the agent to scrape a URL:

> "Scrape this WeChat article: https://mp.weixin.qq.com/s/xxx"
> "Download this Douyin video: https://www.douyin.com/video/xxx"
> "Extract this Xiaohongshu post: https://www.xiaohongshu.com/explore/xxx"

The skill triggers automatically on platform URLs and scraping-related keywords.
