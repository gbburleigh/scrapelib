import sys, os, time, json, logging, datetime, traceback, inspect, uuid, hashlib
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, driver, hist, target=None, debug=False, stats=None, users=None):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.driver = driver
        self.hist = hist
        self.logger = logging.getLogger(__name__)
        if users is None:
            self.users = {}
        else:
            self.users = users
        targets = ['https://community.upwork.com/t5/Freelancers/bd-p/freelancers']#/
                #'https://community.upwork.com/t5/Announcements/bd-p/news',\
                #'https://community.upwork.com/t5/Clients/bd-p/clients', \
                #'https://community.upwork.com/t5/Agencies/bd-p/Agencies']
        self.ref = {}
        #if stats is None:
        self.stats = {}
            #print('Formatting new stats dict')
            # self.stats['deletions'] = 0
            # self.stats['modifications'] = 0
            # self.stats['user_mods'] = {}
            # self.stats['user_deletes'] = {}
        for tar in targets:
            self.stats[tar.split('/t5/')[1].split('/')[0]] = {}
            self.stats[tar.split('/t5/')[1].split('/')[0]]['deletions'] = 0
            self.stats[tar.split('/t5/')[1].split('/')[0]]['modifications'] = 0
            self.stats[tar.split('/t5/')[1].split('/')[0]]['user_mods'] = {}
            self.stats[tar.split('/t5/')[1].split('/')[0]]['user_deletes'] = {}
            self.ref[tar] = tar.split('/t5/')[1].split('/')[0]
        #else:
        if stats is not None:
            self.stats.update(stats)

        self.debug_mode = debug

        #print(f'Scraper stats keys {self.stats.keys()}')

    def update_stats(self, stats):
        self.stats = stats

    def make_soup(self, html, url, users, tar=None, categ=None):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html, 'html.parser')
        if self.soup is None:
            return None

        category = categ
        
        try:
            hist_partition = self.hist[tar]
            #print('Got hist')
        except KeyError:
            hist_partition = None

        try:
            messages = hist_partition[url]['messages'].copy()
        except:
            messages = {}

        oldest = datetime.datetime.now()
        oldmsg = None
        #input(f"keys: {hist_partition[url]['update_version']}")
        if hist_partition is not None:
            try:
                version = hist_partition[url]['update_version']
            except Exception as e:
                version = 0

            try:
                for user in hist_partition[url]['messages'].keys():
                    for msg in hist_partition[url]['messages'][user][version]:
                        obj = datetime.datetime.strptime(msg[0], '%m-%d-%Y %H:%M')
                        if oldest > obj:
                            oldest = obj
                            oldmsg = msg
            except:
                pass
        else:
            version = 0
        version += 1
        #print(f'generating version {version} for {url}')
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
        pages = self.get_page_numbers()
        start = pages
        seen = []
        if start > 25:
            end = start - 25
        else:
            end = 1
        msg_cache = {}
        now = datetime.datetime.now()
        debugli = []
        for pagenum in range(start, end - 1, -1):
            self.logger.info(f'Currently on page {pagenum} of {url}')
            print(f'Currently on page {pagenum} of {url}')
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

            expired = False
            msgs = op + unread + solved
            for msg in msgs:
                edit_status = 'Unedited'
                _url = 'https://community.upwork.com' + \
                    msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name', href=True)['href']
                name = msg.find('a', class_='lia-link-navigation lia-page-link lia-user-name-link user_name').find('span').text
                member_since = msg.find('span', class_='custom-upwork-member-since').text.split(': ')[1]
                rank = msg.find('div', class_='lia-message-author-rank lia-component-author-rank lia-component-message-view-widget-author-rank')\
                    .text.replace(' ', '').strip()
                timestamp = msg.find('span', class_='DateTime lia-message-posted-on lia-component-common-widget-date')\
                            .find('span', class_='message_post_text').text
                try:
                    editdate = msg.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                                .find('span', class_='message_post_text').text
                except:
                    editdate = ''
                postdate = str(timestamp)
                try:
                    postdate = postdate.split(' AM')[0]
                except:
                    pass
                try:
                    postdate = postdate.split(' PM')[0]
                except:
                    pass
                try:
                    editdate = postdate.split(' AM')[0]
                except:
                    pass
                try:
                    editdate = postdate.split(' PM')[0]
                except:
                    pass
                date_format = "%b %d, %Y %H:%M:%S"
                dt = datetime.datetime.strptime(postdate, date_format)
                if name not in self.users.keys():
                    user_id = uuid.uuid4().hex[:8]
                    #user_id = abs(hash(name)) % (10 ** 8)
                    self.users[name] = {'user_id': user_id, 'user_url': _url, 'member_since': member_since, 'rank': rank}
                    contributors[name] = self.users[name]
                else:
                    user_id = self.users[name]['user_id']
                    #if user_id != abs(hash(name)) % (10 ** 8):
                        #del self.users[name]
                        #self.users[name] = {'user_id': abs(hash(name)) % (10 ** 8), 'user_url': _url, 'member_since': member_since, 'rank': rank}
                    contributors[name] = self.users[name]
                if self.debug_mode is True:
                    debugli.append(user_id)
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

                #print(post)
                #input(post)
                if '**Edited for' in post:
                    edit_status = '**Edited for'
                if '**edited for' in post:
                    edit_status = '**edited for'
                #input(edit_status)

                if edit_status != 'Unedited':
                    self.stats[category]['modifications'] += 1
                    if user_id in self.stats[category]['user_mods'].keys():
                        self.stats[category]['user_mods'][user_id] += 1
                    else:
                        self.stats[category]['user_mods'][user_id] = 1

                if post != '':
                    #mid = int(hashlib.sha1(post.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
                    if user_id in messages.keys():
                        if str(version) in messages[user_id].keys():
                            if (timestamp, post, edit_status, editdate) not in messages[user_id][str(version)]:
                                if version > 1:
                                    if user_id in hist_partition[url]['messages'].keys():
                                        if str(version - 1) in hist_partition[url]['messages'][user_id].keys():
                                            messages[user_id][str(version)].append((timestamp, post, 'NEW, ' + edit_status, editdate))
                                        else:
                                            messages[user_id][str(version)].append((timestamp, post, edit_status, editdate))
                                    else:
                                        messages[user_id][str(version)].append((timestamp, post, 'NEW, ' + edit_status, editdate))
                                else:
                                    messages[user_id][str(version)].append((timestamp, post, edit_status, editdate))
                        else:
                            messages[user_id][str(version)] = [(timestamp, post, edit_status, editdate)]
                    else:
                        messages[user_id] = {}
                        if version > 1:
                            messages[user_id][str(version)] = [(timestamp, post, 'NEW, ' + edit_status, editdate)]
                        else:
                            messages[user_id][str(version)] = [(timestamp, post, edit_status, editdate)]

                    #print(f'Generated version {str(version)}: {messages[user_id][str(version)]}')

                    if user_id not in msg_cache.keys():
                        msg_cache[user_id] = [post]
                    else:
                        msg_cache[user_id].append(post)

                    # if version > 1:
                    #     for key in range(1, version):
                    #         try:
                    #             messages[user_id][str(key)].update(hist_partition[url]['messages'][user_id][str(key)])
                    #         except:
                    #             print(f'Missing version {str(key)} for user {user_id}')
                    #             try:
                    #                 messages[user_id][str(key)] = hist_partition[url]['messages'][user_id][str(key)].copy()
                    #             except:
                    #                 print(f'SOMETHING REALLY WENT WRONG')
                    
                    if version > 1:
                        for key in range(1, version):
                            try:
                                if str(key) in messages[user_id].keys():
                                    messages[user_id][str(key)].update(hist_partition[url]['messages'][user_id][str(key)])
                                else:
                                    messages[user_id][str(key)] = hist_partition[url]['messages'][user_id][str(key)].copy()
                            except:
                                if user_id in hist_partition[url]['messages'].keys() and \
                                str(key) in hist_partition[url]['messages'][user_id].keys():
                                    old = hist_partition[url]['messages'][user_id][str(key)]
                                    if old is not None:
                                        messages[user_id][str(key)] = old.copy()

                seen.append((timestamp, post, edit_status, editdate))

                if (now-dt).days > 7:
                    if oldmsg in seen or dt < oldest:
                        expired = True
                        #print(f'Ended on message: {post[:40]}')
                        break
                
            if expired is True:
                break

        if self.debug_mode is True:
            import random
            rand = random.random()
            if rand > 0.7:
                try:
                    choice = random.choice(debugli)
                    #input(contributors[choice])
                    msg = random.choice(messages[choice][str(version)])
                    popped = messages[choice][str(version)].pop(random.randrange(len(messages[choice][str(version)])))
                    print(f'Removed entry from user {key}, text: {popped[1][:24]}')
                    # for entry in contributors.keys():
                    #     if contributors[entry]['user_id'] == choice:
                    #         print(f'User info: {contributors[entry]}')
                except:
                    pass
            
        #For each user we have messages for
        if version > 1:
            for user_id in messages.keys():
                #Get the last version
                if str(version - 1) in messages[user_id].keys():
                    last = version - 1
                    #Get the entries from the current scan
                    #print(json.dumps(messages[user_id], indent=4))
                    #print(messages[user_id].keys())
                    if str(version) in messages[user_id].keys():
                        curr_entries = messages[user_id][str(version)]
                        #For each cached entry
                        for entry in messages[user_id][str(last)]:
                            c = False
                            for e in curr_entries:
                                if e[0] == entry[0] and e[1] == entry[1]:
                                    c = True
                                elif e[0] == entry[0] and e[1].find('**') != -1:
                                    c = True
                            if c is True:
                                continue
                            #For messages not in the current cached memory
                            if entry not in curr_entries:
                                #print(f'Old entries: {messages[user_id][str(last)]}')
                                #print(f'New entries: {curr_entries}')
                                messages[user_id][str(version)].append((timestamp, entry[1], '<--Deleted-->', 'Deleted in last day'))
                                self.stats[category]['deletions'] += 1
                                if user_id in self.stats[category]['user_deletes'].keys():
                                    self.stats[category]['user_deletes'][user_id] += 1
                                else:
                                    self.stats[category]['user_deletes'][user_id] = 1
                    else:
                        #print(f'USER ID {user_id} MISSING VERSION ON URL {url}')
                        messages[user_id][str(version)] = []
                        for entry in messages[user_id][str(last)]:
                            messages[user_id][str(version)].append((entry[0], entry[1], '<--Deleted-->', 'Deleted in last day'))

        # if version > 1 and hist_partition is not None:
        #     #If we have data saved about this thread
        #     if url in hist_partition.keys():
        #         #Iterate through each user's messages
        #         for user_id in hist_partition[url]['messages'].keys():
        #             v = version - 1
        #             #Get the last version, if its available
        #             if str(v) in hist_partition[url]['messages'][user_id].keys():
        #                 #Make a list of each post for this user
        #                 hist_tups = [x for x in hist_partition[url]['messages'][user_id][str(v)]]
        #                 #For each msg object
        #                 for tup in hist_tups:
        #                     timestamp = tup[0]
        #                     msgpost = tup[1]
        #                     edit_status = tup[2]
        #                     #If we have this user's ID in our messages
        #                     if user_id in messages.keys() and str(version) in messages[user_id].keys():
        #                         #Get their messages
        #                         new_tups = [x for x in messages[user_id][str(version)]]
        #                         obj = []
        #                         for tup_ in new_tups:
        #                             obj.append(tup_[0])
        #                         #We don't have a message with the given timestamp, so it must have been deleted
        #                         if timestamp not in obj and edit_status != '<--Deleted-->':
        #                             #Handle deletion
        #                             self.stats[category]['deletions'] += 1
        #                             if user_id in self.stats[category]['user_deletes'].keys():
        #                                 self.stats[category]['user_deletes'][user_id] += 1
        #                             else:
        #                                 self.stats[category]['user_deletes'][user_id] = 1
        #                             print(f'Found a user missing a timestamp {timestamp}')
        #                             print(f'User timestamps: {obj}')
        #                             messages[user_id][str(version)].append((timestamp, msgpost, '<--Deleted-->', 'Deleted in last day'))
        #                     else:
        #                         # if user_id in messages.keys() and str(version) in messages[user_id].keys():
        #                         #     self.stats[category]['deletions'] += 1
        #                         #     if user_id in self.stats[category]['user_deletes'].keys():
        #                         #         self.stats[category]['user_deletes'][user_id] += 1
        #                         #     else:
        #                         #         self.stats[category]['user_deletes'][user_id] = 1
        #                         #     messages[user_id][str(version)].append((timestamp, msgpost, '<--Deleted-->', 'Deleted in last day'))
        #                         #else:
        #                         if user_id in messages.keys():
        #                             self.stats[category]['deletions'] += 1
        #                             if user_id in self.stats[category]['user_deletes'].keys():
        #                                 self.stats[category]['user_deletes'][user_id] += 1
        #                             else:
        #                                 self.stats[category]['user_deletes'][user_id] = 1
        #                             print(f'Found user, but didnt find entry for this version')
        #                             print(messages[user_id])
        #                             messages[user_id][str(version)] = [(timestamp, msgpost, '<--Deleted-->', 'Deleted in last day')]
        #                         else:
        #                             self.stats[category]['deletions'] += 1
        #                             if user_id in self.stats[category]['user_deletes'].keys():
        #                                 self.stats[category]['user_deletes'][user_id] += 1
        #                             else:
        #                                 self.stats[category]['user_deletes'][user_id] = 1
        #                             messages[user_id] = {}
        #                             messages[user_id][str(version)] = [(timestamp, msgpost, '<--Deleted-->', 'Deleted in last day')]
        #                             print('Didnt find user or version in messages, creating deleted entry')

        pkg = {}
        pkg['pkg_creation_stamp'] = str(datetime.datetime.now())
        pkg['title'] = title
        pkg['post_date'] = post_date
        pkg['edit_date'] = edit_date
        pkg['contributors'] = contributors
        #input(pkg['contributors'][removed])
        pkg['messages'] = messages
        pkg['update_version'] = version

        #print(f'Scraper stats: {self.stats}')

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