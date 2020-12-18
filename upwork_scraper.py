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
        try:
            self.thread_name = self.driver.find_elements_by_class_name('lia-message-subject-banner \
                lia-component-forums-widget-message-subject-banner')[0].text
        except:
            print('Failed to fetch thread name for {}'.format(url))
            sys.exit()
        
