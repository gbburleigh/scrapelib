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
                        #'https://community.upwork.com/t5/Announcements/bd-p/news',\
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

            #Get current page's data
            category = self.parse_page(target)
            print(f'Created CATEGORY: {category.__str__()}')
            self.db.add(category)

        #total['timestamp'] = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            
        return self.db

    def parse_page(self, tar):
        """Helper for parsing relevant links and metadata from thread listing page"""

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
        

