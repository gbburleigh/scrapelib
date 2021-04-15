from zipfile import ZipFile
from dbmanager import DBConn
import os

with open('upwork-data.sql.zip', 'x') as z:
    with z.open('upwork-data.sql', 'w') as f:
        with DBConn as d:
            data = '\n'.join(d.conn.iterdump())
            f.write(data)