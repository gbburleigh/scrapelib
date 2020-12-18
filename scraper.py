import sys, os, time, pandas
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class PostScraper:
    def __init__(self, url):
        self.driver = webdriver.Chrome()
        self.page = self.driver.get(url)
        time.sleep(5)