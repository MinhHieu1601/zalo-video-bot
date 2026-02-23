import os
import re
import json
import httpx
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler

# Config
API_KEY = 'hieudepzainhatvutru1601'

def get_douyin_video(url: str) -> dict:
    """Get Douyin video without watermark"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Referer': 'https://www.douyin.com/',
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
            resp = client.get(url)
            final_url = str(resp.url)
            html = resp.text
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}
    
    # Extract video ID
    match = re.search(r'/video/(\d+)', final_url)
    if not match:
        match = re.search(r'modal_id=(\d+)', final_url)
    if not match:
        return {'error': 'Cannot find video ID'}
    
    aweme_id = match.group(1)
    
    video_url = None
    video_url_wm = None
    audio_url = ''
    title = ''
    
    # Method 1: Extract playApi from HTML (this is usually watermark version)
    play_match = re.search(r'"playApi":"([^"]+)"', html)
    if play_match:
        video_url_wm = play_match.group(1).replace('\\u002F', '/')
        if video_url_wm.startswith('//'):
            video_url_wm = 'https:' + video_url_wm
    
    # Method 2: Try play_addr
    if not video_url_wm:
        play_match = re.search(r'"play_addr":\{[^}]*"url_list":\["([^"]+)"', html)
        if play_match:
            video_url_wm = play_match.group(1).replace('\\u002F', '/')
    
    if not video_url_wm:
        return {'error': 'Cannot find video URL'}
    
    # No watermark version (replace playwm with play)
    video_url = video_url_wm.replace('playwm', 'play')
    
    # Try to get audio URL
    music_match = re.search(r'"music":\{[^}]*"play_url":\{[^}]*"uri":"([^"]+)"', html)
    if music_match:
        audio_url = music_match.group(1)
        if not audio_url.startswith('http'):
            audio_url = f'https://sf-tk-sg.ibytedtos.com/obj/{audio_url}'
    
    # Get title from desc field
    desc_match = re.search(r'"desc":"([^"]+)"', html)
    if desc_match:
        title = desc_match.group(1).replace('\\u002F', '/')
    
    return {
        'success': True,
        'platform': 'douyin',
        'aweme_id': aweme_id,
        'title': title,
        'video_url': video_url,
        'video_url_wm': video_url_wm,
        'audio_url': audio_url
    }


def get_youtube_video(url: str) -> dict:
    """Get YouTube Shorts video"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cookie': 'CONSENT=YES+cb.20210720-07-p0.en+FX+999'
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
            resp = client.get(url)
            html = resp.text
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}
    
    video_url = None
    title = ''
    
    # Try to parse ytInitialPlayerResponse
    player_match = re.search(r'var ytInitialPlayerResponse = (\{.+?\});', html)
    if player_match:
        try:
            data = json.loads(player_match.group(1))
            
            # Get title
            title = data.get('videoDetails', {}).get('title', '')
            
            # Get streaming data
            streaming = data.get('streamingData', {})
            formats = streaming.get('formats', [])
            
            if formats:
                # Get highest quality format with url
                for fmt in reversed(formats):
                    if fmt.get('url'):
                        video_url = fmt['url']
                        break
        except:
            pass
    
    # Fallback: regex search
    if not video_url:
        url_match = re.search(r'"url":"(https://[^"]*googlevideo\.com/videoplayback[^"]+)"', html)
        if url_match:
            video_url = url_match.group(1).replace('\\u0026', '&')
    
    # Get title fallback
    if not title:
        title_match = re.search(r'"title":"([^"]+)"', html)
        if title_match:
            title = title_match.group(1)
    
    if not video_url:
        return {'error': 'Cannot find video URL'}
    
    return {
        'success': True,
        'platform': 'youtube',
        'title': title,
        'video_url': video_url
    }


# Xiaohongshu cookie
XHS_COOKIE = 'abRequestId=25ecac5a-e7e5-54f5-98c9-86e2d8f258ba; webBuild=5.11.0; xsecappid=xhs-pc-web; a1=19c64d47dcdxmyf53be9l10ocv6bjxd7b8m9uvfpi30000428035; webId=db6c9d6bdaa9e787cffb1beb42b7f547; gid=yjSK4f4j4YD4yjSK4f4WfYhiSfC6vi2qDdj16U3y8lShKjq8DVCfW78884JY8q284iJqWSf4; web_session=040069b8e6a36cc9d676f2a8a73b4bd26cc38e'

