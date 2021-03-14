import sys, os, time, json, logging, traceback, inspect, uuid, hashlib, random
from bs4 import BeautifulSoup
from datetime import datetime
from header import *

class ThreadScraper:
    def __init__(self, driver, sitedb: SiteDB, debug=False):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.page = 0
        self.db = sitedb
        self.debug = debug

    def update_page(self, pagenum):
        self.page = pagenum

    def make_soup(self, html, url):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html.encode('utf-8'), 'html.parser')
        userlist = UserList([])
        postlist = PostList([])
        if len(self.db.pred.keys()) > 0:
            oldest_index = self.db.find_oldest_index(url)
        else:
            oldest_index = 0

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
        #contributors = {}
        pages = self.get_page_numbers()
        start = pages
        #seen = []
        if start > 25:
            end = start - 25
        else:
            end = 1
        #msg_cache = {}
        now = datetime.now()
        debugli = []
        post_total = str(10 * pages)
        try:
            op = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
        except:
            op = None

        if op is not None:
            for msg in op:
                try:
                    post_total = msg.find('span', class_='MessagesPositionInThread').text.split('of ')[1].replace('\n', '').replace(',', '')
                except:
                    post_total = str(10 * pages)
            

        for pagenum in range(start, end - 1, -1):
            self.logger.info(f'Currently on page {pagenum} of {url}')
            #print(f'Currently on page {pagenum} of {url}')
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
                author = op[0].find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
            except:
                author = ''
            try:
                unread = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
            except:
                unread = None
            try:
                solved = self.soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved')
            except:
                solved = None

            expired = False
            msgs = op + unread + solved
            idx = 0
            if self.debug is True:
                l = []
                for msg in msgs:
                    l.append(msg)
                l.remove(random.choice(l))
                msgs = l
            for msg in msgs:
                edit_status = 'Unedited'
                _url = 'https://community.upwork.com' + \
                    msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
                name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
                member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
                rank = msg.find('div', class_='lia-message-author-rank lia-component-author-rank lia-component-message-view-widget-author-rank')\
                    .text.replace(' ', '').strip()
                dateheader = msg.find('p', class_='lia-message-dates lia-message-post-date lia-component-post-date-last-edited lia-paging-page-link custom-lia-message-dates')
                timestamp = dateheader.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
                            .find('span', class_='message_post_text').text
                try:
                    e = dateheader.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')
                    for span in e.find_all('span', class_='message_post_text'):
                        if span.text != 'by':
                            editdate = span.text
                except:
                    editdate = ''
                try:
                    edited_by = dateheader.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                        .find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                            .find('a').find('span').text
                except:
                    edited_by = ''
                try:
                    edited_url = str(msg.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                        .find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                            .find('a').get_attribute('href'))
                except:
                    edited_url = ''

                if edited_url != '' and edited_by != '':
                    user_id = hashlib.md5((edited_by + edited_url).encode('utf-8')).hexdigest()[:16]
                else:
                    user_id = ''

                postdate = str(timestamp)
                try:
                    index = msg.find('span', class_='MessagesPositionInThread').find('a').text.replace('\n', '')
                except:
                    index = str((10 * pages) - idx)

                date_format = "%b %d, %Y %I:%M:%S %p"
                dt = datetime.strptime(postdate, date_format)
                now = datetime.now()
                if (now-dt).days > 7:
                    if oldest_index is not None:
                        if int(index) < oldest_index:
                            expired = True
                            #print(f'post is more than a week old, and were past our open index {oldest_index} at index {index}')
                            break
                    else:
                        expired = True
                        #print('post is a week old and we have no oldest index, continuing')
                        break
                
                body = msg.find('div', class_='lia-message-body-content').find_all(['p', 'ul'])
                post = ''
                for p in body:
                    if p.text == '&nbsp':
                        pass
                    if p.name == 'ul':
                        li = p.find_all('li')
                        for item in li:
                            post += item.text
                    else:
                        post += ('' + p.text + '').replace('\u00a0', '').replace('\n', '')
                
                #if name not in self.users.keys():
                u = User(name, member_since, _url, rank)
                userlist.handle_user(u)
                if post != '':
                    if editdate != '' and user_id != '':
                        p = Post(postdate, editdate + f'({user_id})', post, u, url, pagenum, index, url.split('/t5/')[1].split('/')[0])
                    else:
                        p = Post(postdate, editdate, post, u, url, pagenum, index, url.split('/t5/')[1].split('/')[0])
                    #print(f'Generated post: {p.__str__()}')
                    if user_id != '':
                        p.add_edited(u)
                    else:
                        p.add_edited(User('', '', '', ''))
                    postlist.add(p)
                idx += 1
            if expired is True:
                break
        return Thread(postlist, url, author, url.split('/t5/')[1].split('/')[0], \
            self.page, post_date, title, edit_date, userlist, post_total)

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