"""
Telegram Bot - Upload video lên Zalo Video
"""

import re
import os
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)

import database as db
from video_downloader import get_video_info

# Bot settings - Lấy từ environment variable (không hardcode)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ Thiếu BOT_TOKEN! Set environment variable BOT_TOKEN")
API_URL = "https://douyin-api-vercel.vercel.app/api"
API_KEY = "hieudepzainhatvutru1601"

# Conversation states
(
    UPVIDEO_LINK,
    UPVIDEO_CAPTION,
    UPVIDEO_SCHEDULE,
    UPVIDEO_ACCOUNT,
    NEWPROFILE_COOKIE,
    NEWPROFILE_NAME,
) = range(6)

# Temp storage cho conversation
user_data = {}

def extract_url(text: str) -> str | None:
    """Extract video URL from text"""
    patterns = [
        r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?',
        r'https?://www\.douyin\.com/video/\d+',
        r'https?://vt\.tiktok\.com/[A-Za-z0-9_-]+/?',
        r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+',
        r'https?://(?:web\.)?facebook\.com/share/r/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?',
        r'https?://(?:www\.)?facebook\.com/reel/\d+/?(?:\?[^\s]*)?',
        r'https?://fb\.watch/[A-Za-z0-9_-]+/?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

# ==================== START ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start - Menu chính"""
    keyboard = [
        [InlineKeyboardButton("📤 Upload Video Zalo", callback_data="upvideo")],
        [InlineKeyboardButton("👤 Quản lý Account", callback_data="accounts")],
        [InlineKeyboardButton("📋 Xem Jobs", callback_data="jobs")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 *Chào mừng đến với Zalo Video Bot!*\n\n"
        "📤 `/upvideo` - Upload video lên Zalo\n"
        "👤 `/newprofile` - Thêm tài khoản Zalo\n"
        "📋 `/jobs` - Xem danh sách jobs\n"
        "📊 `/accounts` - Xem tài khoản Zalo\n\n"
        "Chọn chức năng:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ==================== UPLOAD VIDEO ====================

async def upvideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bắt đầu flow upload video (từ command /upvideo)"""
    # Kiểm tra có account nào chưa
    accounts = db.get_all_accounts()
    if not accounts:
        await update.message.reply_text(
            "❌ Chưa có tài khoản Zalo nào!\n\n"
            "Dùng `/newprofile` để thêm tài khoản trước."
        )
        return ConversationHandler.END
    
    user_data[update.effective_user.id] = {}
    
    await update.message.reply_text(
        "📤 *UPLOAD VIDEO LÊN ZALO*\n\n"
        "Bước 1/4: Gửi link video (Douyin/TikTok/Facebook):",
        parse_mode="Markdown"
    )
    return UPVIDEO_LINK

async def upvideo_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bắt đầu flow upload video (từ inline button)"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra có account nào chưa
    accounts = db.get_all_accounts()
    if not accounts:
        await query.message.reply_text(
            "❌ Chưa có tài khoản Zalo nào!\n\n"
            "Dùng `/newprofile` để thêm tài khoản trước."
        )
        return ConversationHandler.END
    
    user_data[query.from_user.id] = {}
    
    await query.message.reply_text(
        "📤 *UPLOAD VIDEO LÊN ZALO*\n\n"
        "Bước 1/4: Gửi link video (Douyin/TikTok/Facebook):",
        parse_mode="Markdown"
    )
    return UPVIDEO_LINK

async def upvideo_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận link video"""
    text = update.message.text
    url = extract_url(text)
    
    if not url:
        await update.message.reply_text(
            "❌ Không tìm thấy link video hợp lệ!\n\n"
            "Hỗ trợ: Douyin, TikTok, Facebook Reels\n"
            "Gửi lại link:"
        )
        return UPVIDEO_LINK
    
    # Lưu URL
    user_data[update.effective_user.id]['video_url'] = url
    
    # Kiểm tra video
    processing = await update.message.reply_text("⏳ Đang kiểm tra video...")
    info = await get_video_info(url)
    
    if not info:
        await processing.edit_text(
            "❌ Không lấy được thông tin video!\n\n"
            "Gửi lại link khác:"
        )
        return UPVIDEO_LINK
    
    user_data[update.effective_user.id]['video_info'] = info
    
    await processing.edit_text(
        f"✅ *Video hợp lệ!*\n\n"
        f"📝 Title: {info.get('title', 'N/A')[:100]}\n"
        f"👤 Author: {info.get('author', 'N/A')}\n\n"
        f"Bước 2/4: Nhập caption (gửi `0` nếu không cần):",
        parse_mode="Markdown"
    )
    return UPVIDEO_CAPTION

async def upvideo_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận caption"""
    text = update.message.text.strip()
    
    if text == "0":
        user_data[update.effective_user.id]['caption'] = None
    else:
        user_data[update.effective_user.id]['caption'] = text
    
    await update.message.reply_text(
        "Bước 3/4: Nhập thời gian đăng\n\n"
        "📅 Format: `DD-MM-YYYY HH:mm`\n"
        "Ví dụ: `23-02-2026 11:20`\n\n"
        "Gửi `0` để đăng ngay:",
        parse_mode="Markdown"
    )
    return UPVIDEO_SCHEDULE

async def upvideo_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận thời gian đăng"""
    text = update.message.text.strip()
    
    if text == "0":
        user_data[update.effective_user.id]['schedule_time'] = None
        schedule_display = "Đăng ngay"
    else:
        # Validate format
        try:
            dt = datetime.strptime(text, "%d-%m-%Y %H:%M")
            user_data[update.effective_user.id]['schedule_time'] = text
            schedule_display = text
        except ValueError:
            await update.message.reply_text(
                "❌ Format không đúng!\n\n"
                "📅 Format: `DD-MM-YYYY HH:mm`\n"
                "Ví dụ: `23-02-2026 11:20`\n\n"
                "Nhập lại:",
                parse_mode="Markdown"
            )
            return UPVIDEO_SCHEDULE
    
    # Hiển thị danh sách account
    accounts = db.get_all_accounts()
    account_list = "\n".join([
        f"  {acc['id']}. {acc['name']}" for acc in accounts
    ])
    
    await update.message.reply_text(
        f"Bước 4/4: Chọn tài khoản Zalo\n\n"
        f"📋 Danh sách:\n{account_list}\n\n"
        f"Nhập số thứ tự:",
        parse_mode="Markdown"
    )
    return UPVIDEO_ACCOUNT

async def upvideo_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận account và tạo job"""
    text = update.message.text.strip()
    
    try:
        account_id = int(text)
        account = db.get_account_by_id(account_id)
        
        if not account:
            accounts = db.get_all_accounts()
            account_list = "\n".join([
                f"  {acc['id']}. {acc['name']}" for acc in accounts
            ])
            await update.message.reply_text(
                f"❌ Không tìm thấy account #{account_id}!\n\n"
                f"📋 Danh sách:\n{account_list}\n\n"
                f"Nhập lại số thứ tự:"
            )
            return UPVIDEO_ACCOUNT
        
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số!\n\nNhập lại:")
        return UPVIDEO_ACCOUNT
    
    # Tạo job
    data = user_data[update.effective_user.id]
    
    # Parse schedule_time thành datetime
    schedule_dt = None
    if data.get('schedule_time'):
        schedule_dt = datetime.strptime(data['schedule_time'], "%d-%m-%Y %H:%M")
    
    job_id = db.create_job(
        video_url=data['video_url'],
        zalo_account_id=account_id,
        telegram_user_id=update.effective_user.id,
        caption=data.get('caption'),
        schedule_time=schedule_dt
    )
    
    # Xóa temp data
    del user_data[update.effective_user.id]
    
    schedule_display = data.get('schedule_time') or "Đăng ngay"
    caption_display = data.get('caption') or "(Không có)"
    
    await update.message.reply_text(
        f"✅ *Đã tạo job #{job_id}!*\n\n"
        f"🔗 Video: {data['video_url'][:50]}...\n"
        f"📝 Caption: {caption_display[:50]}\n"
        f"📅 Thời gian: {schedule_display}\n"
        f"👤 Account: {account['name']}\n\n"
        f"Bot sẽ tự động đăng theo lịch.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def upvideo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hủy flow upload"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text("❌ Đã hủy upload video.")
    return ConversationHandler.END

# ==================== NEW PROFILE ====================

async def newprofile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bắt đầu flow thêm profile"""
    user_data[update.effective_user.id] = {}
    
    await update.message.reply_text(
        "👤 *THÊM TÀI KHOẢN ZALO*\n\n"
        "Bước 1/2: Gửi file cookie JSON\n"
        "(Export từ J2Team Cookies)",
        parse_mode="Markdown"
    )
    return NEWPROFILE_COOKIE

async def newprofile_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận file cookie"""
    # Kiểm tra có file không
    if update.message.document:
        file = await update.message.document.get_file()
        content = (await file.download_as_bytearray()).decode('utf-8')
    elif update.message.text:
        content = update.message.text
    else:
        await update.message.reply_text(
            "❌ Vui lòng gửi file JSON hoặc paste nội dung JSON!"
        )
        return NEWPROFILE_COOKIE
    
    # Validate JSON
    try:
        import json
        data = json.loads(content)
        
        # Kiểm tra format J2Team
        if isinstance(data, dict) and 'cookies' in data:
            cookies_count = len(data['cookies'])
        elif isinstance(data, list):
            cookies_count = len(data)
        else:
            raise ValueError("Invalid format")
        
        user_data[update.effective_user.id]['cookies'] = content
        
        await update.message.reply_text(
            f"✅ Đã nhận {cookies_count} cookies!\n\n"
            "Bước 2/2: Đặt tên cho profile\n"
            "(Ví dụ: Hiếu, Account 1, Shop ABC...)"
        )
        return NEWPROFILE_NAME
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ File JSON không hợp lệ!\n\n"
            f"Lỗi: {str(e)}\n\n"
            "Gửi lại file cookie:"
        )
        return NEWPROFILE_COOKIE

async def newprofile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận tên profile và lưu"""
    name = update.message.text.strip()
    
    if len(name) < 1 or len(name) > 100:
        await update.message.reply_text(
            "❌ Tên phải từ 1-100 ký tự!\n\nNhập lại:"
        )
        return NEWPROFILE_NAME
    
    cookies = user_data[update.effective_user.id]['cookies']
    
    # Lưu vào database
    account_id = db.add_zalo_account(name, cookies)
    
    # Xóa temp data
    del user_data[update.effective_user.id]
    
    await update.message.reply_text(
        f"✅ *Đã thêm tài khoản!*\n\n"
        f"🆔 ID: {account_id}\n"
        f"👤 Tên: {name}\n\n"
        f"Dùng `/upvideo` để upload video.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def newprofile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hủy flow thêm profile"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text("❌ Đã hủy thêm tài khoản.")
    return ConversationHandler.END

# ==================== ACCOUNTS & JOBS ====================

async def accounts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách accounts"""
    accounts = db.get_all_accounts()
    
    if not accounts:
        text = "📊 Chưa có tài khoản Zalo nào!\n\nDùng `/newprofile` để thêm."
    else:
        lines = ["📊 *DANH SÁCH TÀI KHOẢN ZALO*\n"]
        for acc in accounts:
            lines.append(f"  {acc['id']}. {acc['name']}")
        text = "\n".join(lines)
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def jobs_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách jobs của user"""
    jobs = db.get_jobs_by_user(update.effective_user.id)
    
    if not jobs:
        text = "📋 Chưa có job nào!\n\nDùng `/upvideo` để tạo job mới."
    else:
        lines = ["📋 *DANH SÁCH JOBS*\n"]
        for job in jobs:
            status_emoji = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(job['status'], '❓')
            
            schedule = job['schedule_time'].strftime("%d-%m-%Y %H:%M") if job['schedule_time'] else "Ngay"
            
            lines.append(
                f"{status_emoji} *Job #{job['id']}*\n"
                f"   📅 {schedule} | 👤 {job['account_name']}\n"
                f"   📝 {(job['caption'] or 'Không caption')[:30]}"
            )
        text = "\n\n".join(lines)
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== CALLBACK QUERY ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý callback từ inline buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accounts":
        accounts = db.get_all_accounts()
        if not accounts:
            text = "📊 Chưa có tài khoản Zalo nào!\n\nDùng `/newprofile` để thêm."
        else:
            lines = ["📊 *DANH SÁCH TÀI KHOẢN ZALO*\n"]
            for acc in accounts:
                lines.append(f"  {acc['id']}. {acc['name']}")
            text = "\n".join(lines)
        await query.message.reply_text(text, parse_mode="Markdown")
    
    elif query.data == "jobs":
        jobs = db.get_jobs_by_user(query.from_user.id)
        if not jobs:
            text = "📋 Chưa có job nào!"
        else:
            lines = ["📋 *DANH SÁCH JOBS*\n"]
            for job in jobs:
                status_emoji = {'pending': '⏳', 'completed': '✅', 'failed': '❌'}.get(job['status'], '❓')
                lines.append(f"{status_emoji} Job #{job['id']} - {job['account_name']}")
            text = "\n".join(lines)
        await query.message.reply_text(text, parse_mode="Markdown")
    
# ==================== MAIN ====================

def create_bot_application():
    """Tạo và cấu hình bot application"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler cho /upvideo
    upvideo_handler = ConversationHandler(
        entry_points=[
            CommandHandler("upvideo", upvideo_start),
            CallbackQueryHandler(upvideo_start_callback, pattern="^upvideo$"),
        ],
        states={
            UPVIDEO_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, upvideo_link)],
            UPVIDEO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, upvideo_caption)],
            UPVIDEO_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, upvideo_schedule)],
            UPVIDEO_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, upvideo_account)],
        },
        fallbacks=[CommandHandler("cancel", upvideo_cancel)],
        per_message=False,
    )
    
    # Conversation handler cho /newprofile
    newprofile_handler = ConversationHandler(
        entry_points=[CommandHandler("newprofile", newprofile_start)],
        states={
            NEWPROFILE_COOKIE: [
                MessageHandler(filters.Document.ALL, newprofile_cookie),
                MessageHandler(filters.TEXT & ~filters.COMMAND, newprofile_cookie),
            ],
            NEWPROFILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, newprofile_name)],
        },
        fallbacks=[CommandHandler("cancel", newprofile_cancel)],
    )
    
    # Thêm handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(upvideo_handler)
    app.add_handler(newprofile_handler)
    app.add_handler(CommandHandler("accounts", accounts_list))
    app.add_handler(CommandHandler("jobs", jobs_list))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    return app

def main():
    """Chạy bot standalone"""
    # Init database
    db.init_database()
    
    app = create_bot_application()
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
