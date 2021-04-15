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

    def __exit__(self):
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
        fd = open('/scripts/createdb.sql', 'r')
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
        self.curs.execute(f'''
            INSERT INTO categories VALUES
            ({category.id}, {category.name}, {category.url}, {category.page_count}, {len(category.threadlist)})
        ''')
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
        self.curs.execute(f'''
            INSERT INTO threads VALUES
            ({thread.id}, {category_id}, {thread.title}, {thread.postdate}, {thread.editdate}, 
            {thread.url}, {thread.op}, {thread.post_count})
        ''')
        self.conn.commit()

    def insert_post(self, id, thread_id, category_id, message_text, author_id, \
        edit_status, post_page, post_index, edit_date='NULL', edit_time='NULL', editor_id='NULL'):
        self.curs.execute(f'''
            INSERT INTO posts VALUES
            ({id}, {thread_id}, {category_id}, {message_text}, {post_date}, 
            {edit_date}, {edit_time}, {author_id}, {editor_id}, {edit_status},
            {post_page}, {post_index})
        ''')
        self.conn.commit()

    def insert_from_post(self, post: Post, thread_id, category_id):
        self.curs.execute(f'''
            INSERT INTO posts VALUES
            ({post.id}, {thread_id}, {category_id}, {post.message}, {post.postdate}, 
            {post.editdate}, {post.edit_time}, {post.author.id}, {post.editor.id}, {post.edit_status},
            {post.page}, {post.index})
        ''')
        self.conn.commit()

    def insert_user(self, id, user_name, user_url, join_date, user_rank):
        self.curs.execute(f'''
            INSERT INTO users VALUES
            ({id}, {user_name}, {user_url}, {join_date}, {user_rank})
        ''')
        self.conn.commit()

    def insert_from_user(self, user: User):
        self.curs.execute(f'''
            INSERT INTO users VALUES
            ({user.id}, {user.name}, {user.url}, {user.joindate}, {user.rank})
        ''')
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