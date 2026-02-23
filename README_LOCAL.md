# 🎬 Zalo Video Uploader - Local UI

Upload video lên Zalo Video với giao diện đơn giản.

## Yêu cầu

- Python 3.9+
- Google Chrome (browser)
- macOS hoặc Windows

## Cài đặt

```bash
# 1. Clone repo (nếu chưa có)
git clone https://github.com/MinhHieu1601/zalo-video-bot.git
cd zalo-video-bot

# 2. Tạo virtual environment (khuyến nghị)
python -m venv venv

# Kích hoạt venv:
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Cài dependencies
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
streamlit run app.py
```

Trình duyệt sẽ tự mở tại: http://localhost:8501

## Hướng dẫn sử dụng

### 1. Thêm Account Zalo

1. Vào tab **"👥 Quản lý Accounts"**
2. Nhập tên account
3. Dán cookies từ **J2Team Cookies** extension:
   - Cài extension: [J2Team Cookies](https://chrome.google.com/webstore/detail/j2team-cookies/okpidcojinmlaakglciglbpcpajaibco)
   - Đăng nhập vào https://video.zalo.me/
   - Click extension → Export → Copy
   - Dán vào ô "Cookies JSON"
4. Click **"💾 Lưu Account"**

### 2. Upload Video

1. Vào tab **"📤 Upload Video"**
2. Chọn account Zalo
3. Chọn nguồn video:
   - **File có sẵn**: Upload file từ máy
   - **Link TikTok/Douyin**: Dán link video
4. Nhập caption (tùy chọn)
5. **Bỏ tick "Chạy ẩn"** để xem Chrome hoạt động
6. Click **"🚀 Upload ngay"**

### 3. Xem lịch sử

Tab **"📋 Lịch sử"** hiển thị tất cả jobs đã chạy.

## Tips

- **Lần đầu**: Bỏ tick "Chạy ẩn" để xem Chrome và đảm bảo cookies hoạt động
- **Cookie hết hạn**: Export lại cookies từ J2Team và cập nhật account
- **Lỗi**: Xem lịch sử để biết chi tiết lỗi

## Cấu trúc files

```
anca-video-bot/
├── app.py              # Streamlit UI (chạy file này)
├── zalo_uploader.py    # Logic upload Zalo
├── video_downloader.py # Download video TikTok
├── local_data.db       # Database SQLite (tự tạo)
├── downloads/          # Thư mục chứa video tạm
└── requirements.txt    # Dependencies
```

## Troubleshooting

### "ChromeDriver not found"
```bash
pip install webdriver-manager
```

### "Không tìm thấy nút Đăng video"
- Cookie có thể đã hết hạn → Export lại từ J2Team
- Thử bỏ tick "Chạy ẩn" để xem Chrome

### Permission denied (macOS)
```bash
chmod +x /path/to/chromedriver
```
