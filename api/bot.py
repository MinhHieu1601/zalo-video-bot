import re
import json
import httpx
import time
from urllib.parse import quote
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = "8463335315:AAEO5UifHqDIfLkkIeOhqk4RO7U9e_5nonE"

# Rate limit: 10 seconds between messages
RATE_LIMIT_SECONDS = 10
user_last_request = {}
API_URL = "https://douyin-api-vercel.vercel.app/api"
API_KEY = "hieudepzainhatvutru1601"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def extract_url(text: str) -> str | None:
    """Extract Douyin, TikTok, Facebook, Twitter/X URL from text"""
    patterns = [
        r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?',
        r'https?://www\.douyin\.com/video/\d+',
        r'https?://www\.douyin\.com/[^\s]*modal_id=\d+',
        r'https?://vt\.tiktok\.com/[A-Za-z0-9_-]+/?',
        r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+',
        r'https?://(?:www\.)?tiktok\.com/@[^/]+/photo/\d+',
        r'https?://(?:www\.|web\.)?facebook\.com/[^\s]+',
        r'https?://fb\.watch/[A-Za-z0-9_-]+/?',
        r'https?://(?:www\.)?xiaohongshu\.com/[^\s]+',
        r'https?://xhslink\.com/[A-Za-z0-9_-]+/?',
        r'https?://(?:www\.)?twitter\.com/[^/]+/status/\d+',
        r'https?://(?:www\.)?x\.com/[^/]+/status/\d+',
        r'https?://x\.com/i/status/\d+',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def send_message(chat_id: int, text: str, reply_markup: dict = None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/sendMessage", data=data)

def get_file_size(url: str) -> int:
    """Get file size from URL using HEAD request"""
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.head(url)
            content_length = resp.headers.get('content-length')
            if content_length:
                return int(content_length)
    except:
        pass
    return 0


def format_caption(title: str, audio_url: str = '') -> str:
    """Format caption with code block for easy copying"""
    if not title and not audio_url:
        return ''
    parts = []
    if title:
        t = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        parts.append(f"Caption:\n<pre>{t[:800]}</pre>")
    if audio_url:
        parts.append(f'Audio (MP3):\n<a href="{audio_url}">Tải xuống</a>')
    return '\n\n'.join(parts)

def send_images_with_options(chat_id: int, data: dict):
    """Send image(s) with caption if provided."""
    title = data.get('title', '')
    images = data.get('images', []) or []
    audio_url = data.get('audio_url', '')
    if not images:
        return
    caption = format_caption(title, audio_url)
    with httpx.Client(timeout=120) as client:
        if len(images) == 1:
            # Send single photo with caption
            client.post(f"{TELEGRAM_API}/sendPhoto", data={
                'chat_id': chat_id,
                'photo': images[0],
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            # Send as album (chunks of 10); caption only on the first image of the first chunk
            for i in range(0, len(images), 10):
                chunk = images[i:i+10]
                media = []
                for idx, url in enumerate(chunk):
                    item = {'type': 'photo', 'media': url}
                    if i == 0 and idx == 0 and caption:
                        item['caption'] = caption
                        item['parse_mode'] = 'HTML'
                    media.append(item)
                client.post(f"{TELEGRAM_API}/sendMediaGroup", data={
                    'chat_id': chat_id,
                    'media': json.dumps(media)
                })


def send_video_with_options(chat_id: int, data: dict):
    """Send video with buttons for TikTok/Douyin"""
    platform = data.get('platform', '')
    video_url = data.get('video_url', '')
    audio_url = data.get('audio_url', '')
    title = data.get('title', '')
    
    with httpx.Client(timeout=120) as client:
        # Try to send video with caption; attach Audio button (if any) to the video message itself
        caption = format_caption(title)
        send_data = {
            "chat_id": chat_id,
            "video": video_url,
            "caption": caption,
            "parse_mode": "HTML",
            "supports_streaming": "true"
        }
        if audio_url:
            send_data["reply_markup"] = json.dumps({
                "inline_keyboard": [[{"text": "Audio (MP3)", "url": audio_url}]]
            })
        resp = client.post(f"{TELEGRAM_API}/sendVideo", data=send_data)
        result = resp.json()
        
        if result.get("ok"):
            # Video sent successfully; nothing else to send
            pass
        else:
            # Failed to send video (too large or other error) - send buttons
            buttons = []
            buttons.append([{"text": "Download Video", "url": video_url}])
            if audio_url:
                buttons.append([{"text": "Audio (MP3)", "url": audio_url}])
            
            message = "Video tìm thấy. Bấm nút để tải."
            
            client.post(f"{TELEGRAM_API}/sendMessage", data={
                "chat_id": chat_id,
                "text": message,
                "reply_markup": json.dumps({"inline_keyboard": buttons})
            })

def edit_message(chat_id: int, message_id: int, text: str):
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/editMessageText", data={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        })

def delete_message(chat_id: int, message_id: int):
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/deleteMessage", data={
            "chat_id": chat_id,
            "message_id": message_id
        })

FANPAGE = "https://www.facebook.com/ANCAvn1/"

def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "Các nền tảng hỗ trợ"}, {"text": "Liên hệ"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def handle_start(chat_id: int):
    # Send welcome with reply keyboard
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/sendMessage", data={
            "chat_id": chat_id,
            "text": "ANCA Video Downloader\n\n"
                    "Tải video không watermark từ:\n"
                    "Douyin | TikTok | Facebook | Twitter/X | Xiaohongshu\n\n"
                    "Gửi link video để bắt đầu.",
            "reply_markup": json.dumps(get_main_keyboard())
        })

