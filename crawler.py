import sys, os, time, json, logging, schedule, datetime, traceback, inspect, csv
from threadscraper import ThreadScraper
from selenium.common.exceptions import StaleElementReferenceException

class Crawler:
    def __init__(self, driver, hist, target=None, genesis=None,\
                max_page_scroll=15, debug=False):
        #Inherit objects and instantiate scraper class
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.genesis = {}
        self.max_page_scroll = max_page_scroll
        # self.genesis['https://community.upwork.com/t5/Freelancers/bd-p/freelancers']\
        #      = 'https://community.upwork.com/t5/Freelancers/Withdrawal-Invoice/td-p/870565'
        self.genesis = genesis
        self.hist = hist
        self.reached_genesis = False
        self.stats = {}
        self.stats['deletions'] = 0
        self.stats['modifications'] = 0
        self.stats['user_mods'] = {}
        self.stats['user_deletes'] = {}
        self.skipped = ['https://community.upwork.com/t5/Announcements/Welcome-to-the-Upwork-Community/td-p/1']
        self.scraper = ThreadScraper(self.driver, self.hist, debug=debug)
        print(f'Debug mode ={debug}')

        #Get targets
        if target is None and '-f' not in sys.argv:
            raise FileNotFoundError
        if target == 'upwork':
            self.targets = ['https://community.upwork.com/t5/Freelancers/bd-p/freelancers',\
                            #'https://community.upwork.com/t5/Announcements/bd-p/news',\
                            'https://community.upwork.com/t5/Clients/bd-p/clients', \
                            'https://community.upwork.com/t5/Agencies/bd-p/Agencies']

        # if '-f' not in sys.argv:
        #     for tar in self.targets:
        #         self.genesis[tar] = None

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

        total['timestamp'] = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            
        return json.dumps(total, indent=4)

    def parse_page(self, tar):
        """Helper for parsing relevant links and metadata from thread listing page"""

        #Init subpackage
        pkg = {}
        self.driver.get(tar)
        time.sleep(3)

        #Parse pages
        #FIXME: GENESIS BLOCK PAGE CHECK self.get_page_numbers() + 1
        pages = self.get_page_numbers() + 1
        for currentpage in range(1, self.max_page_scroll):
            if currentpage == 1:
                pass
            else:
                self.driver.get(self.generate_next(tar, currentpage))
                time.sleep(3)

            self.logger.info(f'Current category pagenum {currentpage}')
            #Get all thread links on current page
            urls = self.get_links("//a[@class='page-link lia-link-navigation lia-custom-event']")
            
            #Iterate through each thread
            for url in urls:
                if url in self.skipped:
                    continue
                self.logger.info(f'Parsing link {url}')
                #If we've reached genesis, we want to exit after parsing this page
                if self.genesis is not None:
                    try:
                        if url == self.genesis[tar]:
                            self.reached_genesis = True
                    except KeyError:
                        pass

                #Fetch page
                self.driver.get(url)
                time.sleep(2)
                self.scraper.update_stats(self.stats)
                res = self.scraper.make_soup(self.driver.page_source, url, tar)
                if res is not None:
                    self.stats['deletions'] = self.scraper.stats['deletions']
                    self.stats['modifications'] = self.scraper.stats['modifications']
                    try:
                        self.stats['user_mods'].update(self.scraper.stats['user_mods'])
                    except:
                        print('error updating user modification entries')
                    try:
                        self.stats['user_deletes'].update(self.scraper.stats['user_deletes'])
                    except:
                        print('error updating user delete entries')
                    #if res is not None:
                        #Parse threads and send to subpackage
                    try:
                        pkg[url].update(res)

                    except KeyError:
                        pkg[url] = res
                else:
                    self.logger.critical(f'Something went wrong while parsing url {url}')

            #We've hit the last post, let's exit    
            # if self.reached_genesis is True:
            #     return pkg

        return pkg

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

if __name__ == '__main__':
    # from selenium import webdriver
    # from selenium.webdriver.chrome.options import Options
    # from webdriver_manager import chrome
    # from webdriver_manager.chrome import ChromeDriverManager
    # options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    # c = Crawler(driver)
    # targets = ['https://community.upwork.com/t5/Announcements/Insight-on-how-Job-Success-Score-is-calculated/m-p/87248',\
    #             'https://community.upwork.com/t5/Announcements/Replacing-5-Star-Average-Feedback-with-Job-Success-Score/m-p/106120']

    # pkg = {}
    # for target in targets:
    #     driver.get(target)
    #     time.sleep(3)
    #     try:
    #         pkg[target].update(c.scraper.make_soup(c.driver.page_source, target, tar='HATIM'))
    #     except KeyError:
    #         pkg[target] = c.scraper.make_soup(c.driver.page_source, target, tar='HATIM')

    # total = {}
    # total['HATIM'] = pkg
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    # with open(os.getcwd() + '/cache/hatim_logs/{}_HATIM.json'.format(now), 'w') as f:
    #     f.write(json.dumps(total, indent=4))

    with open(os.getcwd() + '/cache/hatim_logs/{}_HATIM.json'.format(now), 'r') as f:
        data = json.loads(f.read())['HATIM']

    with open(os.getcwd() + f'/cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
        f = csv.writer(f)
        f.writerow(["thread_url" , "title", "post_date", "edit_date", "contributor_id", \
                    "contributor_rank", "message_text", "post_version", "post_datetime", \
                    "post_moderation"])

        users = {}

        for thread_url in data:
            if data[thread_url]['update_version'] > 1:
                #TODO: MAKE A TEXT DIFF HERE AND APPEND IT
                pass                
                
            for name in data[thread_url]['contributors']:
                users[name] = data[thread_url]['contributors'][name]

            for key in data[thread_url]['messages']:
                for v in data[thread_url]['messages'][key]:
                    for message in data[thread_url]['messages'][key][v]:
                        try:
                            edited = message[2]
                        except:
                            edited = 'Unedited'

                        for entry in users:
                            if users[entry]['user_id'] == key:
                                rank = users[entry]['rank']

                        f.writerow([thread_url, data[thread_url]['title'],\
                        data[thread_url]['post_date'], \
                        data[thread_url]['edit_date'], \
                        key, rank, message[1], v, \
                        message[0], edited])

    with open (os.getcwd() + f'/cache/csv/userdb/users_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
        f = csv.writer(f)
        f.writerow(["user_name", "user_id", "user_url", "user_join_date", "user_rank"])

        for name in users:
            f.writerow([name, users[name]['user_id'], users[name]['user_url'], users[name]['member_since'], users[name]['rank']])
        

