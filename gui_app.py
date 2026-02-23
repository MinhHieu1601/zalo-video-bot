"""
Zalo Video Uploader - Desktop UI
Chay: python3 gui_app.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import threading
import asyncio
import platform
import subprocess
import hashlib
import json
import urllib.request
import ssl

from database import get_all_accounts, get_account_by_id, add_zalo_account, delete_account, get_all_jobs, delete_job

# === LICENSE CONFIG ===
# Doi URL nay sau khi deploy len Vercel
LICENSE_SERVER_URL = "https://license-server-topaz.vercel.app"
LICENSE_KEY_FILE = os.path.expanduser("~/.zalo_uploader_key")


def get_machine_id():
    """Lay machine ID duy nhat cho may nay"""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2]
        elif platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True, text=True
            )
            return result.stdout.split("\n")[1].strip()
        else:  # Linux
            with open("/etc/machine-id", "r") as f:
                return f.read().strip()
    except Exception:
        pass
    # Fallback: hash cua hostname + username
    data = f"{platform.node()}-{os.getlogin()}"
    return hashlib.md5(data.encode()).hexdigest()


def load_saved_key():
    """Load key da luu"""
    if os.path.exists(LICENSE_KEY_FILE):
        with open(LICENSE_KEY_FILE, "r") as f:
            return f.read().strip()
    return None


def save_key(key):
    """Luu key vao file"""
    with open(LICENSE_KEY_FILE, "w") as f:
        f.write(key)


def verify_license(key):
    """Verify license key voi server"""
    try:
        machine_id = get_machine_id()
        data = json.dumps({"key": key, "machine_id": machine_id}).encode()
        req = urllib.request.Request(
            f"{LICENSE_SERVER_URL}/api/verify",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        # SSL context bo qua verify
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = json.loads(resp.read().decode())
            return result.get("valid", False), result.get("error", "")
    except Exception as e:
        return False, str(e)


def check_license():
    """Check license khi khoi dong"""
    # Thu load key da luu
    saved_key = load_saved_key()
    
    if saved_key:
        valid, error = verify_license(saved_key)
        if valid:
            return True
        # Key khong hop le, xoa va yeu cau nhap lai
        os.remove(LICENSE_KEY_FILE)
    
    # Hien dialog nhap key
    root = tk.Tk()
    root.withdraw()
    
    key = simpledialog.askstring(
        "License Key",
        "Nhap License Key de su dung ung dung:",
        parent=root
    )
    
    if not key:
        messagebox.showerror("Loi", "Ban can nhap License Key!")
        return False
    
    valid, error = verify_license(key.strip())
    
    if valid:
        save_key(key.strip())
        root.destroy()
        return True
    else:
        messagebox.showerror("Loi", f"Key khong hop le: {error}")
        root.destroy()
        return False
from zalo_uploader import upload_video_to_zalo
from video_downloader import download_from_share_url


class ZaloUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zalo Video Uploader")
        self.root.geometry("600x650")
        
        self.accounts = []
        self.license_key = load_saved_key()
        
        self.setup_style()
        self.create_ui()
        self.load_accounts()
        
        # Bat dau kiem tra license dinh ky
        self.start_license_checker()
    
    def start_license_checker(self):
        """Kiem tra license moi 30 giay"""
        def check():
            if self.license_key:
                valid, error = verify_license(self.license_key)
                if not valid:
                    self.root.after(0, self.license_expired)
                    return
            # Kiem tra lai sau 30 giay
            self.root.after(30000, check)
        
        # Bat dau kiem tra sau 30 giay
        self.root.after(30000, check)
    
    def license_expired(self):
        """Xu ly khi license het han hoac bi vo hieu"""
        # Xoa key da luu
        if os.path.exists(LICENSE_KEY_FILE):
            os.remove(LICENSE_KEY_FILE)
        messagebox.showerror("License", "License key da bi vo hieu hoa!\nUng dung se dong lai.")
        self.root.destroy()
    
    def setup_style(self):
        """Cấu hình style"""
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=[20, 8])
        style.configure('TButton', padding=[10, 5])
        style.configure('Header.TLabel', font=('', 12, 'bold'))
    
    def create_ui(self):
        """Tạo giao diện chính"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab Upload
        tab1 = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab1, text="  Upload Video  ")
        self.create_upload_tab(tab1)
        
        # Tab Account
        tab2 = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab2, text="  Quan ly Account  ")
        self.create_account_tab(tab2)
        
        # Tab Lich trinh
        tab3 = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab3, text="  Lich trinh  ")
        self.create_schedule_tab(tab3)
    
    def create_upload_tab(self, parent):
        """Tab Upload Video"""
        # Account
        row1 = ttk.Frame(parent)
        row1.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(row1, text="Account:", width=12, style='Header.TLabel').pack(side=tk.LEFT)
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(row1, textvariable=self.account_var, state="readonly")
        self.account_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Video
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(row2, text="Video:", width=12, style='Header.TLabel').pack(side=tk.LEFT)
        self.video_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.video_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(row2, text="Chọn file", command=self.browse_file).pack(side=tk.LEFT)
        
        ttk.Label(parent, text="Nhập link TikTok/Douyin hoặc chọn file từ máy", 
                  foreground='gray').pack(anchor=tk.W, padx=(100, 0), pady=(0, 15))
        
        # Caption
        row3 = ttk.Frame(parent)
        row3.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(row3, text="Caption:", width=12, style='Header.TLabel').pack(side=tk.LEFT, anchor=tk.N)
        self.caption_text = tk.Text(row3, height=3, width=40)
        self.caption_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Thời gian
        row4 = ttk.Frame(parent)
        row4.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(row4, text="Thời gian:", width=12, style='Header.TLabel').pack(side=tk.LEFT)
        self.date_var = tk.StringVar()
        ttk.Entry(row4, textvariable=self.date_var, width=20).pack(side=tk.LEFT)
        ttk.Label(row4, text="DD-MM-YYYY HH:mm (để trống = đăng ngay)", 
                  foreground='gray').pack(side=tk.LEFT, padx=10)
        
        # Options
        row5 = ttk.Frame(parent)
        row5.pack(fill=tk.X, pady=(15, 0))
        ttk.Label(row5, text="", width=12).pack(side=tk.LEFT)
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row5, text="Chạy ẩn (bỏ tick để xem Chrome)", 
                        variable=self.headless_var).pack(side=tk.LEFT)
        
        # Button + Status
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(20, 10))
        ttk.Label(btn_frame, text="", width=12).pack(side=tk.LEFT)
        self.upload_btn = ttk.Button(btn_frame, text="DANG VIDEO", command=self.start_upload)
        self.upload_btn.pack(side=tk.LEFT)
        
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(status_frame, text="", width=12).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(parent, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0), padx=(100, 0))
    
    def create_account_tab(self, parent):
        """Tab Quản lý Account"""
        # Form thêm account
        add_frame = ttk.LabelFrame(parent, text=" Thêm Account mới ", padding=15)
        add_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Tên
        name_row = ttk.Frame(add_frame)
        name_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(name_row, text="Tên:", width=10).pack(side=tk.LEFT)
        self.new_acc_name = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.new_acc_name).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Cookies
        cookie_row = ttk.Frame(add_frame)
        cookie_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(cookie_row, text="Cookies:", width=10).pack(side=tk.LEFT, anchor=tk.N)
        self.new_acc_cookies = scrolledtext.ScrolledText(cookie_row, height=4)
        self.new_acc_cookies.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Button
        btn_row = ttk.Frame(add_frame)
        btn_row.pack(fill=tk.X)
        ttk.Label(btn_row, text="", width=10).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Luu Account", command=self.add_account).pack(side=tk.LEFT)
        
        # Danh sách
        list_frame = ttk.LabelFrame(parent, text=" Danh sách Account ", padding=15)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.acc_tree = ttk.Treeview(tree_frame, columns=('id', 'name'), show='headings', height=6)
        self.acc_tree.heading('id', text='ID')
        self.acc_tree.heading('name', text='Tên Account')
        self.acc_tree.column('id', width=60, anchor=tk.CENTER)
        self.acc_tree.column('name', width=400)
        self.acc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.acc_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.acc_tree.configure(yscrollcommand=scrollbar.set)
        
        ttk.Button(list_frame, text="Xoa account da chon", command=self.del_account).pack(pady=(10, 0))
    
    def create_schedule_tab(self, parent):
        """Tab Lich trinh dang video"""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Danh sach lich trinh dang video", style='Header.TLabel').pack(side=tk.LEFT)
        ttk.Button(header, text="Lam moi", command=self.load_jobs).pack(side=tk.RIGHT)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('id', 'account', 'video', 'schedule', 'status')
        self.job_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        self.job_tree.heading('id', text='ID')
        self.job_tree.heading('account', text='Account')
        self.job_tree.heading('video', text='Video URL')
        self.job_tree.heading('schedule', text='Thoi gian')
        self.job_tree.heading('status', text='Trang thai')
        
        self.job_tree.column('id', width=40, anchor=tk.CENTER)
        self.job_tree.column('account', width=100)
        self.job_tree.column('video', width=200)
        self.job_tree.column('schedule', width=120, anchor=tk.CENTER)
        self.job_tree.column('status', width=80, anchor=tk.CENTER)
        
        self.job_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.job_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.job_tree.configure(yscrollcommand=scrollbar.set)
        
        # Button xoa
        ttk.Button(parent, text="Xoa job da chon", command=self.del_job).pack(pady=(10, 0))
        
        # Load jobs
        self.load_jobs()
    
    def load_jobs(self):
        """Load jobs tu database"""
        try:
            jobs = get_all_jobs()
            
            # Clear treeview
            for item in self.job_tree.get_children():
                self.job_tree.delete(item)
            
            # Add jobs
            for job in jobs:
                schedule = job['schedule_time'].strftime('%d-%m-%Y %H:%M') if job['schedule_time'] else 'Dang ngay'
                video = job['video_url'][:40] + '...' if len(job['video_url']) > 40 else job['video_url']
                self.job_tree.insert('', tk.END, values=(
                    job['id'],
                    job['account_name'],
                    video,
                    schedule,
                    job['status']
                ))
        except Exception as e:
            print(f"Loi load jobs: {e}")
    
    def del_job(self):
        """Xoa job da chon"""
        selected = self.job_tree.selection()
        if not selected:
            messagebox.showwarning("Canh bao", "Chon job can xoa!")
            return
        
        item = self.job_tree.item(selected[0])
        job_id = item['values'][0]
        
        if messagebox.askyesno("Xac nhan", f"Xoa job ID {job_id}?"):
            try:
                delete_job(job_id)
                self.load_jobs()
            except Exception as e:
                messagebox.showerror("Loi", str(e))
    
    def load_accounts(self):
        """Load accounts từ database"""
        try:
            self.accounts = get_all_accounts()
            
            # Update combobox
            names = [f"{a['name']} (ID: {a['id']})" for a in self.accounts]
            self.account_combo['values'] = names
            if names:
                self.account_combo.current(0)
            
            # Update treeview
            for item in self.acc_tree.get_children():
                self.acc_tree.delete(item)
            for acc in self.accounts:
                self.acc_tree.insert('', tk.END, values=(acc['id'], acc['name']))
                
            self.status_var.set("Sẵn sàng")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối database:\n{e}")
    
    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[('Video', '*.mp4 *.mov *.avi *.mkv')])
        if path:
            self.video_var.set(path)
    
    def add_account(self):
        name = self.new_acc_name.get().strip()
        cookies = self.new_acc_cookies.get("1.0", tk.END).strip()
        
        if not name or not cookies:
            messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin!")
            return
        
        try:
            add_zalo_account(name, cookies)
            messagebox.showinfo("Thành công", f"Đã thêm: {name}")
            self.new_acc_name.set("")
            self.new_acc_cookies.delete("1.0", tk.END)
            self.load_accounts()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
    
    def del_account(self):
        selected = self.acc_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Chọn account cần xóa!")
            return
        
        item = self.acc_tree.item(selected[0])
        acc_id, acc_name = item['values']
        
        if messagebox.askyesno("Xác nhận", f"Xóa '{acc_name}'?"):
            try:
                delete_account(acc_id)
                self.load_accounts()
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))
    
    def start_upload(self):
        idx = self.account_combo.current()
        if idx < 0:
            messagebox.showerror("Lỗi", "Chọn account!")
            return
        
        video = self.video_var.get().strip()
        if not video:
            messagebox.showerror("Lỗi", "Nhập link hoặc chọn file video!")
            return
        
        account = get_account_by_id(self.accounts[idx]['id'])
        caption = self.caption_text.get("1.0", tk.END).strip() or None
        schedule = self.date_var.get().strip() or None
        headless = self.headless_var.get()
        is_url = video.startswith('http')
        
        self.upload_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_var.set("Đang xử lý...")
        
        thread = threading.Thread(target=self.do_upload, 
                                  args=(account, video, is_url, caption, schedule, headless))
        thread.daemon = True
        thread.start()
    
    def do_upload(self, account, video, is_url, caption, schedule, headless):
        video_path = None
        temp = False
        
        try:
            if is_url:
                self.root.after(0, lambda: self.status_var.set("Đang tải video..."))
                loop = asyncio.new_event_loop()
                video_path, _ = loop.run_until_complete(download_from_share_url(video))
                loop.close()
                if not video_path:
                    raise Exception("Download thất bại!")
                temp = True
            else:
                if not os.path.exists(video):
                    raise Exception("File không tồn tại!")
                video_path = video
            
            self.root.after(0, lambda: self.status_var.set("Đang upload..."))
            success, msg = upload_video_to_zalo(video_path, account['cookies'], caption, schedule, headless)
            
            if success:
                self.root.after(0, lambda: self.status_var.set("Thanh cong!"))
                self.root.after(0, lambda: messagebox.showinfo("OK", "Upload thành công!"))
            else:
                self.root.after(0, lambda: self.status_var.set("Loi"))
                self.root.after(0, lambda: messagebox.showerror("Lỗi", msg))
            
            if temp and video_path and os.path.exists(video_path):
                os.remove(video_path)
                
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set("Loi"))
            self.root.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self.root.after(0, lambda: self.upload_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress.stop())


if __name__ == "__main__":
    # Check license truoc khi chay app
    if not check_license():
        exit(1)
    
    root = tk.Tk()
    app = ZaloUploaderApp(root)
    root.mainloop()
