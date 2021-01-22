import sys, os, time, json, logging, schedule, datetime
from threadscraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException

class ForumCrawler:
    def __init__(self, driver, target=None, genesis=None):
        #Inherit objects and instantiate scraper class
        self.driver = driver
        self.scraper = ThreadScraper()
        self.logger = logging.getLogger(__name__)
        self.genesis = genesis
        self.mode = target

        #Get targets
        if target is None:
            raise FileNotFoundError
        if target == 'upwork':
            self.targets = ['https://community.upwork.com/t5/forums/recentpostspage', \
                'https://community.upwork.com/t5/Announcements/bd-p/news', \
                'https://community.upwork.com/t5/Freelancers/bd-p/freelancers']

    def crawl(self):
        """Main crawler function. For each specified target URL, fetches thread data
        and scrapes each URL sequentially. TODO: Add additional forums, processes"""
        total = {}
        for target in self.targets:
            hist = []
            self.driver.get(target)
            time.sleep(3)
            start = datetime.datetime.now()
            links = self.driver.find_elements_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']")
            urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")
            self.logger.debug('Successfully obtained URLs on homepage')
            pkg = {}
            for url in urls:
                if self.genesis is None:
                    self.genesis = url
                try:
                    self.driver.get(url)
                    time.sleep(3)
                    pkg[url] = self.scraper.make_soup(self.driver.page_source, url)
                except StaleElementReferenceException:
                    pass
            self.logger.debug('Completed crawl on {} in {}s'.format\
                (target, (datetime.datetime.now() - start).total_seconds()))

            total[target] = pkg

        return json.dumps(total, indent=4)

    def get_links(self, tag):
        """Helper function for fetching links from page."""
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

    def return_genesis(self):
        if self.genesis is not None:
            #We've scanned already, and set a genesis block
            return self.genesis
        else:
            if self.mode == 'upwork':
                #If we don't have a genesis post, choose an arbitrary one
                self.driver.get(self.targets[0])
                links = self.driver.find_elements_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']")
                urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")[0]
              