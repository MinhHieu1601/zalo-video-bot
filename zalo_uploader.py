"""
Selenium script đăng video lên Zalo Video - Headless mode
Sử dụng undetected-chromedriver để bypass bot detection
"""

import json
import time
import os
from pathlib import Path

# Import selenium cơ bản
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Thử dùng selenium-stealth
try:
    from selenium_stealth import stealth
    USE_STEALTH = True
    print("✅ Sử dụng selenium-stealth")
except ImportError:
    USE_STEALTH = False
    print("⚠️ Không có selenium-stealth")

# Thư mục lưu Chrome user data
USER_DATA_BASE = Path(__file__).parent / "chrome_profiles"
USER_DATA_BASE.mkdir(exist_ok=True)

def get_chrome_options(headless: bool = True) -> Options:
    """Tạo Chrome options - giả lập browser thật"""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # Window size
    options.add_argument("--window-size=1920,1080")
    
    # Giả lập browser thật - tránh bị detect headless
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Các options chung
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--lang=vi-VN")
    
    # Cho Docker/Railway
    if os.environ.get('CHROME_BIN'):
        options.binary_location = os.environ.get('CHROME_BIN')
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Giả lập browser thật
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })
    
    return options

def import_cookies(driver, cookies_json: str):
    """Import cookies từ JSON string (J2Team format)"""
    try:
        data = json.loads(cookies_json)
        
        # J2Team format: {"url": "...", "cookies": [...]}
        if isinstance(data, dict) and 'cookies' in data:
            cookies = data['cookies']
        else:
            cookies = data
        
        imported = 0
        for cookie in cookies:
            selenium_cookie = {
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                'domain': cookie.get('domain'),
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', False),
                'httpOnly': cookie.get('httpOnly', False),
            }
            
            if 'expirationDate' in cookie:
                selenium_cookie['expiry'] = int(cookie['expirationDate'])
            
            try:
                driver.add_cookie(selenium_cookie)
                imported += 1
            except:
                pass
        
        return imported
    except Exception as e:
        print(f"❌ Lỗi import cookies: {e}")
        return 0

