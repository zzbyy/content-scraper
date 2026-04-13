---
name: content-scraper
description: >
  Scrape content from Chinese and international social platforms: X/Twitter
  (posts, threads, bookmarks), WeChat (公众号 articles), Xiaohongshu/RED
  (小红书 image notes), Jike (即刻 posts with interaction data), and Douyin
  (抖音 videos without watermark). Use when the user asks to extract, download,
  archive, or collect content from these platforms. Triggers: "scrape", "crawl",
  "extract", "download", "archive", "get this tweet", "grab that post",
  "download Douyin video", "scrape WeChat article", "extract Xiaohongshu post",
  "save this jike post". All methods are token-free and safe.
metadata:
  {
    "openclaw":
      {
        "emoji": "🕷️",
        "requires": { "anyBins": ["python3"] },
        "install":
          [
            {
              "id": "pip-deps",
              "kind": "shell",
              "command": "pip install requests beautifulsoup4 --break-system-packages",
              "label": "Install Python scraping dependencies (requests, bs4)",
            },
            {
              "id": "pip-playwright",
              "kind": "shell",
              "command": "pip install playwright --break-system-packages && playwright install chromium",
              "label": "Install Playwright + Chromium (for Douyin video scraping)",
            },
          ],
      },
  }
---

# Content Scraper

Scrape content from X/Twitter, WeChat, Xiaohongshu, Jike, and Douyin.
No personal API tokens needed. All methods are safe.

## Platform Detection

Identify the platform from the URL, then follow the matching section below.

