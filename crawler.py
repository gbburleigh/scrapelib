import sys, os, time, json, logging, schedule, traceback, inspect, csv
from scraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import InvalidSessionIdException
from header import *
from datetime import datetime
from selenium import webdriver
from progress.bar import Bar
from progress.spinner import Spinner

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
    def __init__(self, driver, sitedb: SiteDB, debug=False, target='upwork', max_page_scroll=5):
        self.driver = driver
        self.max_page_scroll = max_page_scroll
        self.db = sitedb
        self.skipped = ['https://community.upwork.com/t5/Announcements/Welcome-to-the-Upwork-Community/td-p/1',\
                        'https://community.upwork.com/t5/Announcements/Upwork-Community-Guidelines']
        if debug is True:
            self.scraper = ThreadScraper(self.driver, self.db, debug=True)
        else:
            self.scraper = ThreadScraper(self.driver, self.db)
        self.targets = ['https://community.upwork.com/t5/Announcements/bd-p/news', \
                        'https://community.upwork.com/t5/Freelancers/bd-p/freelancers', \
                       'https://community.upwork.com/t5/Clients/bd-p/clients', \
                       'https://community.upwork.com/t5/Agencies/bd-p/Agencies']

    def crawl(self):
        """
        Main crawling wrapper function. Uses crawler.parse_page to parse category listings, and compiles
        them into the DB. Also checks for remaining threads from previous scans that should be checked, and
        handles deletion checks for entire threads/privilege errors.
        """

        iter_ = 0        
        now = datetime.now()
        self.db.set_start(now)
        for target in self.targets:
            if iter_ > 0:
                self.regenerate_driver()
                time.sleep(2)
            self.driver.get(target)

            start = datetime.now()

            category = self.parse_page(target)
            print(f'\nCreated CATEGORY: {category.__str__()}')
            #threads = self.db.get_remaining(category)
            threads = []
            if category.name in self.db.pred.keys():
                for url, thread in self.db.pred[category.name].threads.items():
                    if url not in category.threads.keys():
                        threads.append(url)
            
            
            if len(threads) > 0 and self.max_page_scroll > 1:
                with Bar(f'Finishing remaining threads in category {category.name}', max=len(threads)) as bar:
                    for url in threads:
                        self.driver.get(url)
                        time.sleep(1)
                        try:
                            thread = self.scraper.make_soup(self.driver.page_source, url, category.name)
                        except AttributeError:
                            if category.name in self.db.stats.deleted_threads.keys():
                                self.db.stats.deleted_threads[category.name].append(url)
                            else:
                                self.db.stats.deleted_threads[category.name] = [url]
                        category.add(thread)
                        bar.next()
            iter_ += 1
            self.db.add(category)

        return self.db

    def parse_page(self, tar):
        """
        Main parsing function for getting URLs and thread objects from category page. Interfaces with
        scraper object to iterate through possible threads and scrape all data from them. Checks for
        different stats such as deleted threads. Utilizes crawler.get_links to pull links on page
        """
        self.driver.get(tar)
        threadli = []
        bar_count = 30 * self.max_page_scroll
        if tar.split('/t5/')[1].split('/')[0] == 'Freelancers':
            bar_count += 1
        elif tar.split('/t5/')[1].split('/')[0] == 'Announcements':
            bar_count += 2
        try:
            with Bar(f"Parsing {tar.split('/t5/')[1].split('/')[0]}", max=bar_count) as bar:
                for currentpage in range(1, self.max_page_scroll + 1):
                    if currentpage == 1:
                        self.driver.get(tar)
                    else:
                        self.driver.get(self.generate_next(tar, currentpage))
                    self.scraper.update_page(currentpage)
                    urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")
                    for url in urls:
                        if url in self.skipped:
                            continue
                        self.driver.get(url)
                        thread = None
                        try:
                            thread = self.scraper.make_soup(self.driver.page_source, url, tar.split('/t5/')[1].split('/')[0])
                        except AttributeError:
                            if tar.split('/t5/')[1].split('/')[0] in self.db.stats.deleted_threads.keys():
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]].append(url)
                            else:
                                self.db.stats.deleted_threads[tar.split('/t5/')[1].split('/')[0]] = [url]
                        except Exception as e:
                            print(e)
                        if thread is not None and thread.post_count != 0:
                            threadli.append(thread)
                        bar.next()
        except Exception as e:
            print(e)

        return Category(threadli, tar.split('/t5/')[1].split('/')[0])

    def generate_next(self, url, _iter):
        """
        Helper function for generating next page url

        <--Args-->
        url(str): url to format
        _iter(int): current page to format
        """
        return url + f'/page/{_iter}'

    def regenerate_driver(self):
        """
        Regenerates the webdriver using the specified parameters. Same logic used as 
        Driver constructor.
        """
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

    def get_links(self, tag):
        """
        Pull links on category page under given tag. NOTE: This is the only parsing function that
        directly uses selenium rather than BS4, consider fixing.

        <--Args-->
        tag(str): xpath tag to search for URLs from
        """
        hist = []
        urls = []
        for elem in self.driver.find_elements_by_xpath(tag):
            try:
                res = str(elem.get_attribute('href'))
                if res not in hist:
                    hist.append(res)
                    urls.append(res)
                else:
                    continue
            except StaleElementReferenceException:
                pass

        return urls

    def get_page_numbers(self):
        """
        Helper for finding number of pages in a category listing. NOTE: This is defunct.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        menubar = soup.find('div', class_='lia-paging-full-wrapper lia-paging-pager lia-paging-full-left-position lia-component-menu-bar')
        if menubar is not None:
            last = menubar.find('li', class_='lia-paging-page-last')
            try:
                pages = int(last.find('a').text)
            except:
                pages = int(last.find('span').text)
        else:
            pages = 1

        return pages

