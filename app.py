"""
Zalo Video Uploader - Streamlit UI
Chạy: streamlit run app.py
"""

import streamlit as st
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

# Import các module của project
from zalo_uploader import upload_video_to_zalo
from video_downloader import download_video_no_watermark

# Cấu hình trang
st.set_page_config(
    page_title="Zalo Video Uploader",
    page_icon="🎬",
    layout="wide"
)

# Database local
DB_PATH = Path(__file__).parent / "local_data.db"

def init_db():
    """Khởi tạo database SQLite local"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Bảng accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zalo_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cookies_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Bảng jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS upload_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            video_url TEXT,
            video_path TEXT,
            caption TEXT,
            schedule_time TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES zalo_accounts(id)
        )
    """)
    
    conn.commit()
    conn.close()

def get_accounts():
    """Lấy danh sách accounts"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zalo_accounts ORDER BY created_at DESC")
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def add_account(name: str, cookies_json: str):
    """Thêm account mới"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO zalo_accounts (name, cookies_json) VALUES (?, ?)",
        (name, cookies_json)
    )
    conn.commit()
    conn.close()

def delete_account(account_id: int):
    """Xóa account"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM zalo_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()

def get_jobs(limit: int = 50):
    """Lấy danh sách jobs"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, a.name as account_name 
        FROM upload_jobs j 
        LEFT JOIN zalo_accounts a ON j.account_id = a.id 
        ORDER BY j.created_at DESC 
        LIMIT ?
    """, (limit,))
    jobs = cursor.fetchall()
    conn.close()
    return jobs

def add_job(account_id: int, video_url: str = None, video_path: str = None, 
            caption: str = None, schedule_time: str = None):
    """Thêm job mới"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO upload_jobs 
           (account_id, video_url, video_path, caption, schedule_time, status) 
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (account_id, video_url, video_path, caption, schedule_time)
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def update_job_status(job_id: int, status: str, error_message: str = None):
    """Cập nhật trạng thái job"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE upload_jobs SET status = ?, error_message = ? WHERE id = ?",
        (status, error_message, job_id)
    )
    conn.commit()
    conn.close()

def process_job(job_id: int, account_id: int, video_url: str, video_path: str,
                caption: str, cookies_json: str, headless: bool):
    """Xử lý upload job"""
    try:
        update_job_status(job_id, "processing")
        
        # Download video nếu có URL
        if video_url and not video_path:
            st.session_state.job_status = "Đang tải video..."
            success, result = download_video_no_watermark(video_url)
            if not success:
                update_job_status(job_id, "failed", f"Download failed: {result}")
                return
            video_path = result
        
        # Upload lên Zalo
        st.session_state.job_status = "Đang upload lên Zalo..."
        success, message = upload_video_to_zalo(
            video_path=video_path,
            cookies_json=cookies_json,
            caption=caption,
            headless=headless
        )
        
        if success:
            update_job_status(job_id, "completed")
            st.session_state.job_status = "✅ Upload thành công!"
        else:
            update_job_status(job_id, "failed", message)
            st.session_state.job_status = f"❌ Lỗi: {message}"
            
        # Xóa file video tạm
        if video_url and video_path and os.path.exists(video_path):
            os.remove(video_path)
            
    except Exception as e:
        update_job_status(job_id, "failed", str(e))
        st.session_state.job_status = f"❌ Lỗi: {str(e)}"

# Khởi tạo database
init_db()

# Session state
if "job_status" not in st.session_state:
    st.session_state.job_status = None

# Header
st.title("🎬 Zalo Video Uploader")
st.markdown("Upload video lên Zalo Video một cách dễ dàng")

# Tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload Video", "👥 Quản lý Accounts", "📋 Lịch sử"])

# Tab 1: Upload Video
with tab1:
    st.header("Upload Video")
    
    # Chọn account
    accounts = get_accounts()
    if not accounts:
        st.warning("⚠️ Chưa có account nào. Vui lòng thêm account trước.")
    else:
        account_options = {f"{a['name']} (ID: {a['id']})": a for a in accounts}
        selected_account = st.selectbox(
            "Chọn Account Zalo",
            options=list(account_options.keys())
        )
        account = account_options[selected_account]
        
        # Nguồn video
        video_source = st.radio(
            "Nguồn video",
            ["📁 File có sẵn", "🔗 Link TikTok/Douyin"],
            horizontal=True
        )
        
        video_url = None
        video_path = None
        
        if video_source == "📁 File có sẵn":
            uploaded_file = st.file_uploader(
                "Chọn file video",
                type=["mp4", "mov", "avi", "mkv"]
            )
            if uploaded_file:
                # Lưu file tạm
                temp_dir = Path(__file__).parent / "downloads"
                temp_dir.mkdir(exist_ok=True)
                video_path = str(temp_dir / uploaded_file.name)
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ Đã chọn: {uploaded_file.name}")
        else:
            video_url = st.text_input(
                "Nhập link video (TikTok/Douyin)",
                placeholder="https://www.tiktok.com/@user/video/..."
            )
        
        # Caption
        caption = st.text_area(
            "Caption (tùy chọn)",
            placeholder="Nhập nội dung caption...",
            height=100
        )
        
        # Chế độ chạy
        col1, col2 = st.columns(2)
        with col1:
            headless = st.checkbox("Chạy ẩn (headless)", value=False,
                                   help="Bỏ tick để xem Chrome hoạt động")
        
        # Nút upload
        if st.button("🚀 Upload ngay", type="primary", use_container_width=True):
            if not video_url and not video_path:
                st.error("❌ Vui lòng chọn video hoặc nhập link!")
            else:
                # Tạo job
                job_id = add_job(
                    account_id=account['id'],
                    video_url=video_url,
                    video_path=video_path,
                    caption=caption if caption else None
                )
                
                # Chạy upload trong thread riêng
                with st.spinner("Đang xử lý..."):
                    process_job(
                        job_id=job_id,
                        account_id=account['id'],
                        video_url=video_url,
                        video_path=video_path,
                        caption=caption if caption else None,
                        cookies_json=account['cookies_json'],
                        headless=headless
                    )
                
                # Hiển thị kết quả
                if st.session_state.job_status:
                    if "✅" in st.session_state.job_status:
                        st.success(st.session_state.job_status)
                    else:
                        st.error(st.session_state.job_status)

# Tab 2: Quản lý Accounts
with tab2:
    st.header("Quản lý Zalo Accounts")
    
    # Form thêm account
    with st.expander("➕ Thêm Account mới", expanded=True):
        with st.form("add_account_form"):
            acc_name = st.text_input("Tên account", placeholder="VD: Account chính")
            acc_cookies = st.text_area(
                "Cookies JSON (J2Team format)",
                placeholder='Dán cookies từ J2Team Cookies extension...',
                height=150
            )
            
            submitted = st.form_submit_button("💾 Lưu Account", use_container_width=True)
            if submitted:
                if not acc_name or not acc_cookies:
                    st.error("❌ Vui lòng điền đầy đủ thông tin!")
                else:
                    try:
                        # Validate JSON
                        json.loads(acc_cookies)
                        add_account(acc_name, acc_cookies)
                        st.success(f"✅ Đã thêm account: {acc_name}")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Cookies không đúng định dạng JSON!")
    
    # Danh sách accounts
    st.subheader("📋 Danh sách Accounts")
    accounts = get_accounts()
    
    if not accounts:
        st.info("Chưa có account nào.")
    else:
        for acc in accounts:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{acc['name']}** (ID: {acc['id']})")
            with col2:
                st.caption(acc['created_at'][:10] if acc['created_at'] else "")
            with col3:
                if st.button("🗑️", key=f"del_{acc['id']}", help="Xóa account"):
                    delete_account(acc['id'])
                    st.success(f"Đã xóa: {acc['name']}")
                    st.rerun()

# Tab 3: Lịch sử
with tab3:
    st.header("📋 Lịch sử Upload")
    
    jobs = get_jobs()
    
    if not jobs:
        st.info("Chưa có job nào.")
    else:
        for job in jobs:
            status_icon = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(job['status'], "❓")
            
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.write(f"{status_icon} **Job #{job['id']}**")
                with col2:
                    st.caption(f"Account: {job['account_name'] or 'N/A'}")
                    if job['video_url']:
                        st.caption(f"URL: {job['video_url'][:50]}...")
                    if job['error_message']:
                        st.error(job['error_message'][:100])
                with col3:
                    st.caption(job['created_at'][:16] if job['created_at'] else "")
                st.divider()

# Footer
st.markdown("---")
st.caption("💡 Tip: Bỏ tick 'Chạy ẩn' để xem Chrome hoạt động và debug dễ hơn.")
