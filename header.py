import hashlib, json, os, sys, datetime, csv, random

class User:
    def __init__(self, name, joindate, url, rank):
        self.name = name
        self.joindate = joindate
        self.url = url
        self.rank = rank
        payload = str(self.name) + str(self.url)
        payload = payload.encode('utf-8')
        self.id = str(hashlib.md5(payload).hexdigest()[:16])

    def __str__(self):
        return f'User(name={self.name}, id={self.id})'

    def __json__(self):
        return {'name': self.name, 'joindate': self.joindate, 'url': self.url, 'id': self.id, 'rank': self.rank}

    def load(self, d):
        self.name = d['name']
        self.joindate = d['joindate']
        self.url = d['url']
        self.id = d['id']
        self.rank = d['rank']

class UserList:
    def __init__(self, users: [User]):
        self.userlist = users
        self.users = {}
        if len(users) > 0:
            for u in users:
                self.users[u.id] = u

    def handle_user(self, user: User):
        if user.id not in self.users.keys():
            self.users[user.id] = user

    def check_user(self, user: User):
        if user.id in self.users.keys():
            return True
        else:
            return False

    def merge(self, src):
        for user in src.userlist:
            self.handle_user(user)

    def __json__(self):
        d = {}
        d['userlist'] = []
        d['users'] = {}
        for user in self.userlist:
            d['userlist'].append(user.__json__())
            d['users'][user.id] = user.__json__()
        return d

    def load(self, d):
        for user in d['userlist']:
            u = User('', '', '', '')
            u.load(user)
            self.userlist.append(u)
            self.users[u.id] = u

class Post:
    """Generic post object. Generates unique ID based on author str and postdate. In the case
    that a post is deleted, its id should therefor not even appear in the postlist. Wrapper for
    csv and json functionality later"""
    def __init__(self, postdate, editdate, message, user : User, url, page, index):
        self.postdate = postdate
        self.editdate = editdate
        try:
            self.postdate = self.postdate.split(' AM')[0]
        except:
            pass
        try:
            self.postdate = self.postdate.split(' PM')[0]
        except:
            pass

        date_format = "%b %d, %Y %H:%M:%S"
        if self.postdate != '':
            dt = datetime.datetime.strptime(self.postdate, date_format)
            self.poststamp = dt
            if self.editdate != '':
                try:
                    self.editdate = self.postdate.split(' AM')[0]
                except:
                    pass
                try:
                    self.editdate = self.postdate.split(' PM')[0]
                except:
                    pass
                dt2 = datetime.datetime.strptime(self.editdate, date_format)
                self.editstamp = dt2
                self.edit_time = dt2 - dt
            else:
                self.editstamp, self.edit_time = None, None

        self.message = message
        payload = (user.__str__() + self.postdate).encode('utf-8')
        self.id = hashlib.md5(payload).hexdigest()[:16]
        self.author = user
        self.url = url
        self.edit_status = 'Unedited'
        self.page = page
        self.index = int(index)
        self.edited = User('', '', '', '')
        self.seen_for_mod = False
        self.seen_for_del = False

        if self.message.find('**Edited') != -1 or self.message.find('**edited') != -1:
            self.edit_status = '**Edited**'

    def add_edited(self, user: User):
        self.edited = user

    def __str__(self):
        return f'Post(name={self.author.__str__()}, id={self.id}, url={self.url})'

    def __json__(self):
        d = {}
        d['postdate'] = self.postdate
        d['editdate'] = self.editdate
        d['message'] = self.message
        d['id'] = self.id
        d['author'] = self.author.__json__()
        d['url'] = self.url
        d['edit_status'] = self.edit_status
        d['page'] = self.page
        d['index'] = self.index
        d['edited'] = self.edited.__json__()
        d['seen_for_mod'] = self.seen_for_mod
        d['seen_for_del'] = self.seen_for_del

        return d

    def load(self, d):
        self.postdate = d['postdate']
        self.editdate = d['editdate']
        self.message = d['message']
        self.id = d['id']
        u = User('', '', '', '')
        u.load(d['author'])
        self.author = u
        self.url = d['url']
        self.edit_status = d['edit_status']
        self.page = d['page']
        self.index = d['index']
        self.seen_for_mod = d['seen_for_mod']
        self.seen_for_del = d['seen_for_del']
        u = User('', '', '', '')
        u.load(d['edited'])
        self.edited = u

