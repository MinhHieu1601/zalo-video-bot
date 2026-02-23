"""
Scheduler - Chạy jobs đăng video theo lịch
"""

import asyncio
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as db
from video_downloader import download_from_share_url, cleanup_old_videos
from zalo_uploader import upload_video_to_zalo

import os

# Telegram bot để gửi thông báo
BOT_TOKEN = os.getenv("BOT_TOKEN", "8636525026:AAHrvCkUnWKJ5C3GlrcD_u87eRUy270b_IE")

async def send_telegram_notification(user_id: int, message: str):
    """Gửi thông báo qua Telegram"""
    try:
        import httpx
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": user_id,
                "text": message,
                "parse_mode": "Markdown"
            })
    except Exception as e:
        print(f"❌ Lỗi gửi thông báo Telegram: {e}")

async def process_job(job: dict):
    """Xử lý một job đăng video"""
    job_id = job['id']
    print(f"\n{'='*50}")
    print(f"🔄 Đang xử lý Job #{job_id}")
    print(f"   Video: {job['video_url'][:50]}...")
    print(f"   Account: {job['account_name']}")
    
    try:
        # Cập nhật status = processing
        db.update_job_status(job_id, 'processing')
        
        # Download video
        print(f"⏳ Đang download video...")
        video_path, video_info = await download_from_share_url(job['video_url'])
        
        if not video_path:
            raise Exception("Không download được video")
        
        # Cập nhật video_path
        db.update_job_video_path(job_id, video_path)
        print(f"✅ Đã download: {video_path}")
        
        # Upload lên Zalo
        print(f"⏳ Đang upload lên Zalo...")
        success, message = upload_video_to_zalo(
            video_path=video_path,
            cookies_json=job['cookies'],
            caption=job.get('caption'),
            schedule_time=None,  # Đăng ngay vì đã đến giờ
            headless=True
        )
        
        if success:
            db.update_job_status(job_id, 'completed')
            print(f"✅ Job #{job_id} hoàn thành!")
            
            # Gửi thông báo
            await send_telegram_notification(
                job['telegram_user_id'],
                f"✅ *Job #{job_id} đã đăng thành công!*\n\n"
                f"👤 Account: {job['account_name']}\n"
                f"📝 Caption: {job.get('caption') or 'Không có'}"
            )
        else:
            raise Exception(message)
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Job #{job_id} thất bại: {error_msg}")
        db.update_job_status(job_id, 'failed', error_msg)
        
        # Gửi thông báo lỗi
        await send_telegram_notification(
            job['telegram_user_id'],
            f"❌ *Job #{job_id} thất bại!*\n\n"
            f"👤 Account: {job['account_name']}\n"
            f"🔴 Lỗi: {error_msg[:200]}"
        )

async def check_and_process_jobs():
    """Kiểm tra và xử lý các jobs đến giờ"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Kiểm tra jobs...")
    
    # Lấy jobs pending đã đến giờ
    jobs = db.get_pending_jobs()
    
    if not jobs:
        print("   Không có job nào cần xử lý")
        return
    
    print(f"   Tìm thấy {len(jobs)} jobs cần xử lý")
    
    # Xử lý từng job
    for job in jobs:
        await process_job(job)
        # Delay giữa các jobs để tránh bị block
        await asyncio.sleep(5)

def cleanup_task():
    """Dọn dẹp video cũ"""
    print(f"\n🗑️ [{datetime.now().strftime('%H:%M:%S')}] Dọn dẹp video cũ...")
    cleanup_old_videos(max_age_hours=24)

def create_scheduler() -> AsyncIOScheduler:
    """Tạo và cấu hình scheduler"""
    scheduler = AsyncIOScheduler()
    
    # Kiểm tra jobs mỗi 1 phút
    scheduler.add_job(
        check_and_process_jobs,
        trigger=IntervalTrigger(minutes=1),
        id='check_jobs',
        name='Check and process pending jobs',
        replace_existing=True
    )
    
    # Dọn dẹp video cũ mỗi 6 giờ
    scheduler.add_job(
        cleanup_task,
        trigger=IntervalTrigger(hours=6),
        id='cleanup',
        name='Cleanup old videos',
        replace_existing=True
    )
    
    return scheduler

async def run_scheduler():
    """Chạy scheduler"""
    print("🚀 Khởi động Scheduler...")
    
    scheduler = create_scheduler()
    scheduler.start()
    
    print("✅ Scheduler đang chạy")
    print("   - Kiểm tra jobs: mỗi 1 phút")
    print("   - Dọn dẹp video: mỗi 6 giờ")
    
    # Chạy kiểm tra ngay lập tức
    await check_and_process_jobs()
    
    # Giữ scheduler chạy
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\n👋 Scheduler đã dừng")

if __name__ == "__main__":
    # Init database
    db.init_database()
    
    # Chạy scheduler
    asyncio.run(run_scheduler())
