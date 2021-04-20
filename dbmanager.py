import sqlite3
import os
from sqlite3 import Error
from header import *

class DBConn:
    def __init__(self):
        self.conn = None
        self.create_connection()
        self.curs = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.conn.close()
        except:
            pass

    def create_connection(self, db_file=os.getcwd() + '/cache/sql/upwork.db'):
        try:
            self.conn = sqlite3.connect(db_file)
            #self.conn.execute("PRAGMA foreign_keys = 1")
        except Error as e:
            print(e)

    def create_tables(self):
        fd = open(os.getcwd() + '/scripts/createdb.sql', 'r')
        sql_file = fd.read()
        fd.close()

        sql_commands = sql_file.split(';')

        for command in sql_commands:
            try:
                self.curs.execute(command)
            except Error as e:
                print(e)

    def generate_db(self):
        fd = open('upwork-data.sql', 'r')
        sql_file = fd.read()
        fd.close()

        sql_commands = sql_file.split(';')

        for command in sql_commands:
            try:
                self.curs.execute(command)
            except Error as e:
                print(e)

    def insert_category(self, id, name, url, page_count='NULL', thread_count='NULL'):
        self.curs.execute(f'''
            INSERT INTO categories VALUES
            ({id}, {name}, {url}, {page_count}, {thread_count})
        ''')
        self.conn.commit()

    def insert_from_category(self, category: Category):
        self.curs.execute("SELECT rowid FROM categories WHERE cid = ?", (int(category.id),))
        data = self.curs.fetchall()
        if len(data)==0:
            print(f'Inserting category into database w/ id {category.id}')
            self.curs.execute(f"""
                INSERT INTO categories(cid, category_name, category_url, page_count, thread_count) VALUES
                (?, ?, ?, ?, ?);
            """, (int(category.id), str(category.name), str(category.url), int(category.page_count), len(category.threadlist)))
            self.conn.commit()

    def insert_thread(self, id, category_id, title, post_date, thread_url, author_name, \
        edit_date='NULL', post_count='NULL'):
        self.curs.execute(f'''
            INSERT INTO threads VALUES
            ({id}, {category_id}, {title}, {post_date}, {edit_date}, 
            {thread_url}, {author_name}, {post_count})
        ''')
        self.conn.commit()

    def insert_from_thread(self, thread: Thread, category_id):
        self.curs.execute("SELECT rowid FROM threads WHERE tid = ?", (str(thread.id),))
        data = self.curs.fetchall()
        if len(data)==0:
            print(f'Inserting thread into database w/ id {thread.id}')
            self.curs.execute(f"""
                INSERT INTO threads(tid, category_id, title, post_date, edit_date, thread_url, author_name, post_count) VALUES
                (?, ?, ?, ?, ?, ?, ?, ?);
            """, (str(thread.id), int(category_id), str(thread.title), str(thread.postdate), str(thread.editdate), 
                str(thread.url), str(thread.op), int(thread.post_count)))
            self.conn.commit()
        else:
            print('Thread id already found in DB')

    def insert_post(self, id, thread_id, category_id, message_text, author_id, \
        edit_status, post_page, post_index, edit_date='NULL', edit_time='NULL', editor_id='NULL'):
        self.curs.execute(f'''
            INSERT INTO posts (pid, tid, cid, message_text, post_date, edit_date, edit_time, author_id, 
            editor_id, edit_status, post_page, post_index) VALUES
            ({id}, {thread_id}, {category_id}, {message_text}, {post_date}, 
            {edit_date}, {edit_time}, {author_id}, {editor_id}, {edit_status},
            {post_page}, {post_index})
        ''')
        self.conn.commit()

    def insert_from_post(self, post: Post, thread_id, category_id):
        self.curs.execute("SELECT rowid FROM posts WHERE pid = ?", (str(post.id),))
        data = self.curs.fetchall()
        if len(data)==0:
            print(f'Inserting post into database w/ id {post.id}')
            self.curs.execute(f"""
                INSERT INTO posts(pid, tid, cid, message_text, post_date, edit_date, edit_time, author_id, 
                editor_id, edit_status, post_page, post_index) VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (str(post.id), str(thread_id), str(category_id), str(post.message), str(post.postdate), str(post.editdate), str(post.edit_time), \
                str(post.author.id), str(post.editor.id), str(post.edit_status), int(post.page), int(post.index)))
            self.conn.commit()
        else:
            print('Post id already found in DB')

    def insert_user(self, uid, user_name, user_url, join_date, user_rank):
        self.curs.execute(f'''
            INSERT INTO users(uid, user_name, user_url, join_date, user_rank) VALUES
            ('?', '?', '?', '?', '?')
        ''', (str(uid), str(user_name), str(user_url), str(join_date), str(user_rank)))
        self.conn.commit()

    def insert_from_user(self, user: User):
        self.curs.execute("SELECT rowid FROM users WHERE uid = ?", (str(user.id),))
        data = self.curs.fetchall()
        if len(data)==0:
            print(f'Inserting user into database w/ id {user.id}')
            self.curs.execute(f"""
                INSERT INTO users(uid, user_name, user_url, join_date, user_rank) VALUES
                (?, ?, ?, ?, ?);
            """, (str(user.id), str(user.name), str(user.url), str(user.joindate), str(user.rank)))
            self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except:
            pass

if __name__ == "__main__":
    d = DBConn()
    if '--create' in sys.argv:
        d.create_tables()