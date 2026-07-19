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

# 文字顏色
print("\033[30m黑色文字\033[0m")
print("\033[31m紅色文字\033[0m")
print("\033[32m綠色文字\033[0m")
print("\033[33m黃色文字\033[0m")
print("\033[34m藍色文字\033[0m")
print("\033[35m紫色文字\033[0m")
print("\033[36m青色文字\033[0m")
print("\033[37m白色文字\033[0m")

# ================================

# 粗體(Bold)
print("\033[1;31m粗體紅字\033[0m")
print("\033[1;32m粗體綠字\033[0m")
print("\033[1;33m粗體黃字\033[0m")
print("\033[1;34m粗體藍字\033[0m")
print("\033[1;35m粗體紫字\033[0m")
print("\033[1;36m粗體青字\033[0m")
print("\033[1;37m粗體白字\033[0m")

# ================================

# 背景顏色
print("\033[41m紅底白字\033[37m 紅底白字 \033[0m")
print("\033[42m綠底黑字\033[30m 綠底黑字 \033[0m")
print("\033[43m黃底黑字\033[30m 黃底黑字 \033[0m")
print("\033[44m藍底白字\033[37m 藍底白字 \033[0m")
print("\033[45m紫底白字\033[37m 紫底白字 \033[0m")
print("\033[46m青底黑字\033[30m 青底黑字 \033[0m")
print("\033[47m白底黑字\033[30m 白底黑字 \033[0m")

# ================================

# 高亮背景 (100~107)
print("\033[100m亮黑底\033[37m 亮黑底 \033[0m")
print("\033[101m亮紅底\033[37m 亮紅底 \033[0m")
print("\033[102m亮綠底\033[30m 亮綠底 \033[0m")
print("\033[103m亮黃底\033[30m 亮黃底 \033[0m")
print("\033[104m亮藍底\033[37m 亮藍底 \033[0m")
print("\033[105m亮紫底\033[37m 亮紫底 \033[0m")
print("\033[106m亮青底\033[30m 亮青底 \033[0m")
print("\033[107m亮白底\033[30m 亮白底 \033[0m")

# ================================

# 特殊效果
print("\033[1m粗體文字\033[0m")
print("\033[2m淡色文字\033[0m")
print("\033[3m斜體文字\033[0m")
print("\033[4m底線文字\033[0m")
print("\033[5m閃爍文字(部分終端支援)\033[0m")
print("\033[7m反白文字\033[0m")
print("\033[9m刪除線文字\033[0m")
