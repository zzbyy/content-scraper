#!/usr/bin/env python3
"""
Universal Content Scraper Agent
================================
A general-purpose content scraping agent for use with Claude Code, Openclaw, 
and other AI coding assistants.

Supports:
- X/Twitter (posts, threads, long articles, bookmarks)
- WeChat Official Accounts (公众号)
- Xiaohongshu/RED (小红书)
- Jike (即刻)
- Douyin (抖音)

All methods are token-free and use the safest available approaches.

Usage:
    # As a module
    from content_scraper_agent import scrape, download
    result = scrape("https://x.com/user/status/123456")
    
    # As CLI
    python content_scraper_agent.py <url> [--download] [--output-dir ./output]
    
    # As an agent tool
    agent.call("scrape_content", {"url": "https://..."})
"""

import re
import json
import asyncio
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, quote
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# Optional imports - installed as needed
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class Platform(Enum):
    """Supported platforms."""
    TWITTER = "twitter"
    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"
    JIKE = "jike"
    DOUYIN = "douyin"
    UNKNOWN = "unknown"


@dataclass
class ScrapeResult:
    """Standardized result from any scraper."""
    success: bool
    platform: str
    url: str
    title: str = ""
    content: str = ""
    author: Dict[str, Any] = None
    media: List[Dict[str, Any]] = None
    stats: Dict[str, Any] = None
    raw_data: Dict[str, Any] = None
    error: str = ""
    
    def __post_init__(self):
        if self.author is None:
            self.author = {}
        if self.media is None:
            self.media = []
        if self.stats is None:
            self.stats = {}
        if self.raw_data is None:
            self.raw_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# Platform Detection
# =============================================================================

