import re
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8064862449:AAFizHK73KR_6K3xXB5byeA62Zd-dDr97qM"
API_URL = "https://douyin-api-vercel.vercel.app/api"
API_KEY = "hieudepzainhatvutru1601"

# Store user states
user_states = {}

def extract_url(text: str) -> str | None:
    """Extract Douyin, TikTok or Facebook URL from text"""
    patterns = [
        r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?',
        r'https?://www\.douyin\.com/video/\d+',
        r'https?://vt\.tiktok\.com/[A-Za-z0-9_-]+/?',
        r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+',
        # Facebook Reels
        r'https?://(?:web\.)?facebook\.com/share/r/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?',
        r'https?://(?:www\.)?facebook\.com/reel/\d+/?(?:\?[^\s]*)?',
        r'https?://fb\.watch/[A-Za-z0-9_-]+/?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📥 Download Video", callback_data="download")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Chào mừng bạn đến với Bot Download Video!\n\n"
        "Hỗ trợ: Douyin, TikTok & Facebook Reels\n\n"
        "Bấm nút bên dưới để tải video:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "download":
        user_id = query.from_user.id
        user_states[user_id] = "waiting_url"
        await query.message.reply_text(
            "📎 Gửi link video hoặc paste nội dung có chứa link Douyin/TikTok/Facebook:"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Check if user is in download mode or just sent a link
    url = extract_url(text)
    
    if not url:
        # No URL found, show menu
        keyboard = [[InlineKeyboardButton("📥 Download Video", callback_data="download")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ Không tìm thấy link Douyin/TikTok/Facebook.\n\nBấm nút để thử lại:",
            reply_markup=reply_markup
        )
        return
    
    # Clear state
    user_states.pop(user_id, None)
    
    # Send processing message
    processing_msg = await update.message.reply_text("⏳ Đang xử lý...")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API_URL}?key={API_KEY}&url={url}")
            data = resp.json()
        
        if not data.get("success"):
            await processing_msg.edit_text(f"❌ Lỗi: {data.get('error', 'Unknown error')}")
            return
        
        video_url = data.get("video_url")
        title = data.get("title", "")
        platform = data.get("platform", "").upper()
        author = data.get("author", "")
        
        # Caption is just the title
        caption = title if title else ""
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send video
        await update.message.reply_video(
            video=video_url,
            caption=caption[:1024],  # Telegram caption limit
            supports_streaming=True
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Lỗi: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
