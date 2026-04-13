# Xiaohongshu (小红书/RED) Scraping Reference

## Overview

Xiaohongshu notes can be scraped by parsing the HTML page and extracting data from the `window.__INITIAL_STATE__` JavaScript object, which contains all the structured note data.

## Method: HTML + INITIAL_STATE Parsing

### Step 1: Fetch the Page

```python
import requests

def fetch_xhs_page(url: str) -> str:
    """Fetch Xiaohongshu page HTML."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
```

### Step 2: Extract Meta Tags (Quick Preview)

For basic info, meta tags contain key data:

```python
from bs4 import BeautifulSoup

def extract_meta_preview(html: str) -> dict:
    """Extract basic note info from meta tags."""
    soup = BeautifulSoup(html, 'html.parser')
    
    return {
        'title': soup.find('meta', {'name': 'og:title'})['content'] if soup.find('meta', {'name': 'og:title'}) else '',
        'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
        'image': soup.find('meta', {'property': 'og:image'})['content'] if soup.find('meta', {'property': 'og:image'}) else '',
    }
```

### Step 3: Parse INITIAL_STATE (Full Data)

The complete note data is in `window.__INITIAL_STATE__`:

```python
import re
import json

def extract_initial_state(html: str) -> dict:
    """Extract and parse window.__INITIAL_STATE__ from HTML."""
    # Find the INITIAL_STATE script
    pattern = r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*</script>'
    match = re.search(pattern, html, re.DOTALL)
    
    if not match:
        # Try alternative pattern
        pattern2 = r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*\n'
        match = re.search(pattern2, html, re.DOTALL)
    
    if not match:
        raise ValueError("Could not find __INITIAL_STATE__ in page")
    
    # Parse JSON (handle undefined values)
    json_str = match.group(1)
    # Replace JavaScript undefined with null
    json_str = re.sub(r':\s*undefined', ': null', json_str)
    
    return json.loads(json_str)
```

### Step 4: Extract Note Data

