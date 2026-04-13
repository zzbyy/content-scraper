---
name: content-scraper
description: >
  Scrape content from Chinese and international social platforms including
  X/Twitter (posts, threads, bookmarks), WeChat articles (公众号),
  Xiaohongshu/RED (小红书), Jike (即刻), and Douyin (抖音).
  Use this skill whenever the user wants to extract, download, archive, or
  collect content from these platforms. Triggers include mentions of scraping,
  crawling, extracting, downloading, archiving posts/articles/videos, or any
  platform-specific requests like "get this tweet", "download this Douyin video",
  "scrape WeChat article", "extract Xiaohongshu post", "grab that jike post".
  All methods are token-free and use the safest available approaches.
---

# Content Scraper

Scrape content from X/Twitter, WeChat, Xiaohongshu, Jike, and Douyin.
No personal API tokens required.

## Dependency Check

Before first use, ensure dependencies are installed:

```bash
pip install requests beautifulsoup4 --break-system-packages 2>/dev/null || pip install requests beautifulsoup4
# For Douyin only:
pip install playwright --break-system-packages 2>/dev/null || pip install playwright
playwright install chromium 2>/dev/null || true
```

## Workflow

1. Identify the platform from the URL
2. Read the platform-specific reference for detailed code
3. Execute the scraping method
4. Return structured content to the user

## Platform Routing

| URL pattern | Platform | Reference |
|---|---|---|
| `x.com/*`, `twitter.com/*` | X/Twitter | `references/x-twitter.md` |
| `mp.weixin.qq.com/*` | WeChat | `references/wechat.md` |
| `xiaohongshu.com/*`, `xhslink.com/*` | Xiaohongshu | `references/xiaohongshu.md` |
| `okjike.com/*`, `m.okjike.com/*` | Jike | `references/jike.md` |
| `douyin.com/*`, `v.douyin.com/*` | Douyin | `references/douyin.md` |

## Quick Inline Methods

For simple cases, use these directly without reading reference files.

### WeChat (simplest - one curl call)

```bash
# URL-encode the article link, then call the free API
python3 -c "
from urllib.parse import quote
import requests, sys
url = quote(sys.argv[1], safe='')
r = requests.get(f'https://down.mptext.top/api/public/v1/download?url={url}&format=markdown', timeout=60)
print(r.text)
" "WECHAT_URL_HERE"
```

### X/Twitter (nitter proxy)

```bash
# Convert x.com URL to nitter, fetch static HTML, parse with BeautifulSoup
# See references/x-twitter.md for full code with fallback instances
```

### Xiaohongshu (HTML + INITIAL_STATE parsing)

```bash
# Fetch page with mobile UA, parse window.__INITIAL_STATE__ JSON
# Extracts: title, description, images, author, stats
# See references/xiaohongshu.md for full code
```

### Jike (multiple methods)

- **Jina** (simplest, no stats): `curl -s "https://r.jina.ai/JIKE_URL"`
- **Direct parsing** (with stats): fetch HTML, parse `__INITIAL_STATE__`
- See `references/jike.md` for all 4 methods

### Douyin (requires Playwright)

```bash
# Requires headless Chromium to bypass signature verification
# Intercepts aweme/detail API response for no-watermark video URL
# See references/douyin.md for full async Playwright code
```

## Using the Bundled Script

For complex or batch scraping, use the bundled Python script:

```bash
# Single URL scrape
python3 scripts/content_scraper_agent.py "URL" --json

# With media download
python3 scripts/content_scraper_agent.py "URL" --download --output-dir ./downloads
```

The script auto-detects the platform and returns a standardized JSON result with:
`success`, `platform`, `title`, `content`, `author`, `media[]`, `stats`.

## Important Notes

- All methods avoid personal API tokens - safe by design
- Add delays between requests when batch scraping (rate limiting)
- Douyin requires Playwright + Chromium (heavier dependency)
- Xiaohongshu short links (xhslink.com) are auto-expanded via redirect
- WeChat API returns markdown format by default
