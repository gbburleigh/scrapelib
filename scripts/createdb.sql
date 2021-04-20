CREATE TABLE categories (
    cid integer NOT NULL,
    category_name text NOT NULL,
    category_url text NOT NULL,
    page_count integer,
    thread_count integer
);

CREATE TABLE threads (
    tid text NOT NULL,
    category_id integer NOT NULL,
    title text NOT NULL,
    post_date text NOT NULL,
    edit_date text,
    thread_url text NOT NULL,
    author_name text NOT NULL,
    post_count text
);

CREATE TABLE posts (
    pid text NOT NULL,
    tid text NOT NULL,
    cid text NOT NULL,
    message_text text NOT NULL,
    post_date text NOT NULL,
    edit_date text,
    edit_time text,
    author_id text NOT NULL,
    editor_id text,
    edit_status text NOT NULL,
    post_page integer NOT NULL,
    post_index integer NOT NULL
);

CREATE TABLE users (
    uid text NOT NULL,
    user_name text NOT NULL,
    user_url text NOT NULL,
    join_date text,
    user_rank text NOT NULL
);