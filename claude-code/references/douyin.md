# Douyin (抖音) Video Scraping Reference

## Overview

Douyin videos require browser automation to bypass signature verification (msToken, X-Bogus). The approach uses headless Chromium to intercept API responses containing the video direct link.

## Why Browser Automation?

Douyin uses encrypted parameters (`msToken`, `X-Bogus`, `a_bogus`) that are generated client-side by JavaScript. Rather than reverse-engineering these (which changes frequently), we let the browser handle them naturally.

## Method: Headless Chromium + API Interception

### Core Workflow

1. **Launch headless Chromium** - Simulates a real Chrome browser
2. **Navigate to Douyin page** - `page.goto(url)` loads the page, browser executes JS
3. **Intercept API response** - Monitor for `aweme/detail` API responses
4. **Extract video URL** - Parse JSON for `play_addr.url_list[0]`
5. **Download video** - Use requests with proper Referer header

### Step 1: Setup Playwright

```bash
pip install playwright --break-system-packages
playwright install chromium
```

### Step 2: The Scraper

```python
import asyncio
from playwright.async_api import async_playwright
import requests
import json
import re

async def scrape_douyin_video(url: str) -> dict:
    """
    Scrape Douyin video URL using headless browser.
    
    Args:
        url: Douyin video URL (douyin.com/video/xxx or v.douyin.com/xxx)
        
    Returns:
        dict with video info and download URL
    """
    video_data = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Set up response interception
        async def handle_response(response):
            nonlocal video_data
            
            url = response.url
            # Look for the detail API endpoint
            if 'aweme/detail' in url or 'aweme/v1/web/aweme/detail' in url:
                try:
                    data = await response.json()
                    video_data = data
                except:
                    pass
        
        page.on('response', handle_response)
        
        # Navigate to the page
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait a bit for API calls to complete
        await asyncio.sleep(3)
        
        await browser.close()
    
    if video_data:
        return parse_video_data(video_data)
    
    return {'error': 'Could not intercept video data'}

def parse_video_data(data: dict) -> dict:
    """Parse the video data from Douyin API response."""
    # Navigate to aweme detail
    aweme = None
    
    if 'aweme_detail' in data:
        aweme = data['aweme_detail']
    elif 'aweme_list' in data and data['aweme_list']:
        aweme = data['aweme_list'][0]
    elif 'item_list' in data and data['item_list']:
        aweme = data['item_list'][0]
    
    if not aweme:
        return {'error': 'Could not find aweme data', 'raw': data}
    
    # Extract video URL
    video_url = ''
    play_addr = aweme.get('video', {}).get('play_addr', {})
    url_list = play_addr.get('url_list', [])
    
    if url_list:
        video_url = url_list[0]
        # Remove watermark by using different URL pattern if available
        video_url = video_url.replace('playwm', 'play')
    
    # Alternative: bit_rate for quality options
    bit_rate = aweme.get('video', {}).get('bit_rate', [])
    if bit_rate:
        # Get highest quality
        best_quality = max(bit_rate, key=lambda x: x.get('bit_rate', 0))
        play_addr = best_quality.get('play_addr', {})
        if play_addr.get('url_list'):
            video_url = play_addr['url_list'][0]
    
    return {
        'aweme_id': aweme.get('aweme_id', ''),
        'desc': aweme.get('desc', ''),
        'video_url': video_url,
        'video_url_no_watermark': video_url.replace('playwm', 'play'),
        'cover': aweme.get('video', {}).get('cover', {}).get('url_list', [''])[0],
        'duration': aweme.get('video', {}).get('duration', 0),
        'author': {
            'uid': aweme.get('author', {}).get('uid', ''),
            'nickname': aweme.get('author', {}).get('nickname', ''),
            'unique_id': aweme.get('author', {}).get('unique_id', ''),
        },
        'stats': {
            'digg_count': aweme.get('statistics', {}).get('digg_count', 0),
            'comment_count': aweme.get('statistics', {}).get('comment_count', 0),
            'share_count': aweme.get('statistics', {}).get('share_count', 0),
            'play_count': aweme.get('statistics', {}).get('play_count', 0),
        },
        'music': {
            'title': aweme.get('music', {}).get('title', ''),
            'author': aweme.get('music', {}).get('author', ''),
        },
        'create_time': aweme.get('create_time', 0),
    }
```

### Step 3: Download Video

```python
def download_douyin_video(video_url: str, output_path: str) -> bool:
    """
    Download Douyin video with proper headers.
    
    Args:
        video_url: Direct video URL from scraper
        output_path: Where to save the video
        
    Returns:
        bool indicating success
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
        'Accept': '*/*',
    }
    
    try:
        response = requests.get(video_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False
```

---

## Complete Example Script

