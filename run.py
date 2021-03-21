from header import *
from scraper import *
from driver import *
from crawler import *

import schedule


def run():
    now = datetime.now()
    print(f'Starting scan at {now}')
    d = Driver(start=now)
    if '-flush' in sys.argv:
        d.flush()
    try:
        d.run()
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    d.close()

schedule.every(4).hours.do(run)

run()
while True:
    schedule.run_pending()