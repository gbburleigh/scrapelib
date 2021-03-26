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
        else:
            #Otherwise, we only use postdate to determine when to stop
            oldest_index = None
       
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
        debugli = []
        post_total = str(10 * pages)
        last = 0

        #Try to find original author container
        try:
            op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-reply')
        except:
            op = None

        #Parse out the number of posts on the thread
        if op is not None:
            for msg in op:
                try:
                    post_total = msg.find('span', class_='MessagesPositionInThread').text.split('of ')[1].replace('\n', '').replace(',', '')
                    break
                except:
                    pass

        #Iterate through thread pages from last page to limit defined above
        for pagenum in range(start, end - 1, -1):
            #If we're past the first page, we want to generate the next page URL and validate it
            if pagenum > 1 and validators.url(self.generate_next(url, pagenum)):
                #Get the page and recreate the parsing object
                self.driver.get(self.generate_next(url, pagenum))
                soup = BeautifulSoup(self.driver.page_source.encode('utf-8').strip(), 'lxml')

            #Get all possible message divs and add them to a list to iterate through
            try:
                op = soup.find_all('div', class_='MessageView lia-message-view-forum-message lia-message-view-display lia-row-standard-unread lia-thread-topic')
            except:
                op = None
           
            #Get thread author name
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
            expired = False
            msgs = op + unread + solved + no_content + resolved + solution
            idx = 0

            #If we're in debug mode, delete some random messages
            if self.debug is True:
                l = []
                for msg in msgs:
                    l.append(msg)
                l.remove(random.choice(l))
                msgs = l

            #Convert ResultSet to generic list
            msgli = []
            for msg in msgs:
                msgli.append(msg)


            queue = []
            #Iterate through list in reverse order
            for msg in reversed(msgli):
                if msg is None:
                    continue

                #Set default edit status
                edit_status = 'Unedited'

                #Get profile URL
                _url = 'https://community.upwork.com' + \
                    msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
                
                #Get profile name
                name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
                
                #Get profile joindate
                member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
                
                #Get profile rank
                rank = msg.find('div', class_='lia-message-author-rank lia-component-author-rank lia-component-message-view-widget-author-rank')\
                    .text.replace(' ', '').strip()
                
                #Get post/edit info container
                dateheader = msg.find('p', class_='lia-message-dates lia-message-post-date lia-component-post-date-last-edited lia-paging-page-link custom-lia-message-dates')
                
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

                #If we have editor info, generate MD5 hash ID for them
                if edited_by != '' and edited_url != '':
                    editor_id = hashlib.md5((edited_by + edited_url).encode('utf-8')).hexdigest()[:16]
                else:
                    editor_id = ''

                #Get post index and add to checked indices
                postdate = str(timestamp)
                index = msg.find('span', class_='MessagesPositionInThread').find('a').text.replace('\n', '')
                checked_indices.append(index)

                #If message is older than a week old and we've passed our oldest index break.
                #If we don't have an oldest index, just break when we find a message thats a week old
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

                #Handle user object in Thread userlist
                userlist.handle_user(u)

                #Generate post object
                p = Post(postdate, editdate, post, u, url, pagenum, index, url.split('/t5/')[1].split('/')[0])
                debugli.append(p.__str__())
                in_queue = False
                
                #If this post was edited, add it to the queue to find the editor info
                if editor_id != '' and edited_by != u.name:
                    queue.append((p, edited_url, edited_by))
                    in_queue = True
                elif editor_id != '' and edited_by == u.name:
                    p.add_edited(u)
                if not in_queue:
                    postlist.add(p)
                idx += 1
                last = index

            #If we determined we should stop, break here
            if expired is True:
                break
        
        if len(queue) > 0:
            #For each item queued
            for item in queue:
                #Get editor profile
                self.driver.get(item[1])

                #Parse out relevant user info
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
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

        #Debug helper for checking if any posts were missed in last scan
        if url.split('/t5/')[1].split('/')[0] in self.db.pred.keys():
            if url in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads.keys():
                for post in self.db.pred[url.split('/t5/')[1].split('/')[0]].threads[url].postlist.postlist:
                    if str(post.index) not in checked_indices:
                        print(f'Missing {post.index} in checked indices on {url}')
        
        #Generate thread object and return
        t = Thread(postlist, url, author, url.split('/t5/')[1].split('/')[0], \
            self.page, post_date, title, edit_date, userlist, post_total)
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