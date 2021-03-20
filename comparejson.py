import json, os, datetime
from header import *

if __name__ == "__main__":
    old_db = SiteDB([], 'upwork')
    #old_db.load(debug=True, file='2021-03-14.json')

    old_db.load_from_raw_json('/v2/v2.json')

    new_db = SiteDB([], 'upwork')
    new_db.load_from_raw_json('/v3/v3.json')
    #new_db.load(debug=True, file='2021-03-15.json')

    not_in_old = []
    old = []
    new = []
    newdict = {}
    olddict = {}
    newthreads = {}
    oldthreads = {}

    for name, category in new_db.cache.items():
        for url, thread in category.threads.items():
            #if name in old_db.cache.keys() and url in old_db.cache[name].threads.keys():
            for pid, post in thread.posts.items():
                    #if pid not in old_db.cache[name].threads[url].posts.keys():
                new.append(pid)
                newdict[pid] = post
            newthreads[url] = thread

    for name, category in old_db.cache.items():
        for url, thread in category.threads.items():
            #if name in old_db.cache.keys() and url in old_db.cache[name].threads.keys():
            for pid, post in thread.posts.items():
                    #if pid not in old_db.cache[name].threads[url].posts.keys():
                old.append(pid)
                olddict[pid] = post
        oldthreads[url] = thread
            #else:
                #print('thread url not found')
        #print('category name not found')

    for pid in olddict.keys():
        if pid not in newdict.keys():
            not_in_old.append(pid)

    missing_urls_old = []
    missing_urls_new = []
    for url in oldthreads.keys():
        if url not in newthreads.keys():
            missing_urls_new.append(url)

    for url in newthreads.keys():
        if url not in oldthreads.keys():
            missing_urls_old.append(url)

    # for url, thread in newthreads.items():
    #     if url in oldthreads.keys():
    #         print('OLDEST INDEX COMPARE: ', thread.oldest_index, oldthreads[url].oldest_index)
    #         for post in oldthreads[url].postlist.postlist:
    #             if post.index < thread.oldest_index:
    #                 if post.id not in thread.posts.keys():
    #                     not_in_old.append(post.id)
    #                 else:
    #                     print('post id found successfully')
    #             else:
    #                 print('Old post index is older than our given oldest index, something went wrong')
    #     else:
    #         print('url not found')
    # for pid in old:
    #     if pid not in new:
    #         not_in_old.append(pid)


#    print(not_in_old)
    print(f'Total posts in old: {len(olddict.keys())}')
    print(f'Total posts in new: {len(newdict.keys())}')
    print(f'Total threads in old and not in new {len(missing_urls_new)}')
    print(missing_urls_new)
    print(f'Total threads in new and not in old {len(missing_urls_old)}')
    # for i in range(10):
    #     print(olddict[not_in_old[i]].__str__())
    #     print(oldthreads[olddict[not_in_old[i]].url].oldest_index)
    #
