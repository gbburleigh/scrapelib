import sys, os, time, json, hashlib, random
from bs4 import BeautifulSoup
from datetime import datetime
from header import *
import validators

class ThreadScraper:
    """
    Main scraper object used to parse data from individual threads. Handles page scrolling,
    object instantiation at lowest level, and generates Thread objects via make_soup.

    <--Args-->
    driver(WebDriver): webdriver to use for getting additional pages
    sitedb(SiteDB): parent db handler
    """
    def __init__(self, driver, sitedb: SiteDB, debug=False):
        self.driver = driver
        self.page = 0
        self.db = sitedb
        self.debug = debug

    def update_page(self, pagenum):
        """
        Convenience method for updating the category page we're scraping from

        <--Args-->
        pagenum(int): pagenum to set as current page
        """
        self.page = pagenum

    def make_soup(self, html, url, categ):
        """
        Main data collection and serialization function. Creates BeautifulSoup object and 
        collects relevant information, if available. Updates self.db.stats as needed and creates
        Thread objects from PostList accumulated over all pages. Also checks for editor information
        if available and parses user profiles if necessary before creating User object

        <--Args-->
        html(str): raw html data for the page to parse via BeautifulSoup
        url(str): thread url
        categ(str): category thread belongs to
        """
        soup = BeautifulSoup(html.encode('utf-8').strip(), 'lxml')
        userlist = UserList([])
        postlist = PostList([])
        checked_indices = []

        if len(self.db.pred.keys()) > 0:
            oldest_index = self.db.find_oldest_index(url, categ)
        else:
            oldest_index = None
       
        try:
            title = soup.find('h1', class_='lia-message-subject-banner lia-component-forums-widget-message-subject-banner')\
                .text.replace('\n\t', '').replace('\n', '').replace('\u00a0', '')
        except:
            title = url.split(categ + '/')[1].split('/td-p')[0].replace('-', ' ')
            
        post_date = soup.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
            .find('span', class_='message_post_text').text
        
        try:
            edit_date = soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        
        pages = self.get_page_numbers(soup)
        start = pages
        if start > 30:
            end = start - 30
        else:
            end = 1
            
        now = datetime.now()
        debugli = []
        post_total = str(10 * pages)
        oldest_reached = False
        last = 0

        try:
            op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
        except:
            op = None

        if op is not None:
            for msg in op:
                try:
                    post_total = msg.find('span', class_='MessagesPositionInThread').text.split('of ')[1].replace('\n', '').replace(',', '')
                except:
                    post_total = str(10 * pages)

        for pagenum in range(start, end - 1, -1):
            #print(f'Currently on page {pagenum} of url {url}')
            if pagenum > 1 and validators.url(self.generate_next(url, pagenum)):
                self.driver.get(self.generate_next(url, pagenum))
                soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')

            try:
                op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic')
            except:
                op = None
           
            try:
                author = op[0].find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
            except:
                author = ''
            
            try:
                unread = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
            except:
                unread = None
            
            try:
                solved = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved')
            except:
                solved = None

            try:
                resolved = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic lia-list-row-thread-solved')
            except:
                resolved = None
            
            try:
                solution = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved lia-accepted-solution')
            except:
                solution = None

            try:
                no_content = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-message-with-no-content')
            except:
                no_content = None

            if no_content is not None:
                if categ in self.db.stats.no_content.keys():
                    if url in self.db.stats.no_content[categ].keys():
                        self.db.stats.no_content[categ][url] += len(no_content)
                    else:
                        self.db.stats.no_content[categ][url] = len(no_content)
                else:
                    self.db.stats.no_content[categ] = {url: len(no_content)}

            expired = False
            msgs = op + unread + solved + no_content + resolved + solution
            idx = 0
            if self.debug is True:
                l = []
                for msg in msgs:
                    l.append(msg)
                l.remove(random.choice(l))
                msgs = l

            msgli = []
            for msg in msgs:
                msgli.append(msg)

            queue = []
            for msg in reversed(msgli):
                if msg is None:
                    continue

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

                # try:
                #     editinfo = dateheader.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')
                # except:
                #     editinfo = None

                try:
                    edited_by = dateheader.find('span', class_='username_details').find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                    .find('a').find('span').text
                except:
                    edited_by = ''
                
                try:
                    box = dateheader.find('span', class_='username_details').find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                    .find('a')
                    edited_url = 'https://community.upwork.com/' 
                    edited_url += str(box).split('href="')[1].split('"')[0]
                except Exception as e:
                    edited_url = ''

                if edited_by != '' and edited_url != '':
                    editor_id = hashlib.md5((edited_by + edited_url).encode('utf-8')).hexdigest()[:16]
                else:
                    editor_id = ''

                postdate = str(timestamp)
                index = msg.find('span', class_='MessagesPositionInThread').find('a').text.replace('\n', '')
                checked_indices.append(index)

                date_format = "%b %d, %Y %I:%M:%S %p"
                dt = datetime.strptime(postdate, date_format)
                now = datetime.now()
                if (now-dt).days > 7:
                    if oldest_index is not None:
                        if int(index) < oldest_index:
                            expired = True
                            last = int(index)
                    else:
                        expired = True
                
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

                u = User(name, member_since, _url, rank)
                userlist.handle_user(u)

                p = Post(postdate, editdate, post, u, url, pagenum, index, url.split('/t5/')[1].split('/')[0])
                debugli.append(p.__str__())
                in_queue = False
                if editor_id != '' and edited_by != u.name:
                    queue.append((p, edited_url, edited_by))
                    in_queue = True
                elif editor_id != '' and edited_by == u.name:
                    p.add_edited(u)
                if not in_queue:
                    postlist.add(p)
                idx += 1
                last = index

            if expired is True:
                #print('Breaking..........')
                break
        
        if len(queue) > 0:
            for item in queue:
                self.driver.get(item[1])
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                data_container = soup.find('div', class_='userdata-combine-container')
                joininfo = data_container.find_all('span', class_='member-info')
                for entry in joininfo:
                    if entry.text != 'Member since:':
                        joindate = entry.text
                rank_container = data_container.find('div', class_='user-userRank')
                rank = rank_container.text.strip()
                u = User(item[2], joindate, item[1], rank)
                #print(f'Created user {u.__str__()}')
                userlist.handle_user(u)
                item[0].add_edited(u)
                postlist.add(item[0])

        #print(f'Added {len(postlist.postlist)} posts')
        postqueue = []
        if url.split('/t5/')[1].split('/')[0] in self.db.pred.keys():
            if url in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads.keys():
                for post in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads[url].postlist.postlist:
                    if str(post.index) not in checked_indices:
                        print(f'Missing {post.index} in checked indices')
        t = Thread(postlist, url, author, url.split('/t5/')[1].split('/')[0], \
            self.page, post_date, title, edit_date, userlist, post_total)
        #print(f'Created thread {t.__str__()}')
        return t

    def generate_next(self, url, _iter):
        """
        Helper function for generating next page url

        <--Args-->
        url(str): url to format
        _iter(int): current page to format
        """
        return url + f'/page/{_iter}'

    def get_page_numbers(self, soup):
        """
        Get total page number to base scraping parameters off. This should be fixed to
        not require soup to be preloaded.

        <--Args-->
        soup(BeautifulSoup): soup object to scrape with
        """
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