import sys, os, time, json, logging, datetime, traceback, inspect
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, driver, target=None):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.driver = driver
        self.logger = logging.getLogger(__name__)

    def make_soup(self, html, url):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html, 'html.parser')
        time.sleep(2)

        print(f'PARSING {url}')

        try:
            title = self.soup.find('h1', class_='lia-message-subject-banner lia-component-forums-widget-message-subject-banner')\
                .text.replace('\n\t', '').replace('\n', '').replace('\u00a0', '')
        except:
            self.logger.warning(traceback.format_exc())
        try:
            post_date = self.soup.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except:
            self.logger.warning(traceback.format_exc())
        try:
            edit_date = self.soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        contributors = {}
        messages = {}
        
        pages = self.get_page_numbers()

        edit_status = False
        for pagenum in range(1, pages + 1):
            if pagenum == 1:
                pass
            else:
                self.driver.get(self.generate_next(url, pagenum))
                time.sleep(3)
                self.soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            try:
                op = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic')
            except:
                op = None
            
            try:
                unread = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
            except:
                unread = None
            try:
                solved = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved')
            except:
                solved = None

            msgs = op + unread + solved
            for msg in msgs:
                _url = 'https://community.upwork.com' + \
                    msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
                name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
                member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
                contributors[name] = [_url, member_since]
                body = msg.find('div', class_='lia-message-body-content').find_all('p')
                post = ''
                for p in body:
                    if p.text == '&nbsp':
                        pass
                    else:
                        post += ('' + p.text + '').replace('\u00a0', '').replace('\n', '')

                    try:
                        edited = str(p.find('span').text)
                        if edited.find('**Edited for') != -1:
                            edit_status = True
                    except:
                        pass
                if name not in messages.keys():
                    messages[name] = post

        pkg = {}
        pkg['pkg_creation_stamp'] = str(datetime.datetime.now())
        pkg['title'] = title
        pkg['post_date'] = post_date
        pkg['edit_date'] = edit_date
        pkg['contributors'] = contributors
        pkg['messages'] = messages
        pkg['moderated'] = edit_status

        return pkg

    def generate_next(self, url, _iter):
        return url + f'/page/{_iter}'

    def get_page_numbers(self):
        menubar = self.soup.find('div', class_='lia-paging-full-wrapper lia-paging-pager lia-paging-full-left-position lia-component-menu-bar')
        if menubar is not None:
            last = menubar.find('li', class_='lia-paging-page-last')
            try:
                pages = int(last.find('a').text)
            except:
                pages = int(last.find('span').text)
        else:
            pages = 1

        return pages