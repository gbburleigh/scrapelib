import hashlib, json, os, sys, csv, random
from datetime import datetime

class User:
    """
    Main wrapper object for user info. Encapsulates ID generation via available info

    <---Args-->
    name (str): Given username
    joindate(str): User joindate (Note: this is a str type, not datetime)
    url(str): URL to user profile
    rank(str): User's community rank

    <--Attributes-->
    id(str): MD5 hash of name and url sliced to 16 characters
    """
    def __init__(self, name, joindate, url, rank):
        self.name = name
        self.joindate = joindate
        self.url = url
        self.rank = rank
        payload = (str(self.name) + str(self.url)).encode('utf-8')
        self.id = str(hashlib.md5(payload).hexdigest()[:16])

    def __str__(self):
        """Generic string descriptor for object"""
        return f'User(name={self.name}, id={self.id})'

    def __json__(self):
        """
        Saves user info as a dictionary. This is called recursively by higher level objects.
        """
        return {'name': self.name, 'joindate': self.joindate, 'url': self.url, 'id': self.id, 'rank': self.rank}

    def load(self, d):
        """
        Loads user data into blank user object from dictionary
        
        <---Args-->
        d(dict): dictionary to load from
        """
        self.name = d['name']
        self.joindate = d['joindate']
        self.url = d['url']
        self.id = d['id']
        self.rank = d['rank']

class UserList:
    """
    Wrapper for holding lists of users associated with a thread. Saves user objects
    as both a list of objects and a dictionary associating them via id. Note that only
    user list is saved upon caching, and dictionary is generated at load time.

    <---Args-->
    users(list(User)): List of user objects to instantiate UserList from

    <--Attributes-->
    users(dict): dictionary associating user ids and user objects in backend via userlist attribute
    """
    def __init__(self, users: [User]):
        self.userlist = users
        self.users = {}
        if len(users) > 0:
            for u in users:
                self.users[u.id] = u

    def handle_user(self, user: User):
        """
        Handler for adding additional user objects to list. This is used to
        avoid duplicate user objects from being added and can be used in deletion checks later
        
        <---Args-->
        user(User): user object to add to list
        """
        if user.id not in self.users.keys():
            self.users[user.id] = user
        elif user.id in self.users.keys():
            if self.users[user.id].joindate == '' and user.joindate != '':
                self.users[user.id].joindate = user.joindate
            if self.users[user.id].rank == '' and user.rank != '':
                self.users[user.id].rank = user.rank

    def check_user(self, user: User):
        """
        Convenience method for checking if user is available in conditionals

        <---Args-->
        user(User): user object to check
        """
        if user.id in self.users.keys():
            return True
        else:
            return False

    def merge(self, src):
        """
        Method for merging userlist with another

        <---Args-->
        src(UserList): UserList to be absorbed
        """
        for user in src.userlist:
            self.handle_user(user)

    def __json__(self):
        """
        Serializes UserList to dictionary for loading into JSON object.
        """
        d = {}
        d['userlist'] = []
        for user in self.userlist:
            d['userlist'].append(user.__json__())
        return d

    def load(self, d):
        """
        Loads UserList object from dictionary.
        
        <---Args-->
        d(dict): dictionary to load from
        """
        for user in d['userlist']:
            u = User('', '', '', '')
            u.load(user)
            self.userlist.append(u)
            
        for u in self.userlist:
            self.users[u.id] = u

class Post:
    """
    Generic post object. Generates unique ID based on author str and postdate. In the case
    that a post is deleted, its id should therefor not even appear in the postlist. Wrapper for
    csv and json functionality later

    <---Args-->
    postdate(str): Date post was originally made, parsed into datetime later
    editdate(str): Date post was edited, if available, parsed into datetime later
    message(str): Message text
    user(User): User object associated with post
    url(str): Thread URL post was made on
    page(str): Page of thread post was found on
    index(str): Index in thread post is on
    category(str): Category thread belongs to

    <--Attributes-->
    editor(User): User that edited this post, if available
    seen_for_mod, seen_for_del (bool): Backend params used for stat tracking
    edit_status(str): Either 'Unedited' or some variation of '**Edited'
    """

    def __init__(self, postdate, editdate, message, user : User, url, page, index, category):
        self.postdate = postdate
        self.editdate = editdate
        date_format = "%b %d, %Y %H:%M:%S"
        if self.postdate != '':
            self.poststamp = datetime.strptime(self.postdate, "%b %d, %Y %I:%M:%S %p")
        if self.editdate != '':
            self.editstamp = datetime.strptime(self.editdate, "%b %d, %Y %I:%M:%S %p")
            self.edit_time = self.editstamp - self.poststamp
            if self.edit_time.days < 0:
                print(self.poststamp, self.editstamp)
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
        self.editor = User('', '', '', '')
        self.seen_for_mod = False
        self.seen_for_del = False
        self.category = category

        if self.message.find('**Edited') != -1 or self.message.find('**edited') != -1:
            self.edit_status = '**Edited**'

    def add_edited(self, user: User):
        """
        Adds a User object as editor of this post

        <---Args-->
        user(User): user object 
        """
        self.editor = user

    def enumerate_data(self, return_str=False):
        """
        Prints all associated data with a post. This is used to flush post data when we find the same
        post id with no content on a later scan.

        <--Args-->
        return_str(bool): determine if we return anything or print to stdout
        """
        if not return_str:
            print(f'Message: {self.message}')
            print(f'URL: {self.url}')
            print(f'Author: {self.author.__str__()}')
            if self.editor.name != '':
                print(f'Editor: {self.editor.__str__()}')
            return None
        else:
            body = ''
            body +=(f'Message: {self.message}')
            body +=(f'URL: {self.url}')
            body +=(f'Author: {self.author.__str__()}')
            if self.editor.name != '':
                body +=(f'Editor: {self.editor.__str__()}')
            return body

        

    def str_to_td(self, s):
        """ 
        Helper for converting a date string to a timedelta, used in determining edit time
        
        <--Args-->
        s(str): string of date in format H:M:S
        """
        t = datetime.strptime(s,"%H:%M:%S")
        delta = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        return delta

    def __str__(self):
        """
        Generic string descriptor for post
        """
        if self.editor.name != '':
            return  f'Post(name={self.author.__str__()}, id={self.id}, url={self.url}, page={self.page}, index={self.index}, editor={self.editor.name})'
        else:
            return f'Post(name={self.author.__str__()}, id={self.id}, url={self.url}, page={self.page}, index={self.index})'

    def __json__(self):
        """
        Serialize object into dictionary for caching, called recursively
        """
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
        d['editor'] = self.editor.__json__()
        d['seen_for_mod'] = self.seen_for_mod
        d['seen_for_del'] = self.seen_for_del
        d['category'] = self.category

        return d

    def load(self, d):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
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
        self.category = d['category']
        u = User('', '', '', '')
        u.load(d['editor'])
        self.editor = u

