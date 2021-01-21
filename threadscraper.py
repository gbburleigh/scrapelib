import sys, os, time, json, logging
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, target=None):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.logger = logging.getLogger(__name__)

    def make_soup(self, html, url):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html, 'html.parser')
        title = self.soup.find('h1', class_='lia-message-subject-banner lia-component-forums-widget-message-subject-banner')\
            .text.replace('\n\t', '').replace('\n', '').replace('\u00a0', '')
        op = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic')
        unread = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
        solved = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved')
        msgs = op + unread + solved
        post_date = self.soup.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
            .find('span', class_='message_post_text').text
        try:
            edit_date = self.soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        contributors = {}
        messages = {}
        edit_status = False
        for msg in msgs:
            url = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
            name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
            member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
            contributors[name] = [url, member_since]
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
        pkg['title'] = title
        pkg['post_date'] = post_date
        pkg['edit_date'] = edit_date
        pkg['contributors'] = contributors
        pkg['messages'] = messages
        pkg['moderated'] = edit_status

        return pkg