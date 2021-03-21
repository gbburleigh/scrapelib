import time, json, csv, sts, os
from selenium import webdriver
from crawler import Crawler
from header import *
from datetime import datetime

class Driver:
    def __init__(self, flush=False, start=None):
        self.db = SiteDB([], 'upwork')
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
            firefox_options=options)
        elif '-c' in sys.argv:
            import chromedriver_binary
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.webdriver = webdriver.Chrome(options=options)
        else:
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager import chrome
            from webdriver_manager.chrome import ChromeDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        
    def run(self):
        """
        
        """
        old_db = SiteDB([], 'upwork')
        old_db.load()
        self.db.pred = old_db.cache
        if '-d' in sys.argv:
            crawler = Crawler(self.webdriver, self.db, debug=True)
        else:
            crawler = Crawler(self.webdriver, self.db)
        self.db = crawler.crawl()
        if '-d' in sys.argv:
            deletes = self.db.compare(old_db)
        self.db.write()
   
    def close(self):
        """

        """
        self.webdriver.quit()
        sys.exit()
 
if __name__ == "__main__":
    now = datetime.now()
    try:
        d = Driver(start=now)
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    d.close()