class PostList:
    """
    Object to encapsulate holding posts in Thread object. Takes in a simple list of Post objects
    and generates a dictionary relating them via post ids. Also has helpers to help with stats tracking

    <--Args-->
    posts(list(Post)): list of posts to instantiate object from

    <--Attributes-->
    posts(dict): dictionary for backend associating post ids and post objects
    post_count(int): current number of posts stored in object
    """
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
        """
        Serialize object into dictionary for caching, called recursively
        """
        d = {}
        d['postlist'] = []
        for post in self.postlist:
            d['postlist'].append(post.__json__())
        d['post_count'] = self.post_count

        return d

    def load(self, d):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
        for item in d['postlist']:
            p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
            p.load(item)
            self.postlist.append(p)
        
        for p in self.postlist:
            self.posts[p.id] = p
        self.post_count = d['post_count']

    def diff(self, other):
        """
        Returns the list of posts in the other postlist that aren't present in the current list.
        Thread object will use this method to determine which posts have been deleted
        
        <--Args-->
        other(PostList): postlist to compare with
        """
        deleted = []
        for post in other.postlist:
            if post.author.id in self.posts.keys():
                if post.id not in self.posts[post.author.id].keys():
                    deleted.append(post)
            else:
                deleted.append(post)

        return DeleteList(deleted)

    def get_post_count(self):
        """
        Convenience method to quickly access and update number of posts in list
        """
        self.post_count = 0
        for post in self.postlist:
            self.post_count += 1

    def add(self, post: Post):
        """
        Adds a post to the object. Updates dictionary, list, and count.

        <--Args-->
        post(Post): post to add to list
        """
        if post.author.id in self.posts.keys():
            self.posts[post.author.id][post.id] = post
        else:
            self.posts[post.author.id] = {post.id: post}
        self.postlist.append(post)
        self.post_count += 1

    def merge(self, src):
        """
        Handler for merging two postlists. Called recursively in higher level objects

        <--Args-->
        src(PostList): postlist to absorb
        """
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
    """
    Backend object to track deleted posts in a similar fashion to postlists. Note that
    the use of this object will be defunct soon.

    <--Args-->
    posts(list(Post)): list of posts to instantiate object from

    <--Attributes-->
    posts(dict): dictionary associating post ids and post objects
    """
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
        """
        Handler for merging two deletelists. Called recursively in higher level objects

        <--Args-->
        src(DeleteList): deletelist to absorb
        """
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
        """
        Adds a post to the object. Updates dictionary, list, and count.

        <--Args-->
        post(Post): post to add to list
        """
        if post.author.id in self.posts.keys():
            self.posts[post.author.id][post.id] = post
        else:
            self.posts[post.author.id] = {post.id: post}

    def __json__(self):
        """
        Serialize object into dictionary for caching, called recursively
        """
        d = {}
        d['deletelist'] = []
        for post in self.deletelist:
            d['deletelist'].append(post.__json__())

        return d

    def load(self, d):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
        for item in d['deletelist']:
            p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
            p.load(item)
            self.deletelist.append(p)

        for p in self.deletelist:
            self.posts[p.id] = p

        
