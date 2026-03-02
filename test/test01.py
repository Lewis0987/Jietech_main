from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import( 
TimeoutException, ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException, NoSuchWindowException)
from pathlib import Path
from colorama import Fore,Style
import os, time
import sys
import threading
import configparser
import pyperclip
import re

# 設定 ChromeOptions 
config = configparser.ConfigParser()
# ====== 設定下載路徑 ====== 
download_path =r"C:\Users\lewis.chiu\Downloads"  #另種寫法 "C:\\Users\howar\Downloads" 或 【自用 r"C:\Users\User\Downloads"】
#r"D:\下載"	✅ 推薦	不用擔心 \ 變跳脫符號
#"D:\\下載"	✅ 推薦	手動雙斜線跳脫更安全
#"D:\下載"	❌ 不推薦	萬一剛好有 \t、\n、\r 很容易踩坑

# ====== 初始化 Chrome Driver ======
options = webdriver.ChromeOptions()

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_keyfile = os.path.join(current_dir, 'IND.ini')
# 讀取配置文件
config.read(config_keyfile, encoding='utf-8')
################確認遊戲模板(請輸入 'U1、U2.../V1、V2...')###########################
ui_version = 'IN'
product_numbers = ['INPV6']
################確認帳號#######################################
phone='8888888888' #for 登入
# 初始化Chrome浏览器
driver = webdriver.Chrome(service=Service(), options=options)
# 打开网页
WebDriverWait(driver, 10)
for product in product_numbers:
    url = config.get(ui_version, product)
    driver.get(url)
    driver.maximize_window() #網頁整頁

#<<<<<<<<<<<<<<<<<<<<<背景偵測popup，並關閉>>>>>>>>>>>>>>>>>>>>>>
exit_event = threading.Event()
def handle_popups(driver):
    while not exit_event.is_set():
        try:
            # 在这里执行查找弹窗的操作
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]")))
            
            # 找到弹窗后执行关闭的操作
            close_button = driver.find_element(By.CSS_SELECTOR, '[alt="ic_close"]')                                  
        except TimeoutException:
            # 超时异常，表示未找到弹窗，不输出错误信息
            pass
        except NoSuchWindowException:
            # 窗口已經被關閉，結束循環
            break
#<<<<<<<<<<<<<<<<<<<<<背景偵測popup，並關閉>>>>>>>>>>>>>>>>>>>>>>

sleep(1)
#-------------------------1.A.首頁模塊 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# A.首頁 Popup 
    # 首頁[Subscribe] 訂閱 
print('\033[33m首頁[Subscribe] 訂閱 \033[0m')
print("\033[44m\033[32m" + "Subscribe 訂閱" + "\033[0m")
try:
    Subscribe =  WebDriverWait(driver, 5).until(
    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Later')]"))
    ).click()
    print('A-1.Subscribe_Later \033[32mOK\033[0m')
except TimeoutException:
    print("\033[94m未偵測活動元素，繼續流程...\033[0m")


'''#首頁[surprise_reward_popup] 【1】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
print("\033[107m\033[30m" + "A.[首頁/popup]" + "\033[0m")
popup = WebDriverWait(driver, 5).until(
    EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'popup_surprise_reward')]"))
).click()
print('A-1.surprise_reward popup \033[32mOK\033[0m')
try:
    popup = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'The reward has been claimed')]"))
    )
    print('A-1.已領取過獎勵toast \033[32mOK\033[0m')
        # 領取過獎勵重整網頁
    driver.refresh()
    sleep(3)
    try:
        popup = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
        )
        print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
         # 找到關閉按鈕並點擊
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
    except TimeoutException:
        print("\033[93mA-1-1.未偵測到 ，可略過。\033[0m")
except TimeoutException:
        print("\033[93m" + "A-1.未偵測到已領取文字，繼續流程..." + "\033[0m")
'''

    #首頁[充值大輪盤_popup]【A】
