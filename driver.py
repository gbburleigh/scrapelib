import doctest, sys, os, shutil, selenium, datetime
from scraper import ThreadScraper
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager

class ThreadPull:
    def __init__(self, category_url):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        self.category_url = category_url

    def pull(self):
        dt = datetime.datetime.now().replace(second=0, microsecond=0)
        start = datetime.datetime.now().replace(microsecond=0)
        _dir = os.path.dirname(__file__)
        url = self.category_url.replace('https://', '')
        path = os.path.join(_dir, f'cache/scraped_html/{url}')
        if not os.path.exists(path):
            os.makedirs(path)
        for elem in self.driver.find_element_by_xpath("//a[@class='page-link lia-link-navigation lia-custom-event']"):
            try:
                link = elem.get_attribute('href')
                self.driver.get(link)
                html = self.driver.page_source
                new_path = os.path.join(path, elem.text)
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                with open(os.path.join(new_path, f'{dt}.html'), 'wb') as fp:
                    fp.write(html)
            except:
                pass
        end = datetime.datetime.now().replace(microsecond=0)
        print(f'Pulled all files in {end-start} seconds')

if __name__ == "__main__":
    # url = 'https://community.upwork.com/t5/Freelancers/Possible-scam/td-p/848751'
    bot = ThreadPull('https://community.upwork.com/t5/Freelancers/bd-p/freelancers')
    bot.pull()
    # scraper = ThreadScraper('tags.json', url)
    doctest.testmod()

