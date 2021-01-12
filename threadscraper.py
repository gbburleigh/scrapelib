import sys, os, time, json, logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, target=None):
        self.soup = None
        self.logger = logging.getLogger(__name__)

    def make_soup(self, html, url):
        self.soup = BeautifulSoup(html, 'html.parser')
        title = self.soup.find('h1', class_='lia-message-subject-banner lia-component-forums-widget-message-subject-banner').text
        self.logger.info('Successfully scraped url {}'.format(url))