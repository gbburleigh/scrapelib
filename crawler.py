import sys, os, time, json, logging, schedule, datetime, traceback, inspect
from threadscraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException
from progress.spinner import Spinner

class ForumCrawler:
    def __init__(self, driver, target=None, genesis=None):
        #Inherit objects and instantiate scraper class
        self.driver = driver
        self.scraper = ThreadScraper(self.driver)
        self.logger = logging.getLogger(__name__)
        self.genesis = {}
        self.read_genesis()
        self.reached_genesis = False
        self.mode = target

        #Get targets
        if target is None:
            raise FileNotFoundError
        if target == 'upwork':
            self.targets = ['https://community.upwork.com/t5/forums/recentpostspage', \
                'https://community.upwork.com/t5/Announcements/bd-p/news', \
                'https://community.upwork.com/t5/Freelancers/bd-p/freelancers']

        for tar in self.targets:
            self.genesis[tar] = None

        self.logger.info('Crawler configured successfully')

    def crawl(self):
        """Main crawler function. For each specified target URL, fetches thread data
        and scrapes each URL sequentially. TODO: Add additional forums, processes"""
        
        #Init return pkg
        total = {}

        self.logger.info('Beginning crawl...')
        #Iterate through given category pages
        for target in self.targets:
            #Fetch page 
            self.driver.get(target)

            #Backend params
            time.sleep(3)
            start = datetime.datetime.now()

            #Get current page's data
            total[target] = self.parse_page(target)
            self.logger.debug('Completed crawl on {} in {}s'.format\
                (target, (datetime.datetime.now() - start).total_seconds()))
            
        return json.dumps(total, indent=4)

    def parse_page(self, tar):
        """Helper for parsing relevant links and metadata from thread listing page"""

        #Init subpackage
        print(f'PARSING {tar}')
        pkg = {}
        currentpage = 2
        self.driver.get(tar)
        time.sleep(3)

        #Parse pages
        try:
            #FIXME: GENESIS BLOCK PAGE CHECK self.get_page_numbers() + 1
            for currentpage in range(1, 4):
                if currentpage == 1:
                    pass
                else:
                    self.driver.get(self.generate_next(url, currentpage))
                    time.sleep(3)

                self.logger.info(f'Current category pagenum {currentpage}')
                #Get all thread links on current page
                urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")
                
                #Iterate through each thread
                for url in urls:
                    self.logger.info(f'Parsing link {url}')
                    #If we've reached genesis, we want to exit after parsing this page
                    if url == self.genesis[tar]:
                        self.reached_genesis = True

                    #Fetch page
                    self.driver.get(url)
                    time.sleep(3)

                    #Parse threads and send to subpackage
                    try:
                        pkg[url].update(self.scraper.make_soup(self.driver.page_source, url))
                    except KeyError:
                        pkg[url] = self.scraper.make_soup(self.driver.page_source, url)

                #We've hit the last post, let's exit    
                if self.reached_genesis is True:
                    return pkg
                
        except StaleElementReferenceException:
            pass

        except Exception as e:
            self.logger.warning(traceback.format_exc())

        return pkg

    def find_page(self, pagenum):
        """Helper for fetching next page (if available). This is shared between forum
        category pages, and thread pages."""

        try:

            li = self.driver.find_element_by_class_name('lia-paging-full-pages')

            if pagenum == 1:
                currentpage = li.find_element_by_class_name(f'lia-js-data-pageNum-{pagenum}')\
                    .find_element_by_tag_name("span").get_attribute('aria-label').replace('Page ', '')
            else:
                currentpage = li.driver.find_element_by_class_name(f'lia-js-data-pageNum-{pagenum}')\
                    .find_element_by_tag_name('span').get_attribute('aria-label').replace('Page ', '')
            nextpage = str(li.find_element_by_class_name(f'lia-js-data-pageNum-{pagenum+1}')\
                .find_element_by_tag_name('a').get_attribute('href'))

            return nextpage
        except Exception as e:
            self.logger.warning('Errored while finding next/current page')
            print(e)
            return None

    def generate_next(self, url, _iter):
        return url + f'/page/{_iter}'

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
            self.logger.warning(f'Current genesis post set at {self.genesis}')
            return self.genesis
        else:
            if self.mode == 'upwork':
                #If we don't have a genesis post, choose an arbitrary one
                self.driver.get(self.targets[0])
                url = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")[0]
                self.genesis = url
                self.logger.warning(f'Current genesis post set at {self.genesis}')
                return self.genesis

    def read_genesis(self):
        #Right now this is really inefficient. Should only be used at init time
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        filenames.remove('debug.log')
        oldest_file = str(min([datetime.datetime.strptime(x.strip('.json'), '%Y-%m-%d') for x in filenames]).date()) + '.json'
        
        try:
            with open(os.getcwd() + '/cache/logs/' + oldest_file, 'rb') as f:
                data = json.load(f)
                for url in data.keys():
                    li = []
                    for link, postdata in data[url].items():
                        li.append([postdata['pkg_creation_stamp'], link])

                    li = sorted(li, key=lambda x: x[0])
                    self.genesis[url] = li[0][1]

            self.logger.info(f'Got genesis URLS: {self.genesis}')
        except:
            pass

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

              