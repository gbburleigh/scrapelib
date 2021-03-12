import sys,os, signal

#Configure packages FIXME
if sys.prefix == sys.base_prefix:
    import subprocess
    print('Configuring...')
    os.system('. resources/activate.sh')

import time, json, logging, schedule, datetime, atexit, csv
from selenium import webdriver
from newcrawler import Crawler
from header import *

class Driver:
    def __init__(self, flush=False, start=None):
        self.db = SiteDB([], 'upwork')
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            try:
                self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                    firefox_options=options, log_path=os.getcwd() + '/cache/sys/geckodriver.log')
            except OSError:
                import subprocess
                try:
                    out = subprocess.check_output(['lsof', '/home/gbb5412/.wdm/drivers/geckodriver/linux64/v0.29.0/geckodriver'],\
                        stderr=open(os.devnull, 'w'))
                    pids = []
                    lines = out.strip().split('\n')
                    for line in lines:
                        pids.append(int(line))
                    for pid in pids:
                        subprocess.call(['kill', pid])
                    self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                        firefox_options=options, log_path=os.getcwd()+ '/cache/sys/geckodriver.log')
                except:
                    self.close()
        else:
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager import chrome
            from webdriver_manager.chrome import ChromeDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        #Configure scheduling
        schedule.every().day.at('00:00').do(self.run)
        
    def run(self):

        """Main driver function. Inherits crawler class and functionality to scrape various threads.
        Inherited fields are webdriver and logger object. This function will execute once every day.
        Handles cache management and garbage collection."""
        old_db = SiteDB([], 'upwork')
        old_db.load()
        if '-d' in sys.argv:
            crawler = Crawler(self.webdriver, self.db, debug=True)
        else:
            crawler = Crawler(self.webdriver, self.db)
        self.db = crawler.crawl()
        if '-d' in sys.argv:
            deletes = self.db.compare(old_db)
        self.db.write()
   
    def close(self):
        #Cleans up webdriver processes and exits program
        self.webdriver.quit()
        sys.exit()

    def flush_cache(self):
        dirs = ['/cache/logs/']
        for dir_ in dirs:
            _, _, filenames = next(os.walk(os.getcwd() + dir_))
            if len(filenames) > 0:
                for f in filenames:
                    os.remove(os.getcwd() + dir_ + f)

    def flush_csv(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/csv'))
        if len(filenames) > 0:
            for f in filenames:
                os.remove(os.getcwd() + f'/cache/csv/{f}')

    def flush_stats(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/sys/stats'))
        if len(filenames) > 0:
            for f in filenames:
                os.remove(os.getcwd() + f'/cache/sys/stats/{f}')

    def flush(self):
        self.flush_cache()
        self.flush_csv()
        self.flush_stats()

 
if __name__ == "__main__":
    #Run test functions
    now = datetime.datetime.now()
    d = Driver(start=now)
    if '-flush' in sys.argv:
        d.flush()
    try:
        d.run()
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    d.close()
