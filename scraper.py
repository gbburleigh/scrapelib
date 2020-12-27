import sys, os, time, json, logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from util import *
from bs4 import BeautifulSoup

class ThreadScraper:
    """Generic thread scraper object with HTML targets passed
    in through JSON format."""
    
    def __init__(self, targets, url):
        self.parsed = {}

        #Enable headless selenium driver
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')

        with json.load(targets) as targets:
            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            self.page = self.driver.get(url)
            time.sleep(3)
            #Get latest updated HTML for this thread
            self.soup = BeautifulSoup(self.page, 'html.parser')
            try:
                self.thread_name = self.driver.find_element_by_xpath(targets['thread_name'])[0].text
            except:
                print('Invalid XPath for thread name')

            try:
                self.op = self.driver.find_element_by_xpath(targets['original_poster'])[0].text
            except:
                print('Invalid XPath for original poster')
                
            try:
                self.posted_date = self.driver.find_element_by_xpath(targets['post_date'])[0].text
            except:
                print('Invalid XPath for original post datetime')

            try:
                self.views = self.driver.find_element_by_xpath(targets['views'])[0].text
            except:
                print('Invalid XPath for thread views')

            try:
                self.category = self.driver.find_element_by_xpath(targets['category'])[0].text
            except:
                print('Invalid XPath for thread category')

            try:
                self.op_join_date = self.driver.find_element_by_xpath(targets['op_join_date'])[0].text
            except:
                print('Invalid XPath for OP join date')
                
            try:
                self.op_text = self.driver.find_element_by_xpath(targets['original_post_text'])[0].text
            except:
                print('Invalid XPath for original post text')

            if self.op_text.find(targets['moderator_msg']) != -1:
                self.moderated = True
                self.moderator = self.driver.find_element_by_xpath(targets['moderator'])[0].text
            else:
                self.moderated = False

            try:
                self.op_rank = self.driver.find_element_by_xpath(targets['author_rank'])[0].text
            except:
                print('Invalid XPath for OP rank')

            

    def parse_replies(self):
        return NotImplementedError

    def config_dict(self, targets):
        """Alternate method for populating scraped data dictionary"""
        with json.load(targets) as targets:
            failures = []
            for key, val in targets.items():
                try:
                    self.parsed[str(key)] = self.driver.find_element_by_xpath(val)[0].text
                except:
                    failures.append(str(key))

        print('Faiiled to construct dictionary values for following fields: {}'.format(failures))

    def exit(self):
        self.driver.close()
        print('Closing...')
        sys.exit()