def detect_platform(url: str) -> Platform:
    """Detect which platform a URL belongs to."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # X/Twitter
    if any(d in domain for d in ['twitter.com', 'x.com', 'nitter']):
        return Platform.TWITTER
    
    # WeChat
    if 'mp.weixin.qq.com' in domain:
        return Platform.WECHAT
    
    # Xiaohongshu
    if any(d in domain for d in ['xiaohongshu.com', 'xhslink.com']):
        return Platform.XIAOHONGSHU
    
    # Jike
    if 'okjike.com' in domain:
        return Platform.JIKE
    
    # Douyin
    if any(d in domain for d in ['douyin.com', 'v.douyin.com']):
        return Platform.DOUYIN
    
    return Platform.UNKNOWN


# =============================================================================
# X/Twitter Scraper
# =============================================================================

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.woodland.cafe",
]

def scrape_twitter(url: str) -> ScrapeResult:
    """Scrape X/Twitter post using nitter."""
    if not HAS_REQUESTS or not HAS_BS4:
        return ScrapeResult(
            success=False,
            platform=Platform.TWITTER.value,
            url=url,
            error="Missing dependencies: pip install requests beautifulsoup4"
        )
    
    # Extract tweet info
    pattern = r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)'
    match = re.search(pattern, url)
    
    if not match:
        return ScrapeResult(
            success=False,
            platform=Platform.TWITTER.value,
            url=url,
            error="Invalid Twitter/X URL format"
        )
    
    username, status_id = match.groups()
    
    # Try nitter instances
    for instance in NITTER_INSTANCES:
        try:
            nitter_url = f"https://{instance}/{username}/status/{status_id}"
            
            response = requests.get(nitter_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                main_tweet = soup.select_one('.main-tweet')
                
                if not main_tweet:
                    continue
                
                content = main_tweet.select_one('.tweet-content')
                author_elem = main_tweet.select_one('.fullname')
                handle = main_tweet.select_one('.username')
                
                # Stats
                stats = {}
                for stat_type in ['comment', 'retweet', 'quote', 'heart']:
                    stat_elem = main_tweet.select_one(f'.icon-{stat_type}')
                    if stat_elem:
                        parent = stat_elem.find_parent('.tweet-stat')
                        if parent:
                            num = parent.select_one('.tweet-stat-num')
                            stats[stat_type] = num.get_text(strip=True) if num else '0'
                
                # Images
                images = []
                for img in main_tweet.select('.attachment.image img'):
                    src = img.get('src', '')
                    if src:
                        images.append({'url': src, 'type': 'image'})
                
                return ScrapeResult(
                    success=True,
                    platform=Platform.TWITTER.value,
                    url=url,
                    content=content.get_text(strip=True) if content else '',
                    author={
                        'name': author_elem.get_text(strip=True) if author_elem else '',
                        'handle': handle.get_text(strip=True) if handle else '',
                    },
                    media=images,
                    stats=stats,
                )
                
        except requests.RequestException:
            continue
    
    return ScrapeResult(
        success=False,
        platform=Platform.TWITTER.value,
        url=url,
        error="All nitter instances failed"
    )


# =============================================================================
# WeChat Scraper
# =============================================================================

def scrape_wechat(url: str) -> ScrapeResult:
    """Scrape WeChat article using mptext.top API."""
    if not HAS_REQUESTS:
        return ScrapeResult(
            success=False,
            platform=Platform.WECHAT.value,
            url=url,
            error="Missing dependency: pip install requests"
        )
    
    try:
        encoded_url = quote(url, safe='')
        api_url = f"https://down.mptext.top/api/public/v1/download?url={encoded_url}&format=markdown"
        
        response = requests.get(api_url, timeout=60, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        content = response.text
        
        # Extract title from markdown
        title = ''
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        
        return ScrapeResult(
            success=True,
            platform=Platform.WECHAT.value,
            url=url,
            title=title,
            content=content,
        )
        
    except requests.RequestException as e:
        return ScrapeResult(
            success=False,
            platform=Platform.WECHAT.value,
            url=url,
            error=str(e)
        )


# =============================================================================
# Xiaohongshu Scraper
# =============================================================================

def scrape_xiaohongshu(url: str) -> ScrapeResult:
    """Scrape Xiaohongshu note via HTML parsing."""
    if not HAS_REQUESTS or not HAS_BS4:
        return ScrapeResult(
            success=False,
            platform=Platform.XIAOHONGSHU.value,
            url=url,
            error="Missing dependencies: pip install requests beautifulsoup4"
        )
    
    try:
        # Expand short URLs
        if 'xhslink.com' in url:
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        result = ScrapeResult(
            success=True,
            platform=Platform.XIAOHONGSHU.value,
            url=url,
        )
        
        # Meta tags
        og_title = soup.find('meta', {'property': 'og:title'})
        og_desc = soup.find('meta', {'property': 'og:description'})
        og_image = soup.find('meta', {'property': 'og:image'})
        
        if og_title:
            result.title = og_title.get('content', '')
        if og_desc:
            result.content = og_desc.get('content', '')
        if og_image:
            result.media.append({'url': og_image.get('content', ''), 'type': 'image'})
        
        # Try INITIAL_STATE
        state_pattern = r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*(?:</script>|;\s*\n)'
        state_match = re.search(state_pattern, html, re.DOTALL)
        
        if state_match:
            try:
                json_str = state_match.group(1)
                json_str = re.sub(r':\s*undefined', ': null', json_str)
                initial_state = json.loads(json_str)
                
                # Extract note from state
                note = None
                if 'note' in initial_state and 'noteDetailMap' in initial_state['note']:
                    note_map = initial_state['note']['noteDetailMap']
                    if note_map:
                        first_key = list(note_map.keys())[0]
                        note = note_map[first_key].get('note', {})
                
                if note:
                    result.title = note.get('title', result.title)
                    result.content = note.get('desc', result.content)
                    
                    # Author
                    user = note.get('user', {})
                    result.author = {
                        'user_id': user.get('userId', ''),
                        'nickname': user.get('nickname', ''),
                    }
                    
                    # Images
                    for img in note.get('imageList', []):
                        img_url = img.get('urlDefault') or img.get('url', '')
                        if img_url and not img_url.startswith('http'):
                            img_url = f"https://sns-img-bd.xhscdn.com/{img_url}"
                        if img_url:
                            result.media.append({'url': img_url, 'type': 'image'})
                    
                    # Stats
                    interact = note.get('interactInfo', {})
                    result.stats = {
                        'likes': interact.get('likedCount', 0),
                        'collects': interact.get('collectedCount', 0),
                        'comments': interact.get('commentCount', 0),
                    }
                    
                    result.raw_data = note
                    
            except (json.JSONDecodeError, KeyError):
                pass
        
        return result
        
    except requests.RequestException as e:
        return ScrapeResult(
            success=False,
            platform=Platform.XIAOHONGSHU.value,
            url=url,
            error=str(e)
        )


# =============================================================================
# Jike Scraper
# =============================================================================

def scrape_jike(url: str, method: str = 'auto') -> ScrapeResult:
    """Scrape Jike post."""
    if not HAS_REQUESTS:
        return ScrapeResult(
            success=False,
            platform=Platform.JIKE.value,
            url=url,
            error="Missing dependency: pip install requests"
        )
    
    # Try Jina first (simplest)
    if method in ['jina', 'auto']:
        try:
            jina_url = f"https://r.jina.ai/{url}"
            response = requests.get(jina_url, timeout=60)
            
            if response.status_code == 200:
                return ScrapeResult(
                    success=True,
                    platform=Platform.JIKE.value,
                    url=url,
                    content=response.text,
                )
        except Exception:
            pass

    # Try direct scraping
    if method in ['xcrawl', 'auto'] and HAS_BS4:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            result = ScrapeResult(
                success=True,
                platform=Platform.JIKE.value,
                url=url,
            )
            
            # Try to extract from scripts
            for script in soup.find_all('script'):
                text = script.string or ''
                state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*(?:\n|$)', text, re.DOTALL)
                
                if state_match:
                    try:
                        data = json.loads(state_match.group(1))
                        
                        # Find post data
                        post = data.get('originalPost') or data.get('post') or {}
                        
                        if post:
                            result.content = post.get('content', '')
                            result.author = {
                                'screenName': post.get('user', {}).get('screenName', ''),
                                'username': post.get('user', {}).get('username', ''),
                            }
                            result.stats = {
                                'likes': post.get('likeCount', 0),
                                'comments': post.get('commentCount', 0),
                                'reposts': post.get('repostCount', 0),
                            }
                            result.media = [{'url': p.get('picUrl', ''), 'type': 'image'} 
                                          for p in post.get('pictures', [])]
                            result.raw_data = post
                            
                            return result
                    except json.JSONDecodeError:
                        continue
            
            # Fallback to meta
            og_desc = soup.find('meta', {'property': 'og:description'})
            if og_desc:
                result.content = og_desc.get('content', '')
            
            return result
            
        except requests.RequestException as e:
            pass
    
    return ScrapeResult(
        success=False,
        platform=Platform.JIKE.value,
        url=url,
        error="All scraping methods failed"
    )


# =============================================================================
# Douyin Scraper
# =============================================================================

async def scrape_douyin_async(url: str) -> ScrapeResult:
    """Scrape Douyin video using Playwright."""
    if not HAS_PLAYWRIGHT:
        return ScrapeResult(
            success=False,
            platform=Platform.DOUYIN.value,
            url=url,
            error="Missing dependency: pip install playwright && playwright install chromium"
        )
    
    video_data = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        
        page = await context.new_page()
        
        async def handle_response(response):
            nonlocal video_data
            resp_url = response.url
            
            if any(p in resp_url for p in ['aweme/detail', 'aweme/v1/web/aweme/detail']):
                try:
                    data = await response.json()
                    if 'aweme_detail' in data or 'aweme_list' in data:
                        video_data = data
                except Exception:
                    pass

        page.on('response', handle_response)
        
        try:
            # Expand short URLs
            if 'v.douyin.com' in url:
                await page.goto(url, wait_until='domcontentloaded')
                url = page.url
            
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
        except Exception as e:
            await browser.close()
            return ScrapeResult(
                success=False,
                platform=Platform.DOUYIN.value,
                url=url,
                error=f"Page load error: {e}"
            )
        
        await browser.close()
    
    if not video_data:
        return ScrapeResult(
            success=False,
            platform=Platform.DOUYIN.value,
            url=url,
            error="Could not capture video data from API"
        )
    
    # Parse the response
    aweme = video_data.get('aweme_detail') or (video_data.get('aweme_list', [{}])[0])
    
    video = aweme.get('video', {})
    play_addr = video.get('play_addr', {})
    url_list = play_addr.get('url_list', [])
    
    video_url = url_list[0] if url_list else ''
    video_url_clean = video_url.replace('/playwm/', '/play/')
    
    author = aweme.get('author', {})
    stats = aweme.get('statistics', {})
    
    return ScrapeResult(
        success=True,
        platform=Platform.DOUYIN.value,
        url=url,
        title=aweme.get('desc', ''),
        content=aweme.get('desc', ''),
        author={
            'uid': author.get('uid', ''),
            'nickname': author.get('nickname', ''),
            'unique_id': author.get('unique_id', ''),
        },
        media=[
            {
                'url': video_url_clean,
                'url_watermark': video_url,
                'type': 'video',
                'cover': video.get('cover', {}).get('url_list', [''])[0],
                'duration_ms': video.get('duration', 0),
            }
        ],
        stats={
            'likes': stats.get('digg_count', 0),
            'comments': stats.get('comment_count', 0),
            'shares': stats.get('share_count', 0),
            'plays': stats.get('play_count', 0),
        },
        raw_data=aweme,
    )


def scrape_douyin(url: str) -> ScrapeResult:
    """Synchronous wrapper for Douyin scraper."""
    return asyncio.run(scrape_douyin_async(url))


# =============================================================================
# Main API
# =============================================================================

def scrape(url: str, **kwargs) -> ScrapeResult:
    """
    Universal scrape function - detects platform and calls appropriate scraper.
    
    Args:
        url: The URL to scrape
        **kwargs: Platform-specific options
        
    Returns:
        ScrapeResult with scraped content
        
    Example:
        >>> result = scrape("https://x.com/user/status/123")
        >>> print(result.content)
    """
    platform = detect_platform(url)
    
    if platform == Platform.TWITTER:
        return scrape_twitter(url)
    elif platform == Platform.WECHAT:
        return scrape_wechat(url)
    elif platform == Platform.XIAOHONGSHU:
        return scrape_xiaohongshu(url)
    elif platform == Platform.JIKE:
        return scrape_jike(url, method=kwargs.get('method', 'auto'))
    elif platform == Platform.DOUYIN:
        return scrape_douyin(url)
    else:
        return ScrapeResult(
            success=False,
            platform=Platform.UNKNOWN.value,
            url=url,
            error=f"Unknown platform for URL: {url}"
        )


def download_media(result: ScrapeResult, output_dir: str = '.') -> List[str]:
    """
    Download all media from a scrape result.
    
    Args:
        result: ScrapeResult from scrape()
        output_dir: Directory to save files
        
    Returns:
        List of downloaded file paths
    """
    if not HAS_REQUESTS:
        raise ImportError("requests is required for downloading")
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded = []
    
    for i, media in enumerate(result.media):
        url = media.get('url', '')
        if not url:
            continue
        
        media_type = media.get('type', 'unknown')
        ext = 'mp4' if media_type == 'video' else 'jpg'
        
        # Generate filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', result.title or 'media')[:50]
        filename = f"{safe_title}_{i+1}.{ext}"
        filepath = os.path.join(output_dir, filename)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            # Add referer for Douyin
            if result.platform == Platform.DOUYIN.value:
                headers['Referer'] = 'https://www.douyin.com/'
            
            response = requests.get(url, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            downloaded.append(filepath)
            print(f"Downloaded: {filepath}")
            
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
    return downloaded


# =============================================================================
# Agent Tool Interface
# =============================================================================

TOOL_SCHEMA = {
    "name": "scrape_content",
    "description": "Scrape content from social platforms (X/Twitter, WeChat, Xiaohongshu, Jike, Douyin). Extracts text, images, videos, and metadata.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to scrape"
            },
            "download_media": {
                "type": "boolean",
                "description": "Whether to download media files",
                "default": False
            },
            "output_dir": {
                "type": "string",
                "description": "Directory for downloaded files",
                "default": "./downloads"
            }
        },
        "required": ["url"]
    }
}


def agent_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent tool interface for scraping.
    
    This function can be registered as a tool for AI agents like Claude Code or Openclaw.
    
    Args:
        params: Tool parameters including 'url', optionally 'download_media' and 'output_dir'
        
    Returns:
        Dict with scrape results
    """
    url = params.get('url')
    if not url:
        return {'error': 'URL is required'}
    
    result = scrape(url)
    output = result.to_dict()
    
    if params.get('download_media') and result.success and result.media:
        output_dir = params.get('output_dir', './downloads')
        downloaded = download_media(result, output_dir)
        output['downloaded_files'] = downloaded
    
    return output


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Universal Content Scraper Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://x.com/user/status/123456
  %(prog)s https://mp.weixin.qq.com/s/xxx --output ./articles
  %(prog)s https://www.douyin.com/video/xxx --download
        """
    )
    
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--download', '-d', action='store_true', 
                        help='Download media files')
    parser.add_argument('--output-dir', '-o', default='./downloads',
                        help='Output directory for downloads')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON only')
    
    args = parser.parse_args()
    
    # Check dependencies
    if not HAS_REQUESTS:
        print("Error: requests library not installed")
        print("Run: pip install requests beautifulsoup4 playwright")
        sys.exit(1)
    
    result = scrape(args.url)
    
    if args.json:
        print(result.to_json())
    else:
        print(f"\n{'='*60}")
        print(f"Platform: {result.platform}")
        print(f"Success: {result.success}")
        print(f"{'='*60}")
        
        if result.success:
            if result.title:
                print(f"\nTitle: {result.title}")
            if result.author:
                print(f"Author: {json.dumps(result.author, ensure_ascii=False)}")
            if result.content:
                print(f"\nContent:\n{result.content[:500]}{'...' if len(result.content) > 500 else ''}")
            if result.stats:
                print(f"\nStats: {json.dumps(result.stats, ensure_ascii=False)}")
            if result.media:
                print(f"\nMedia: {len(result.media)} item(s)")
                for m in result.media[:3]:
                    print(f"  - {m.get('type', 'unknown')}: {m.get('url', '')[:80]}...")
        else:
            print(f"\nError: {result.error}")
    
    if args.download and result.success and result.media:
        print(f"\n{'='*60}")
        print("Downloading media...")
        downloaded = download_media(result, args.output_dir)
        print(f"Downloaded {len(downloaded)} file(s)")


if __name__ == '__main__':
    main()
