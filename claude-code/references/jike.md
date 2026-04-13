# Jike (即刻) Scraping Reference

## Overview

Jike articles and posts can be scraped using multiple methods, each with different trade-offs for interaction data availability.

## Method Comparison

| Method | Interaction Data | Free | Complexity |
|--------|-----------------|------|------------|
| Jina | ❌ | ✅ | Low |
| Camoufox | ❌ | ✅ | Medium |
| xcrawl | ✅ | ✅ | Medium |
| curl + parsing | ✅ | ✅ | High |

---

## Method 1: Jina (Simplest)

Jina Reader converts any URL to markdown. Fast but doesn't capture interaction data.

```python
import requests

def scrape_jike_via_jina(url: str) -> str:
    """
    Scrape Jike content using Jina Reader.
    No interaction data (likes, comments, etc.)
    """
    jina_url = f"https://r.jina.ai/{url}"
    
    response = requests.get(jina_url, timeout=60, headers={
        'Accept': 'text/markdown'
    })
    response.raise_for_status()
    
    return response.text
```

### Example Usage

```python
url = "https://m.okjike.com/originalPosts/xxxxx"
content = scrape_jike_via_jina(url)
print(content)
```

---

## Method 2: Camoufox

Camoufox is a stealth browser for bypassing detection. Also doesn't capture interaction data directly.

```python
# Requires: pip install camoufox playwright
# Then: camoufox fetch

from camoufox.sync_api import Camoufox

def scrape_jike_via_camoufox(url: str) -> dict:
    """
    Scrape Jike using Camoufox stealth browser.
    """
    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        page.goto(url, wait_until='networkidle')
        
        # Wait for content to load
        page.wait_for_selector('.post-content', timeout=10000)
        
        content = page.content()
        
    return parse_jike_html(content)

def parse_jike_html(html: str) -> dict:
    """Parse Jike page HTML."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract post content (selectors may need updating)
    post = soup.select_one('.post-content, .original-post')
    author = soup.select_one('.username, .nickname')
    
    return {
        'content': post.get_text(strip=True) if post else '',
        'author': author.get_text(strip=True) if author else '',
        'html': str(post) if post else ''
    }
```

---

## Method 3: xcrawl (Recommended for Full Data)

xcrawl can capture interaction data including likes, comments, reposts.

```python
import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_jike_via_xcrawl(url: str) -> dict:
    """
    Scrape Jike post with full interaction data using xcrawl approach.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text
    
    # Parse initial state from script tags
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the script containing the post data
    scripts = soup.find_all('script')
    post_data = None
    
    for script in scripts:
        script_text = script.string or ''
        
        # Look for __INITIAL_STATE__ or similar
        if '__INITIAL_STATE__' in script_text or 'window.__NUXT__' in script_text:
            # Extract JSON
            json_match = re.search(r'(\{.+\})', script_text, re.DOTALL)
            if json_match:
                try:
                    post_data = json.loads(json_match.group(1))
                    break
                except json.JSONDecodeError:
                    continue
    
    if post_data:
        return extract_jike_data(post_data)
    
    # Fallback to HTML parsing
    return parse_jike_html_basic(soup)

def extract_jike_data(data: dict) -> dict:
    """Extract post data from Jike's initial state."""
    # Navigate to post data (structure varies)
    post = None
    
    # Try common paths
    if 'originalPost' in data:
        post = data['originalPost']
    elif 'post' in data:
        post = data['post']
    elif 'data' in data and 'originalPost' in data.get('data', {}):
        post = data['data']['originalPost']
    
    if not post:
        return {'raw_data': data}
    
    return {
        'id': post.get('id', ''),
        'content': post.get('content', ''),
        'type': post.get('type', ''),
        'user': {
            'id': post.get('user', {}).get('id', ''),
            'screenName': post.get('user', {}).get('screenName', ''),
            'username': post.get('user', {}).get('username', ''),
            'avatarImage': post.get('user', {}).get('avatarImage', {}).get('smallPicUrl', ''),
        },
        'topic': post.get('topic', {}).get('content', ''),
        'stats': {
            'likeCount': post.get('likeCount', 0),
            'commentCount': post.get('commentCount', 0),
            'repostCount': post.get('repostCount', 0),
            'shareCount': post.get('shareCount', 0),
        },
        'pictures': [p.get('picUrl', '') for p in post.get('pictures', [])],
        'createdAt': post.get('createdAt', ''),
    }

def parse_jike_html_basic(soup) -> dict:
    """Basic HTML parsing fallback."""
    return {
        'title': soup.title.string if soup.title else '',
        'content': soup.get_text(strip=True)[:1000],
    }
```

---

## Method 4: curl + Direct Parsing (Full Control)

For maximum control and guaranteed interaction data:

