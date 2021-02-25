import sys, os, time, json, logging, datetime, traceback, inspect, uuid, hashlib
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, driver, hist, target=None, debug=False, stats=None):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.driver = driver
        self.hist = hist
        self.logger = logging.getLogger(__name__)
        self.users = {}
        if stats is None:
            self.stats = {}
            self.stats['deletions'] = 0
            self.stats['modifications'] = 0
            self.stats['user_mods'] = {}
            self.stats['user_deletes'] = {}
        else:
            self.stats = stats
        self.debug_mode = debug

    def update_stats(self, stats):
        self.stats = stats

    def make_soup(self, html, url, tar=None):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html, 'html.parser')
        if self.soup is None:
            return None
        
        try:
            hist_partition = self.hist[tar]
        except KeyError:
            hist_partition = None

        try:
            messages = hist_partition[url]['messages'].copy()
        except:
            messages = {}

        if hist_partition is not None:
            try:
                for user, userdata in hist_partition[url]['contributors'].items():
                    self.users[user] = {'user_id': userdata['user_id'], \
                                        'user_url':userdata['user_url'], \
                                        'member_since': userdata['member_since'], \
                                        'rank': userdata['rank']}
            except:
                pass

        if hist_partition is not None:
            try:
                version = hist_partition[url]['update_version']
            except:
                version = 0
        else:
            version = 0
        version += 1
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

        # d = str(post_date)
        # try:
        #     d = d.split(' AM')[0]
        # except:
        #     pass
        # try:
        #     d = d.split(' PM')[0]
        # except:
        #     pass
        # date_format = "%b %d, %Y %H:%M:%S"
        # dt = datetime.datetime.strptime(d, date_format)
        # input((datetime.datetime.now()-dt).days)
        # if (datetime.datetime.now()-dt).days > 7:
        #     return {}
        try:
            edit_date = self.soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        contributors = {}
        pages = self.get_page_numbers()
        start = pages
        if start > 25:
            end = start - 25
        else:
            end = 1
        msg_cache = {}
        # if pages > 10:
        #     pages = 10
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
                postdate = str(timestamp)
                try:
                    postdate = postdate.split(' AM')[0]
                except:
                    pass
                try:
                    postdate = postdate.split(' PM')[0]
                except:
                    pass
                date_format = "%b %d, %Y %H:%M:%S"
                dt = datetime.datetime.strptime(postdate, date_format)
                if (now-dt).days > 7:
                    expired = True
                    break
                if name not in self.users.keys():
                    user_id = uuid.uuid4().hex[:8]
                    self.users[name] = {'user_id': user_id, 'user_url': _url, 'member_since': member_since, 'rank': rank}
                else:
                    user_id = self.users[name]['user_id']

                if self.debug_mode is True:
                    debugli.append(user_id)
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
                            edit_status = '**Edited for'
                        elif edited.find('**edited for') != -1:
                            edit_status = '**edited for'
                    except:
                        pass

                if edit_status != 'Unedited':
                    self.stats['modifications'] += 1
                    if user_id in self.stats['user_mods'].keys():
                        self.stats['user_mods'][user_id] += 1
                    else:
                        self.stats['user_mods'][user_id] = 1

                if post != '':
                    mid = int(hashlib.sha1(post.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
                    if user_id in messages.keys():
                        if str(version) in messages[user_id].keys():
                            messages[user_id][str(version)].append((timestamp, post, edit_status))
                        else:
                            messages[user_id][str(version)] = [(timestamp, post, edit_status)]
                    else:
                        messages[user_id] = {}
                        messages[user_id][str(version)] = [(timestamp, post, edit_status)]

                    if user_id not in msg_cache.keys():
                        msg_cache[user_id] = [post]
                    else:
                        msg_cache[user_id].append(post)

                if version > 1:
                    for key in range(1, version):
                        try:
                            messages[user_id][str(key)].update(hist_partition[url]['messages'][user_id][str(key)])
                        except:
                            if user_id in hist_partition[url]['messages'].keys() and \
                            str(key) in hist_partition[url]['messages'][user_id].keys():
                                old = hist_partition[url]['messages'][user_id][str(key)]
                                messages[user_id][str(key)] = old.copy()

            if expired is True:
                break

        if self.debug_mode is True:
            import random
            try:
                choice = random.choice(debugli)
                del messages[choice]
                print(f'Removed entry w/ key {choice}')
            except:
                pass
            
        if version > 1 and hist_partition is not None:
            for user_id in hist_partition[url]['messages'].keys():
                for v in hist_partition[url]['messages'][user_id].keys():
                    hist_tups = [x for x in hist_partition[url]['messages'][user_id][v]]
                    for tup in hist_tups:
                        timestamp = tup[0]
                        msgpost = tup[1]
                        edit_status = tup[2]
                        if user_id in messages.keys() and str(version) in messages[user_id].keys():
                            new_tups = [x for x in messages[user_id][str(version)]]
                            obj = []
                            for tup_ in new_tups:
                                obj.append(tup[0])
                            if timestamp not in obj:
                                self.stats['deletions'] += 1
                                if user_id in self.stats['user_deletes'].keys():
                                    self.stats['user_deletes'][user_id] += 1
                                else:
                                    self.stats['user_deletes'][user_id] = 1
                                messages[user_id][str(version)].append((timestamp, '<--Deleted-->', '<--Deleted-->'))
                        else:
                            if user_id in messages.keys() and str(version) in messages[user_id].keys():
                                self.stats['deletions'] += 1
                                if user_id in self.stats['user_deletes'].keys():
                                    self.stats['user_deletes'][user_id] += 1
                                else:
                                    self.stats['user_deletes'][user_id] = 1
                                messages[user_id][str(version)].append((timestamp, '<--Deleted-->', '<--Deleted-->'))
                            else:
                                self.stats['deletions'] += 1
                                if user_id in self.stats['user_deletes'].keys():
                                    self.stats['user_deletes'][user_id] += 1
                                else:
                                    self.stats['user_deletes'][user_id] = 1
                                messages[user_id] = {}
                                messages[user_id][str(version)] = [(timestamp, '<--Deleted-->', '<--Deleted-->')]

        pkg = {}
        pkg['pkg_creation_stamp'] = str(datetime.datetime.now())
        pkg['title'] = title
        pkg['post_date'] = post_date
        pkg['edit_date'] = edit_date
        pkg['contributors'] = self.users
        pkg['messages'] = messages
        pkg['update_version'] = version

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