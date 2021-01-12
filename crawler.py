import sys, os, time, json, logging, schedule
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from threadscraper import ThreadScraper
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait

class ForumCrawler:
    def __init__(self, driver, target=None):
        self.driver = driver
        self.scraper = ThreadScraper()
        self.logger = logging.getLogger(__name__)
        if target is None:
            raise FileNotFoundError
        if target == 'upwork':
            self.target = 'https://community.upwork.com/t5/forums/recentpostspage'

    def crawl(self):
        #print('Crawling on target {}'.format(self.target))
        hist = []
        self.driver.get(self.target)
        time.sleep(3)
        for elem in self.driver.find_elements_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']"):
            time.sleep(3)
            try:
                url = str(elem.get_attribute('href'))
                if url in hist:
                    continue
                self.logger.info('Sending URL to scraper')
                time.sleep(1)
                self.driver.get(url)
                time.sleep(5)
                self.scraper.make_soup(self.driver.page_source, url)
            except StaleElementReferenceException:
                pass

    def save_to_cache(self):
        raise NotImplementedError