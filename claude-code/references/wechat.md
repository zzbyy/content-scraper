# WeChat (公众号) Article Scraping Reference

## Overview

WeChat Official Account articles can be scraped using a free third-party API that converts them to markdown format.

## Method: mptext.top API

### Step 1: Get the Article URL

WeChat article URLs look like:
```
https://mp.weixin.qq.com/s/CljajqS3x3ETOe4tPubQzw
```

### Step 2: URL Encode the Link

The article URL must be URL-encoded before passing to the API.

```python
from urllib.parse import quote

def encode_wechat_url(url: str) -> str:
    """URL encode a WeChat article link."""
    return quote(url, safe='')

# Example:
# Input:  https://mp.weixin.qq.com/s/CljajqS3x3ETOe4tPubQzw
# Output: https%3A%2F%2Fmp.weixin.qq.com%2Fs%2FCljajqS3x3ETOe4tPubQzw
```

### Step 3: Call the API

```python
import requests
from urllib.parse import quote

def scrape_wechat_article(article_url: str, format: str = 'markdown') -> str:
    """
    Scrape a WeChat article using mptext.top API.
    
    Args:
        article_url: WeChat article URL (mp.weixin.qq.com/s/...)
        format: Output format - 'markdown' or 'html'
        
    Returns:
        Article content in requested format
    """
    encoded_url = quote(article_url, safe='')
    api_url = f"https://down.mptext.top/api/public/v1/download?url={encoded_url}&format={format}"
    
    response = requests.get(api_url, timeout=60)
    response.raise_for_status()
    
    return response.text
```

### API Parameters

| Parameter | Required | Values | Description |
|-----------|----------|--------|-------------|
| url | Yes | URL-encoded string | The encoded WeChat article URL |
| format | No | `markdown`, `html` | Output format (default: markdown) |

### Supported URL Formats

The API supports various WeChat URL patterns:

```
# Short links
https://mp.weixin.qq.com/s/CljajqS3x3ETOe4tPubQzw

# Long links with parameters
https://mp.weixin.qq.com/s?__biz=MzI1MjQ...&mid=2247...&idx=1&sn=...

# Mini-program article links
https://mp.weixin.qq.com/s?...
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""
WeChat (公众号) article scraper using mptext.top API.
"""

import requests
from urllib.parse import quote, urlparse
import re
import json

def is_wechat_url(url: str) -> bool:
    """Check if URL is a valid WeChat article URL."""
    parsed = urlparse(url)
    return parsed.netloc == 'mp.weixin.qq.com' and '/s' in parsed.path

def scrape_wechat_article(article_url: str, format: str = 'markdown') -> dict:
    """
    Scrape a WeChat Official Account article.
    
    Args:
        article_url: WeChat article URL
        format: 'markdown' or 'html'
        
    Returns:
        dict with content and metadata
    """
    if not is_wechat_url(article_url):
        raise ValueError(f"Not a valid WeChat URL: {article_url}")
    
    # URL encode the article link
    encoded_url = quote(article_url, safe='')
    
    # Call the API
    api_url = f"https://down.mptext.top/api/public/v1/download?url={encoded_url}&format={format}"
    
    try:
        response = requests.get(api_url, timeout=60, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        content = response.text
        
        # Try to extract title from markdown
        title = ''
        if format == 'markdown':
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                title = title_match.group(1)
        
        return {
            'url': article_url,
            'title': title,
            'content': content,
            'format': format,
            'success': True
        }
        
    except requests.RequestException as e:
        return {
            'url': article_url,
            'error': str(e),
            'success': False
        }

def batch_scrape_wechat(urls: list, format: str = 'markdown') -> list:
    """Scrape multiple WeChat articles."""
    results = []
    for url in urls:
        result = scrape_wechat_article(url, format)
        results.append(result)
    return results

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wechat_scraper.py <wechat_url> [format]")
        print("  format: markdown (default) or html")
        sys.exit(1)
    
    url = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else 'markdown'
    
    result = scrape_wechat_article(url, fmt)
    
    if result['success']:
        print(result['content'])
    else:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
```

---

## Alternative: Direct HTML Parsing

If the API is unavailable, you can scrape directly (requires cookies/session):

```python
import requests
from bs4 import BeautifulSoup

def scrape_wechat_direct(url: str) -> dict:
    """
    Direct scraping (less reliable, may need session/cookies).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        'Accept': 'text/html,application/xhtml+xml'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract article content
    title = soup.select_one('#activity-name')
    content = soup.select_one('#js_content')
    author = soup.select_one('#js_name')
    
    return {
        'title': title.get_text(strip=True) if title else '',
        'content': content.get_text(strip=True) if content else '',
        'content_html': str(content) if content else '',
        'author': author.get_text(strip=True) if author else '',
    }
```

## Notes

- The mptext.top API is free and doesn't require authentication
- Rate limiting may apply - add delays between requests if scraping many articles
- Some articles with special formatting may not convert perfectly
- Images in articles are usually preserved as links in markdown output