class Thread:
    """
    Object for tracking and representing threads in backend schema. Encapsulates a variety of 
    stat tracking features and makes use of lower level objects defined previously to represent all
    necessary data associated with a URL.

    <--Args-->
    posts(list(Post)): list of post objects scraped from thread
    url(str): thread URL
    op(str): Username that posted this thread TODO: remove this
    category(str): category name used to store thread in higher level cache
    page(int): Page number of category this thread was found on
    postdate(str): datetime-formatted str
    title(str): thread title
    editdate(str): datetime-formatted str, if available
    users(UserList): list of users associated with this thread
    total(int): total number of posts

    <--Attributes-->
    oldest_index(int): current oldest index stored in our list of posts. Used in backend to ensure
    that later scans parse up to this point before finishing the thread
    posts(dict): dictionary associating post ids and posts for backend
    """
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
        """
        Serialize object into dictionary for caching, called recursively
        """
        d = {}
        d['url'] = self.url
        d['title'] = self.title
        d['editdate'] = self.editdate
        d['postdate'] = self.postdate
        d['op'] = self.op
        d['category'] = self.category
        d['postlist'] = []
        u = UserList([])
        for post in self.postlist.postlist:
            d['postlist'].append(post.__json__())
            u.handle_user(post.author)
        d['page'] = self.page
        d['total'] = self.total
        d['users'] = u.__json__()
        d['oldest_index'] = self.oldest_index
        d['post_count'] = self.post_count

        return d

    def load(self, d):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
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
            p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
            p.load(item)
            self.postlist.postlist.append(p)
        for p in self.postlist.postlist:
            self.posts[p.id] = p
        self.users = UserList([])
        for post in self.postlist.postlist:
            self.users.handle_user(post.author)
        self.post_count = d['post_count']
        if len(self.postlist.postlist) > 0:
            self.oldest_index = min([post.index for post in self.postlist.postlist])
        else:
            self.oldest_index = 0


    def refresh_count(self):
        """
        Backend convenience method for getting most recent number of posts
        """
        self.post_count = self.postlist.post_count
        return self.post_count

    def compare(self, src):
        """
        Compare two threads and generate a deletelist. This is used to compare thread objects generated
        from the same source. Recursively calls postlist diff and post compare functions.

        <--Args-->
        src(Thread): thread object to compare to. this thread object should be an older version of the same
        object
        """
        deleted = self.postlist.diff(src.postlist)
        return deleted

    def update(self, src):
        """
        Update thread object with another. This is defunct TODO: remove dependencies on this function

        <--Args-->
        src(Thread): thread object to update from
        """
        src_users = src.users
        src_posts = src.postlist
        self.postlist.merge(src_posts)
        for post in src.posts:
            self.posts[post.id] = post
        self.users.merge(src_users)
        self.get_post_count()


    def get_post_count(self):
        """
        Convenience method for accessing current post count
        TODO: remove one of this, or refresh_count
        """
        self.post_count = 0
        for post in self.postlist.postlist:
            self.post_count += 1

    def sorted(self):
        """
        Return a sorted list of posts by index on page, used for backend comparisons
        """
        return sorted(self.postlist.postlist, key=lambda x: x.index, reverse=True)

    def reverse_iterator(self):
        """
        Generator for returning posts in a backwards fashion.
        TODO: remove this
        """
        index = self.total
        for post in self.postlist.postlist:
            if post.index == index:
                index -= 1
                yield post

    def get_next(self, idx):
        """
        Return next post in postlist from given index.

        <--Args-->
        idx(int): index from which next post should be given from
        """
        for post in self.postlist.postlist:
            if post.index == idx:
                return post

    def __str__(self):
        """
        Generic string descriptor for object
        """
        return f'Thread(title={self.title[:24]}, category={self.category}, posts={self.post_count})'

class Category:
    """
    Higher level structure for holding list of threads found in a given forum category. For example,
    all threads found on the category 'Freelancers' on Upwork would be saved in an object of this type
    with name 'Freelancers'. These objects are stored in DB cache and are main interface from which
    threadlists are accessed

    <--Args-->
    threads(list(Thread)): list of thread objects scraped from this category
    name(str): name of categry we scraped from

    <--Attributes-->
    oldest(Thread): oldest thread associated with category
    """
    def __init__(self, threads: [Thread], name):
        self.name = name
        self.threads = {}
        self.threadlist = threads
        self.oldest = Thread(PostList([]), '', '', '', '', '', '', '', UserList([]), '0')
        if len(threads) > 0:
            for thread in threads:
                self.threads[thread.url] = thread
            self.oldest = self.threads[random.choice(list(self.threads.keys()))]
            self.find_oldest()

    def find_oldest(self):
        """
        Backend method for determining oldest thread in threadlist from datetime str
        """
        for url, thread in self.threads.items():
            dt = datetime.strptime(thread.postdate, "%b %d, %Y %I:%M:%S %p")
            if dt < datetime.strptime(self.oldest.postdate, "%b %d, %Y %I:%M:%S %p"):
                self.oldest = thread


    def merge(self, src):
        """
        Merges two category objects together, with caller absorbing category given as arg.

        <--Args-->
        src(Category): category object to absorb
        """
        for url, thread in src.threads.keys():
            if url in self.threads.keys():
                self.threads[url].update(thread)
            else:
                self.threads[url] = thread
        self.find_oldest()
    
    def add(self, thread: Thread):
        """
        Add thread to threadlist and update backend params. This is used for parsing leftover
        threads from cache that we didn't find on current scan.

        <--Args-->
        thread(Thread): thread to add to category object
        """
        if thread.url in self.threads.keys():
            self.threads[thread.url].update(thread)
        else:
            self.threads[thread.url] = thread
        self.threadlist.append(thread)
        self.find_oldest()

    def __json__(self):
        """
        Serialize object into dictionary for caching, called recursively
        """
        d = {}
        d['name'] = self.name
        d['threadlist'] = []
        for thread in self.threadlist:
            d['threadlist'].append(thread.__json__())
        d['oldest'] = self.oldest.__json__()

        return d

    def load(self, d):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
        self.name = d['name']
        for thread in d['threadlist']:
            t = Thread(PostList([]), '', '', '', '', '', '', '', UserList([]), '0')
            t.load(thread)
            self.threadlist.append(t)
        for t in self.threadlist:
            self.threads[t.url] = t
        self.oldest = d['oldest']

    def __str__(self):
        """
        Generic string descriptor for object
        """
        return f'Category(name={self.name}, threads={len(self.threads.keys())})'

