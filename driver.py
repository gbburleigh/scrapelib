import time, json, csv, sys, os
from selenium import webdriver
from crawler import Crawler
from header import *
from datetime import datetime
from selenium.common.exceptions import InvalidSessionIdException

class Driver:
    """
    Main driver object for running script from. Instantiates crawler and scraper objects to handle
    all data collection, and interfaces with db.load and db.write to handle all caching. Comparisons
    are done via lower level objects, and handles opening and closing processes associated with webdriver.
    """
    def __init__(self, flush=False, start=None):
        self.db = SiteDB([], 'upwork')
        self.driver_type = '' 
        #Generate webdriver object depending on argument given at runtime. Always runs in headless
        #mode with disabled GPU
        if '-p' not in sys.argv:
            if '-f' in sys.argv:
                from selenium.webdriver.firefox.options import Options
                from webdriver_manager import firefox
                from webdriver_manager.firefox import GeckoDriverManager
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                firefox_options=options)
                self.driver_type = 'firefox_wdm'
            elif '-c' in sys.argv:
                import chromedriver_binary
                from selenium.webdriver.chrome.options import Options
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                self.webdriver = webdriver.Chrome(options=options)
                self.driver_type = 'chrome_binary'
            else:
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager import chrome
                from webdriver_manager.chrome import ChromeDriverManager
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                self.driver_type = 'chrome_wdm'
        else:
            self.webdriver = None
        self.crawler = self.generate_crawler()
        
    def run(self):
        """
        Main run function. Creates an old db to load data into and to compare new db with. Creates
        db through crawler.crawl and handles writing.
        """

        #Load old cache
        if '-r' not in sys.argv:
            old_db = SiteDB([], 'upwork')
            old_db.load()

            #Set it to current DBs old cache
            self.db.pred = old_db.cache

        #Generate crawler object
        
        crawler = self.generate_crawler()

        #Generate DB for latest scan
        if '-full' not in sys.argv:
            self.db = crawler.crawl()
        else:
            _ = crawler.crawl()

        if '-r' not in sys.argv:
            #Get deleted info
            _ = self.db.compare(old_db)

        targets = ['https://community.upwork.com/t5/Announcements/bd-p/news', \
        'https://community.upwork.com/t5/Freelancers/bd-p/freelancers', \
        'https://community.upwork.com/t5/Clients/bd-p/clients', \
        'https://community.upwork.com/t5/Agencies/bd-p/Agencies']
        target = None
        for tar in targets:
            if tar in sys.argv:
                target = tar

        #Write result
        #self.db.write(target_name=target)

    def generate_crawler(self):
        """
        Convenience method for creating Crawler objects in driver.run
        """
        
        targets = ['https://community.upwork.com/t5/Announcements/bd-p/news', \
        'https://community.upwork.com/t5/Freelancers/bd-p/freelancers', \
        'https://community.upwork.com/t5/Clients/bd-p/clients', \
        'https://community.upwork.com/t5/Agencies/bd-p/Agencies']
        target = None
        for tar in targets:
            if tar in sys.argv:
                target = tar

        #Regenerate crawler object depending on params
        if target is None:
            if '-d' in sys.argv:
                crawler = Crawler(self.webdriver, self.db, debug=True)
            else:
                crawler = Crawler(self.webdriver, self.db)
        else:
            if '-d' in sys.argv:
                crawler = Crawler(self.webdriver, self.db, debug=True, link=target)
            else:
                crawler = Crawler(self.webdriver, self.db, link=target)

        return crawler

    def close(self):
        """
        Close all processes associated with program and webdriver. Also uses pkill as a sanity
        check if chrome process is running.
        """

        #Kill all zombie PIDs and exit gracefully
        try:
            self.webdriver.quit()
        except:
            pass
        if 'p' not in sys.argv:
            self.kill()
        sys.exit()

    def kill(self):
        """ 
        Wrapper for killing zombie processes after webdriver should have exited gracefully
        Running this without root privileges should only remove the PIDs associated w/ user
        """

        #Kill relevant process names
        if self.driver_type != 'firefox_wdm':
            os.system('pkill -f chrome')
            os.system('pkill -f Chrome')
            os.system('pkill -f chromedriver')
        else:
            os.system('pkill -f FireFox')
            #TODO: confirm this -> os.system('pkill -f geckodriver')

    def restart(self):
        """
        Convenience method in case of random errors (busy ports, webdriver crashes, etc.)
        Regenerates webdriver object and restarts scan
        """

        #Kill processes
        print('Restarting scan...... \n')
        self.kill()

        #Delete crawler
        del self.crawler
        self.crawler = self.generate_crawler()

        #Give ourselves a second
        time.sleep(2)

    def scan(self):
        """
        Main wrapper for running entire scan. Handles restarting and running through methods defined above.
        Lower level exceptions aside from major crashes are handled at object level.
        """

        from urllib3.exceptions import MaxRetryError, NewConnectionError
        #While we haven't successfully run
        while True:
            try:
                #Try to run
                self.run()
                break
            except:
                #Otherwise restart
                sys.exit()
                #self.restart()
                time.sleep(10)

if __name__ == "__main__":
    now = datetime.now()
    d = Driver(start=now)
    d.run()
    #try:
    #    d.scan()
    #except KeyboardInterrupt:
        #d.close()
        #os.system('deactivate')
    #    pass
    d.close()

