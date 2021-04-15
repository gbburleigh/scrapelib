CREATE TABLE categories (
    cid integer NOT NULL,
    category_name text NOT NULL,
    category_url text NOT NULL,
    page_count integer,
    thread_count integer
);

CREATE TABLE threads (
    tid integer NOT NULL,
    category_id integer NOT NULL,
    title text NOT NULL,
    post_date text NOT NULL,
    edit_date text,
    thread_url text NOT NULL,
    author_name text NOT NULL,
    post_count text
);

CREATE TABLE posts (
    pid integer NOT NULL,
    tid integer NOT NULL,
    c_id integer NOT NULL,
    message_text text NOT NULL,
    post_date text NOT NULL,
    edit_date text,
    edit_time text,
    author_id integer NOT NULL,
    editor_id integer,
    edit_status text NOT NULL,
    post_page integer NOT NULL,
    post_index integer NOT NULL
);

CREATE TABLE users (
    uid integer NOT NULL,
    user_name text NOT NULL,
    user_url text NOT NULL,
    join_date text,
    user_rank text NOT NULL
);