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
TimeoutException, ElementClickInterceptedException, ElementNotInteractableException, 
NoSuchElementException, NoSuchWindowException,StaleElementReferenceException)
from pathlib import Path
from colorama import Fore,Style
from pathlib import Path
import os, time
import sys  
import threading
import configparser
import pyperclip
import re


# 設定 ChromeOptions 
config = configparser.ConfigParser()
# ====== 設定下載路徑 ====== 
#download_path =r"C:\Users\lewis.chiu\Downloads"  #另種寫法 "C:\\Users\howar\Downloads" 或 【自用 r"C:\Users\User\Downloads"】windows系統
download_path = str(Path.home() / "Downloads")  # Apple 系統
#r"D:\下載"	✅ 推薦	不用擔心 \ 變跳脫符號
#"D:\\下載"	✅ 推薦	手動雙斜線跳脫更安全
#"D:\下載"	❌ 不推薦	萬一剛好有 \t、\n、\r 很容易踩坑

# ====== 初始化 Chrome Driver ======
options = webdriver.ChromeOptions()
options.add_argument("--disable-infobars")
options.add_argument("--disable-notifications")
options.add_argument("--disable-popup-blocking")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_keyfile = os.path.join(current_dir, 'URL.ini')
# 讀取配置文件
config.read(config_keyfile, encoding='utf-8')
################確認遊戲模板(請輸入 'U1、U2.../V1、V2...')###########################
ui_version = 'IN'
product_numbers = ['INV6']
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

# 公告跑馬燈
# B.2-2 首頁【公告跑馬燈】
print('\033[33mB.2-2 首頁【公告跑馬燈】 \033[0m')
print("\033[44m\033[32m" + "B.2-2 首頁【公告跑馬燈】" + "\033[0m")
try:
    notice = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((
    By.XPATH,
    "//div[contains(@class,'scroll-item')]"
    ))
    )
    text = notice.text.strip() # 去掉字串前後的空白、Tab、換行。

    if text:
        print(f"\033[1;36m📢 公告內容：\033[33m{text}\033[0m")                         
    else:
        print("⚠️ 已找到公告元素，但內容為空白。")

except TimeoutException:
    print("❌ 5 秒內找不到公告元素。")

except NoSuchElementException:
    print("❌ 公告元素不存在。")

except StaleElementReferenceException:
    print("⚠️ 公告元素已更新（Stale Element），請重新抓取。")

except Exception as e:
    print(f"❌ 抓取公告失敗：{type(e).name}：{e}")






input('Press Enter to exit...') #執行不關視窗
