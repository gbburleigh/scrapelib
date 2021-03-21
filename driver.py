import time, json, csv, sys, os
from selenium import webdriver
from crawler import Crawler
from header import *
from datetime import datetime

class Driver:
    """
    Main driver object for running script from. Instantiates crawler and scraper objects to handle
    all data collection, and interfaces with db.load and db.write to handle all caching. Comparisons
    are done via lower level objects, and handles opening and closing processes associated with webdriver.
    """
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
        Main run function. Creates an old db to load data into and to compare new db with. Creates
        db through crawler.crawl and handles writing.
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
        Close all processes associated with program and webdriver. Also uses pkill as a sanity
        check if chrome process is running.
        """
        self.webdriver.quit()
        os.system('pkill -f chrome')
        sys.exit()
 
if __name__ == "__main__":
    now = datetime.now()
    d = Driver(start=now)
    try:
        d.run()
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    d.close()