class StatTracker:
    """
    Backend data structure for holding stats found on a scan. Includes information about
    edittimes, modification and deletion tallies, posts found without content, threads that were
    made inaccessible by admins, and average statistics.

    <--Attributes-->
    user_deletions(dict): Relates user ids with deletion counts
    user_modifcations(dict): Relates user ids with modification counts
    deletions(dict): dict mapping category nmes to deletion tallies
    modifications(dict): dict mapping category names to modification tallies
    avg_edit_time(dict): dict mapping category names to average edit times
    avg_timestamp(dict): backend dict used to hold days, hours, minutes, seconds for average edit time
    edit_times(dict): maps category names to post ids to edit times
    min_time(dict): maps min edit time to category name
    max_time(dict): maps max edit time to category names
    no_content(dict): maps category names to dicts holding thread urls and no content post tallies
    under_five(dict): maps category names to lists of posts edited in under five minutes
    deleted_threads(dict): dict mapping category names to lists of inaccessible urls
    total_posts(int): total number of posts seen
    """
    def __init__(self, src=None):
        self.user_deletions = {}
        self.user_modifications = {}
        self.deletions = {}
        self.modifications = {}
        self.avg_edit_time = {}
        self.avg_timestamp = {}
        self.edit_times = {}
        self.min_time = {}
        self.max_time = {}
        self.no_content = {}
        self.under_five = {}
        self.deleted_threads = {}
        self.total_posts = 0
        if src is not None and type(src) is dict:
            self.deletions = src['deletions']
            self.modifications = src['modifications']
            for user, count in src['user_deletions'].items():
                self.user_deletions[user] = count
            for user, count in src['user_modifications'].items():
                self.user_modifications[user] = count
        
    def update_modifications(self, src):
        """
        Reads DB cache and updates backend modification stats from new data

        <--Args-->
        src(dict): dict mapping categories to category names. normally called using
        db.cache, or db.pred.
        """
        for _, category in src.items():
            if category.name not in self.modifications.keys():
                self.modifications[category.name] = 0
            for url, thread in category.threads.items():
                for post in thread.postlist.postlist:
                    self.total_posts += 1
                    if post.edit_status != 'Unedited' and post.edit_status != '<--Deleted-->' and post.seen_for_mod is False:
                        if category.name in self.modifications.keys():
                            self.modifications[category.name] += 1
                        else:
                            self.modifications[category.name] = 1
                        if category.name in self.user_modifications.keys():
                            if post.author.id in self.user_modifications[category.name].keys():
                                self.user_modifications[category.name][post.author.id] += 1
                            else:
                                self.user_modifications[category.name][post.author.id] = 1
                        else:
                            self.user_modifications[category.name] = {}
                            self.user_modifications[category.name][post.author.id] = 1
                        post.seen_for_mod = True

    def update_deletions(self, deletelist: DeleteList):
        """
        Update deletions stats using given deletelist accumulated over a scan. Note that this function
        is currently using defunct dependencies, and should be updated to reflect new logic used for detecting
        deletions.

        <--Args-->
        deletelist(DeleteList): deletelist to update stats from
        """
        for post in deletelist.deletelist:
            if post.seen_for_del is False:
                if post.category in self.deletions.keys():
                    self.deletions[post.category] += 1
                else:
                    self.deletions[post.category] = 1
                if post.category in self.user_deletions.keys():
                    if post.author.id in self.user_deletions[post.category].keys():
                        self.user_deletions[post.category][post.author.id] += 1
                    else:
                        self.user_deletions[post.category][post.author.id] = 1
                else:
                    self.user_deletions[post.category] = {}
                    self.user_deletions[post.category][post.author.id] = 1
                post.seen_for_del = True

    def update_edit_time(self, src):
        """
        Reads DB cache and updates backend edit time stats from new data

        <--Args-->
        src(dict): dict mapping categories to category names. normally called using
        db.cache, or db.pred.
        """
        count, total = 0, 0
        min_ = None
        max_ = None
        for _, category in src.items():
            seen = []
            for url, thread in category.threads.items():
                for post in thread.postlist.postlist:
                    if post.edit_time is not None and post.id not in self.edit_times.keys() and post.edit_status != 'Unedited':
                        total += post.edit_time.seconds
                        count += 1
                        seen.append((post.edit_time, post))
                        if category.name in self.edit_times.keys():
                            self.edit_times[category.name][post.id] = post.edit_time
                        else:
                            self.edit_times[category.name] = {}
                            self.edit_times[category.name][post.id] = post.edit_time

                        if post.edit_time.seconds < 300:
                            if category.name in self.under_five.keys():
                                if post not in self.under_five[category.name]:
                                    self.under_five[category.name].append(post)
                            else:
                                self.under_five[category.name] = [post]
                                
            if count != 0:
                self.avg_edit_time[category.name] = total/count
                self.sec_to_str(total/count, category.name)
            else:
                self.avg_edit_time[category.name] = 0.0
                self.sec_to_str(0, category.name)
            if len(seen) > 0:
                for tup in seen:
                    if tup[1].edit_status == 'Unedited':
                        seen.remove(tup)
                self.min_time[category.name] = min(seen, key = lambda x: x[0])[1]
                self.max_time[category.name] = max(seen, key = lambda x: x[0])[1]
        
    def sec_to_str(self, sec, categ): 
        """
        Backend helper for converting a datetime object into presentable information.
        Note that this is seriously janky and should be fixed. Why am I putting this in a dict?
        """
        days = sec // (24 * 3600) 
        self.avg_timestamp[categ] = {}
        if days < 0:
            self.avg_timestamp[categ]['days'] = 0
        else:
            self.avg_timestamp[categ]['days'] = days
        sec = sec % (24 * 3600) 
        hour = sec // 3600
        self.avg_timestamp[categ]['hours'] = hour
        sec %= 3600
        minutes = sec // 60
        self.avg_timestamp[categ]['minutes'] = minutes
        sec %= 60
        self.avg_timestamp[categ]['seconds'] = sec

    def __json__(self):
        """
        Serialize object into dictionary for caching, called recursively
        """
        d = {}
        d['user_deletions'] = self.user_deletions
        d['user_modifications'] = self.user_modifications
        d['deletions'] = self.deletions
        d['modifications'] = self.modifications
        d['avg_timestamp'] = self.avg_timestamp
        d['avg_edit_time'] = self.avg_edit_time
        d['edit_times'] = {}
        d['under_five'] = {}
        d['min_time'] = {}
        d['max_time'] = {}
        d['no_content'] = self.no_content
        d['total_posts'] = self.total_posts
        for category in self.max_time.keys():
            d['max_time'][category] = self.max_time[category].__json__()
        for category in self.min_time.keys():
            d['min_time'][category] = self.min_time[category].__json__()
        for category, post in self.edit_times.items():
            d['edit_times'][category] = {}
            for pid, edit_time in post.items():
                d['edit_times'][category][pid] = str(edit_time)

        return d

    def load(self, src):
        """
        Helper for loading object from dictionary. Used at loadtime recursively.

        <--Args-->
        d(dict): dict containing object information to load
        """
        self.user_modifications = src['user_modifications']
        self.user_deletions = src['user_deletions']
        self.deletions = src['deletions']
        self.modifications = src['modifications']
        self.edit_times = src['edit_times']
        self.avg_edit_time = src['avg_edit_time']
        self.avg_timestamp = src['avg_timestamp']
        try:
            self.no_content = src['no_content']
        except:
            self.no_content = 0
        try:
            self.total_posts = src['total_posts']
        except:
            self.total_posts = 0

        for category, _dict in src['min_time'].items():
            p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
            p.load(_dict)
            if category in self.min_time.keys():
                self.min_time[category][p.id] = p
            else:
                self.min_time[category] = {p.id: p}
        for category, _dict in src['max_time'].items():
            p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
            p.load(_dict)
            if category in self.max_time.keys():
                self.max_time[category][p.id] = p
            else:
                self.max_time[category] = {p.id: p}

        for category in src['under_five'].items():
            li = []
            for obj in src['under_five'][category]:
                p = Post('', '', '', User('', '', '', ''), '', '', '0', '')
                p.load(obj)
                li.append(obj)
            self.under_five[category] = li

