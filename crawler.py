import sys, os, time, json, logging, schedule, traceback, inspect, csv
from scraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import InvalidSessionIdException
from header import *
from datetime import datetime
from bs4 import BeautifulSoup, element
from selenium import webdriver
from dbmanager import DBConn
from progress.bar import Bar
import requests

class Crawler:
    """
    Crawler object serves as intermediary between Driver object interfaced by user and threadscraper 
    object used to pull thread data. Responsible for parsing URLs from category thread listings and compiling
    them into Category objects. Holds all scraping functionality along with scraper.

    <--Args-->
    driver(WebDriver): webdriver object created by driver. Note this can be regenerated using crawler.regenerate_driver()
    sitedb(SiteDB): parent db to save info to

    <--Attributes-->
    max_page_scroll(int): max number of pages to pull threads from
    skipped(list(str)): URLs to skip parsing for
    targets(list(str)): category URLs to scrape form
    """
    def __init__(self, driver, sitedb: SiteDB, debug=False, target='upwork', max_page_scroll=1, link=None):
        #Inherited driver object
        self.driver = driver

        #Default max page scroll
        if '-full' not in sys.argv:
            self.max_page_scroll = max_page_scroll
        else:
            self.max_page_scroll = 0

        #Inherited sitedb object
        self.db = sitedb

        #Skipped URLs
        self.skipped = ['https://community.upwork.com/t5/Announcements/Welcome-to-the-Upwork-Community/td-p/1',\
                        'https://community.upwork.com/t5/Announcements/Upwork-Community-Guidelines/td-p/3']
        
        #Generate scraper object
        if debug is True:
            self.scraper = ThreadScraper(self.driver, self.db, debug=True)
        else:
            self.scraper = ThreadScraper(self.driver, self.db)
        
        #Category URLs to parse
        if link is None:
            self.targets = ['https://community.upwork.com/t5/Announcements/bd-p/news', \
                            'https://community.upwork.com/t5/Freelancers/bd-p/freelancers', \
                        'https://community.upwork.com/t5/Clients/bd-p/clients', \
                        'https://community.upwork.com/t5/Agencies/bd-p/Agencies']
        else:
            self.targets=[link]

    def crawl(self):
        """
        Main crawling wrapper function. Uses crawler.parse_page to parse category listings, and compiles
        them into the DB. Also checks for remaining threads from previous scans that should be checked, and
        handles deletion checks for entire threads/privilege errors.
        """

        #Iteration tracker for checking when to regenerate driver
        iter_ = 0        

        #Set DB scan start
        now = datetime.now()
        self.db.set_start(now)
        failures = []
        status = {}
        with open(os.getcwd() + '/scan-status.txt', 'r') as f:
            for line in f.readlines():
                category = line.split(' ')[0]
                pagenum = line.split(' ')[1]
                try:
                    pagenum.replace('\n', '')
                except:
                    pass
                status[category] = pagenum
            
        #Iterate through targets
        for target in self.targets:
            if status[target.split('/t5/')[1].split('/')[0]] == 'DONE':
                continue
            if iter_ > 0:
                #Regenerate driver if necessary
                if '-p' not in sys.argv:
                    print('Regenerating driver...... \n')
                    self.regenerate_driver()
            #        time.sleep(2)

            #time.sleep(2)

            #Generate a category object from target URL
            category = self.parse_page(target, iter_ + 1)

            #If something went wrong with creating the object, throw relevant exception to 
            #trigger restart
            if len(category.threadlist) == 0:
                raise DBError
            print(f'\nCreated CATEGORY: {category.__str__()}')

            #Get threads remaining from old cache
            threads = []
            if category.name in self.db.pred.keys():
                for url, thread in self.db.pred[category.name].threads.items():
                    if url not in category.threads.keys():
                        threads.append(url)
            
            #Go through remaining threads and add parsed objects to category object
            if len(threads) > 0:
                with Bar(f'Finishing remaining threads in category {category.name}', max=len(threads)) as bar:
                    for url in threads:
                        thread = None
                        if '-p' not in sys.argv:
                            self.driver.get(url)
                            #Attempt to parse thread page
                            try:
                                thread = self.scraper.parse(self.driver.page_source, url, target.split('/t5/')[1].split('/')[0], iter_)
                            #This indicates a thread has been made inaccessible, add it to deleted threads
                            except AttributeError:
                                if target.split('/t5/')[1].split('/')[0] in self.db.stats.deleted_threads.keys():
                                    self.db.stats.deleted_threads[target.split('/t5/')[1].split('/')[0]].append(url)
                                else:
                                    self.db.stats.deleted_threads[target.split('/t5/')[1].split('/')[0]] = [url]
                        else:
                            r = requests.get(url)
                            try:
                                thread = self.scraper.parse(r.text, url, target.split('/t5/')[1].split('/')[0], iter_)
                            #This indicates a thread has been made inaccessible, add it to deleted threads
                            except AttributeError:
                                if target.split('/t5/')[1].split('/')[0] in self.db.stats.deleted_threads.keys():
                                    self.db.stats.deleted_threads[target.split('/t5/')[1].split('/')[0]].append(url)
                                else:
                                    self.db.stats.deleted_threads[target.split('/t5/')[1].split('/')[0]] = [url]
                        #time.sleep(2)
                        category.add(thread)
                        bar.next()
            iter_ += 1
        if '-full' not in sys.argv:
            self.db.add(category)
            for elem in failures:
                if elem not in self.db.stats.failures:
                    self.db.stats.failures.append(elem)
            return self.db
        else:
            return

    def parse_page(self, tar, iter_):
        """
        Main parsing function for getting URLs and thread objects from category page. Interfaces with
        scraper object to iterate through possible threads and scrape all data from them. Checks for
        different stats such as deleted threads. Utilizes crawler.get_links to pull links on page
        """

        #Get the target page
        if '-p' not in sys.argv:
            self.driver.get(tar)
            if '-full' in sys.argv:
                self.max_page_scroll = self.get_page_numbers(self.driver.page_source.encode('utf-8').strip())
        else:
            r = requests.get(tar)
            if '-full' in sys.argv:
                self.max_page_scroll = self.get_page_numbers(r.text)

        #Instantiate thread list 
        threadli = []

        #Get progress bar count
        bar_count = 30 * self.max_page_scroll
        if tar.split('/t5/')[1].split('/')[0] == 'Freelancers':
            bar_count += 1
        elif tar.split('/t5/')[1].split('/')[0] == 'Announcements':
            bar_count += 2

        #Progress bar context manager
        with Bar(f"Parsing {tar.split('/t5/')[1].split('/')[0]}", max=bar_count) as bar:
            #Iterate through each page in range
            cache = []
            status = {}
            with open(os.getcwd() + '/scan-status.txt', 'r') as f:
                for line in f.readlines():
                    category = line.split(' ')[0]
                    pagenum = line.split(' ')[1]
                    try:
                        pagenum.replace('\n', '')
                    except:
                        pass
                    status[category] = pagenum
            for currentpage in range(int(status[tar.split('/t5/')[1].split('/')[0]]), self.max_page_scroll + 1):
                #Get correct page
                if '-p' not in sys.argv:
                    if currentpage == 1:
                        self.driver.get(tar)
                    else:
                        self.driver.get(self.generate_next(tar, currentpage))
                    soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')
                else:
                    if currentpage == 1:
                        r = requests.get(tar)
                    else:
                        r = requests.get(self.generate_next(tar, currentpage))
                    soup = BeautifulSoup(r.text, 'lxml')
                #time.sleep(2)

                #Update scraper pagenumber
                self.scraper.update_page(currentpage)

                #Fetch all URLs on category page
                urls = self.get_links(soup)
                #Iterate through URLs we found
                for url in urls:
                    if url in self.skipped:
                        continue
                    thread = None
                    if '-p' not in sys.argv:
                        self.driver.get(url)
                        #Attempt to parse thread page
                        try:
                            thread = self.scraper.parse(self.driver.page_source, url, tar.split('/t5/')[1].split('/')[0], iter_)
                        #This indicates a thread has been made inaccessible, add it to deleted threads
                        except AttributeError:
                            if tar.split('/t5/')[1].split('/')[0] in self.db.stats.deleted_threads.keys():
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]].append(url)
                            else:
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]] = [url]
                    else:
                        r = requests.get(url)
                        try:
                            thread = self.scraper.parse(r.text, url, tar.split('/t5/')[1].split('/')[0], iter_)
                        #This indicates a thread has been made inaccessible, add it to deleted threads
                        except AttributeError:
                            if tar.split('/t5/')[1].split('/')[0] in self.db.stats.deleted_threads.keys():
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]].append(url)
                            else:
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]] = [url]
                    #time.sleep(2)
                    if thread is not None and thread.post_count != 0:
                        cache.append(thread)
                        threadli.append(thread)
                        with DBConn() as conn:
                            conn.insert_from_thread(thread, iter_)
                        #print(thread.__str__())
                    bar.next()
                if '-full' in sys.argv:
                    if currentpage % 10 == 0 or currentpage == self.max_page_scroll:
                        self.db.write_segment(cache, tar.split('/t5/')[1].split('/')[0], f'{currentpage-10}-{currentpage}')
                        cache = []
                else:
                    if currentpage % 1 == 0 or currentpage == self.max_page_scroll:
                        self.db.write_segment(cache, tar.split('/t5/')[1].split('/')[0], f'{currentpage-1}-{currentpage}')
                        cache = []
                
        c = Category(threadli, tar.split('/t5/')[1].split('/')[0], iter_, self.max_page_scroll)
        with DBConn() as conn:
            conn.insert_from_category(c)
        #Create and return category object
        return c

    def generate_next(self, url, _iter):
        """
        Helper function for generating next page url

        <--Args-->
        url(str): url to format
        _iter(int): current page to format
        """

        #Format the URL with page and pagenumber appended
        return url + f'/page/{_iter}'

    def regenerate_driver(self):
        """
        Regenerates the webdriver using the specified parameters. Same logic used as 
        Driver constructor.
        """

        #Generate webdriver object depending on argument given at runtime. Always runs in headless
        #mode with disabled GPU
        if '-f' in sys.argv:
            print('Regenerating FireFox driver...')
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
            firefox_options=options)
        elif '-c' in sys.argv:
            print('Regenerating ChromeDriver binary...')
            import chromedriver_binary
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.driver = webdriver.Chrome(options=options)
        else:
            print('Regenerating normal ChromeDriver through WDM')
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager import chrome
            from webdriver_manager.chrome import ChromeDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    def get_links(self, soup):
        """
        Pull links on category page under given tag. NOTE: This is the only parsing function that
        directly uses selenium rather than BS4, consider fixing.

        <--Args-->
        tag(str): xpath tag to search for URLs from
        """
        hist = []
        urls = []

        #Parse all available links with tag given as arg
        for elem in soup.find_all('a', class_='page-link lia-link-navigation lia-custom-event', href=True):
            res = 'https://community.upwork.com/' + str(elem['href'])
            if res not in hist:
                hist.append(res)
                urls.append(res)
            else:
                continue

        return urls

    def get_page_numbers(self, html):
        """
        Helper for finding number of pages in a category listing. NOTE: This is defunct.
        """
        from bs4 import BeautifulSoup

        #Create soup object 
        soup = BeautifulSoup(html, 'html.parser')
       
        #Parse out menu container
        menubar = soup.find('div', class_='lia-menu-bar lia-menu-bar-top lia-component-menu-bar')
        if menubar is not None:
            #Try to find last page number
            last = menubar.find('li', class_='lia-paging-page-last')
            try:
                pages = int(last.find('a').text)
            except:
                pages = int(last.find('span').text)
        else:
            pages = 1

        return pages