print('\033[33m充值大輪盤【A】\033[0m')
print("\033[44m\033[32m" + "充值大輪盤【A】" + "\033[0m")
try:
    popup = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'SPIN')]"))
    )
    print('A.Prize wheel_popup \033[32mOK\033[0m')
    
    sleep(1)
    try:
        popup = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
        )
        print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
         # 找到關閉按鈕並點擊
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
    except TimeoutException:
        print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")
    
    close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
except TimeoutException:
        print("\033[94m" + "A-1.未偵測活動元素，繼續流程..." + "\033[0m")

sleep(0.5)
    #首頁[首充_popup]【2】
print('\033[33m首充Popup\033[0m')
print("\033[44m\033[32m" + "首充Popup" + "\033[0m")
try:
    popup = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'popup_first_recharge_vb')]"))
    )
    print('A-2.FirstRecharge_popup \033[32mOK\033[0m')
    
    sleep(1)
    try:
        popup = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
        )
        print("A-1-1.首充 popup \033[32mOK\033[0m")
         # 找到關閉按鈕並點擊
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
    except TimeoutException:
        print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")
    
    close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
except TimeoutException:
        print("\033[94m" + "A-1.未偵測活動元素，繼續流程..." + "\033[0m")

sleep(0.5)
    #首頁[mission_popup]【3】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
print('\033[33mmission 任務中心 \033[0m')
print("\033[44m\033[32m" + "mission 任務中心" + "\033[0m")
try:
    popup = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'p-4 box-border')]"))
    )
    print('A-3.mission_popup \033[32mOK\033[0m')

    sleep(1)
    try:
        popup = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
        )
        print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
         # 找到關閉按鈕並點擊
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
    except TimeoutException:
        print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")

    close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-3.【關閉】mission popup \033[32mOK\033[0m")
except TimeoutException:
        print("\033[94m" + "A-1.未偵測活動元素，繼續流程..." + "\033[0m")

sleep(0.5)
    #首頁[club_popup]【4】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
print('\033[33mclub 俱樂部 \033[0m')
print("\033[44m\033[32m" + "club 俱樂部" + "\033[0m")

try:
    popup = WebDriverWait(driver, 1).until(
    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'popup_club')]"))
    )
    print('A-4.club popup \033[32mOK\033[0m') 
    sleep(3)
    try:
        popup = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
        )
        print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
         # 找到關閉按鈕並點擊
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
    except TimeoutException:
        print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")
        
    close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-4.【關閉】popup_club \033[32mOK\033[0m")
except TimeoutException:
        print("\033[94m" + "A-4.未偵測活動元素，繼續流程..." + "\033[0m")


sleep(1)
    #首頁[telegram_popup]【5】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
print('\033[33mtelegram gift\033[0m')
print("\033[44m\033[32m" + "telegram gift" + "\033[0m")
try:
    popup = WebDriverWait(driver, 3).until(
    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'popup_subscribe_telegram')]"))
)
    print('A-5.telegram popup \033[32mOK\033[0m')

    # 找到關閉按鈕並點擊
    close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-5.關閉telegram popup \033[32mOK\033[0m")
except TimeoutException as e:
    print("\033[94m" + "A-5.未偵測活動元素，繼續流程..." + "\033[0m")
    checked = True  # 防止重複執行
except Exception as e:
    print("\033[91mA-5 其他錯誤：\033[0m", str(e).split("Stacktrace")[0])                          # 只保留 Stacktrace 前的部分
    checked = True  # 防止重複執行

sleep(1)
    #首頁[Jackpot_popup]【6】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
print('\033[33mJackpot \033[0m')
print("\033[44m\033[32m" + "Jackpot" + "\033[0m")    
try:
    popup = WebDriverWait(driver, 3).until(
    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'popup_jackpot')]"))
)
    print('A-6.jackpot popup \033[32mOK\033[0m')

    # 找到關閉按鈕並點擊
    get_button = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
    print("A-6.關閉jackpot popup \033[32mOK\033[0m")