```python
def extract_note_data(initial_state: dict) -> dict:
    """Extract structured note data from INITIAL_STATE."""
    # Navigate to note data (structure may vary)
    note_data = None
    
    # Try different paths where note data might be
    if 'note' in initial_state:
        note_data = initial_state['note']
    elif 'noteData' in initial_state:
        note_data = initial_state['noteData']
    elif 'noteDetailMap' in initial_state:
        # Get first note from map
        note_map = initial_state['noteDetailMap']
        if note_map:
            first_key = list(note_map.keys())[0]
            note_data = note_map[first_key].get('note', {})
    
    if not note_data:
        return {}
    
    # Extract key fields
    return {
        'id': note_data.get('noteId', note_data.get('id', '')),
        'title': note_data.get('title', ''),
        'desc': note_data.get('desc', ''),
        'type': note_data.get('type', ''),  # 'normal' for images, 'video' for video
        'user': {
            'id': note_data.get('user', {}).get('userId', ''),
            'nickname': note_data.get('user', {}).get('nickname', ''),
            'avatar': note_data.get('user', {}).get('avatar', ''),
        },
        'images': extract_images(note_data),
        'video': extract_video(note_data),
        'tags': [tag.get('name', '') for tag in note_data.get('tagList', [])],
        'stats': {
            'likes': note_data.get('interactInfo', {}).get('likedCount', 0),
            'collects': note_data.get('interactInfo', {}).get('collectedCount', 0),
            'comments': note_data.get('interactInfo', {}).get('commentCount', 0),
            'shares': note_data.get('interactInfo', {}).get('shareCount', 0),
        },
        'time': note_data.get('time', ''),
    }

def extract_images(note_data: dict) -> list:
    """Extract image URLs from note data."""
    images = []
    
    # Images are usually in imageList
    image_list = note_data.get('imageList', [])
    
    for img in image_list:
        # Try different URL fields
        url = img.get('urlDefault') or img.get('url') or img.get('original', '')
        
        # Build full URL if needed
        if url and not url.startswith('http'):
            url = f"https://sns-img-bd.xhscdn.com/{url}"
        
        if url:
            images.append({
                'url': url,
                'width': img.get('width', 0),
                'height': img.get('height', 0),
            })
    
    return images

def extract_video(note_data: dict) -> dict:
    """Extract video info if present."""
    video = note_data.get('video', {})
    
    if not video:
        return {}
    
    return {
        'url': video.get('url', video.get('urlDefault', '')),
        'cover': video.get('cover', {}).get('url', ''),
        'duration': video.get('duration', 0),
    }
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""
Xiaohongshu (小红书/RED) note scraper.
Extracts images, text, and metadata from XHS posts.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse

def is_xhs_url(url: str) -> bool:
    """Check if URL is a valid Xiaohongshu URL."""
    parsed = urlparse(url)
    return parsed.netloc in ['www.xiaohongshu.com', 'xiaohongshu.com', 'xhslink.com']

def normalize_xhs_url(url: str) -> str:
    """Normalize short links to full URLs."""
    if 'xhslink.com' in url:
        # Follow redirect for short links
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.url
    return url

def scrape_xhs_note(url: str) -> dict:
    """
    Scrape a Xiaohongshu note.
    
    Args:
        url: Xiaohongshu note URL
        
    Returns:
        dict with note content, images, metadata
    """
    url = normalize_xhs_url(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract meta preview first
    result = {
        'url': url,
        'title': '',
        'description': '',
        'images': [],
        'video': None,
        'author': {},
        'stats': {},
        'tags': [],
    }
    
    # Get meta tags
    og_title = soup.find('meta', {'property': 'og:title'})
    og_desc = soup.find('meta', {'property': 'og:description'})
    og_image = soup.find('meta', {'property': 'og:image'})
    
    if og_title:
        result['title'] = og_title.get('content', '')
    if og_desc:
        result['description'] = og_desc.get('content', '')
    if og_image:
        result['images'].append({'url': og_image.get('content', ''), 'source': 'meta'})
    
    # Try to get INITIAL_STATE for full data
    try:
        state_pattern = r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*(?:</script>|;\s*\n)'
        state_match = re.search(state_pattern, html, re.DOTALL)
        
        if state_match:
            json_str = state_match.group(1)
            json_str = re.sub(r':\s*undefined', ': null', json_str)
            initial_state = json.loads(json_str)
            
            # Extract detailed note data
            note_detail = extract_note_detail(initial_state)
            if note_detail:
                result.update(note_detail)
                
    except (json.JSONDecodeError, KeyError) as e:
        result['parse_warning'] = f"Could not parse INITIAL_STATE: {e}"
    
    return result

def extract_note_detail(state: dict) -> dict:
    """Extract detailed note info from INITIAL_STATE."""
    note = None
    
    # Try different state structures
    if 'note' in state and 'noteDetailMap' in state['note']:
        note_map = state['note']['noteDetailMap']
        if note_map:
            first_key = list(note_map.keys())[0]
            note = note_map[first_key].get('note', {})
    elif 'noteData' in state:
        note = state['noteData']
    
    if not note:
        return {}
    
    result = {
        'note_id': note.get('noteId', ''),
        'title': note.get('title', ''),
        'description': note.get('desc', ''),
        'type': note.get('type', 'normal'),
    }
    
    # Author
    user = note.get('user', {})
    result['author'] = {
        'user_id': user.get('userId', ''),
        'nickname': user.get('nickname', ''),
        'avatar': user.get('avatar', ''),
    }
    
    # Images
    image_list = note.get('imageList', [])
    result['images'] = []
    for img in image_list:
        url = img.get('urlDefault') or img.get('url', '')
        if url and not url.startswith('http'):
            url = f"https://sns-img-bd.xhscdn.com/{url}"
        if url:
            result['images'].append({
                'url': url,
                'width': img.get('width'),
                'height': img.get('height'),
            })
    
    # Video
    if note.get('video'):
        video = note['video']
        result['video'] = {
            'url': video.get('url', ''),
            'cover': video.get('cover', {}).get('url', ''),
        }
    
    # Stats
    interact = note.get('interactInfo', {})
    result['stats'] = {
        'likes': interact.get('likedCount', 0),
        'collects': interact.get('collectedCount', 0),
        'comments': interact.get('commentCount', 0),
        'shares': interact.get('shareCount', 0),
    }
    
    # Tags
    result['tags'] = [t.get('name', '') for t in note.get('tagList', [])]
    
    return result

def download_images(note_data: dict, output_dir: str = '.') -> list:
    """Download all images from a scraped note."""
    import os
    
    downloaded = []
    
    for i, img in enumerate(note_data.get('images', [])):
        url = img.get('url', '')
        if not url:
            continue
        
        try:
            response = requests.get(url, timeout=30)
            ext = 'jpg'  # Default extension
            
            filename = f"{note_data.get('note_id', 'xhs')}_{i+1}.{ext}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            downloaded.append(filepath)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
    return downloaded

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python xhs_scraper.py <xiaohongshu_url>")
        sys.exit(1)
    
    result = scrape_xhs_note(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## Image Download Tips

Xiaohongshu images are served from CDN with potential restrictions:

```python
def get_image_direct_link(image_url: str) -> str:
    """Get direct download link for XHS image."""
    # Remove any query parameters that might cause issues
    base_url = image_url.split('?')[0]
    
    # Ensure using the right CDN domain
    if 'xhscdn.com' not in base_url:
        # Try common CDN patterns
        pass
    
    return base_url
```

## Notes

- Mobile User-Agent often works better than desktop
- The `__INITIAL_STATE__` structure may vary between page types
- Some content may require cookies/session for full access
- Rate limiting applies - add delays for batch scraping
- For visual analysis of images, the scraped URLs can be passed to vision models