def get_xiaohongshu_video(url: str) -> dict:
    """Get Xiaohongshu media (video or images)"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Cookie': XHS_COOKIE,
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
            resp = client.get(url)
            html = resp.text
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}
    
    video_url = None
    images = []
    title = ''
    
    # Parse __INITIAL_STATE__
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>', html, re.DOTALL)
    if state_match:
        try:
            state_str = state_match.group(1).replace('undefined', 'null')
            data = json.loads(state_str)
            
            note_map = data.get('note', {}).get('noteDetailMap', {})
            if note_map:
                first_key = list(note_map.keys())[0]
                note_data = note_map[first_key].get('note', {})
                
                # Get title
                title = note_data.get('title', '')
                
                # Get video (if any)
                video = note_data.get('video', {})
                if video:
                    media = video.get('media', {})
                    stream = media.get('stream', {})
                    
                    # Find stream without watermark (no 'WM' in streamDesc)
                    # Priority: h264 no-WM > h265 no-WM > any stream
                    for codec in ['h264', 'h265', 'av1', 'h266']:
                        if codec in stream and stream[codec]:
                            for s in stream[codec]:
                                desc = s.get('streamDesc', '')
                                # Skip streams with WM (watermark) in description
                                if 'WM' not in desc.upper():
                                    master_url = s.get('masterUrl', '')
                                    if master_url:
                                        video_url = master_url
                                        break
                        if video_url:
                            break
                    
                    # Fallback to any stream if no non-WM found
                    if not video_url:
                        for codec in ['h264', 'h265']:
                            if codec in stream and stream[codec]:
                                master_url = stream[codec][0].get('masterUrl', '')
                                if master_url:
                                    video_url = master_url
                                    break
                
                # Get images (for image posts)
                if not video_url:
                    # Common structures: imageList (list of dicts with url), or images
                    if isinstance(note_data.get('imageList'), list):
                        for im in note_data['imageList']:
                            u = (im.get('url') or im.get('originUrl') or '').replace('\\u002F','/')
                            if u:
                                images.append(u)
                    elif isinstance(note_data.get('images'), list):
                        for im in note_data['images']:
                            if isinstance(im, str) and im.startswith('http'):
                                images.append(im)
                            elif isinstance(im, dict):
                                u = (im.get('url') or im.get('originUrl') or '').replace('\\u002F','/')
                                if u:
                                    images.append(u)
                    # Fallback: regex on HTML
                    if not images:
                        block = re.search(r'"imageList"\s*:\s*\[(.+?)\]', html, re.DOTALL)
                        if block:
                            urls = re.findall(r'"url"\s*:\s*"(https?:[^"\\]+)"', block.group(1))
                            images.extend([u.replace('\\u002F','/') for u in urls])
        except Exception as e:
            return {'error': f'Parse error: {str(e)}'}
    
    # If neither video nor images found -> error
    if not video_url and not images:
        return {'error': 'Cannot find media URL. Make sure it is a valid note.'}
    
    res = {
        'success': True,
        'platform': 'xiaohongshu',
        'title': title,
    }
    if video_url:
        res['video_url'] = video_url
    if images:
        res['images'] = images
    return res


def get_facebook_video(url: str) -> dict:
    """Get Facebook video"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
            resp = client.get(url)
            html = resp.text
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}
    
    video_url = None
    title = ''
    
    # Try different patterns for video URL
    # HD first, then SD
    patterns = [
        r'"browser_native_hd_url":"([^"]+)"',
        r'"browser_native_sd_url":"([^"]+)"',
        r'"playable_url_quality_hd":"([^"]+)"',
        r'"playable_url":"([^"]+)"',
        r'data-video-url="([^"]+)"',
        r'"video_url":"([^"]+)"',
        r'(https://video[^"<>\s]*fbcdn\.net[^"<>\s]*\.mp4[^"<>\s]*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            video_url = match.group(1)
            video_url = video_url.replace('\\/', '/').replace('\\u0025', '%').replace('&amp;', '&')
            break
    
    if not video_url:
        return {'error': 'Cannot find video URL'}
    
    # Get title
    title_match = re.search(r'<title>([^<]+)</title>', html)
    if title_match:
        title = title_match.group(1).split(' | ')[0]
    
    return {
        'success': True,
        'platform': 'facebook',
        'title': title,
        'video_url': video_url
    }


def get_tiktok_video(url: str) -> dict:
    """Get TikTok video without watermark using tikwm.com API"""
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            # Use tikwm.com API to get tiktokcdn URLs
            api_url = f'https://tikwm.com/api/?url={url}'
            resp = client.get(api_url)
            
            if resp.status_code != 200:
                return {'error': f'API request failed: {resp.status_code}'}
            
            data = resp.json()
            
            if not data.get('data'):
                return {'error': 'No data returned from API'}
            
            d = data['data']
            
            # No watermark video
            video_url = d.get('play') or d.get('hdplay')
            # Watermark video
            video_url_wm = d.get('wmplay', '')
            # Audio
            audio_url = d.get('music', '')
            
            if not video_url:
                video_url = video_url_wm
            
            if not video_url:
                return {'error': 'Cannot find video URL'}
            
            return {
                'success': True,
                'platform': 'tiktok',
                'aweme_id': d.get('id', ''),
                'title': d.get('title', ''),
                'video_url': video_url,
                'video_url_wm': video_url_wm,
                'audio_url': audio_url,
                'images': d.get('images', []) or [],
                'author': d.get('author', {}).get('nickname', ''),
                'cover': d.get('cover', '')
            }
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}


