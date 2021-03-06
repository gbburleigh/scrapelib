import sys,os, signal

#Configure packages FIXME
if sys.prefix == sys.base_prefix:
    import subprocess
    os.system('. activate.sh')

import time, json, logging, schedule, datetime, atexit
from selenium import webdriver
from crawler import ForumCrawler

class DriverBot:
    def __init__(self):

        #Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.fh = logging.FileHandler(os.getcwd() + '/cache/logs/debug.log', 'w+')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        self.formatter = logging.Formatter('[%(levelname)s :: (%(asctime)s)]: %(message)s')
        self.fh.setFormatter(self.formatter)
        self.ch.setFormatter(self.formatter)
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)

        #Configure webdriver
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                firefox_options=options, log_path=os.getcwd()+ '/cache/logs/geckodriver.log')
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

        #Import libraries for logging
        import socket, datetime
        self.logger.info('Beginning scan at {}'.format(socket.gethostname()))

        #Instantiate crawler
        crawler = ForumCrawler(self.webdriver, target='upwork')

        #Fetch crawler data
        data = crawler.crawl()
        
        #Cleanup cache
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        if len(filenames) > 100:
            dif = len(filenames) - 100
            for _ in range(dif):
                oldest_file = min(filenames, key=os.path.getctime)
                os.remove(os.path.abspath(oldest_file))
        
        #Log data
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(os.getcwd() + '/cache/logs/{}.json'.format(now), 'w') as f:
            f.write(data)
        self.logger.warning('Finished scan.')
   
    def close(self):
        #Cleans up webdriver processes and exits program
        self.webdriver.quit()
        sys.exit()

if __name__ == "__main__":
    #Run test functions
    d = DriverBot()
    try:
        d.run()
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    try:
        if '-s' in sys.argv:
            while True:
                schedule.run_pending()
    except:
        pass
    atexit.register(d.close())
    d.close()

