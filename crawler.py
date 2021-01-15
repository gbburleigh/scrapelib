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
        hist = []
        self.driver.get(self.target)
        time.sleep(3)
        links = self.driver.find_elements_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']")
        urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")
        self.logger.info('Successfully obtained URLs on homepage')
        pkg = {}
        for url in urls:
            try:
                self.logger.info('Sending URL to scraper')
                self.driver.get(url)
                time.sleep(3)
                pkg[url] = self.scraper.make_soup(self.driver.page_source, url)
            except StaleElementReferenceException:
                self.logger.debug('Caught a StaleElementException')
                pass

        return json.dumps(pkg, indent=4)

    def get_links(self, tag):
        hist = []
        urls = []
        for elem in self.driver.find_elements_by_xpath(tag):
            try:
                res = str(elem.get_attribute('href'))
                if res not in hist:
                    hist.append(res)
                    self.logger.debug('Found URL {}'.format(res))
                    urls.append(res)
                else:
                    self.logger.debug('Found a stale URL')
                    continue
            except StaleElementReferenceException:
                self.logger.warning('Caught a StaleElementException')
                pass

        return urls


    def save_to_cache(self):
        raise NotImplementedError