```python
import subprocess
import json

def scrape_jike_via_curl(url: str) -> dict:
    """
    Scrape Jike using curl for maximum compatibility.
    """
    # Use curl with mobile user agent
    curl_cmd = [
        'curl', '-s',
        '-H', 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        '-H', 'Accept: text/html',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9',
        '-L',  # Follow redirects
        url
    ]
    
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    
    return parse_jike_response(result.stdout)

def parse_jike_response(html: str) -> dict:
    """Parse Jike HTML response."""
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'content': '',
        'author': '',
        'stats': {},
        'images': [],
    }
    
    # Try to find embedded JSON data
    for script in soup.find_all('script'):
        text = script.string or ''
        if 'originalPost' in text or '__INITIAL_STATE__' in text:
            # Extract and parse JSON
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return extract_jike_data(data)
                except json.JSONDecodeError:
                    pass
    
    # Fallback: parse visible content
    content_elem = soup.select_one('[class*="content"], [class*="post-text"]')
    if content_elem:
        result['content'] = content_elem.get_text(strip=True)
    
    # Get images
    for img in soup.select('img[src*="jike"], img[src*="okjike"]'):
        result['images'].append(img.get('src', ''))
    
    return result
```

---

## Complete Example Script

```python
#!/usr/bin/env python3
"""
Jike (即刻) content scraper with multiple methods.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import sys
from urllib.parse import urlparse

def is_jike_url(url: str) -> bool:
    """Check if URL is a valid Jike URL."""
    parsed = urlparse(url)
    return parsed.netloc in ['okjike.com', 'm.okjike.com', 'www.okjike.com', 'web.okjike.com']

def scrape_jike(url: str, method: str = 'auto') -> dict:
    """
    Scrape a Jike post using specified method.
    
    Args:
        url: Jike post URL
        method: 'jina', 'xcrawl', 'curl', or 'auto'
        
    Returns:
        dict with post content and metadata
    """
    if not is_jike_url(url):
        raise ValueError(f"Not a valid Jike URL: {url}")
    
    if method == 'jina':
        content = scrape_via_jina(url)
        return {'content': content, 'method': 'jina'}
    
    elif method == 'curl':
        return scrape_via_curl(url)
    
    elif method == 'xcrawl' or method == 'auto':
        return scrape_via_requests(url)
    
    else:
        raise ValueError(f"Unknown method: {method}")

def scrape_via_jina(url: str) -> str:
    """Simple Jina reader approach."""
    jina_url = f"https://r.jina.ai/{url}"
    response = requests.get(jina_url, timeout=60)
    return response.text

def scrape_via_requests(url: str) -> dict:
    """Direct requests with full parsing."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept': 'text/html,application/xhtml+xml',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'url': url,
        'method': 'xcrawl',
        'content': '',
        'author': {},
        'stats': {},
        'images': [],
    }
    
    # Try to extract from scripts
    for script in soup.find_all('script'):
        text = script.string or ''
        
        # Look for initial state data
        state_match = re.search(r'window\.__(?:INITIAL_STATE__|NUXT__)?\s*=\s*(\{.+?\});?\s*(?:\n|$)', text, re.DOTALL)
        if state_match:
            try:
                data = json.loads(state_match.group(1))
                extracted = extract_post_data(data)
                if extracted.get('content'):
                    result.update(extracted)
                    return result
            except json.JSONDecodeError:
                continue
    
    # Fallback to HTML content
    og_title = soup.find('meta', {'property': 'og:title'})
    og_desc = soup.find('meta', {'property': 'og:description'})
    
    if og_title:
        result['title'] = og_title.get('content', '')
    if og_desc:
        result['content'] = og_desc.get('content', '')
    
    return result

def scrape_via_curl(url: str) -> dict:
    """Use curl subprocess."""
    import subprocess
    
    cmd = ['curl', '-sL', '-H', 'User-Agent: Mozilla/5.0 (iPhone)', url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return {'error': result.stderr}
    
    return scrape_html_content(result.stdout, url)

def scrape_html_content(html: str, url: str) -> dict:
    """Parse HTML content from curl output."""
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {'url': url, 'method': 'curl'}
    
    # Try JSON extraction first
    for script in soup.find_all('script'):
        text = script.string or ''
        if '__INITIAL_STATE__' in text:
            match = re.search(r'=\s*(\{.+?\});', text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    result.update(extract_post_data(data))
                    return result
                except:
                    pass
    
    # Fallback
    result['content'] = soup.get_text(strip=True)[:500]
    return result

def extract_post_data(data: dict) -> dict:
    """Extract post from Jike's state object."""
    post = None
    
    # Try various paths
    for path in ['originalPost', 'post', ('data', 'originalPost'), ('state', 'post')]:
        if isinstance(path, tuple):
            current = data
            for key in path:
                current = current.get(key, {}) if isinstance(current, dict) else {}
            if current:
                post = current
                break
        elif path in data:
            post = data[path]
            break
    
    if not post:
        return {}
    
    return {
        'id': post.get('id', ''),
        'content': post.get('content', ''),
        'author': {
            'screenName': post.get('user', {}).get('screenName', ''),
            'username': post.get('user', {}).get('username', ''),
        },
        'stats': {
            'likes': post.get('likeCount', 0),
            'comments': post.get('commentCount', 0),
            'reposts': post.get('repostCount', 0),
        },
        'images': [p.get('picUrl', '') for p in post.get('pictures', [])],
        'created_at': post.get('createdAt', ''),
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python jike_scraper.py <jike_url> [method]")
        print("  method: jina, xcrawl, curl, or auto (default)")
        sys.exit(1)
    
    url = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    result = scrape_jike(url, method)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## Notes

- Jina is simplest but doesn't capture stats
- xcrawl/curl methods capture full interaction data
- Mobile URLs (m.okjike.com) often work better
- Page structure may change - update selectors as needed