class PostList:
    def __init__(self, posts : [Post]):
        self.postlist = posts
        self.posts = {}
        if len(posts) > 0:
            for post in posts:
                if post.author.id in self.posts.keys():
                    self.posts[post.author.id][post.id] = post
                else:
                    self.posts[post.author.id] = {post.id: post}
        self.post_count = 0
        self.get_post_count()

    def __json__(self):
        d = {}
        d['postlist'] = []
        d['posts'] = {}
        for post in self.postlist:
            d['postlist'].append(post.__json__())
            d['posts'][post.id] = post.__json__()
        d['post_count'] = self.post_count

        return d

    def load(self, d):
        for item in d['postlist']:
            p = Post('', '', '', User('', '', '', ''), '', '', '0')
            p.load(item)
            self.postlist.append(p)
            self.posts[item['id']] = p
        self.post_count = d['post_count']

    def diff(self, other):
        """Returns the list of posts in the other postlist that aren't present in the current list.
        Thread object will use this method to determine which posts have been deleted"""
        deleted = []
        for post in other.postlist:
            if post.author.id in self.posts.keys():
                if post.id not in self.posts[post.author.id].keys():
                    deleted.append(post)
            else:
                deleted.append(post)

        return DeleteList(deleted)

    def get_post_count(self):
        self.post_count = 0
        for post in self.postlist:
            self.post_count += 1

    def add(self, post: Post):
        if post.author.id in self.posts.keys():
            self.posts[post.author.id][post.id] = post
        else:
            self.posts[post.author.id] = {post.id: post}
        self.postlist.append(post)
        self.post_count += 1

    def merge(self, src):
        """Handler for merging two postlists"""
        for author in src.posts.keys():
            if author in self.posts.keys():
                for pid, post in src.posts[author].items():
                    if pid not in self.posts[author].keys():
                        self.posts[author][pid] = post
                        self.post_count += 1
            else:
                self.posts[author] = {}
                for pid, post in src.posts[author].items():
                    self.posts[author][pid] = post
                    self.post_count += 1

class DeleteList:
    def __init__(self, posts : [Post]):
        self.posts = {}
        self.deletelist = posts
        if len(posts) > 0:
            for post in posts:
                if post.author.id in self.posts.keys():
                    self.posts[post.author.id][post.id] = post
                else:
                    self.posts[post.author.id] = {post.id: post}

    def merge(self, src):
        """Handler for merging two postlists"""
        for author in src.posts.keys():
            if author in self.posts.keys():
                for pid, post in src.posts[author].items():
                    if pid not in self.posts[author].keys():
                        self.posts[author][pid] = post
            else:
                self.posts[author] = {}
                for pid, post in src.posts[author].items():
                    self.posts[author][pid] = post

    def add(self, post: Post):
        if post.author.id in self.posts.keys():
            self.posts[post.author.id][post.id] = post
        else:
            self.posts[post.author.id] = {post.id: post}

    def __json__(self):
        d = {}
        d['deletelist'] = []
        d['posts'] = {}
        for post in self.deletelist:
            d['deletelist'].append(post.__json__())
            d['posts'][post.id] = post.__json__()

        return d

    def load(self, d):
        for item in d['deletelist']:
            p = Post('', '', '', User('', '', '', ''), '', '', '0')
            p.load(item)
            self.deletelist.append(p)
            self.posts[item['id']] = p

        
class Thread:
    def __init__(self, posts: PostList, url, op, category, page, postdate, title, editdate, users: UserList, total):
        self.url = url
        self.title = title
        self.postdate = postdate
        self.editdate = editdate
        self.op = op
        self.category = category
        self.postlist = posts
        self.posts = {}
        self.page = page
        self.users = users
        self.total = int(total)
        for post in self.postlist.postlist:
            self.posts[post.author.id] = post
        self.post_count = posts.post_count
        if len(self.postlist.postlist) > 0:
            self.oldest_index = min([post.index for post in self.postlist.postlist])
        else:
            self.oldest_index = 0

    def __json__(self):
        d = {}
        d['url'] = self.url
        d['title'] = self.title
        d['editdate'] = self.editdate
        d['postdate'] = self.postdate
        d['op'] = self.op
        d['category'] = self.category
        d['postlist'] = []
        d['posts'] = {}
        u = UserList([])
        for post in self.postlist.postlist:
            d['postlist'].append(post.__json__())
            d['posts'][post.id] = post.__json__()
            u.handle_user(post.author)
        d['page'] = self.page
        d['total'] = self.total
        d['users'] = u.__json__()
        d['oldest_index'] = self.oldest_index
        d['post_count'] = self.post_count

        return d

    def load(self, d):
        self.url = d['url']
        self.title = d['title']
        self.editdate = d['editdate']
        self.postdate = d['postdate']
        self.op = d['op']
        self.category = d['category']
        self.page = d['page']
        self.total = d['total']
        self.oldest_index = d['oldest_index']
        for item in d['postlist']:
            p = Post('', '', '', User('', '', '', ''), '', '', '0')
            p.load(item)
            self.postlist.postlist.append(p)
            self.posts[item['id']] = p
        self.users = UserList([])
        for post in self.postlist.postlist:
            self.users.handle_user(post.author)
        self.post_count = d['post_count']

    def refresh_count(self):
        self.post_count = self.postlist.post_count
        return self.post_count

    def compare(self, src):
        deleted = self.postlist.diff(src.postlist)
        return deleted

    def update(self, src):
        src_users = src.users
        src_posts = src.postlist
        self.postlist.merge(src_posts)
        self.users.merge(src_users)
        self.refresh_count()
        #self.post_count += src.post_count
        #self.get_post_count()

    def get_post_count(self):
        self.post_count = 0
        for post in self.postlist.postlist:
            self.post_count += 1

    def sorted(self):
        return sorted(self.postlist.postlist, key=lambda x: x.index, reverse=True)

    def reverse_iterator(self):
        index = self.total
        for post in self.postlist.postlist:
            if post.index == index:
                index -= 1
                yield post

    def get_next(self, idx):
        for post in self.postlist.postlist:
            if post.index == idx:
                return post

    def __str__(self):
        return f'Thread(title={self.title[:24]}, category={self.category}, posts={self.post_count})'

