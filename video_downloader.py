"""
Download video no watermark từ Douyin/TikTok/Facebook
"""

import os
import httpx
import asyncio
from pathlib import Path

# API settings
API_URL = "https://douyin-api-vercel.vercel.app/api"
API_KEY = "hieudepzainhatvutru1601"

# Thư mục lưu video
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

async def get_video_info(url: str) -> dict | None:
    """Lấy thông tin video từ API"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API_URL}?key={API_KEY}&url={url}")
            data = resp.json()
            
            if data.get("success"):
                return {
                    "video_url": data.get("video_url"),
                    "title": data.get("title", ""),
                    "author": data.get("author", ""),
                    "platform": data.get("platform", "")
                }
    except Exception as e:
        print(f"❌ Lỗi lấy thông tin video: {e}")
    return None

async def download_video(video_url: str, filename: str | None = None) -> str | None:
    """
    Download video từ URL, trả về đường dẫn file
    """
    try:
        # Tạo filename nếu chưa có
        if not filename:
            filename = f"video_{int(asyncio.get_event_loop().time() * 1000)}.mp4"
        
        filepath = DOWNLOAD_DIR / filename
        
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            print(f"⏳ Đang download video...")
            
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                
                with open(filepath, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        
        print(f"✅ Đã download: {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"❌ Lỗi download video: {e}")
        return None

async def download_from_share_url(share_url: str) -> tuple[str | None, dict | None]:
    """
    Download video từ share URL (Douyin/TikTok/Facebook)
    Trả về (video_path, video_info)
    """
    # Lấy thông tin video
    info = await get_video_info(share_url)
    if not info or not info.get("video_url"):
        return None, None
    
    # Download video
    video_path = await download_video(info["video_url"])
    return video_path, info

def cleanup_old_videos(max_age_hours: int = 24):
    """Xóa video cũ hơn max_age_hours"""
    import time
    
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for file in DOWNLOAD_DIR.glob("*.mp4"):
        if now - file.stat().st_mtime > max_age_seconds:
            file.unlink()
            print(f"🗑️ Đã xóa video cũ: {file.name}")

# Test
if __name__ == "__main__":
    async def test():
        url = "https://v.douyin.com/xjwq9fXD-IU/"
        video_path, info = await download_from_share_url(url)
        if video_path:
            print(f"✅ Downloaded: {video_path}")
            print(f"📝 Title: {info.get('title')}")
        else:
            print("❌ Download failed")
    
    asyncio.run(test())