def handle_support(chat_id: int):
    keyboard = {
        "inline_keyboard": [
            [{"text": "Liên hệ qua Fanpage", "url": FANPAGE}]
        ]
    }
    send_message(
        chat_id,
        "Hỗ trợ & Liên hệ\n\n"
        "Mọi thắc mắc và yêu cầu hỗ trợ, vui lòng liên hệ qua Fanpage chính thức của ANCA.",
        keyboard
    )

def handle_platforms(chat_id: int):
    keyboard = {
        "inline_keyboard": [[{"text": "ANCA Fanpage", "url": FANPAGE}]]
    }
    send_message(
        chat_id,
        "Nền tảng hỗ trợ\n\n"
        "- Douyin (video & ảnh)\n"
        "- TikTok (video & ảnh)\n"
        "- Facebook Reels\n"
        "- Twitter / X\n"
        "- Xiaohongshu\n\n"
        "Gửi link video để tải ngay.",
        keyboard
    )

def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """Check if user is rate limited. Returns (is_allowed, seconds_remaining)"""
    current_time = time.time()
    last_time = user_last_request.get(user_id, 0)
    time_passed = current_time - last_time
    
    if time_passed < RATE_LIMIT_SECONDS:
        return False, int(RATE_LIMIT_SECONDS - time_passed)
    
    user_last_request[user_id] = current_time
    return True, 0

def handle_text_message(chat_id: int, user_id: int, text: str):
    # Check rate limit
    is_allowed, seconds_remaining = check_rate_limit(user_id)
    if not is_allowed:
        send_message(chat_id, f"Vui lòng chờ {seconds_remaining}s trước khi gửi link tiếp theo.")
        return
    
    url = extract_url(text)
    
    if not url:
        keyboard = {
            "inline_keyboard": [
                [{"text": "Xem nền tảng hỗ trợ", "callback_data": "platforms"}],
                [{"text": "ANCA Fanpage", "url": FANPAGE}]
            ]
        }
        send_message(chat_id, "Không tìm thấy link hợp lệ.\n\nVui lòng gửi link từ các nền tảng được hỗ trợ.", keyboard)
        return
    
    # Send processing message
    with httpx.Client(timeout=10) as client:
        resp = client.post(f"{TELEGRAM_API}/sendMessage", data={
            "chat_id": chat_id,
            "text": "Đang xử lý..."
        })
        msg_data = resp.json()
        processing_msg_id = msg_data.get("result", {}).get("message_id")
    
    try:
        # Call our API (URL encode the video URL)
        encoded_url = quote(url, safe='')
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{API_URL}?key={API_KEY}&url={encoded_url}")
            data = resp.json()

        if not data.get("success"):
            edit_message(chat_id, processing_msg_id, f"Lỗi: {data.get('error', 'Unknown error')}")
            return
        
        # Delete processing message
        delete_message(chat_id, processing_msg_id)
        
        # Choose media type
        if data.get('images'):
            send_images_with_options(chat_id, data)
        else:
            send_video_with_options(chat_id, data)
        
    except Exception as e:
        edit_message(chat_id, processing_msg_id, f"Lỗi: {str(e)}")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update = json.loads(body)
            
            # Handle /start command
            if "message" in update:
                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                
                if text == "/start":
                    handle_start(chat_id)
                elif text == "/fanpage":
                    handle_support(chat_id)
                elif text == "Liên hệ":
                    handle_support(chat_id)
                elif text == "Các nền tảng hỗ trợ":
                    handle_platforms(chat_id)
                else:
                    user_id = message["from"]["id"]
                    handle_text_message(chat_id, user_id, text)
            
            # Handle button callback
            elif "callback_query" in update:
                callback = update["callback_query"]
                chat_id = callback["message"]["chat"]["id"]
                callback_data = callback.get("data", "")
                
                # Answer callback to remove loading state
                with httpx.Client(timeout=10) as client:
                    client.post(f"{TELEGRAM_API}/answerCallbackQuery", data={
                        "callback_query_id": callback["id"]
                    })
                
                if callback_data == "platforms":
                    handle_platforms(chat_id)
                elif callback_data == "support":
                    handle_support(chat_id)
        
        except Exception as e:
            print(f"Error: {e}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Bot webhook is running"}).encode())
