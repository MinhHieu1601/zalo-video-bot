"""
Kết nối PostgreSQL (Supabase) - CRUD cho zalo_accounts và upload_jobs
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from contextlib import contextmanager

# Database URL từ Supabase
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:hieuminh123%40@db.bexsrcaznrzvqxzevhdn.supabase.co:5432/postgres"
)

@contextmanager
def get_connection():
    """Context manager cho database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Tạo bảng nếu chưa có"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Bảng tài khoản Zalo
            cur.execute("""
                CREATE TABLE IF NOT EXISTS zalo_accounts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    cookies TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Bảng jobs đăng video
            cur.execute("""
                CREATE TABLE IF NOT EXISTS upload_jobs (
                    id SERIAL PRIMARY KEY,
                    video_url TEXT NOT NULL,
                    video_path TEXT,
                    caption TEXT,
                    schedule_time TIMESTAMP,
                    zalo_account_id INTEGER REFERENCES zalo_accounts(id),
                    status VARCHAR(20) DEFAULT 'pending',
                    telegram_user_id BIGINT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
    print("✅ Database initialized")

# ==================== ZALO ACCOUNTS ====================

def add_zalo_account(name: str, cookies: str) -> int:
    """Thêm tài khoản Zalo mới, trả về ID"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO zalo_accounts (name, cookies) VALUES (%s, %s) RETURNING id",
                (name, cookies)
            )
            return cur.fetchone()[0]

def get_all_accounts() -> list:
    """Lấy danh sách tất cả tài khoản Zalo"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, created_at FROM zalo_accounts ORDER BY id")
            return cur.fetchall()

def get_account_by_id(account_id: int) -> dict | None:
    """Lấy thông tin tài khoản theo ID"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM zalo_accounts WHERE id = %s", (account_id,))
            return cur.fetchone()

def delete_account(account_id: int) -> bool:
    """Xóa tài khoản Zalo"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM zalo_accounts WHERE id = %s", (account_id,))
            return cur.rowcount > 0

# ==================== UPLOAD JOBS ====================

def create_job(
    video_url: str,
    zalo_account_id: int,
    telegram_user_id: int,
    caption: str | None = None,
    schedule_time: datetime | None = None,
    video_path: str | None = None
) -> int:
    """Tạo job đăng video mới, trả về ID"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO upload_jobs 
                (video_url, video_path, caption, schedule_time, zalo_account_id, telegram_user_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (video_url, video_path, caption, schedule_time, zalo_account_id, telegram_user_id)
            )
            return cur.fetchone()[0]

def get_pending_jobs() -> list:
    """Lấy danh sách jobs đang chờ xử lý (đã đến giờ hoặc đăng ngay)"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT j.*, a.name as account_name, a.cookies
                FROM upload_jobs j
                JOIN zalo_accounts a ON j.zalo_account_id = a.id
                WHERE j.status = 'pending'
                AND (j.schedule_time IS NULL OR j.schedule_time <= NOW())
                ORDER BY j.created_at
                """
            )
            return cur.fetchall()

def get_jobs_by_user(telegram_user_id: int, limit: int = 10) -> list:
    """Lấy danh sách jobs của user"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT j.id, j.video_url, j.caption, j.schedule_time, j.status, 
                       j.created_at, a.name as account_name
                FROM upload_jobs j
                JOIN zalo_accounts a ON j.zalo_account_id = a.id
                WHERE j.telegram_user_id = %s
                ORDER BY j.created_at DESC
                LIMIT %s
                """,
                (telegram_user_id, limit)
            )
            return cur.fetchall()

def update_job_status(job_id: int, status: str, error_message: str | None = None):
    """Cập nhật trạng thái job"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE upload_jobs 
                SET status = %s, error_message = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (status, error_message, job_id)
            )

def update_job_video_path(job_id: int, video_path: str):
    """Cập nhật đường dẫn video đã download"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE upload_jobs SET video_path = %s, updated_at = NOW() WHERE id = %s",
                (video_path, job_id)
            )

def delete_job(job_id: int) -> bool:
    """Xóa job"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM upload_jobs WHERE id = %s", (job_id,))
            return cur.rowcount > 0

# Test connection
if __name__ == "__main__":
    init_database()
    print("✅ Database connection successful")
    
    # Test lấy accounts
    accounts = get_all_accounts()
    print(f"📊 Có {len(accounts)} tài khoản Zalo")
