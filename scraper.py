import sys, os, time, json, hashlib, random
from bs4 import BeautifulSoup, element
from datetime import datetime
from header import *
import requests
import validators
from dbmanager import DBConn

class ThreadScraper:
    """
    Main scraper object used to parse data from individual threads. Handles page scrolling,
    object instantiation at lowest level, and generates Thread objects via parse().

    <--Args-->
    driver(WebDriver): webdriver to use for getting additional pages
    sitedb(SiteDB): parent db handler
    """
    def __init__(self, driver, sitedb: SiteDB, debug=False):
        #Webdriver object
        self.driver = driver
        #Associated category page we got thread from
        self.page = 0

        #Parent SiteDB object
        self.db = sitedb

        #Debug mode NOTE: defunct
        self.debug = debug

    def update_page(self, pagenum):
        """
        Convenience method for updating the category page we're scraping from

        <--Args-->
        pagenum(int): pagenum to set as current page
        """

        #Reset page number
        self.page = pagenum

    def parse(self, html, url, categ, category_id, page_expire_limit=10):
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

        #Create BS4 parsing object from encoded HTML
        soup = BeautifulSoup(html.encode('utf-8').strip(), 'lxml')

        #Instantiate child objects for thread object
        userlist = UserList([])
        postlist = PostList([])

        #List of indices we've seen so far
        checked_indices = []

        #If we have old data in our cache
        if len(self.db.pred.keys()) > 0:
            #Get the oldest index
            oldest_index = self.db.find_oldest_index(url, categ)
            old_indices = self.db.get_indices(url, categ)
            if len(old_indices) == 0:
                old_indices = None
        else:
            #Otherwise, we only use postdate to determine when to stop
            oldest_index = None
            old_indices = None
       
        try:
            #If we can't parse the title
            title = soup.find('h1', class_='lia-message-subject-banner lia-component-forums-widget-message-subject-banner')\
                .text.replace('\n\t', '').replace('\n', '').replace('\u00a0', '')
        except:
            #Format it from the URL
            title = url.split(categ + '/')[1].split('/td-p')[0].replace('-', ' ')
            
        #Get thread postdate from first page
        post_date = soup.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
            .find('span', class_='message_post_text').text
        
        #If we have an edit date available, parse it out
        try:
            edit_date = soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        
        #Get the max number of pages in this thread
        pages = self.get_page_numbers(soup)

        #Set scan limits
        start = pages
        if '-full' not in sys.argv:
            if start > 30:
                end = start - 30
            else:
                end = 1
        else:
            end = 1
            
        
        #Backend tracking params
        now = datetime.now()
        post_total = str(10 * pages)

        #Try to find original author container
        try:
            op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
        except:
            op = None
        
        #Get thread author name
        try:
            author = op[0].find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
        except:
            author = ''

        #Parse out the number of posts on the thread
        if op is not None:
            for msg in op:
                try:
                    post_total = msg.find('span', class_='MessagesPositionInThread').text.split('of ')[1].replace('\n', '').replace(',', '')
                    break
                except:
                    pass

        queue = []
        #Iterate through thread pages from last page to limit defined above
        for pagenum in range(start, end-1, -1):
            #print(f'Currently on page {pagenum} of {url}')
            #If we're past the first page, we want to generate the next page URL and validate it
            if pagenum > 1:
                if validators.url(self.generate_next(url, pagenum)):
                    #Get the page and recreate the parsing object
                    if '-p' not in sys.argv:
                        self.driver.get(self.generate_next(url, pagenum))
                        soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')
                    else:
                        r = requests.get(self.generate_next(url, pagenum))
                        soup = BeautifulSoup(r.content, 'html.parser')
            else:
                if '-p' not in sys.argv:
                    self.driver.get(url)
                    soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')
                else:
                    r = requests.get(url)
                    soup = BeautifulSoup(r.content, 'html.parser')

            msgli, count = self.get_message_divs(soup, categ, url)
            try:
                assert(count > 0)
            except:
                print(url, pagenum)
            if pagenum != start:
                try:
                    assert(count == 10)
                except:
                    print(url, pagenum)
                
            #print(f'Got {count} posts on page {pagenum} of {url}')
            expired = False
            idx = 0

            #Iterate through list in reverse order
            for msg in msgli:
                if msg is None:
                    continue
                #try:
                p, editor_id, edited_url, edited_by = self.parse_message_div(msg, url, pagenum)
                #except Exception as e:
                 #   import traceback
                  #  print(f'Something went wrong while parsing a message div \n {url}, {e}')
                checked_indices.append(p.index)
                userlist.handle_user(p.author)
                in_queue = False
                
                #If this post was edited, add it to the queue to find the editor info
                if editor_id != '' and edited_by != p.author.name:
                    queue.append((p, edited_url, edited_by))
                    in_queue = True
                elif editor_id != '' and edited_by == p.author.name:
                    p.add_edited(p.author)
                if not in_queue:
                    postlist.add(p)
                idx += 1

                """
                We only expire if the following conditions are met:

                1. The thread we are scanning has more than 10 pages. Otherwise, it is inexpensive to
                scan the entire thread.

                2. We have seen a post that is older than a week. If we have no cached data, we stop
                scanning here.

                3. We have an oldest index, we've encountered a post older than a week, and we've reached
                the oldest index.

                4. We have an oldest index and a list of indices we encountered on the last scan. If
                all the previous criteria has been met and we have more checked indices than old indices
                we break.
                """

                #If message is older than a week old and we've passed our oldest index break.
                #If we don't have an oldest index, just break when we find a message thats a week old
                date_format = "%b %d, %Y %I:%M:%S %p"
                dt = datetime.strptime(p.postdate, date_format)
                now = datetime.now()

                if pages > page_expire_limit:
                    if (now-dt).days > 7:
                        if oldest_index is not None:
                            if old_indices is not None:
                                if len(old_indices) < len(checked_indices) and all(elem in checked_indices for elem in old_indices):
                                    expired = True
                            else:
                                if oldest_index in checked_indices:
                                    expired = True
                        else:
                            expired = True

            #If we determined we should stop, break here
            if expired is True:
                break
        
            if len(queue) > 0:
                #For each item queued
                for item in queue:
                    #Get editor profile
                    if '-p' not in sys.argv:
                        self.driver.get(item[1])
                        soup = BeautifulSoup(self.driver.page_source, 'lxml')
                    else:
                        r = requests.get(item[1])
                        soup = BeautifulSoup(r.content, 'html.parser')

                    #Parse out relevant user info
                    
                    data_container = soup.find('div', class_='userdata-combine-container')
                    joininfo = data_container.find_all('span', class_='member-info')
                    for entry in joininfo:
                        if entry.text != 'Member since:':
                            joindate = entry.text
                    rank_container = data_container.find('div', class_='user-userRank')
                    rank = rank_container.text.strip()

                    #Create user object and handle it, then add post
                    u = User(item[2], joindate, item[1], rank)
                    userlist.handle_user(u)
                    item[0].add_edited(u)
                    postlist.add(item[0])

        if '-r' not in sys.argv:
            missing = []
            #Debug helper for checking if any posts were missed in last scan
            if url.split('/t5/')[1].split('/')[0] in self.db.pred.keys():
                if url in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads.keys():
                    for post in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads[url].postlist.postlist:
                        if str(post.index) not in checked_indices:
                            missing.append((post.index, post.page))

            missingqueue = []
            for item in missing:
                missing_bool = False
                if '-p' not in sys.argv:
                    self.driver.get(self.generate_next(url, item[1]))
                    soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')
                else:
                    r = requests.get(self.generate_next(url, item[1]))
                    soup = BeautifulSoup(r.content, 'html.parser')
                newli, _ = self.get_message_divs(soup, categ, url)
                for msg in newli:
                    if msg is None:
                        continue
                    try:
                        p, editor_id, edited_url, edited_by = self.parse_message_div(msg, url, item[1])
                        if p.index == item[0] or p.index not in checked_indices:
                            if editor_id != '' and edited_by != p.author.name:
                                missingqueue.append((p, edited_url, edited_by))
                                missing_bool = True
                            elif editor_id != '' and edited_by == p.author.name:
                                p.add_edited(p.author)
                            if not missing_bool:
                                postlist.add(p)
                    except Exception as e:
                        print(f'Something went wrong while finding missing posts\n {e}')
                        print(url)

            for item in missingqueue:
                #Get editor profile
                if '-p' not in sys.argv:
                    self.driver.get(item[1])
                    soup = BeautifulSoup(self.driver.page_source, 'lxml')
                else:
                    r = requests.get(item[1])
                    soup = BeautifulSoup(r.content, 'html.parser')
                #Parse out relevant user info
                
                data_container = soup.find('div', class_='userdata-combine-container')
                joininfo = data_container.find_all('span', class_='member-info')
                for entry in joininfo:
                    if entry.text != 'Member since:':
                        joindate = entry.text
                rank_container = data_container.find('div', class_='user-userRank')
                rank = rank_container.text.strip()

                #Create user object and handle it, then add post
                u = User(item[2], joindate, item[1], rank)
                userlist.handle_user(u)
                item[0].add_edited(u)
                postlist.add(item[0])

            if old_indices is not None:
                if sorted(checked_indices) != sorted(old_indices):
                    diff = self.list_diff(checked_indices, old_indices)
                try:
                    assert(all(elem in checked_indices for elem in old_indices))
                except:
                    self.db.stats.diffs[url] = self.list_diff(checked_indices, old_indices)
                    print(f'Got diff {diff} on url {url}')
        
        #Generate thread object and return
        t = Thread(postlist, url, author, url.split('/t5/')[1].split('/')[0], \
            self.page, post_date, title, edit_date, userlist, post_total)
        with DBConn() as conn:
            for p in t.postlist.postlist:
                conn.insert_from_post(p, t.id, category_id)
        return t

    def generate_next(self, url, _iter):
        """
        Helper function for generating next page url

        <--Args-->
        url(str): url to format
        _iter(int): current page to format
        """

        #Format the URL with page and pagenumber appended
        return url + f'/page/{_iter}'

    def get_page_numbers(self, soup):
        """
        Get total page number to base scraping parameters off. This should be fixed to
        not require soup to be preloaded.

        <--Args-->
        soup(BeautifulSoup): soup object to scrape with
        """

        #Parse out menu container
        menubar = soup.find('div', class_='lia-paging-full-wrapper lia-paging-pager lia-paging-full-left-position lia-component-menu-bar')
        if menubar is not None:
            #Try to parse number of pages
            last = menubar.find('li', class_='lia-paging-page-last')
            try:
                pages = int(last.find('a').text)
            except:
                pages = int(last.find('span').text)
        else:
            pages = 1

        return pages

    def get_message_divs(self, soup, categ, url):
        """
        Wrapper function for fetching all possible message containers on a given page of a thread.
        Converts BS4 ResultSet object to list and sorts/reverses it to crawl backwards through a thread
        in order.

        <--Args-->
        soup(BeautifulSoup): soup object to parse from. needs to have current html loaded into it
        categ(str): category this thread was found in
        url(str): thread url
        """
        #Get all possible message divs and add them to a list to iterate through
        try:
            op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic')
        except:
            op = None
        
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

        try:
            readonly = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic lia-list-row-thread-readonly')
        except:
            readonly = None

        try:
            readonlyreply = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-readonly')
        except:                                     
            readonlyreply = None

        try:
            solvedreadonly = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-list-row-thread-solved lia-list-row-thread-readonly')
        except: 
            solvedreadonly = None

        try:
            other = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply lia-message-authored-by-you')
        except:
            other = None

        #We have messages with no content, handle them in our statstracker in sitedb
        if no_content is not None:
            if categ in self.db.stats.no_content.keys():
                #db.stats.no_content maps category names to URLs to count of no content posts
                if url in self.db.stats.no_content[categ].keys():
                    self.db.stats.no_content[categ][url] += len(no_content)
                else:
                    self.db.stats.no_content[categ][url] = len(no_content)
            else:
                self.db.stats.no_content[categ] = {url: len(no_content)}

        #Create list to iterate through
        msgs = op + unread + solved + no_content + resolved + solution + readonly + readonlyreply + solvedreadonly + other

        msgli = []
        for msg in msgs:
            msgli.append(msg)

        return reversed(msgli), len(msgli)

    def parse_message_div(self, msg, url, pagenum):
        """
        Wrapper function for parsing relevant information out of a message containers. Uses BS4 tag element
        to parse html and get necessary data for instantiating post object. This is used in main parsing function as
        well as cleanup/validation.

        <--Args-->
        msg(bs4.element): beautifulsoup element to parse HTML with
        url(str): url of this thread
        pagenum(str): pagenumber in thread this message was found on
        """
        #Set default edit status
        edit_status = 'Unedited'

        if type(msg) is not element.Tag:
            print(f'Msg obj: {msg}')

        #Get profile URL
        try:
            _url = 'https://community.upwork.com' + \
                msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
        except:
            _url = '**Deleted Profile**'

        #Get profile name
        try:
            name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
        except:
            name = '**Deleted Profile**'
        #Get profile joindate
        try:
            member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
        except:
            member_since = '**Deleted Profile**'

        try:
            #Get profile rank
            rank = msg.find('div', class_='lia-message-author-rank lia-component-author-rank lia-component-message-view-widget-author-rank')\
                .text.replace(' ', '').strip()
        except:
            rank = '**Deleted Profile**'
        
        #Get post/edit info container
        dateheader = msg.find('p', class_='lia-message-dates lia-message-post-date lia-component-post-date-last-edited lia-paging-page-link custom-lia-message-dates')
        
        if dateheader is not None:
            #Get postdate
            timestamp = dateheader.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
                        .find('span', class_='message_post_text').text
            
            #Try to parse an editdate if available
            try:
                e = dateheader.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')
                for span in e.find_all('span', class_='message_post_text'):
                    if span.text != 'by':
                        editdate = span.text
            except:
                editdate = ''

            #Try to parse an editor name if available
            try:
                edited_by = dateheader.find('span', class_='username_details').find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                .find('a').find('span').text
            except:
                edited_by = ''
            
            #Try to post an editor URL
            try:
                box = dateheader.find('span', class_='username_details').find('span', class_='UserName lia-user-name lia-user-rank-Power-Member lia-component-common-widget-user-name')\
                .find('a')
                edited_url = 'https://community.upwork.com/' 
                edited_url += str(box).split('href="')[1].split('"')[0]
            except Exception as e:
                edited_url = ''
        else:
            timestamp, editdate, edited_by, edited_url = '**Info Inaccessible**'

        #If we have editor info, generate MD5 hash ID for them
        if edited_by != '' and edited_url != '':
            editor_id = hashlib.md5((edited_by + edited_url).encode('utf-8')).hexdigest()[:16]
        else:
            editor_id = ''

        #Get post index and add to checked indices
        postdate = str(timestamp)
        index = msg.find('span', class_='MessagesPositionInThread').find('a').text.replace('\n', '')

        #Parse message content
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

        #Generate author user object
        u = User(name, member_since, _url, rank)

        #Generate post object
        p = Post(postdate, editdate, post, u, url, pagenum, index, url.split('/t5/')[1].split('/')[0])

        return p, editor_id, edited_url, edited_by

    def list_diff(self, li1, li2):
        """
        Helper for getting differences between two lists. Used for finding elements in checked indices
        that are not present in old indices.

        Referenced from: https://www.geeksforgeeks.org/python-difference-two-lists/

        <--Args-->
        li1(list): First list item to check
        li2(list): Second list item to check
        """
        return (list(list(set(li1)-set(li2)) + list(set(li2)-set(li1))))