def get_twitter_video(url: str) -> dict:
    """Get Twitter/X video"""
    
    # Extract tweet ID from URL
    match = re.search(r'/status/(\d+)', url)
    if not match:
        return {'error': 'Cannot find tweet ID'}
    
    tweet_id = match.group(1)
    
    # Try using twitsave.com API
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            # Method 1: Use twitsave
            resp = client.get(
                f'https://twitsave.com/info?url={url}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                }
            )
            html = resp.text
            
            video_url = None
            title = ''
            
            # Find download links - prioritize highest quality
            # Look for direct mp4 links
            patterns = [
                r'<a[^>]*href="(https://[^"]+\.mp4[^"]*)"[^>]*>\s*Download\s*</a>',
                r'href="(https://video\.twimg\.com/[^"]+\.mp4[^"]*)"',
                r'(https://video\.twimg\.com/ext_tw_video/[^"\s<>]+\.mp4[^"\s<>]*)',
                r'(https://video\.twimg\.com/amplify_video/[^"\s<>]+\.mp4[^"\s<>]*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                if matches:
                    # Get highest quality (usually first or last)
                    video_url = matches[0]
                    video_url = video_url.replace('&amp;', '&')
                    break
            
            # Get title/description
            title_match = re.search(r'<p[^>]*class="[^"]*m-2[^"]*"[^>]*>([^<]+)</p>', html)
            if title_match:
                title = title_match.group(1).strip()
            
            if not video_url:
                # Method 2: Try ssstwitter
                resp2 = client.post(
                    'https://ssstwitter.com/r',
                    data={'id': url, 'locale': 'en'},
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
                html2 = resp2.text
                
                # Find video URL
                mp4_match = re.search(r'href="(https://[^"]+\.mp4[^"]*)"', html2)
                if mp4_match:
                    video_url = mp4_match.group(1).replace('&amp;', '&')
            
            if not video_url:
                return {'error': 'Cannot find video URL. Make sure the tweet contains a video.'}
            
            return {
                'success': True,
                'platform': 'twitter',
                'tweet_id': tweet_id,
                'title': title,
                'video_url': video_url
            }
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query params
        query = {}
        if '?' in self.path:
            query_string = self.path.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    query[k] = unquote(v)
        
        # Check API key
        key = query.get('key', '')
        if key != API_KEY:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid API key'}).encode())
            return
        
        # Get video URL
        url = query.get('url', '')
        if not url:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing url parameter'}).encode())
            return
        
        # Fetch video
        try:
            if 'douyin.com' in url:
                result = get_douyin_video(url)
            elif 'tiktok.com' in url or 'vt.tiktok.com' in url:
                result = get_tiktok_video(url)
            elif 'facebook.com' in url or 'fb.watch' in url or 'web.facebook.com' in url:
                result = get_facebook_video(url)
            elif 'xiaohongshu.com' in url or 'xhslink.com' in url:
                result = get_xiaohongshu_video(url)
            elif 'twitter.com' in url or 'x.com' in url:
                result = get_twitter_video(url)
            else:
                result = {'error': 'Unsupported platform'}
            
            status = 200 if result.get('success') else 400
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