```python
#!/usr/bin/env python3
"""
Douyin (抖音) video scraper and downloader.
Uses headless browser to bypass signature verification.
"""

import asyncio
from playwright.async_api import async_playwright
import requests
import json
import re
import sys
import os
from urllib.parse import urlparse

def is_douyin_url(url: str) -> bool:
    """Check if URL is a valid Douyin URL."""
    parsed = urlparse(url)
    return parsed.netloc in [
        'www.douyin.com', 'douyin.com',
        'v.douyin.com',  # Short links
    ]

async def expand_short_url(url: str) -> str:
    """Expand v.douyin.com short URLs."""
    if 'v.douyin.com' in url:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            response = await page.goto(url, wait_until='domcontentloaded')
            final_url = page.url
            
            await browser.close()
            return final_url
    return url

async def scrape_douyin(url: str) -> dict:
    """
    Main scraping function.
    
    Args:
        url: Any Douyin video URL
        
    Returns:
        dict with video info and download URL
    """
    # Expand short URLs
    if 'v.douyin.com' in url:
        url = await expand_short_url(url)
    
    if not is_douyin_url(url):
        return {'error': f'Not a valid Douyin URL: {url}'}
    
    video_data = {'url': url}
    api_response = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        
        page = await context.new_page()
        
        # Intercept responses
        async def capture_response(response):
            nonlocal api_response
            
            resp_url = response.url
            
            # Check for video detail API
            if any(pattern in resp_url for pattern in [
                'aweme/detail',
                'aweme/v1/web/aweme/detail',
                'aweme/post',
            ]):
                try:
                    data = await response.json()
                    if 'aweme_detail' in data or 'aweme_list' in data:
                        api_response = data
                except:
                    pass
        
        page.on('response', capture_response)
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Give extra time for API calls
            await asyncio.sleep(5)
            
        except Exception as e:
            video_data['error'] = f'Page load error: {e}'
        
        await browser.close()
    
    if api_response:
        parsed = parse_aweme_response(api_response)
        video_data.update(parsed)
    else:
        video_data['error'] = 'Could not capture video data from API'
    
    return video_data

def parse_aweme_response(data: dict) -> dict:
    """Extract video info from API response."""
    aweme = None
    
    # Find the aweme object
    if 'aweme_detail' in data:
        aweme = data['aweme_detail']
    elif 'aweme_list' in data and len(data['aweme_list']) > 0:
        aweme = data['aweme_list'][0]
    
    if not aweme:
        return {'parse_error': 'No aweme found in response'}
    
    result = {
        'aweme_id': aweme.get('aweme_id', ''),
        'description': aweme.get('desc', ''),
    }
    
    # Video URLs
    video = aweme.get('video', {})
    
    # Try play_addr first
    play_addr = video.get('play_addr', {})
    url_list = play_addr.get('url_list', [])
    
    if url_list:
        result['video_url_watermark'] = url_list[0]
        # Remove watermark URL
        result['video_url'] = url_list[0].replace('/playwm/', '/play/')
    
    # Try bit_rate for better quality
    bit_rate_list = video.get('bit_rate', [])
    if bit_rate_list:
        # Sort by quality (bit_rate value)
        sorted_rates = sorted(bit_rate_list, key=lambda x: x.get('bit_rate', 0), reverse=True)
        best = sorted_rates[0]
        
        best_urls = best.get('play_addr', {}).get('url_list', [])
        if best_urls:
            result['video_url_hd'] = best_urls[0]
    
    # Cover image
    cover = video.get('cover', {}).get('url_list', [])
    if cover:
        result['cover_url'] = cover[0]
    
    # Duration (milliseconds)
    result['duration_ms'] = video.get('duration', 0)
    
    # Author info
    author = aweme.get('author', {})
    result['author'] = {
        'uid': author.get('uid', ''),
        'sec_uid': author.get('sec_uid', ''),
        'nickname': author.get('nickname', ''),
        'unique_id': author.get('unique_id', ''),
        'signature': author.get('signature', ''),
    }
    
    # Statistics
    stats = aweme.get('statistics', {})
    result['stats'] = {
        'likes': stats.get('digg_count', 0),
        'comments': stats.get('comment_count', 0),
        'shares': stats.get('share_count', 0),
        'plays': stats.get('play_count', 0),
        'collects': stats.get('collect_count', 0),
    }
    
    # Music
    music = aweme.get('music', {})
    result['music'] = {
        'id': music.get('id', ''),
        'title': music.get('title', ''),
        'author': music.get('author', ''),
        'duration': music.get('duration', 0),
    }
    
    # Timestamp
    result['create_time'] = aweme.get('create_time', 0)
    
    return result

def download_video(video_info: dict, output_dir: str = '.') -> str:
    """
    Download the video file.
    
    Args:
        video_info: Result from scrape_douyin
        output_dir: Directory to save video
        
    Returns:
        Path to downloaded file
    """
    # Prefer HD URL, fall back to regular
    video_url = video_info.get('video_url_hd') or video_info.get('video_url')
    
    if not video_url:
        raise ValueError("No video URL found")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    
    # Generate filename
    aweme_id = video_info.get('aweme_id', 'douyin')
    author = video_info.get('author', {}).get('nickname', 'unknown')
    filename = f"{author}_{aweme_id}.mp4"
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Sanitize
    
    output_path = os.path.join(output_dir, filename)
    
    print(f"Downloading to {output_path}...")
    
    response = requests.get(video_url, headers=headers, stream=True, timeout=120)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print(f"\nDownloaded: {output_path}")
    return output_path

async def main():
    if len(sys.argv) < 2:
        print("Usage: python douyin_scraper.py <douyin_url> [--download]")
        print("Options:")
        print("  --download    Download the video after scraping")
        sys.exit(1)
    
    url = sys.argv[1]
    should_download = '--download' in sys.argv
    
    print(f"Scraping: {url}")
    result = await scrape_douyin(url)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if should_download and result.get('video_url'):
        download_video(result)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Notes

- Requires Playwright with Chromium installed
- The `Referer: https://www.douyin.com/` header is **required** for video download
- Short URLs (v.douyin.com) need to be expanded first
- `playwm` → `play` URL substitution removes watermark (may not always work)
- API structure may change - check for `aweme_detail` or `aweme_list` keys
- Rate limiting may apply for batch downloads