class Category:
    def __init__(self, threads: [Thread], name):
        self.name = name
        self.threads = {}
        self.threadlist = threads
        if len(threads) > 0:
            for thread in threads:
                self.threads[thread.url] = thread
            self.oldest = self.threads[random.choice(list(self.threads.keys()))]
            self.find_oldest()

    def find_oldest(self):
        for url, thread in self.threads.items():
            dt = datetime.datetime.strptime(thread.postdate, "%b %d, %Y %I:%M:%S %p")
            if dt < datetime.datetime.strptime(self.oldest.postdate, "%b %d, %Y %I:%M:%S %p"):
                self.oldest = thread


    def merge(self, src):
        for url, thread in src.threads.keys():
            if url in self.threads.keys():
                self.threads[url].update(thread)
            else:
                self.threads[url] = thread
        self.find_oldest()
    
    def add(self, thread: Thread):
        if thread.url in self.threads.keys():
            self.threads[thread.url].update(thread)
        self.find_oldest()

    def __json__(self):
        d = {}
        d['name'] = self.name
        d['threadlist'] = []
        d['threads'] = {}
        for thread in self.threadlist:
            d['threadlist'].append(thread.__json__())
            d['threads'][thread.url] = thread.__json__()
        d['oldest'] = self.oldest.__json__()

        return d

    def load(self, d):
        self.name = d['name']
        for url, thread in d['threads'].items():
            t = Thread(PostList([]), '', '', '', '', '', '', '', UserList([]), '0')
            t.load(thread)
            self.threadlist.append(t)
            self.threads[url] = t
        self.oldest = d['oldest']

    def __str__(self):
        return f'Category(name={self.name}, threads={len(self.threads.keys())})'

class StatTracker:
    def __init__(self, src=None):
        self.user_deletions = {}
        self.user_modifications = {}
        self.deletions = 0
        self.modifications = 0
        self.avg_edit_time = 0
        self.avg_timestamp = {}
        self.edit_times = {}
        if src is not None and type(src) is dict:
            self.deletions = src['deletions']
            self.modifications = src['modifications']
            for user, count in src['user_deletions'].items():
                self.user_deletions[user] = count
            for user, count in src['user_modifications'].items():
                self.user_modifications[user] = count
        
    def update_modifications(self, src):
        for _, category in src.items():
            for url, thread in category.threads.items():
                for post in thread.postlist.postlist:
                    if post.edit_status != 'Unedited' and post.edit_status != '<--Deleted-->' and post.seen_for_mod is False:
                        self.modifications += 1
                        if post.author.id in self.user_modifications.keys():
                            self.user_modifications[post.author.id] += 1
                        else:
                            self.user_modifications[post.author.id] = 1
                        post.seen_for_mod = True

    def update_deletions(self, deletelist: DeleteList):
        for post in deletelist.deletelist:
            if post.seen_for_del is False:
                self.deletions += 1
                if post.author.id in self.user_deletions.keys():
                    self.user_deletions[post.author.id] += 1
                else:
                    self.user_deletions[post.author.id] = 1
                post.seen_for_del = True

    def update_edit_time(self, src):
        #count, daytotal, hourtotal, minutetotal = 0, 0, 0, 0
        count, total = 0, 0
        for _, category in src.items():
            for url, thread in category.threads.items():
                for post in thread.postlist.postlist:
                    if post.edit_time is not None and post.id not in self.edit_times.keys():
                        #days, hours, minutes = post.edit_time.days * 86400, post.edit_time.seconds // 3600, post.edit_time.seconds // 60 % 60
                        #daytotal += days
                        #hourtotal += hours
                        total += post.edit_time.seconds
                        count += 1
                        self.edit_times[post.id] = post.edit_time

        self.avg_edit_time = total/count
        self.sec_to_str(total/count)
        
    def sec_to_str(self, sec): 
        day = sec // (24 * 3600) 
        self.avg_timestamp['days']
        sec = sec % (24 * 3600) 
        hour = sec // 3600
        self.avg_timestamp['hours'] = hour
        sec %= 3600
        minutes = sec // 60
        self.avg_timestamp['minutes'] = minutes
        sec %= 60
        self.avg_timestamp['seconds'] = sec

    def __json__(self):
        d = {}
        d['user_deletions'] = self.user_deletions
        d['user_modifications'] = self.user_modifications
        d['deletions'] = self.deletions
        d['modifications'] = self.modifications
        d['avg_timestamp'] = self.avg_timestamp
        d['avg_edit_time'] = self.avg_edit_time
        d['edit_times'] = self.edit_times
        return d

    def load(self, src):
        self.user_modifications = src['user_modifications']
        self.user_deletions = src['user_deletions']
        self.deletions = src['deletions']
        self.modifications = src['modifications']
        self.edit_times = src['edit_times']
        self.avg_edit_time = src['avg_edit_time']
        self.avg_timestamp = src['avg_timestamp']

