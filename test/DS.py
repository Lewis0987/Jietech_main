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
TimeoutException, ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException, NoSuchWindowException,StaleElementReferenceException)
from pathlib import Path
from colorama import Fore,Style
import os, time
import sys
import threading
import configparser
import pyperclip
import re


# ====== 設定下載路徑 ====== 
#download_path =r"C:\Users\User\Downloads"  #另種寫法 "C:\\Users\howar\Downloads" 
#r"D:\下載"	✅ 推薦	不用擔心 \ 變跳脫符號
#"D:\\下載"	✅ 推薦	手動雙斜線跳脫更安全
#"D:\下載"	❌ 不推薦	萬一剛好有 \t、\n、\r 很容易踩坑
# 【設定 ChromeOptions】 
# ====== 初始化 Chrome Driver ======
options = webdriver.ChromeOptions()
chrome_options = Options()
chrome_options.add_argument("--log-level=3")  # 只顯示 fatal 錯誤
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 關閉 GCM 日誌
# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_keyfile = os.path.join(current_dir, 'IND.ini')
# 讀取配置文件
config = configparser.ConfigParser()
config.read(config_keyfile, encoding='utf-8')

################確認遊戲模板(請輸入 'U1、U2.../V1、V2...')###########################
version = 'DS'
ui_numbers = ['WEB']
################確認帳號#######################################
phone='8888888888' #for 登入
# 初始化Chrome浏览器
driver = webdriver.Chrome(service=Service(), options=chrome_options)
# 開啟網页並將模板引入
WebDriverWait(driver, 10)
for product in ui_numbers:
    url = config.get(version, product)
    driver.get(url)
    driver.maximize_window() #網頁整頁

#-------------------------1.A.首頁模塊 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# A.首頁
print('\033[33mAP平台 \033[0m')
print("\033[44m\033[32m" + "A.首頁" + "\033[0m")

try:
    # 慢慢往下滑動（模擬人）
    for i in range(3):  # 滑 3 次
        driver.execute_script("window.scrollBy(0, 200);")
        time.sleep(0.5)
    print('往下滑動尋找navSlide \033[32mOK\033[0m')

    Contact = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'bannerBtn aos-init aos-animate')]"))
    ).click()
    print('A-1.點擊contact btn \033[32mOK\033[0m')
except TimeoutException: 
    print("\033[94mA-1.未偵測活動元素，繼續流程...\033[0m")
try:
    Contact = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Happy to see you here')]"))
    ).click()
    print('A-2.Contact頁 \033[32mOK\033[0m')
except TimeoutException: 
    print("\033[94mA-2.未偵測活動元素，繼續流程...\033[0m")
driver.back()
print("回首頁 \033[32mOK\033[0m")
driver.refresh
print("重整頁面 \033[32mOK\033[0m")
'''
#執行上下滑動
try:
    Contact = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(@class,'slideLogo')]"))
    ).click()
    print('首頁logo重整 \033[32mOK\033[0m')
except TimeoutException: 
    print("\033[94m.未偵測元素...\033[0m")
## 慢慢往下滑動（模擬人）
for i in range(3):  # 滑 3 次
        driver.execute_script("window.scrollBy(0, -200);")
        time.sleep(0.5)
print('往上滑動 \033[32mOK\033[0m')
'''


#A.3首頁導航條tab bar 頭部導航條抓元素左至右 [1,2,3,4,5] 
print('\033[33m首頁[A.3 tab bar] \033[0m')
print("\033[44m\033[32m" + "A.3 tab bar" + "\033[0m")

#導航條tab【PRODUCTS】
print('\033[33m首頁[A.3-1.tab【products】] \033[0m')
try:
    tabbar = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "(//div[contains(@class,'navSlide')]//a)[2]" #導航條[2]
        ))
    ).click()
    print('A-3-1.首頁_點擊tab【products】 \033[32mOK\033[0m')
    try:
        Prouducts = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Game Support Language')]" #Prouducts頁面
        ))
    ).click()
        print('A-3-1.導向product頁面 \033[32mOK\033[0m')        
    except TimeoutException:
        print("\033[94m.錯誤或其他問題...\033[0m")
except TimeoutException: 
    print("\033[94m.未偵測元素...\033[0m")
sleep(0.5)

# 慢慢往下滑動（模擬人）
for i in range(3):  # 滑 3 次
        driver.execute_script("window.scrollBy(0, 200);")
        time.sleep(0.5)
print('往下滑動尋找navSlide \033[32mOK\033[0m')

#導航條tab【ABOUT】
print('\033[33m首頁[A.3-2.tab【ABOUT】] \033[0m')
try:
    tabbar = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "(//div[contains(@class,'navSlide')]//a)[3]" #導航條[3]
        ))
    ).click()
    print('A-3-2.首頁_點擊tab【ABOUT】 \033[32mOK\033[0m')
    try:
        Prouducts = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'ABOUT')]" #ABOUT頁面
        ))
    ).click()
        print('A-3-2.導向ABOUT頁面 \033[32mOK\033[0m')        
    except TimeoutException:
        print("\033[91m.未偵測元素或其他問題...\033[0m")
except TimeoutException: 
    print("\033[95m.未偵測元素...\033[0m")
111








input('Press Enter to exit...') #執行不關視窗
