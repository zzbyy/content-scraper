# X/Twitter Scraping Reference

## Method 1: Posts and Long Articles (nitter + xcrawl)

### Overview
Uses nitter instances to convert X/Twitter pages to static HTML, then xcrawl to extract structured data.

### Step 1: Convert URL to Nitter Format

```python
def convert_to_nitter(twitter_url: str, nitter_instance: str = "nitter.privacydev.net") -> str:
    """Convert X/Twitter URL to nitter equivalent."""
    import re
    
    # Extract username and status ID
    pattern = r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)'
    match = re.search(pattern, twitter_url)
    
    if match:
        username, status_id = match.groups()
        return f"https://{nitter_instance}/{username}/status/{status_id}"
    
    # For profile URLs
    profile_pattern = r'(?:twitter\.com|x\.com)/(\w+)/?$'
    profile_match = re.search(profile_pattern, twitter_url)
    if profile_match:
        username = profile_match.group(1)
        return f"https://{nitter_instance}/{username}"
    
    return twitter_url
```

### Step 2: Fetch via Nitter

```python
import requests

def fetch_nitter_page(nitter_url: str) -> str:
    """Fetch the static HTML from nitter."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(nitter_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
```

### Step 3: Parse with xcrawl

xcrawl extracts structured data from the nitter HTML:

```python
from bs4 import BeautifulSoup

def parse_tweet_from_nitter(html: str) -> dict:
    """Extract tweet data from nitter HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Main tweet content
    tweet_content = soup.select_one('.main-tweet .tweet-content')
    
    # Tweet stats
    stats = {}
    for stat in soup.select('.main-tweet .tweet-stat'):
        icon = stat.select_one('.icon-container')
        value = stat.select_one('.tweet-stat-num')
        if icon and value:
            stat_type = icon.get('class', [''])[1].replace('icon-', '')
            stats[stat_type] = value.get_text(strip=True)
    
    # Images
    images = [img.get('src') for img in soup.select('.main-tweet .attachment img')]
    
    # Author info
    author = soup.select_one('.main-tweet .fullname')
    username = soup.select_one('.main-tweet .username')
    
    return {
        'content': tweet_content.get_text(strip=True) if tweet_content else '',
        'author': author.get_text(strip=True) if author else '',
        'username': username.get_text(strip=True) if username else '',
        'stats': stats,
        'images': images,
        'html': str(tweet_content) if tweet_content else ''
    }
```

### Available Nitter Instances

Public instances (may change availability):
- `nitter.privacydev.net`
- `nitter.poast.org`
- `nitter.woodland.cafe`

Check https://github.com/zedeus/nitter/wiki/Instances for current list.

---

## Method 2: Bookmarks (fieldtheory)

### Overview
fieldtheory provides a browser extension approach to export X bookmarks.

### Usage

1. Install fieldtheory browser extension
2. Navigate to your X bookmarks page
3. Run the export function

```javascript
// In browser console after installing fieldtheory
// The extension intercepts API calls and extracts bookmark data

// Manual extraction approach (if extension unavailable):
async function exportBookmarks() {
    const bookmarks = [];
    let cursor = null;
    
    do {
        const url = cursor 
            ? `https://twitter.com/i/api/graphql/Bookmarks?cursor=${cursor}`
            : 'https://twitter.com/i/api/graphql/Bookmarks';
        
        // Note: Requires authenticated session cookies
        const response = await fetch(url, {
            credentials: 'include',
            headers: {
                'x-twitter-auth-type': 'OAuth2Session',
                'x-twitter-active-user': 'yes'
            }
        });
        
        const data = await response.json();
        // Process entries...
        
    } while (cursor);
    
    return bookmarks;
}
```

### Output Format

```json
{
    "bookmarks": [
        {
            "id": "1234567890",
            "text": "Tweet content...",
            "author": "username",
            "created_at": "2024-01-01T00:00:00Z",
            "media": [],
            "url": "https://x.com/username/status/1234567890"
        }
    ]
}
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""
X/Twitter content scraper using nitter + xcrawl method.
"""

import requests
from bs4 import BeautifulSoup
import re
import json

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
]

def scrape_tweet(twitter_url: str) -> dict:
    """
    Scrape a tweet from X/Twitter using nitter.
    
    Args:
        twitter_url: URL like https://x.com/user/status/123456
        
    Returns:
        dict with tweet content, author, stats, images
    """
    # Extract tweet info from URL
    pattern = r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)'
    match = re.search(pattern, twitter_url)
    
    if not match:
        raise ValueError(f"Invalid Twitter/X URL: {twitter_url}")
    
    username, status_id = match.groups()
    
    # Try nitter instances
    for instance in NITTER_INSTANCES:
        try:
            nitter_url = f"https://{instance}/{username}/status/{status_id}"
            
            response = requests.get(nitter_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=30)
            
            if response.status_code == 200:
                return parse_tweet(response.text, twitter_url)
                
        except requests.RequestException:
            continue
    
    raise RuntimeError("All nitter instances failed")

def parse_tweet(html: str, original_url: str) -> dict:
    """Parse tweet data from nitter HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    main_tweet = soup.select_one('.main-tweet')
    if not main_tweet:
        raise ValueError("Could not find main tweet content")
    
    content = main_tweet.select_one('.tweet-content')
    author = main_tweet.select_one('.fullname')
    handle = main_tweet.select_one('.username')
    timestamp = main_tweet.select_one('.tweet-date a')
    
    # Extract stats
    stats = {}
    for stat_type in ['comment', 'retweet', 'quote', 'heart']:
        stat_elem = main_tweet.select_one(f'.icon-{stat_type}')
        if stat_elem:
            parent = stat_elem.find_parent('.tweet-stat')
            if parent:
                num = parent.select_one('.tweet-stat-num')
                stats[stat_type] = num.get_text(strip=True) if num else '0'
    
    # Extract images
    images = []
    for img in main_tweet.select('.attachment.image img'):
        src = img.get('src', '')
        if src:
            images.append(src)
    
    return {
        'url': original_url,
        'content': content.get_text(strip=True) if content else '',
        'content_html': str(content) if content else '',
        'author': author.get_text(strip=True) if author else '',
        'handle': handle.get_text(strip=True) if handle else '',
        'timestamp': timestamp.get('title', '') if timestamp else '',
        'stats': stats,
        'images': images
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python x_scraper.py <twitter_url>")
        sys.exit(1)
    
    result = scrape_tweet(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
```
