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
123