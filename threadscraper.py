import sys, os, time, json, logging, datetime, traceback, inspect, uuid
from bs4 import BeautifulSoup

class ThreadScraper:
    def __init__(self, driver, hist, target=None):
        #Instantiate soup object and inherit logger.
        self.soup = None
        self.driver = driver
        self.hist = hist
        self.logger = logging.getLogger(__name__)
        self.users = {}

    def make_soup(self, html, url, tar=None):
        """Main thread scraper function. Uses BeautifulSoup to parse HTML based on class tags and 
        compiles relevant data/metadata in dict format. Detects edit status and moderation status."""
        self.soup = BeautifulSoup(html, 'html.parser')
        
        try:
            hist_partition = self.hist[tar]
            messages = hist_partition[url]['messages']
        except KeyError:
            hist_partition = None
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
        try:
            edit_date = self.soup.find('span', class_='DateTime lia-message-edited-on lia-component-common-widget-date')\
                .find('span', class_='message_post_text').text
        except AttributeError:
            edit_date = 'Unedited'
        contributors = {}
        pages = self.get_page_numbers()
        start = pages
        if start > 100:
            end = start - 100
        else:
            end = 1
        msg_cache = {}
        # if pages > 10:
        #     pages = 10
        
        for pagenum in reversed(range(start, end + 1)):
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
                if name not in self.users.keys():
                    user_id = uuid.uuid4().hex[:8]
                    self.users[name] = {'user_id': user_id, 'user_url': _url, 'member_since': member_since, 'rank': rank}
                else:
                    user_id = self.users[name]['user_id']
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
                if post != '':
                    if user_id not in messages.keys() and hist_partition is not None:
                        try:
                            messages[user_id] = hist_partition[url]['messages'][user_id]
                            messages[user_id][str(version)] = [(timestamp, post, edit_status)]
                        except KeyError:
                            messages[user_id] = {}
                            messages[user_id][str(version)] = [(timestamp, post, edit_status)]
                    else:
                        try:
                            messages[user_id][str(version)].append((timestamp, post, edit_status))
                        except KeyError:
                            messages[user_id] = {}
                            messages[user_id][str(version)] = [(timestamp, post, edit_status)]

                    if user_id not in msg_cache.keys():
                        msg_cache[user_id] = [post]
                    else:
                        msg_cache[user_id].append(post)

                #print(hist_partition[url]['messages'][user_id].keys())

                # try:
                #     messages[user_id] = {**hist_partition[url]['messages'][user_id],\
                #                         **messages[user_id]}
                # except KeyError as e:
                #     print(e)

        if hist_partition is not None:
            if version > 1:
                for v in range(1, version):
                    for user_id in hist_partition[url]['messages']:
                        #input(hist_partition[url]['messages'][user_id])
                        hist_tups = [x for x in hist_partition[url]['messages'][user_id][str(v)]]
                        for msg_tup in hist_tups:
                            try:
                                #Check if the message is still in the list of messages we encountered for that ID
                                if msg_tup[1] not in msg_cache[user_id]:
                                    #Message wasn't found, add a deleted entry with the timestamp
                                    try:
                                        if user_id not in hist_partition[url]['messages'].keys():
                                            messages[user_id] = {}
                                            messages[user_id][str(version)] = []
                                        else:
                                            messages[user_id] = hist_partition[url]['messages'][user_id]
                                        messages[user_id][str(v)].append((msg_tup[0], '!!DELETED!!', '!!DELETED!!'))
                                    except KeyError:
                                        messages[user_id] = {}
                                        messages[user_id][str(v)] = [(msg_tup[0], '!!DELETED!!', '!!DELETED')]
                            except KeyError:
                                #We didn't find the user from history in the users we encountered, so add a deleted entry
                                try:
                                    messages[user_id][str(v)].append((msg_tup[0], '!!DELETED!!'))
                                except KeyError:
                                    messages[user_id] = {}
                                    messages[user_id][str(v)] = [(msg_tup[0], '!!DELETED!!')]
        pkg = {}
        pkg['pkg_creation_stamp'] = str(datetime.datetime.now())
        pkg['title'] = title
        pkg['post_date'] = post_date
        pkg['edit_date'] = edit_date
        pkg['contributors'] = self.users
        if hist_partition is not None:
            pkg['messages'] = {**hist_partition[url]['messages'], **messages}
        else:
            pkg['messages'] = messages
        pkg['update_version'] = version

        #input('crafted package with version {}'.format(pkg['update_version']))

        try:
            pkg = {**pkg, **hist_partition[url]}
        except:
            pass

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