class SiteDB:
    """
    DB object used to store all information about a given scan. Maps category names to category objects
    given in argument, and encapsulates a variety of high level functions that are interfaced in the scraping
    script. 

    <--Args-->
    categories(list(Category)): list of categories to store in cache
    name(str): name of site we are making this DB for
    """
    def __init__(self, categories: [Category], name):
        self.name = name
        self.users = UserList([])
        self.pred = {}
        self.deletes = {}
        self.cache = {}
        self.categories = categories
        self.stats = StatTracker()
        now = datetime.now()
        self.last_scan = now.strftime("%Y-%m-%d %H:%M:%S")
        self.scan_start = now.strftime("%Y-%m-%d %H:%M:%S")

        if len(categories) > 0:
            for category in categories:
                self.cache[category.name] = category
                for _, thread in category.threads.items():
                    self.users.merge(thread.users)

    def add(self, entry: Category):
        """
        Adds a category object into our cache. Updates stats based on new data.

        entry(Category): Category object to add to the cache. Normally this is the result
        of crawler.parse_page.
        """
        self.categories.append(entry)
        self.cache[entry.name] = entry
        for _, thread in entry.threads.items():
            self.users.merge(thread.users)
        self.stats.update_modifications(self.cache)
        self.stats.update_edit_time(self.cache)

    def set_start(self, dt):
        """
        Set start timestamp using given datetime object

        dt(datetime): datetime to cast to string and set scan start to
        """
        self.scan_start = dt.strftime("%Y-%m-%d %H:%M:%S")

    def find_oldest_index(self, url, category):
        """
        Findest oldest index for a given url in the category. This is used find the oldest index
        for a thread without the need to interface lower level objects with cumbersome looping

        <--Args-->
        url(str): key to check our cache for
        category(str): key to access our cache with
        """
        if category in self.pred.keys():
            if url in self.pred[category].threads.keys():
                return self.pred[category].threads[url].oldest_index
            else:
                return 0
        else:
            return 0

    def load(self, debug=False, file=None):
        """
        Main load function. Files are stored in directories named from the date of their creation. 
        zip archives are stored in these directories with a filename denoting their version. This funciton
        finds the latest directory to load from, and the newest zip archived saved inside it. After unzipping,
        data is loaded from json to dict format and dictionary partitions are sent to blank objects for loading.
        The data saved is db.cache, so blank category objects are created with each object in the dictionary
        being used for recursive loading.
        """
        import tempfile, glob
        from zipfile import ZipFile
        from datetime import timedelta
        filenames = [ f.path for f in os.scandir(os.getcwd() + '/cache/logs') if f.is_dir() ]
        now = datetime.now().strftime("%Y-%m-%d")
        if len(filenames) > 0:
            if os.getcwd() + f'/cache/logs/{now}' in filenames:
                list_of_files = glob.glob(os.getcwd() + f'/cache/logs/{now}/*.zip') # * means all if need specific format then *.csv
                curr = None
            else:
                i = 1
                while True:
                    #now = datetime.strptime(now, "%Y-%m-%d")
                    curr = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                    list_of_files = glob.glob(os.getcwd() + f'/cache/logs/{curr}/*.zip')
                    if len(list_of_files) > 0:
                        break
                    else:    
                        i += 1
            if len(list_of_files) != 0:
                latest_file = max(list_of_files, key=os.path.getctime)
                v = str(int(latest_file.split('v')[1].split('.zip')[0]))
                if file is None:
                    print(f'Loading from {latest_file}...')
                    if curr is not None:
                        with ZipFile(os.getcwd() + f'/cache/logs/{curr}/{os.path.basename(latest_file)}', 'r') as z:
                            print(z.namelist())
                            with z.open(f'v{v}.json', 'r') as f:
                                data = json.load(f)
                                self.dict_load(data)
                            with z.open(f"stats_v{v}.json", 'r') as f:
                                data = json.load(f)
                                self.stats.load(data)
                    else:
                        with ZipFile(os.getcwd() + f'/cache/logs/{now}/{os.path.basename(latest_file)}', 'r') as z:
                            with z.open(f'v{v}.json', 'r') as f:
                                data = json.load(f)
                                self.dict_load(data)
                            with z.open(f"stats_v{v}.json", 'r') as f:
                                data = json.load(f)
                                self.stats.load(data)
            
    def load_from_raw_json(self, d):
        """
        Loads data from a raw, unzipped json object. Requires a path to cache directory

        <--Args-->
        d(str): path to json file to load from
        """
        with open(os.getcwd() + d, 'r') as f:
            data = json.load(f)
            self.dict_load(data)
                    

    def to_json(self):
        """
        Serializes object into a json object. NOTE: This is defunct.
        """
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

    def compile(self):
        """
        Graceful serializing helper that recursively uses child objects' __json__ method
        to properly convert all data to a savable/loadable format
        """
        self.stats.update_modifications(self.cache)
        self.stats.update_edit_time(self.cache)
        d = {}
        d['name'] = self.name
        d['users'] = self.users.__json__()
        d['deletes'] = {}
        d['categories'] = []
        for url, deletelist in self.deletes.items():
            d['deletes'][url] = deletelist.__json__()
        for category in self.categories:
            d['categories'].append(category.__json__())
        d['stats'] = self.stats.__json__()
        if self.last_scan is not None:
            d['last_scan'] = self.last_scan

        return d

    def dict_load(self, d, debug=False):
        """
        Helper for loading db object from dictionary

        <--Args-->
        d(dict): dict object to load db object from
        """
        self.name = d['name']
        u = UserList([])
        u.load(d['users'])
        self.users = u
        for url in d['deletes'].keys():
            dl = DeleteList([])
            dl.load(d['deletes'][url])
            self.deletes[url] = dl
        for category in d['categories']:
            c = Category([], '')
            c.load(category)
            self.categories.append(c)
            self.cache[c.name] = c
        self.stats.load(d['stats'])
        try:
            self.last_scan = d['last_scan']
        except:
            now = datetime.now()
            self.last_scan = now.strftime("%Y-%m-%d %H:%M:%S")

    def get_remaining(self, category: Category):
        """
        If we have data cached from a previous scan, this finds threads that were previously
        in the given category object and were no longer found in our current cache. Returns
        a list of urls to check.

        <--Args-->
        category(Category): Category object to check from
        """
        li = []
        if category.name in self.pred.keys():
            for thread in self.pred[category.name].threadlist:
                if thread.url not in category.threads.keys():
                    li.append(thread.url)

        return li

    def compare(self, src):
        """
        Compares two sitedbs and generates a backend dict mapping thread urls to deletelists.
        Because deletelists will become defunct soon, it is important that this is updated to remain
        functional.

        src(SiteDB): object to compare with
        """
        if src is not None and src:
            self.users.merge(src.users)
            for _, category in self.cache.items():
                for url, thread in category.threads.items():
                    if url in src.cache[category.name].threads.keys():
                        self.deletes[url] = thread.compare(src.cache[category.name].threads[url])
                        for post in self.deletes[url].deletelist:
                            self.users.handle_user(post.author)
                    else:
                        li = []
                        for post in thread.postlist.postlist:
                            li.append(post)
                        d = DeleteList(li)
                        self.deletes[url] = d

        for deletelist in self.deletes.values():
            self.stats.update_deletions(deletelist)

        return self.deletes

    def compare_pred(self):
        """
        Alternate method of comparing for deletions that compares current cache with previously stored data.
        Rather than generating a deletelist, simply returns a list of posts that were no longer found in the cache.
        """
        li = []
        for name, category in self.pred.items():
            if name in self.cache.keys():
                for url, thread in category.threads.items():
                    if url in self.cache[category.name].threads.keys():
                        for post in thread.postlist.postlist:
                            if post.id not in self.cache[category.name].threads[url].posts.keys():
                                li.append(post)
                            elif post.id in self.cache[category.name].threads[url].posts.keys() and \
                                self.cache[category.name].threads[url].posts[post.id].message == '':
                                li.append(post)
                    else:
                        for post in thread.postlist.postlist:
                            li.append(post)

        return li

    def write(self):
        """
        Main caching and exporting function. Serializes current cache, stats as json and stores 
        it in a zip archive with filename denoting scan version for this dirctory. Directories are
        denoted with date of creation and are meant to hold all archives associated with scans on this day
        """
        from zipfile import ZipFile
        now = datetime.now().strftime("%Y-%m-%d")
        if not os.path.isdir(os.getcwd() + f'/cache/logs/{now}'):
            os.mkdir(os.getcwd() + f'/cache/logs/{now}')
        try:
            with ZipFile(os.getcwd() + '/cache/logs/{}/v1.zip'.format(now), 'x') as z:
                with z.open('v1.json', 'w') as f:
                    d = self.compile()
                    f.write(json.dumps(d, indent=4).encode('utf-8'))
                with z.open(f'stats_v1.json', 'w') as f:
                    f.write(json.dumps(self.stats.__json__(), indent=4).encode('utf-8'))
        except FileExistsError:
                import glob
                list_of_files = glob.glob(os.getcwd() + f'/cache/logs/{now}/*.zip') # * means all if need specific format then *.csv
                latest_file = max(list_of_files, key=os.path.getctime)
                with ZipFile(os.getcwd() + '/cache/logs/{}/v{}.zip'.format(now, str(int(latest_file.split('v')[1].split('.zip')[0]) + 1)), 'x') as z:
                        with z.open('v{}.json'.format(str(int(latest_file.split('v')[1].split('.zip')[0]) + 1)), 'w') as f:
                            d = self.compile()
                            f.write(json.dumps(d, indent=4).encode('utf-8'))
                        with z.open(f"stats_v{str(int(latest_file.split('v')[1].split('.zip')[0]) + 1)}.json", 'w') as f:
                            f.write(json.dumps(self.stats.__json__(), indent=4).encode('utf-8'))
            
        with open(os.getcwd() + f'/cache/csv/{datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            f = csv.writer(f)
            f.writerow(["title", "post_date", "edit_date", "edit_time", "message_text",\
                    "post_moderation", "category", "url", "page", "index", "user_name", \
                    "user_id", "user_rank", "user_joindate", "user_url", "editor_name", \
                    "editor_id", "editor_joindate", "editor_url", "editor_rank"])
            for category in self.categories:
                for thread in category.threadlist:
                    for author, post in thread.posts.items():
                        if post.message != '':
                            f.writerow([thread.title, post.postdate, post.editdate, post.edit_time, post.message, \
                            post.edit_status, category.name, thread.url, post.page, post.index,\
                            post.author.name, post.author.id, post.author.rank, post.author.joindate, \
                            post.author.url, post.editor.name, post.editor.id, post.editor.joindate, post.editor.url, post.editor.rank])
                        else:
                            try:
                                if post.id in self.pred[category.name].threads[post.url].postlist.posts.keys():
                                    old_post = self.pred[category.name].threads[post.url].postlist.posts[post.id]
                                    f.writerow([thread.title, post.postdate, post.editdate, post.edit_time, old_post.message, \
                                    '<--Deleted-->', category.name, thread.url, post.page, post.index,\
                                    post.author.name, post.author.id, post.author.rank, post.author.joindate, \
                                    post.author.url, post.editor.name, post.editor.id, post.editor.joindate, post.editor.url, post.editor.rank])
                            except KeyError:
                                pass
                    if thread.url in self.deletes.keys():
                        for post in self.deletes[thread.url].deletelist:
                            f.writerow([thread.title, post.postdate, post.editdate, post.edit_time, post.message, \
                            '<--Deleted-->', category.name, thread.url, post.page, post.index,\
                            post.author.name, post.author.id, post.author.rank, post.author.joindate, \
                            post.author.url, post.editor.name, post.editor.id, post.editor.joindate, post.editor.url, post.editor.rank])
            if category.name in self.stats.deleted_threads.keys():
                for url in self.stats.deleted_threads[category.name]:
                    try:
                        if url in self.pred[category.name].threads.keys():
                            entry = self.pred[category.name].threads[url]
                            for post in entry.postlist.postlist:
                                f.writerow([thread.title, post.postdate, post.editdate, post.edit_time, post.message, \
                                '<--Deleted-->', category.name, thread.url, post.page, post.index,\
                                post.author.name, post.author.id, post.author.rank, post.author.joindate, \
                                post.author.url, post.editor.name, post.editor.id, post.editor.joindate, post.editor.url, post.editor.rank])
                    except KeyError:
                        pass

        self.report()
        self.save_log()

    def report(self):
        """
        Main reporting method for stats accumulated during last scan. Simply flushes results to stdout.
        Consider adding a more sophisticated report method (tabulate, etc.) and saving this as a logfile.
        """
        now = datetime.now()
        diff = now - datetime.strptime(self.last_scan, "%Y-%m-%d %H:%M:%S")
        dur =  now - datetime.strptime(self.scan_start, "%Y-%m-%d %H:%M:%S")
        days, hours, minutes = diff.days, diff.seconds // 3600, diff.seconds // 60 % 60
        durdays, durhours, durmins = dur.days, dur.seconds // 3600, dur.seconds // 60 % 60
        print(f'Scan took {durhours} hours, {durmins} minutes\n')
        print(f'{days} days, {hours} hours, and {minutes} minutes since last scan.\n')
        if len(self.stats.deletions.keys()) > 0:
            for category in self.stats.deletions.keys():
                if self.stats.deletions[category] > 0:
                    print(f'{self.stats.deletions[category]} posts no longer found in category {category}\n')
                else:
                    print(f'No posts found deleted in category {category}\n')
        li = self.compare_pred()
        if len(li) > 0:
            print(f'{len(li)} Posts found deleted w/o DeleteList:\n')
            #for post in li:
                #post.enumerate_data(return_str=False)
        else:
            print('No deletions detected since last scan.')
        for category in self.stats.modifications.keys():
            print(f'{self.stats.modifications[category]} posts moderated in category {category}\n')
        sum_ = 0
        for category in self.stats.avg_timestamp.keys():
            days = self.stats.avg_timestamp[category]['days']
            hours = self.stats.avg_timestamp[category]['hours']
            mins = self.stats.avg_timestamp[category]['minutes']
            secs = self.stats.avg_timestamp[category]['seconds']
            print(f'Average moderation time on a post in category {category} was {days} days, {hours} hours, {mins} minutes, {secs} seconds\n')
            try:
                print(f'Min edit time: {self.stats.min_time[category].edit_time} on {self.stats.min_time[category].__str__()}\n')
                print(f'Max edit time: {self.stats.max_time[category].edit_time} on {self.stats.max_time[category].__str__()}\n')
            except:
                pass
            if category in self.stats.under_five.keys():
                print(f'{len(self.stats.under_five[category])} posts edited in under five minutes for {category}')
            if category in self.stats.no_content.keys():
                s = 0
                for url, count in self.stats.no_content[category].items():
                    s += count
                print(f'{s} posts found without content in category {category}')
                sum_ += s
            if category in self.stats.deleted_threads.keys():
                print(f'Got {len(self.stats.deleted_threads[category])} threads that were inaccessible')
                for url in self.stats.deleted_threads[category]:
                    try:
                        thread = self.pred[category].threads[url]
                        print(f'Thread {url} no longer found and we have cached data for it')
                        #for post in thread.postlist.postlist:
                        #   _ = post.enumerate_data()
                            #print(post.__str__())
                        #print(self.pred[category].threads[url].__str__())
                    except:
                        print(f'Thread {url} no longer found and we do not have cached data for it')
        print(f'Total of {sum_} posts found without content')
        for name, category in self.cache.items():
            for thread in category.threadlist:
                for post in thread.postlist.postlist:
                    if post.message == '':
                        if category.name in self.pred.keys():
                            if thread.url in self.pred[category.name].threads.keys():
                                if post.id in self.pred[category.name].threads[thread.url].posts.keys():
                                    if self.pred[category.name].threads[thread.url].posts[post.id].message != '':
                                        print(self.pred[category.name].threads[thread.url].posts[post.id].enumerate_data(return_str=True))

    def create_log(self):
        """
        Creates a str to log to file in same format as report function above. Incldues additional
        information such as individual post and threads stats.
        """
        body = ''
        now = datetime.now()
        diff = now - datetime.strptime(self.last_scan, "%Y-%m-%d %H:%M:%S")
        dur =  now - datetime.strptime(self.scan_start, "%Y-%m-%d %H:%M:%S")
        days, hours, minutes = diff.days, diff.seconds // 3600, diff.seconds // 60 % 60
        durdays, durhours, durmins = dur.days, dur.seconds // 3600, dur.seconds // 60 % 60
        body += (f'Scan took {durhours} hours, {durmins} minutes\n')
        body += (f'{days} days, {hours} hours, and {minutes} minutes since last scan.\n')
        if len(self.stats.deletions.keys()) > 0:
            for category in self.stats.deletions.keys():
                if self.stats.deletions[category] > 0:
                    body += (f'{self.stats.deletions[category]} posts no longer found in category {category}\n')
                else:
                    body += (f'No posts found deleted in category {category}\n')
        li = self.compare_pred()
        if len(li) > 0:
            body += (f'{len(li)} Posts found deleted w/o DeleteList:\n')
            #for post in li:
            #    body += post.enumerate_data(return_str=True)
        else:
            body += ('No deletions detected since last scan.')
        for category in self.stats.modifications.keys():
            body += (f'{self.stats.modifications[category]} posts moderated in category {category}\n')
        sum_ = 0
        for category in self.stats.avg_timestamp.keys():
            days = self.stats.avg_timestamp[category]['days']
            hours = self.stats.avg_timestamp[category]['hours']
            mins = self.stats.avg_timestamp[category]['minutes']
            secs = self.stats.avg_timestamp[category]['seconds']
            body += (f'Average moderation time on a post in category {category} was {days} days, {hours} hours, {mins} minutes, {secs} seconds\n')
            try:
                body += (f'Min edit time: {self.stats.min_time[category].edit_time} on {self.stats.min_time[category].__str__()}\n')
                body += (f'Max edit time: {self.stats.max_time[category].edit_time} on {self.stats.max_time[category].__str__()}\n')
            except:
                pass
            if category in self.stats.under_five.keys():
                body += (f'{len(self.stats.under_five[category])} posts edited in under five minutes for {category}')
            if category in self.stats.no_content.keys():
                s = 0
                for url, count in self.stats.no_content[category].items():
                    s += count
                body += (f'{s} posts found without content in category {category}')
                sum_ += s
            if category in self.stats.deleted_threads.keys():
                print(f'Got {len(self.stats.deleted_threads[category])} threads that were inaccessible')
                for url in self.stats.deleted_threads[category]:
                    try:
                        thread = self.pred[category].threads[url]
                        body += (f'Thread {url} no longer found and we have cached data for it')
                        for post in thread.postlist.postlist:
                            body += (post.enumerate_data(return_str=True))
                        #print(self.pred[category].threads[url].__str__())
                    except:
                        body += (f'Thread {url} no longer found and we do not have cached data for it')
        body +=(f'Total of {sum_} posts found without content')

        for name, category in self.cache.items():
            for thread in category.threadlist:
                for post in thread.postlist.postlist:
                    if post.message == '':
                        if category.name in self.pred.keys():
                            if thread.url in self.pred[category.name].threads.keys():
                                if post.id in self.pred[category.name].threads[thread.url].posts:
                                    if self.pred[category.name].threads[thread.url].message != '':
                                        body += self.pred[category.name].threads[thread.url].posts[post.id].enumerate_data(return_str=True)

        return body

    def save_log(self):
        """
        Saves a logfile with a simple naming scheme using the data created in the function above
        Saves to the 'reports' directory in cache
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.getcwd() + f'/cache/reports/{now}', 'w') as f:
            data = self.create_log()
            f.write(data)
