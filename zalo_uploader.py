"""
Selenium script đăng video lên Zalo Video - Headless mode
"""

import json
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Thư mục lưu Chrome user data
USER_DATA_BASE = Path(__file__).parent / "chrome_profiles"
USER_DATA_BASE.mkdir(exist_ok=True)

def get_chrome_options(headless: bool = True) -> Options:
    """Tạo Chrome options"""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    
    # Các options chung
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-software-rasterizer")
    
    # Cho Docker/Railway
    if os.environ.get('CHROME_BIN'):
        options.binary_location = os.environ.get('CHROME_BIN')
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
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
    try:
        # Kiểm tra file video tồn tại
        if not os.path.exists(video_path):
            return False, f"File video không tồn tại: {video_path}"
        
        # Khởi tạo driver
        options = get_chrome_options(headless)
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)
        
        # Mở trang Zalo Video
        driver.get("https://video.zalo.me/")
        time.sleep(2)
        
        # Kiểm tra cần đăng nhập không
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button.styles_login-btn__3HqY4")
            if login_btn:
                print("⚠️ Chưa đăng nhập, đang import cookie...")
                imported = import_cookies(driver, cookies_json)
                print(f"✅ Đã import {imported} cookies")
                
                # Truy cập lại
                driver.get("https://video.zalo.me/")
                time.sleep(3)
        except:
            print("✅ Đã đăng nhập sẵn")
        
        # Click nút "Đăng video"
        print("⏳ Đang chờ nút 'Đăng video'...")
        btn_dang_video = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'ant-btn-primary')]//span[text()='Đăng video']/parent::button"))
        )
        btn_dang_video.click()
        print("✅ Đã click nút 'Đăng video'")
        
        # Chờ modal và upload video
        time.sleep(2)
        print(f"⏳ Đang upload video: {video_path}")
        
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][accept*='video']")
        file_input.send_keys(video_path)
        print("✅ Đã chọn video, đang upload...")
        
        # Chờ video xử lý
        print("⏳ Đang chờ video xử lý...")
        time.sleep(10)  # Tăng thời gian chờ cho headless
        
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
        error_msg = str(e)
        print(f"❌ Lỗi: {error_msg}")
        
        # Chụp screenshot để debug
        if driver:
            try:
                screenshot_path = f"/tmp/error_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                print(f"📸 Đã chụp screenshot: {screenshot_path}")
                
                # Log page source
                print(f"📄 Page URL: {driver.current_url}")
                print(f"📄 Page title: {driver.title}")
            except:
                pass
        
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
