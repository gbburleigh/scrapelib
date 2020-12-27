import sys, os, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from util import generate_xpath

class PostScraper:
    def __init__(self, url):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        #self.driver = webdriver.Chrome(ChromeDriverManager().install())
        self.page = self.driver.get(url)
        time.sleep(3)
        #try:
        self.thread_name = self.driver.find_elements_by_xpath("//h1[@class='lia-message-subject-banner lia-component-forums-widget-message-subject-banner']")[0].text
        print(self.thread_name)
        self.last_edited = self.driver.find_elements_by_xpath("//a[@class='lia-link-navigation lia-page-link lia-user-name-link user_name']//span")[0].text
        self.op = self.driver.find_elements_by_xpath("//a[@class='lia-link-navigation lia-page-link lia-user-name-link user_name']//span")[1].text
        self.op_details = self.driver.find_elements_by_xpath("//span[@class='custom-upwork-member-since']")[0].text
        print(self.op, self.op_details)
        # counter = 1
        # self.posters = {}
        # while True:
        #     try:
        #         p = self.op = self.driver.find_elements_by_xpath("//a[@class='lia-link-navigation lia-page-link lia-user-name-link user_name']//span")[counter].text
        #         if p not in self.posters.keys():
        #             self.posters[p] = self.driver.find_elements_by_xpath("//span[@class='custom-upwork-member-since']")[counter].text
        #         counter += 1
        #     except:
        #         break

        print(self.posters)

if __name__ == '__main__':
    url = 'https://community.upwork.com/t5/Freelancers/Possible-scam/td-p/848751'
    p = PostScraper(url)

        
