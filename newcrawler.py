import sys, os, time, json, logging, schedule, datetime, traceback, inspect, csv
from newscraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException
from header import *

class Crawler:
    def __init__(self, driver, sitedb: SiteDB, debug=False, target='upwork', max_page_scroll=20):
        #Inherit objects and instantiate scraper class
        self.driver = driver
        self.max_page_scroll = max_page_scroll
        self.db = sitedb
        self.skipped = ['https://community.upwork.com/t5/Announcements/Welcome-to-the-Upwork-Community/td-p/1']
        if debug is True:
            self.scraper = ThreadScraper(self.driver, self.db, debug=True)
        else:
            self.scraper = ThreadScraper(self.driver, self.db)
        self.targets = ['https://community.upwork.com/t5/Freelancers/bd-p/freelancers',\
                        'https://community.upwork.com/t5/Announcements/bd-p/news',\
                        'https://community.upwork.com/t5/Clients/bd-p/clients', \
                        'https://community.upwork.com/t5/Agencies/bd-p/Agencies']

    def crawl(self):
        """Main crawler function. For each specified target URL, fetches thread data
        and scrapes each URL sequentially. TODO: Add additional forums, processes"""
        
        #Iterate through given category pages
        for target in self.targets:
            #Fetch page 
            self.driver.get(target)

            #Backend params
            time.sleep(3)
            start = datetime.datetime.now()

            category = self.parse_page(target)
            print(f'Created CATEGORY: {category.__str__()}')
            self.db.add(category)

        return self.db

    def parse_page(self, tar):

        self.driver.get(tar)
        time.sleep(2)
        
        threadli = []
        for currentpage in range(1, self.max_page_scroll):

            self.scraper.update_page(currentpage)
            if currentpage == 1:
                pass
            else:
                self.driver.get(self.generate_next(tar, currentpage))
                time.sleep(2)

            urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")

            for url in urls:
                if url in self.skipped:
                    continue
                self.driver.get(url)
                time.sleep(2)
                thread = self.scraper.make_soup(self.driver.page_source, url)
                print(f'Generated thread: {thread.__str__()}')
                threadli.append(thread)

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

