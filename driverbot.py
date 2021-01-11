import sys, os, time, json, logging, schedule
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from scraper import ThreadScraper
from crawler import ForumCrawler

class DriverBot:
    def __init__(self):
        #logging.basicConfig(format='[%(levelname)s :: %(asctime)s]: %(message)s')
        # root = logging.getLogger()
        # root.setLevel(logging.DEBUG)
        # handler = logging.StreamHandler(sys.stdout)
        # handler.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # handler.setFormatter(formatter)
        # root.addHandler(handler)

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        #root.info('Webdriver configured successfully')
        
        #TODO: Add either file reading or hard coded URLs for forum targets
        self.targets = {}

    def run(self):
        logging.info('Crawling on all targets')
        #root.info('Starting crawler')
        crawler = ForumCrawler(self.webdriver, target='upwork')
        crawler.crawl()
        # for target in self.targets:
        #     crawler = ForumCrawler(self.webdriver, target='upwork')
        #     crawler.crawl()
        #schedule.every(15).minutes.do(self.run())

    def execute(self):
        while True:
            schedule.run_pending()
            time.sleep(0.5)

    def close(self):
        self.webdriver.quit()
        sys.exit()

if __name__ == "__main__":
    d = DriverBot()
    d.run()
    d.close()
    # options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    # webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    # webdriver.get('https://community.upwork.com/t5/forums/recentpostspage')
    # for elem in webdriver.find_elements_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']"):
    #     print(elem.get_attribute('href'))
    # webdriver.quit()