| URL contains | Platform | Section |
|---|---|---|
| `x.com`, `twitter.com` | X/Twitter | [X/Twitter](#xtwitter) |
| `mp.weixin.qq.com` | WeChat | [WeChat](#wechat-公众号) |
| `xiaohongshu.com`, `xhslink.com` | Xiaohongshu | [Xiaohongshu](#xiaohongshu-小红书) |
| `okjike.com` | Jike | [Jike](#jike-即刻) |
| `douyin.com`, `v.douyin.com` | Douyin | [Douyin](#douyin-抖音) |

## Dependency Check

Run once before first scrape:

```bash
pip install requests beautifulsoup4 --break-system-packages 2>/dev/null || pip install requests beautifulsoup4
```

For Douyin video scraping only:

```bash
pip install playwright --break-system-packages 2>/dev/null || pip install playwright
playwright install chromium
```

---

## Using the Bundled Script

The fastest path for any platform. Auto-detects platform from URL.

```bash
# JSON output (structured, best for parsing)
python3 ~/.openclaw/skills/content-scraper/scripts/content_scraper_agent.py "URL" --json

# Human-readable output
python3 ~/.openclaw/skills/content-scraper/scripts/content_scraper_agent.py "URL"

# With media download
python3 ~/.openclaw/skills/content-scraper/scripts/content_scraper_agent.py "URL" --download --output-dir ./downloads
```

The script returns a standardized JSON result:

```json
{
  "success": true,
  "platform": "wechat",
  "title": "Article Title",
  "content": "Full text content...",
  "author": {"name": "Author Name"},
  "media": [{"url": "https://...", "type": "image"}],
  "stats": {"likes": 42, "comments": 5}
}
```

If the bundled script is not found at the expected path, fall back to the inline
methods below.

---

## X/Twitter

### Posts and Threads (nitter + HTML parsing)

Convert X URL to nitter format, fetch static HTML, parse content:

```bash
python3 -c "
import requests, re, json, sys
from bs4 import BeautifulSoup

url = sys.argv[1]
m = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', url)
if not m: print(json.dumps({'error':'Invalid URL'})); sys.exit(1)
user, sid = m.groups()

for inst in ['nitter.privacydev.net','nitter.poast.org','nitter.woodland.cafe']:
    try:
        r = requests.get(f'https://{inst}/{user}/status/{sid}',
            headers={'User-Agent':'Mozilla/5.0'}, timeout=30)
        if r.status_code != 200: continue
        soup = BeautifulSoup(r.text, 'html.parser')
        mt = soup.select_one('.main-tweet')
        if not mt: continue
        content = mt.select_one('.tweet-content')
        author = mt.select_one('.fullname')
        handle = mt.select_one('.username')
        stats = {}
        for st in ['comment','retweet','quote','heart']:
            el = mt.select_one(f'.icon-{st}')
            if el:
                p = el.find_parent('.tweet-stat')
                if p:
                    n = p.select_one('.tweet-stat-num')
                    stats[st] = n.get_text(strip=True) if n else '0'
        images = [img.get('src') for img in mt.select('.attachment.image img') if img.get('src')]
        print(json.dumps({
            'content': content.get_text(strip=True) if content else '',
            'author': author.get_text(strip=True) if author else '',
            'handle': handle.get_text(strip=True) if handle else '',
            'stats': stats, 'images': images
        }, ensure_ascii=False, indent=2))
        sys.exit(0)
    except: continue
print(json.dumps({'error':'All nitter instances failed'}))
" "TWITTER_URL"
```

### Bookmarks (fieldtheory)

X bookmark export requires the fieldtheory browser extension. Instruct the user
to install it and run the export from their browser. This cannot be done headlessly.

---

## WeChat (公众号)

Simplest method - one API call via mptext.top (free, no auth):

```bash
python3 -c "
from urllib.parse import quote
import requests, sys
encoded = quote(sys.argv[1], safe='')
r = requests.get(f'https://down.mptext.top/api/public/v1/download?url={encoded}&format=markdown', timeout=60)
r.raise_for_status()
print(r.text)
" "WECHAT_ARTICLE_URL"
```

URL format: `https://mp.weixin.qq.com/s/CljajqS3x3ETOe4tPubQzw`

The API returns full article content in markdown format including images as links.

---

## Xiaohongshu (小红书)

Fetch page HTML with mobile User-Agent, parse `window.__INITIAL_STATE__` for
structured data including images, author, and engagement stats:

```bash
python3 -c "
import requests, re, json, sys
from bs4 import BeautifulSoup

url = sys.argv[1]
# Expand short links
if 'xhslink.com' in url:
    url = requests.head(url, allow_redirects=True, timeout=10).url

r = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')

result = {'url': url, 'title': '', 'content': '', 'images': [], 'author': {}, 'stats': {}}

# Meta tags as fallback
for tag, key in [('og:title','title'), ('og:description','content'), ('og:image','cover')]:
    el = soup.find('meta', {'property': tag})
    if el: result[key] = el.get('content','')

# Full data from INITIAL_STATE
m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*(?:</script>|;\s*\n)', r.text, re.DOTALL)
if m:
    try:
        js = re.sub(r':\s*undefined', ': null', m.group(1))
        state = json.loads(js)
        nm = state.get('note',{}).get('noteDetailMap',{})
        if nm:
            note = list(nm.values())[0].get('note',{})
            result['title'] = note.get('title', result['title'])
            result['content'] = note.get('desc', result['content'])
            u = note.get('user',{})
            result['author'] = {'nickname': u.get('nickname',''), 'userId': u.get('userId','')}
            result['images'] = []
            for img in note.get('imageList',[]):
                iu = img.get('urlDefault') or img.get('url','')
                if iu and not iu.startswith('http'): iu = f'https://sns-img-bd.xhscdn.com/{iu}'
                if iu: result['images'].append(iu)
            inter = note.get('interactInfo',{})
            result['stats'] = {
                'likes': inter.get('likedCount',0),
                'collects': inter.get('collectedCount',0),
                'comments': inter.get('commentCount',0)
            }
    except: pass

print(json.dumps(result, ensure_ascii=False, indent=2))
" "XHS_URL"
```

---

## Jike (即刻)

Four methods available, ordered by simplicity:

### Method 1: Jina Reader (simplest, no interaction data)

```bash
curl -s "https://r.jina.ai/JIKE_URL"
```

### Method 2: Direct HTML parsing (with interaction data)

```bash
python3 -c "
import requests, re, json, sys
from bs4 import BeautifulSoup

r = requests.get(sys.argv[1], headers={
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
}, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')

result = {'url': sys.argv[1], 'content': '', 'author': {}, 'stats': {}, 'images': []}

for script in soup.find_all('script'):
    text = script.string or ''
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*(?:\n|$)', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            post = data.get('originalPost') or data.get('post') or {}
            if post:
                result['content'] = post.get('content','')
                u = post.get('user',{})
                result['author'] = {'screenName': u.get('screenName',''), 'username': u.get('username','')}
                result['stats'] = {'likes': post.get('likeCount',0), 'comments': post.get('commentCount',0), 'reposts': post.get('repostCount',0)}
                result['images'] = [p.get('picUrl','') for p in post.get('pictures',[])]
                break
        except: continue

if not result['content']:
    og = soup.find('meta', {'property': 'og:description'})
    if og: result['content'] = og.get('content','')

print(json.dumps(result, ensure_ascii=False, indent=2))
" "JIKE_URL"
```

Mobile URLs (`m.okjike.com`) work best.

---

## Douyin (抖音)

Requires Playwright + Chromium. Intercepts the internal API to get no-watermark
video URLs.

```bash
python3 -c "
import asyncio, json, sys

async def scrape(url):
    from playwright.async_api import async_playwright
    video_data = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width':1920,'height':1080}, locale='zh-CN')
        page = await ctx.new_page()

        async def on_resp(resp):
            nonlocal video_data
            if 'aweme/detail' in resp.url or 'aweme/v1/web/aweme/detail' in resp.url:
                try:
                    d = await resp.json()
                    if 'aweme_detail' in d or 'aweme_list' in d: video_data = d
                except: pass
        page.on('response', on_resp)

        if 'v.douyin.com' in url:
            await page.goto(url, wait_until='domcontentloaded')
            url = page.url
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)
        await browser.close()

    if not video_data: return {'error': 'Could not capture video data'}
    aw = video_data.get('aweme_detail') or (video_data.get('aweme_list',[{}])[0])
    v = aw.get('video',{})
    urls = v.get('play_addr',{}).get('url_list',[])
    vurl = urls[0].replace('/playwm/','/play/') if urls else ''
    auth = aw.get('author',{})
    stats = aw.get('statistics',{})
    return {
        'desc': aw.get('desc',''), 'video_url': vurl,
        'cover': v.get('cover',{}).get('url_list',[''])[0],
        'author': {'nickname': auth.get('nickname',''), 'uid': auth.get('uid','')},
        'stats': {'likes': stats.get('digg_count',0), 'comments': stats.get('comment_count',0),
                  'shares': stats.get('share_count',0), 'plays': stats.get('play_count',0)}
    }

print(json.dumps(asyncio.run(scrape(sys.argv[1])), ensure_ascii=False, indent=2))
" "DOUYIN_URL"
```

### Downloading the video after scraping

The video URL requires the `Referer: https://www.douyin.com/` header:

```bash
curl -L -H "Referer: https://www.douyin.com/" -H "User-Agent: Mozilla/5.0" -o video.mp4 "VIDEO_URL"
```

---

## Notes

- All methods avoid personal API tokens
- Add delays between requests when batch scraping
- Douyin is the heaviest (requires Playwright + Chromium)
- Xiaohongshu short links (xhslink.com) auto-expand via redirect
- WeChat API returns markdown by default
- For X bookmarks, the user must use the fieldtheory browser extension
