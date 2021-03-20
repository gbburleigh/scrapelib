import sys, os, time, json, logging, schedule, traceback, inspect, csv
from newscraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import InvalidSessionIdException
from header import *
from datetime import datetime
from progress.bar import Bar
from progress.spinner import PieSpinner

class Crawler:
    def __init__(self, driver, sitedb: SiteDB, debug=False, target='upwork', max_page_scroll=5):
        #Inherit objects and instantiate scraper class
        self.driver = driver
        self.max_page_scroll = max_page_scroll
        self.db = sitedb
        self.skipped = ['https://community.upwork.com/t5/Announcements/Welcome-to-the-Upwork-Community/td-p/1']
        if debug is True:
            self.scraper = ThreadScraper(self.driver, self.db, debug=True)
        else:
            self.scraper = ThreadScraper(self.driver, self.db)
        self.targets = ['https://community.upwork.com/t5/Freelancers/bd-p/freelancers', \
                        'https://community.upwork.com/t5/Announcements/bd-p/news',\
                       'https://community.upwork.com/t5/Clients/bd-p/clients', \
                       'https://community.upwork.com/t5/Agencies/bd-p/Agencies']

    def crawl(self):
        """Main crawler function. For each specified target URL, fetches thread data
        and scrapes each URL sequentially. TODO: Add additional forums, processes"""
        
        #Iterate through given category pages
        # bar_count = len(self.targets) * 30 * self.max_page_scroll
        # for tar in self.targets:
        #     if tar.split('/t5/')[1].split('/')[0] == 'Freelancers':
        #         bar_count += 1
        #     elif tar.split('/t5/')[1].split('/')[0] == 'Announcements':
        #         bar_count += 2
        #with Bar(f'Crawling...', max = bar_count) as bar:
        now = datetime.now()
        self.db.set_start(now)
        for target in self.targets:
            #Fetch page 

            self.driver.get(target)

            start = datetime.now()

            category = self.parse_page(target)
            print(f'\nCreated CATEGORY: {category.__str__()}')
            threads = self.db.get_remaining(category)
            li = []
            for url, thread in self.db.pred[category.name].threads.items():
                if url not in category.threads.keys():
                    threads.append(url)
            
            spinner = PieSpinner(f'Finishing category {category.name}')
            if len(threads) > 0:
                for url in threads:
                    self.driver.get(url)
                    thread = self.scraper.make_soup(self.driver.page_source, url, category.name)
                    category.add(thread)
                    spinner.next()

            self.db.add(category)

        return self.db

    def parse_page(self, tar):

        self.driver.get(tar)
        
        threadli = []
        bar_count = 30 * self.max_page_scroll
        if tar.split('/t5/')[1].split('/')[0] == 'Freelancers':
            bar_count += 1
        elif tar.split('/t5/')[1].split('/')[0] == 'Announcements':
            bar_count += 2
        with Bar(f"Parsing category {tar.split('/t5/')[1].split('/')[0]}", max=bar_count) as bar:
            for currentpage in range(1, self.max_page_scroll + 1):

                self.scraper.update_page(currentpage)
                if currentpage == 1:
                    pass
                else:
                    self.driver.get(self.generate_next(tar, currentpage))

                urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")

                for url in urls:
                    if url in self.skipped:
                        continue
                    self.driver.get(url)
                    thread = None
                    thread = self.scraper.make_soup(self.driver.page_source, url, tar.split('/t5/')[1].split('/')[0])
                    if thread is not None and thread.post_count != 0:
                        threadli.append(thread)
                    bar.next()

        return Category(threadli, tar.split('/t5/')[1].split('/')[0])

    def generate_next(self, url, _iter):
        return url + f'/page/{_iter}'

    def get_links(self, tag):
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