def upload_video_to_zalo(
    video_path: str,
    cookies_json: str,
    caption: str | None = None,
    schedule_time: str | None = None,
    headless: bool = True
) -> tuple[bool, str]:
    """
    Upload video lên Zalo Video
    
    Args:
        video_path: Đường dẫn file video
        cookies_json: JSON string chứa cookies (J2Team format)
        caption: Nội dung caption (None = không có)
        schedule_time: Thời gian hẹn đăng format "DD-MM-YYYY HH:mm" (None = đăng ngay)
        headless: Chạy headless hay không
    
    Returns:
        (success, message)
    """
    driver = None
    current_step = "init"
    try:
        # Kiểm tra file video tồn tại
        current_step = "check_video_file"
        print(f"📝 Bước: {current_step}")
        if not os.path.exists(video_path):
            return False, f"File video không tồn tại: {video_path}"
        print(f"✅ File video tồn tại: {video_path}")
        
        # Khởi tạo driver
        current_step = "init_driver"
        print(f"📝 Bước: {current_step}")
        
        # Khởi tạo Chrome driver
        options = get_chrome_options(headless)
        driver = webdriver.Chrome(options=options)
        print("✅ Đã khởi tạo Chrome driver")
        
        # Áp dụng stealth mode nếu có
        if USE_STEALTH:
            stealth(driver,
                languages=["vi-VN", "vi", "en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            print("✅ Đã áp dụng stealth mode")
        
        wait = WebDriverWait(driver, 30)
        
        # Mở trang Zalo Video
        current_step = "open_zalo_video"
        print(f"📝 Bước: {current_step}")
        driver.get("https://video.zalo.me/")
        time.sleep(3)
        print(f"✅ Đã mở trang - URL: {driver.current_url}")
        print(f"📄 Title: {driver.title}")
        
        # Kiểm tra cần đăng nhập không
        current_step = "check_login"
        print(f"📝 Bước: {current_step}")
        
        # Import cookie trước
        print("⏳ Đang import cookies...")
        imported = import_cookies(driver, cookies_json)
        print(f"✅ Đã import {imported} cookies")
        
        # Refresh trang sau khi import cookie
        driver.get("https://video.zalo.me/")
        time.sleep(3)
        print(f"✅ Đã refresh trang - URL: {driver.current_url}")
        print(f"📄 Title: {driver.title}")
        
        # Kiểm tra đã đăng nhập thành công chưa
        current_step = "verify_login"
        print(f"📝 Bước: {current_step}")
        print(f"📄 Current URL: {driver.current_url}")
        print(f"📄 Page title: {driver.title}")
        
        # Chờ trang load xong
        time.sleep(3)
        
        # Click nút "Đăng video"
        current_step = "click_dang_video_btn"
        print(f"📝 Bước: {current_step}")
        print("⏳ Đang tìm nút 'Đăng video'...")
        
        # Thử nhiều selector
        btn_dang_video = None
        selectors = [
            "//button[contains(@class, 'ant-btn-primary')]//span[text()='Đăng video']/parent::button",
            "//button[contains(@class, 'ant-btn')]//span[contains(text(), 'Đăng video')]/parent::button",
            "//button[contains(text(), 'Đăng video')]",
            "//span[text()='Đăng video']/ancestor::button",
        ]
        
        for i, selector in enumerate(selectors):
            try:
                print(f"   Thử selector {i+1}: {selector[:50]}...")
                btn_dang_video = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Tìm thấy nút với selector {i+1}")
                break
            except:
                print(f"   ❌ Không tìm thấy với selector {i+1}")
                continue
        
        if not btn_dang_video:
            # Log page source để debug
            print("⚠️ Không tìm thấy nút 'Đăng video', kiểm tra page...")
            print(f"📄 Page URL: {driver.current_url}")
            raise Exception("Không tìm thấy nút 'Đăng video' - có thể cookie hết hạn hoặc trang chưa load")
        
        btn_dang_video.click()
        print("✅ Đã click nút 'Đăng video'")
        
        # Chờ modal và upload video
        current_step = "upload_video_file"
        print(f"📝 Bước: {current_step}")
        time.sleep(2)
        
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][accept*='video']")
        file_input.send_keys(video_path)
        print(f"✅ Đã chọn video: {video_path}")
        
        # Chờ video xử lý
        current_step = "wait_video_processing"
        print(f"📝 Bước: {current_step} - chờ 15s...")
        time.sleep(15)  # Tăng thời gian chờ
        
        # Điền caption nếu có
        if caption:
            print(f"✏️ Đang điền caption: {caption}")
            caption_div = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.input-conteneditable[contenteditable='true']"))
            )
            caption_div.click()
            time.sleep(0.3)
            
            actions = ActionChains(driver)
            actions.key_down(Keys.COMMAND if os.name == 'darwin' else Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.COMMAND if os.name == 'darwin' else Keys.CONTROL)
            actions.perform()
            
            caption_div.send_keys(caption)
            print("✅ Đã điền caption")
        
        # Điền thời gian hẹn đăng nếu có
        if schedule_time:
            print(f"📅 Đang chọn thời gian: {schedule_time}")
            time_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Chọn thời điểm']")
            time_input.click()
            time_input.send_keys(schedule_time)
            
            # Click OK
            ok_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'ant-btn-primary') and contains(@class, 'ant-btn-sm')]//span[text()='OK']/parent::button")
            ok_btn.click()
            print("✅ Đã chọn thời gian hẹn đăng")
        
        # Chờ video xử lý xong (kiểm tra progress bar)
        print("⏳ Đang chờ video xử lý xong...")
        time.sleep(5)
        
        # Click nút "Đăng video" cuối cùng
        print("⏳ Đang tìm nút 'Đăng video'...")
        
        # Button có class: ant-btn ant-btn-primary bg-color-5 mt-6, text: "Đăng video"
        try:
            # Cách 1: Tìm theo class bg-color-5 và text "Đăng video"
            submit_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'bg-color-5') and contains(@class, 'mt-6')]//span[text()='Đăng video']/parent::button"))
            )
            submit_btn.click()
            print("✅ Đã click nút 'Đăng video'")
        except:
            try:
                # Cách 2: Tìm theo text và class ant-btn-primary
                submit_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'ant-btn-primary')]//span[text()='Đăng video']/parent::button")
                submit_btn.click()
                print("✅ Đã click nút 'Đăng video' (cách 2)")
            except:
                # Cách 3: Tìm button primary cuối cùng trong form
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button.ant-btn-primary.bg-color-5")
                submit_btn.click()
                print("✅ Đã click nút 'Đăng video' (cách 3)")
        
        # Chờ xác nhận upload thành công
        time.sleep(5)
        
        return True, "Upload thành công!"
        
    except Exception as e:
        error_msg = f"[{current_step}] {str(e)[:200]}"
        print(f"❌ Lỗi tại bước '{current_step}': {str(e)}")
        
        # Chụp screenshot để debug
        if driver:
            try:
                screenshot_path = f"/tmp/error_{current_step}_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                print(f"📸 Đã chụp screenshot: {screenshot_path}")
                print(f"📄 Page URL: {driver.current_url}")
                print(f"📄 Page title: {driver.title}")
            except Exception as ss_err:
                print(f"⚠️ Không chụp được screenshot: {ss_err}")
        
        return False, error_msg
        
    finally:
        if driver:
            driver.quit()

# Test
if __name__ == "__main__":
    # Test với file cookie
    with open("/Users/m1pro/Downloads/video.zalo.me_23-02-2026 (1).json", "r") as f:
        cookies = f.read()
    
    success, msg = upload_video_to_zalo(
        video_path="/Users/m1pro/Downloads/o4UpFGu1LAn9g9XkgQFYhfCDEfwuTWvEAABkNI.mp4",
        cookies_json=cookies,
        caption="Test upload từ bot",
        schedule_time=None,  # Đăng ngay
        headless=False  # Test với GUI
    )
    
    print(f"Result: {success} - {msg}")