except TimeoutException as e:
    print("\033[94m" + "A-6.未偵測活動元素，繼續流程..." + "\033[0m")
    checked = True  # 防止重複執行
except Exception as e:
    print("\033[91mA-6 其他錯誤：\033[0m", str(e).split("Stacktrace")[0])                         # 只保留 Stacktrace 前的部分
    checked = True  # 防止重複執行

sleep(1)
#<<<<<<<<<<<<<<<<<<<<<背景偵測popup，開始>>>>>>>>>>>>>>>>>>>>>>
popup_thread = threading.Thread(target=handle_popups, args=(driver,), daemon=True) #✅ 正確取得 thread 實體並啟動
popup_thread.start()
#<<<<<<<<<<<<<<<<<<<<<背景偵測popup，開始>>>>>>>>>>>>>>>>>>>>>>
try:
    # B.1-1Header_download 【B】>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33m【B】Header_download區 \033[0m')
    print("\033[44m\033[32m" + "【B】Header_download區" + "\033[0m")

    # 自動取得使用者的下載資料夾路徑
    prefs = {
        "download.default_directory": download_path,     # 指定下載的路徑，下載時自動存這裡，不跳詢問
        "download.prompt_for_download": False,           # 關閉「另存新檔」提示，直接自動下載
        "download.directory_upgrade": True,              # 如果資料夾已存在，允許直接使用
        "safebrowsing.enabled": True                     # 啟用安全瀏覽，避免 Chrome 擋下自動下載
    }

    # 把上述設定套用到 Chrome 啟動參數
    options.add_experimental_option("prefs", prefs)      # 設定自動下載路徑等行為
    # 設定離開 Python 時 Chrome 保持開啟（不自動關閉視窗）
    options.add_experimental_option("detach", True)      # 執行完後 Chrome 不自動關閉，方便手動觀察  

    try:
        before_files = set(os.listdir(download_path))
        print("找到下載按鈕，準備點擊")

        download_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]"))
        )
        download_btn.click()
        print("\033[32m✅ 已點擊下載按鈕\033[0m")
        time.sleep(3)

    except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, TimeoutException) as e:
        print("\033[93m⚠️ 行動裝置模式或 UI 不支援下載 \033[0m")
    except Exception as e:
        print("\033[91m❌ 其他錯誤：\033[0m", str(e).split("Stacktrace")[0])


    # ====== 切換到新分頁（若有） ======
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        print(f"🔀 已切換到新分頁：{driver.current_url}")

    # ====== 等待檔案出現 ======
    def wait_for_download(download_path, before_files, timeout=20, auto_delete=True):
        print("📂 等待下載完成...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            after_files = set(os.listdir(download_path))
            new_files = after_files - before_files

            # 排除還在下載中的檔案
            completed_files = [f for f in new_files if f.endswith(".apk")] # 刪除【.apk】 檔案
            '''completed_files = [f for f in new_files if not f.endswith(".crdownload")] ''' # 刪除下載檔案
            if completed_files:
                print(f"\033[32m✅ 下載完成：{completed_files}\033[0m")

                if auto_delete:
                    for file in completed_files:
                        try:
                            os.remove(os.path.join(download_path, file))
                            print(f"\033[31m🗑️ 已刪除：\033[0m")
                        except Exception as e:
                            print(f"\033[91m⚠️ 無法刪除 {file}：{e}\033[0m")
                return True
            time.sleep(1)
        print("\033[91m❌ 下載失敗或超時\033[0m")
        return False

    # 執行等待下載完成邏輯
    wait_for_download(download_path, before_files)
    '''try:
        popup = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Download')]"))
        )
        print('B-1.點擊【Download】 \033[32mOK\033[0m') 
        close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
        print("B-1.【關閉】popup_club \033[32mOK\033[0m")
    except TimeoutException:
            print("\033[93m" + "A-1.未偵測到已領取文字，繼續流程..." + "\033[0m")
    '''

    # B.1-2Header_download >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33mB.1-2Header_download \033[0m')
    print("\033[44m\033[32m" + "B.1-2Header_download" + "\033[0m")

    try:
        # 等待並點擊關閉 download bar
        download_Close_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "img[alt='ic_close_2']"))
        )
        print('B-1-2.download條 \033[32mOK\033[0m')
        download_Close_btn.click()
        print("B.1-2.【關閉】download條 \033[32mOK\033[0m")

        try:
            # 等待信封圖示出現後點擊
            no_download = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'ic_mail_unread')]"))
            )
            no_download.click()

            # 等待 Mail 選項出現後點擊
            mailbox = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Mail')]"))
            )
            mailbox.click()
            print("B-1-2.download條 不存在 \033[32mOK\033[0m")

            driver.back()
            print("回首頁 \033[32mOK\033[0m")
        except TimeoutException:
            print("\033[94m未偵測到信封或 Mail 元素，可略過。\033[0m")
            checked = True

        try: # 模擬觸發內彈
            popup = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'popup_first_recharge_vb')]"))
            )
            print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
            # 找到關閉按鈕並點擊
            close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
            print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
        except TimeoutException:
            print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")
        
        '''    
        # 方法2 JS(Java Script)強制關閉 
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//img[@alt='ic_close_2']"))
        )
        driver.execute_script("arguments[0].click();", element)
        print("✅ JS 點擊關閉成功")
    except Exception as e:
        print("❌ JS 點擊失敗：", str(e))
        '''
    except TimeoutException as e:
        print("B.1-2.【關閉】download條 >>>> \033[91m元素不存在\033[0m", str(e).split("Stacktrace")[0])
        checked = True

    except Exception as e:
        print("\033[91mB.1-2 其他錯誤：\033[0m", str(e).split("Stacktrace")[0])
        checked = True

    # B.1-3 Header_充值輪盤 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33mB.1-3.Header_充值輪盤 \033[0m')
    print("\033[44m\033[32m" + "B.1-3.Header_充值輪盤" + "\033[0m")
    sleep(0.5)
    try:
        # 等待並點擊關閉 download bar
        Luckywheel = WebDriverWait(driver,5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt='ic_lucky_wheel']"))
        )
        print('B-1-3A.找到充值輪盤圖示 \033[32mOK\033[0m')
        checked = True
        '''
        if len(driver.find_elements(By.CSS_SELECTOR, "div.z-[1005]")) > 0:
            print("⛔ 有遮罩，跳過 Luckywheel 點擊")
        else:
            Luckywheel.click()
            print('B-1-3.點擊輪盤圖示 \033[32mOK\033[0m')
        '''
        sleep(0.5)
        Luckywheel = WebDriverWait(driver,5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "img[alt='ic_lucky_wheel']"))
        ).click()
        print('B-1-3B.點擊輪盤圖示 \033[32mOK\033[0m')

        sleep(0.5)
        try:
            # 進入充值輪盤頁面
            no_download = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Deposit Now')]"))
            )
            print("B-1-3C.充值輪盤頁面 \033[32mOK\033[0m")

            driver.back()
            print("回首頁 \033[32mOK\033[0m")   
        except TimeoutException as e:
            print("\033[94m未偵測到元素，可略過。\033[0m")
            checked = True

        try: # 模擬觸發內彈
            popup = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"))
            )
            print("A-1-1.點擊首充 popup \033[32mOK\033[0m")
            # 找到關閉按鈕並點擊
            close_btn = driver.find_element(By.XPATH, "//img[@alt='ic_close']").click()
            print("A-1-1.【關閉】首充 popup \033[32mOK\033[0m")
        except TimeoutException:
            print("\033[94m模擬內彈.未偵測到 ，可略過。\033[0m")
        
    except TimeoutException as e:
        print("B.1-3 >>>> \033[91m元素不存在\033[0m", str(e).split("Stacktrace")[0])
        checked = True
    except Exception as e:
        print("\033[91mB.1-3 其他錯誤：\033[0m", str(e).split("Stacktrace")[0])
        checked = True

    # B.1-4 Header_Mailbox >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33mB.1-4.Header_Mailbox \033[0m')
    print("\033[44m\033[32m" + "B.1-4.Header_Mailbox" + "\033[0m")
    sleep(0.5)
    try:
            # 【mailbox】 信封圖示出現並點擊
            mailbox = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'ic_mail_unread')]"))
            )
            print("B-1-4.mailbox 存在 \033[32mOK\033[0m")
            mailbox.click()
            print("B-1-4.點擊mailbox icon \033[32mOK\033[0m")

            # 【Mail_list】 信件列表
            page = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Mail')]"))
            )
            print("B-1-4.Mail_page \033[32mOK\033[0m")

            # 【Mail_list_backbtn】 返回按鈕
            backbtn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt,'ic_back_header')]"))
            )
            backbtn.click()
            print("B-1-4.使用返回icon...回到首頁 \033[32mOK\033[0m")
    except TimeoutException:
            print("\033[94m未偵測到信封或 Mail 元素，可略過。\033[0m")
            checked = True
    except Exception as e:
        print("\033[91mB.1-4.其他錯誤：\033[0m", str(e).split("Stacktrace")[0])
        checked = True

    # B.2-1 首頁【Banner】廣告模塊 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33mB.2-1 首頁【Banner】\033[0m')
    print("\033[44m\033[32m" + "B.2-1 首頁【Banner】廣告模塊" + "\033[0m")
    sleep(0.5)
    #尋找首頁Banner參數【'0_ENTER_GAME', '1_TEAM_CLUB', '2_FIRST_CHARGE', '3_CHARGE_WHEEL', '4_INVITE_WHEEL','5_RANKINGS', '6_GIFT_CODE', '7_VIP', '8_PIGGY_BANK'】
    banner_alts = ['0_DYNAMIC_ACTIVITY','1_ENTER_GAME', '2_TEAM_CLUB', '3_FIRST_CHARGE', '4_CHARGE_WHEEL', '5_INVITE_WHEEL','6_RANKINGS', '7_GIFT_CODE', '8_VIP', '9_PIGGY_BANK', '00_Daily Mission']
    clicked_banners = set()  # 記錄哪些 banner 成功點擊過
    clicked_banners.clear()  # 僅針對已存在的集合清空

    # 決定要用哪一組名稱對照表 ，如果沒有參數 => 未定義
    if product_numbers == ['INV6']:
        banner_alts = ['0_DYNAMIC_ACTIVITY','1_ENTER_GAME', '2_TEAM_CLUB', '3_FIRST_CHARGE', '4_CHARGE_WHEEL', '5_INVITE_WHEEL','6_RANKINGS', '7_GIFT_CODE', '8_VIP', '9_PIGGY_BANK', '00_Daily Mission']
        alt_names = { 
        '1_ENTER_GAME': '✈️ 飛機遊戲',
        '2_TEAM_CLUB': '👥 團隊俱樂部',
        '3_FIRST_CHARGE': '💎 首儲活動',
        '4_CHARGE_WHEEL': '🎡 充值轉盤',
        '5_INVITE_WHEEL': '🎯 邀請轉盤',
        '6_RANKINGS': '🏆 排行榜',
        '7_GIFT_CODE': '🎁 禮包碼',
        '8_VIP': '👑 VIP專區',
        '9_PIGGY_BANK': '🐷 虧損反水', 
        '00_Daily Mission': '📋 任務中心',
        '0_DYNAMIC_ACTIVITY': '支付教程 動態活動'  
    } 
    else:
        banner_alts = ['0_NEW_PAYMENT_GUIDE', '1_FIRST_CHARGE', '2_PIGGY_BANK', '3_ENTER_GAME', '4_TEAM_CLUB', '5_CHARGE_WHEEL','6_INVITE_WHEEL', '7_GIFT_CODE', '8_VIP', '9_PIGGY_BANK']
        alt_names = { 
        '0_NEW_PAYMENT_GUIDE': '💰 新支付指南',
        '1_FIRST_CHARGE': '💎 首儲活動',
        '2_PIGGY_BANK': '🐷 虧損反水',
        '3_ENTER_GAME': '✈️ 飛機遊戲',
        '4_TEAM_CLUB': '👥 團隊俱樂部',
        '5_CHARGE_WHEEL': '🎡 充值轉盤',
        '6_INVITE_WHEEL': '🎯 邀請轉盤',
        '7_GIFT_CODE': '🎁 禮包碼',
        '8_VIP': '👑 VIP專區',
        '9_PIGGY_BANK': '🐷 虧損反水'
    }
    #  0_NEW_PAYMENT_GUIDE
    running = True  # 控制 while 是否繼續
    error_reported = False   # ⬅️ 新增旗標，避免重複印
    while running: 
        for alt_text in banner_alts:
            print(f"\n👉 正在處理 Banner: {alt_text}")
            if alt_text in clicked_banners:
                continue  # 如果已經點過這個廣告就跳過
            try:
                banner = WebDriverWait(driver, 60).until(
                 EC.element_to_be_clickable((By.XPATH, f"//img[contains(@alt, '{alt_text}')]"))
                )
                if banner.is_displayed():
                    banner.click()
                    print(f" 點擊廣告成功【{alt_text}】\033[32mOK\033[0m")
                    print(f"✅ \033[33m【{alt_names.get(alt_text, alt_text)}】\033[32m\033[0m")
                    # ...其餘流程                
                    time.sleep(1)
                    # ========================================
                                        # ====== ⛔ 錯誤訊息偵測區段（下架訊息）======
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "This game has been taken down")]'))
                        )
                        print(f"\033[31m⚠️【{alt_text}】遊戲異常略過返回首頁。\033[0m")
                        clicked_banners.add(alt_text)
                        continue
                    except TimeoutException:
                        pass # 沒跳出錯誤 → 正常流程

                                        # ====== 💰 出現 Collect 按鈕時，自動點擊 ======
                    try:
                        collect_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Collect')]"))
                        )
                        collect_btn.click()
                        print(f"\033[33m💰 Collect 按鈕，已點擊成功。\033[0m")
                        time.sleep(1)
                        clicked_banners.add(alt_text)
                        continue
                    except TimeoutException:
                        pass  # 沒有 Collect 按鈕就略過
                    # ========================================

                    driver.back()  # 回首頁
                    print("離開返回首頁 \033[32mOK\033[0m")
                    time.sleep(1)
                    clicked_banners.add(alt_text) #繼續點擊 banner
            except NoSuchElementException:
                pass
            except Exception as e:
                if "invalid session id" in str(e):
                    if not error_reported:   # ⬅️ 只在第一次觸發時印
                        print("⚠️ Driver session 已失效，程式即將結束。")
                        error_reported = True
                    running = False   # ⬅️ 停止 while
                else:
                    print(f"\033[31m❌ 元素變動不存在或不再架上【{alt_names.get(alt_text, alt_text)}】，直接跳過\033[0m")
                    continue   # 直接跳下一個 Banner
            else:
                print("沒有錯誤，成功執行！")
            # 👉 跑完一輪就結束
        print("\033[33m🎉 所有 Banners 已處理完畢，程式結束！\033[0m") 
        break # 如果 都點過了，就結束
    # ======= 完成檢查 =======
    missing = set(banner_alts) - clicked_banners
    if missing:
        print(f"\033[31m⚠️ 還有 Banner 沒被觸發: {missing}\033[0m")
    else:
        print("\033[32m🎉 所有 Banner 都已觸發完成！\033[0m")
    time.sleep(1)









    #<<<<<<<<<<<<<<<<<<<<<背景偵測popup，結束>>>>>>>>>>>>>>>>>>>>>>
