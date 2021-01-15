import sys, os, time, json, logging, schedule, datetime, atexit
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
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.fh = logging.FileHandler(os.getcwd() + '/cache/logs/debug.log', 'w+')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        self.formatter = logging.Formatter('[%(levelname)s :: (%(asctime)s)]: %(message)s')
        self.fh.setFormatter(self.formatter)
        self.ch.setFormatter(self.formatter)
        #logging.basicConfig(format='[%(levelname)s :: (%(asctime)s)]: %(message)s')
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        schedule.every(1).minutes.do(self.run)
        
    def run(self):
        import socket, datetime
        self.logger.info('Beginning scan at {}'.format(socket.gethostname()))
        crawler = ForumCrawler(self.webdriver, target='upwork')
        data = crawler.crawl()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M}")
        #_json = "{'titles': {}}".format(data)
        with open(os.getcwd() + f'/cache/logs/log_{now}.json', 'w') as f:
            f.write(data)
        self.logger.warning('Got results \n{}'.format(data))

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
    atexit.register(d.close())
    d.close()