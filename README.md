# Douyin API Vercel

API để tải video từ Douyin, TikTok, Facebook và Xiaohongshu không watermark.

## API Endpoint

```
GET /api?key=YOUR_API_KEY&url=VIDEO_URL
```

### Supported Platforms
- Douyin (抖音)
- TikTok
- Facebook Reels
- Xiaohongshu (小红书)

### Response
```json
{
  "success": true,
  "platform": "douyin",
  "title": "Video title",
  "video_url": "https://..."
}
```

## Telegram Bot

Bot webhook endpoint: `/api/bot`

Set webhook:
```
https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://douyin-api-vercel.vercel.app/api/bot
```

## Deploy to Vercel

1. Fork this repo
2. Connect to Vercel
3. Deploy

## Local Development

```bash
pip install -r requirements.txt
python bot.py
```
