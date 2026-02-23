#!/usr/bin/env python3
"""
Main - Chạy Telegram Bot + Scheduler
"""

import asyncio
import threading
from telegram.ext import Application

import database as db
from bot import create_bot_application
from scheduler import create_scheduler, check_and_process_jobs

async def run_bot_with_scheduler():
    """Chạy bot và scheduler cùng lúc"""
    print("=" * 60)
    print("🚀 ZALO VIDEO UPLOAD BOT")
    print("=" * 60)
    
    # Init database
    print("\n📦 Khởi tạo database...")
    db.init_database()
    
    # Tạo bot application
    print("🤖 Khởi tạo Telegram Bot...")
    app = create_bot_application()
    
    # Tạo scheduler
    print("⏰ Khởi tạo Scheduler...")
    scheduler = create_scheduler()
    scheduler.start()
    
    print("\n" + "=" * 60)
    print("✅ HỆ THỐNG ĐÃ SẴN SÀNG!")
    print("=" * 60)
    print("\n📋 Các lệnh Telegram:")
    print("   /start      - Menu chính")
    print("   /upvideo    - Upload video lên Zalo")
    print("   /newprofile - Thêm tài khoản Zalo")
    print("   /accounts   - Xem danh sách tài khoản")
    print("   /jobs       - Xem danh sách jobs")
    print("\n⏰ Scheduler:")
    print("   - Kiểm tra jobs: mỗi 1 phút")
    print("   - Dọn dẹp video cũ: mỗi 6 giờ")
    print("\n" + "=" * 60)
    
    # Chạy kiểm tra jobs ngay
    await check_and_process_jobs()
    
    # Chạy bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=['message', 'callback_query'])
    
    print("\n🤖 Bot đang chạy... Nhấn Ctrl+C để dừng")
    
    try:
        # Giữ chương trình chạy
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹️ Đang dừng...")
        scheduler.shutdown()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("👋 Đã dừng hệ thống")

def main():
    """Entry point"""
    try:
        asyncio.run(run_bot_with_scheduler())
    except KeyboardInterrupt:
        print("\n👋 Bye!")

if __name__ == "__main__":
    main()