class SiteDB:
    def __init__(self, categories: [Category], name):
        self.name = name
        self.users = UserList([])
        self.pred = {}
        self.deletes = {}
        self.cache = {}
        self.categories = categories
        self.stats = StatTracker()
        
        if len(categories) > 0:
            for category in categories:
                self.cache[category.name] = category
                for _, thread in category.threads.items():
                    self.users.merge(thread.users)

    def add(self, entry: Category):
        self.categories.append(entry)
        self.cache[entry.name] = entry
        for _, thread in entry.threads.items():
            self.users.merge(thread.users)

    def find_oldest_index(self, url):
        for category in self.pred.keys():
            if url in self.pred[category].threads.keys():
                return self.pred[category].threads[url].oldest_index

    def load(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        
        try:
            filenames.remove('debug.log')
        except:
            pass
        try:
            filenames.remove('.DS_Store')
        except:
            pass
        try:
            filenames.remove('geckodriver.log')
        except:
            pass

        if len(filenames) != 0:
            newest_file = str(max([datetime.datetime.strptime(x.strip('.json'), '%Y-%m-%d') for x in filenames]).date()) + '.json'
            with open(os.getcwd() + '/cache/logs/{}'.format(newest_file), 'r') as f:
                d = json.load(f)
                self.dict_load(d)
                

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

    def compile(self):
        d = {}
        d['name'] = self.name
        d['users'] = self.users.__json__()
        d['deletes'] = {}
        d['cache'] = {}
        d['categories'] = []
        for url, deletelist in self.deletes.items():
            d['deletes'][url] = deletelist.__json__()
        for category in self.categories:
            d['cache'][category.name] = category.__json__()
            d['categories'].append(category.__json__())
        d['stats'] = self.stats.__json__()

        return d

    def dict_load(self, d):
        self.name = d['name']
        u = UserList([])
        u.load(d['users'])
        self.users = u
        for url in d['deletes'].keys():
            dl = DeleteList([])
            dl.load(d['deletes'][url])
            self.deletes[url] = dl
        for name, category in d['cache'].items():
            c = Category([], '')
            c.load(d['cache'][name])
            self.cache[name] = c
            self.categories.append(c)
        self.stats.load(d['stats'])

    def compare(self, src):
        if src is not None and src:
            self.users.merge(src.users)
            for _, category in self.cache.items():
                for url, thread in category.threads.items():
                    #d = DeleteList([])
                    #d.merge(thread.compare(src.cache[category][url]))
                    self.deletes[url] = thread.compare(src.cache[category.name].threads[url])
            
                    for post in self.deletes[url].deletelist:
                        self.users.handle_user(post.author)

        for deletelist in self.deletes.values():
            self.stats.update_deletions(deletelist)

        return self.deletes

    def write(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(os.getcwd() + '/cache/logs/{}.json'.format(now), 'w') as f:
            #data = dict(self.cache)
            f.write(json.dumps(self.compile(), indent=4))
        
        with open(os.getcwd() + f'/cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            f = csv.writer(f)
            f.writerow(["title", "post_date", "edit_date", "contributor_id", \
                    "contributor_rank", "message_text",\
                    "post_moderation", "category", "url"])
            for category in self.categories:
                for thread in category.threadlist:
                    for author, post in thread.posts.items():
                        f.writerow([thread.title, post.postdate, post.editdate, post.author.id, \
                            post.author.rank, post.message, post.edit_status, category.name, thread.url])
                    if thread.url in self.deletes.keys():
                        for post in self.deletes[thread.url].deletelist:
                            f.writerow([thread.title, thread.postdate, post.editdate, post.author.id, \
                            post.author.rank, post.message, '<--Deleted-->', category.name, thread.url])