except TimeoutException:
    pass
finally:
    exit_event.set()
    popup_thread.join() 
    #<<<<<<<<<<<<<<<<<<<<<背景偵測popup，結束>>>>>>>>>>>>>>>>>>>>>>

input('Press Enter to exit...')

'''    
    # B.1-5 Header_信件>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    print('\033[33mB.1-5.Header_信件 \033[0m')
    print("\033[44m\033[32m" + "B.1-5.Header_信件" + "\033[0m")
    # 通知列表信件數量(未讀、已讀=總數量)
    print("\033[44m\033[32m" + "通知列表信件數量" + "\033[0m")
    try:
        # 等待未讀信件元素出現
        unread_elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "//img[contains(@alt,'ic_mail_unread')]"))
        )
        print("B-1-5.未讀信件 或 沒有信件 \033[32mOK\033[0m")
        
        # 等待已讀信件元素出現(包含未讀元素存在=已讀總數量)
        read_elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@data-show,'true')]"))
        )
        print("B-1-5.偵測到有未讀信件 \033[32mOK\033[0m")



    #=======================================================================================================================================

    # 統計未讀信件數量(標記紅點)

        unread_count = len(unread_elements)
        print(f"25-1.未讀信件數量: \033[32m{unread_count}\033[0m")
        # 統計已讀信件數量(未有紅點)
        read_count = len(read_elements) ##判斷已讀+未讀數量---顯示總數量
        read_counts = read_count - unread_count ##未有紅點 - 標記紅點
        print(f"25-2.已讀信件數量: \033[32m{read_counts}\033[0m")
        # 計算總數量
        total_count = read_counts + unread_count
        print(f"25-3.總數量(未+已): \033[32m{total_count}\033[0m")
        input('Press Enter to exit...')

    # 統計通知鈴的數量
        print("\033[44m\033[32m" + "26. 通知鈴數量" + "\033[0m")
        notification_icons = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@class,'MessageCountBadge')]"))
            )
        bell_count = sum(int(icon.text) for icon in notification_icons)
        #通知鈴=通知列表數量
        print(f"26-1.通知鈴數量: \033[34m{bell_count}\033[0m")
    # 判斷三項數量是否相等(總數量、通知鈴數量、未讀數量)
        if unread_count == bell_count == total_count:
            print("26-2.總數量、通知鈴數量、未讀數量皆相符\033[32mOK\033[0m")
        elif unread_count == bell_count != total_count:  ## 如果condition1為False且condition2為True，執行這裡的代碼
            print("26-2.未讀數量、通知鈴數量皆相符\033[32m OK\033[0m")
        else:
            print("26-2.\033[91m" +"三項數量皆不符"+ "\033[0m")
    except Exception as e:
        print("\033[91m" +"出現異常"+ "\033[0m", e)
    # 抓所有通知元素
        notifications = driver.find_elements(By.XPATH, "//div[contains(@class, 'your-notification-class')]")
        
    # 初始化已讀和未讀計數
        read_count = 0
        unread_count = 0

        # 遍歷每個通知元素，計算已讀和未讀數量
        for notification in notifications:
            # 檢查通知是否標記為已讀
            red_unread = notification.find_element(By.XPATH, ".//div[contains(@class, 'flex-between fixed right-0 top-[44px] bottom-0 flex w-[450px] flex-col bg-[var(--background-primary)] p-4 text-left')]").is_displayed()
            if red_unread:
                unread_count += 1
            else:
                read_count += 1

        # 打印已讀和未讀數量
        print("已讀數量:", read_count)
        print("未讀數量:", unread_count) 
    except TimeoutException:
        print("找不到通知列表元素。")
    '''