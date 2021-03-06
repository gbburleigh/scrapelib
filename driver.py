import sys,os, signal

#Configure packages FIXME
if sys.prefix == sys.base_prefix:
    import subprocess
    print('Configuring...')
    os.system('. resources/activate.sh')

import time, json, logging, schedule, datetime, atexit, csv
from selenium import webdriver
from crawler import Crawler

class Driver:
    def __init__(self, flush=False, start=None):

        #Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.fh = logging.FileHandler(os.getcwd() + '/cache/sys/debug.log', 'w+')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        self.formatter = logging.Formatter('[%(levelname)s :: (%(asctime)s)]: %(message)s')
        self.fh.setFormatter(self.formatter)
        self.ch.setFormatter(self.formatter)
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)
        self.last_scan = datetime.datetime.now()
        if start is None:
            self.scan_start = datetime.datetime.now()
        else:
            self.scan_start = start

        if flush is False:
            #Configure history dictionary and load data into it if possible
            self.hist, self.stats, self.users, self.genesis = {}, {}, {}, {}
            self.load_history()

            #Instantiate backend tracking fields
            self.read_stats()
            self.ref = {}

            """DEPRECATED"""
            self.find_oldest_post()
        else:
            self.flush()
            self.hist, self.stats, self.users, self.genesis = {}, {}, {}, {}
        #self.read_genesis()

        #Configure webdriver
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            try:
                self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                    firefox_options=options, log_path=os.getcwd() + '/cache/sys/geckodriver.log')
            except OSError:
                #Add a check to make sure geckodriver binary isn't busy already
                import subprocess
                try:
                    out = subprocess.check_output(['lsof', '/home/gbb5412/.wdm/drivers/geckodriver/linux64/v0.29.0/geckodriver'],\
                        stderr=open(os.devnull, 'w'))
                    pids = []
                    lines = out.strip().split('\n')
                    for line in lines:
                        pids.append(int(line))
                    for pid in pids:
                        subprocess.call(['kill', pid])
                    self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                        firefox_options=options, log_path=os.getcwd()+ '/cache/sys/geckodriver.log')
                except Exception as e:
                    self.logger.critical(f'Error while terminating existing driver processes: {e}')
                    self.logger.critical("Try 'lsof [path to .wdm]/.wdm/drivers/geckodriver/linux64/v0.29.0/geckodriver' and 'kill' each pid listed")
                    self.email_results(warn=True)
                    self.logger.critical('This issue has been reported.')
                    self.close()
        else:
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager import chrome
            from webdriver_manager.chrome import ChromeDriverManager
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            self.webdriver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        #Configure scheduling
        schedule.every().day.at('00:00').do(self.run)

    def read_genesis(self):
        """DEPRECATED"""
        #Right now this is really inefficient. Should only be used at init time
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        filenames.remove('debug.log')
        newest_file = str(max([datetime.datetime.strptime(x.strip('.json'), '%Y-%m-%d') for x in filenames]).date()) + '.json'
        print(f'reading {newest_file}')
        try:
            with open(os.getcwd() + '/cache/logs/' + newest_file, 'r') as f:
                data = json.load(f)
                for url in data.keys():
                    print(data[url])
                    li = []
                    for link, postdata in data[url].items():
                        print(link, postdata['pkg_creation_stamp'])
                        li.append([postdata['pkg_creation_stamp'], link])

                    li = sorted(li, key=lambda x: x[0])
                    #self.genesis[url] = li[0]

            self.logger.info(f'Got genesis URLS: {self.genesis}')
        except Exception as e:
            self.logger.critical('Error loading genesis data!')
            self.genesis = None
            print(e)

    def write_stats(self):
        with open(os.getcwd() + f'/cache/sys/stats/{datetime.datetime.now().strftime("%Y-%m-%d")}.json', "w") as f:
            f.write(json.dumps(self.stats))

    def read_stats(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/sys/stats'))
        if len(filenames) > 0:
            newest = max([fn.replace('.json', '') for fn in filenames])
            if datetime.datetime.today().strftime('%A') != 'Sunday':
                try:
                    with open(os.getcwd() + f'/cache/sys/stats/{newest}.json', 'r') as f:
                        self.stats = json.load(f)
                        self.logger.info('Loaded stats successfully')
                except Exception as e:
                    print(e)
                    self.logger.warning('Error while loading stats for today!')


    def find_oldest_post(self):
        if self.hist is not None and type(self.hist) == dict:
            li = []
            for category_url in self.hist.keys():
                if category_url == 'timestamp':
                    continue
                for thread_url in self.hist[category_url].keys():
                    if thread_url == 'timestamp':
                        continue
                    #print(self.hist[category_url][thread_url])
                    timestamp = self.hist[category_url][thread_url]['post_date']
                    postdate = str(timestamp)
                    try:
                        postdate = postdate.split(' AM')[0]
                    except:
                        pass
                    try:
                        postdate = postdate.split(' PM')[0]
                    except:
                        pass
                    date_format = "%b %d, %Y %H:%M:%S"
                    dt = datetime.datetime.strptime(postdate, date_format)
                    li.append((thread_url, dt))
                try:
                    li = sorted(li, key=lambda x: x[1])
                    oldest_url = li[0][0]
                    self.genesis[category_url] = oldest_url
                except:
                    self.genesis[category_url] = None

            print('Acquired genesis urls: {}'.format(self.genesis))

    def go(self):
        try:
            data = self.run()
            self.write_stats()
            return data
        except Exception as e:
            self.email_results(warn=True, excep=e)
            self.close()
            return
        
    def run(self):

        """Main driver function. Inherits crawler class and functionality to scrape various threads.
        Inherited fields are webdriver and logger object. This function will execute once every day.
        Handles cache management and garbage collection."""

        #Import libraries for logging
        import socket, datetime
        self.logger.info('Beginning scan at {}'.format(socket.gethostname()))

        #Instantiate crawler
        lim = None
        if '-l' in sys.argv:
            lim=1
        if '-d' in sys.argv:
            crawler = Crawler(self.webdriver, self.hist, target='upwork', \
                debug=True, genesis=self.genesis, post_lim=lim)
        else:
            crawler = Crawler(self.webdriver, self.hist, target='upwork', genesis=self.genesis, post_lim=lim)

        #Fetch crawler data
        data = crawler.crawl()

        self.stats = crawler.stats
        self.users.update(crawler.users)
        for user in crawler.users.keys():
            if user not in self.users.keys():
                self.users[user] = crawler.users[user]
        self.scan_start = datetime.datetime.now()
        
        #Cleanup cache
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        if len(filenames) > 10:
            dif = len(filenames) - 10
            for _ in range(dif):
                oldest_file = min(filenames, key=os.path.getctime)
                os.remove(os.path.abspath(oldest_file))
        
        #Log data
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(os.getcwd() + '/cache/logs/{}.json'.format(now), 'w') as f:
            f.write(data)
        self.logger.warning('Finished scan.')

        return data

    def flush_cache(self):
        dirs = ['/cache/logs/']
        for dir_ in dirs:
            _, _, filenames = next(os.walk(os.getcwd() + dir_))
            if len(filenames) > 0:
                for f in filenames:
                    self.logger.warning(f'Removing file {f}')
                    os.remove(os.getcwd() + dir_ + f)
                self.logger.warning(f'Emptied directory: {dir_}')
            else:
                self.logger.warning('Nothing to empty in cache, continuing...')

    def flush_csv(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/csv'))
        if len(filenames) > 0:
            for f in filenames:
                os.remove(os.getcwd() + f'/cache/csv/{f}')
            self.logger.warning('Flushed .csv files successfully')
        else:
            self.logger.warning('No .csv files to remove, continuing...')

    def flush_stats(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/sys/stats'))
        if len(filenames) > 0:
            for f in filenames:
                os.remove(os.getcwd() + f'/cache/sys/stats/{f}')
            self.logger.warning('Flushed stats files successfully')
        else:
            self.logger.warning('No stats files to remove')

    def flush(self):
        self.flush_cache()
        self.flush_csv()
        self.flush_stats()
   
    def close(self):
        #Cleans up webdriver processes and exits program
        self.webdriver.quit()
        self.logger.critical('Closing...')
        sys.exit()

    def save_users(self):
        pass

    def write_csv(self, data):
        """Writes json data to csv file in cache"""
        
        #Ensure data is in json/dict format
        if type(data) != dict:
            data = json.loads(data)

        #input(self.users['953dba24'])
        
        #Open file handler
        with open(os.getcwd() + f'/cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            #Create csv writer
            f = csv.writer(f)
            
            #Create csv header
            f.writerow(["title", "post_date", "edit_date", "contributor_id", \
                    "contributor_rank", "message_text", "post_version", "post_datetime", \
                    "post_moderation", "category", "url"])

            #Userdb dict
            users = {}

            #For each category URL
            for category_url in data.keys():

                if category_url == 'timestamp':
                    continue

                #For each thread scraped in that category
                for thread_url in data[category_url].keys():
                    #Add the entry to our userdb

                    if thread_url == 'timestamp':
                        continue

                    for name in data[category_url][thread_url]['contributors'].keys():
                        users[name] = data[category_url][thread_url]['contributors'][name]
                    #self.users[name] = users[name]

                    #For each user in the cached messages
                    for key in data[category_url][thread_url]['messages'].keys():
                        #For each version found of those messages
                        li = []
                        for v in data[category_url][thread_url]['messages'][key].keys():
                            li.append(int(v))
                        latest = max(li)
                        last = None
                        rank = ''
                        for entry in data[category_url][thread_url]['contributors'].keys():
                            if data[category_url][thread_url]['contributors'][entry]['user_id'] == key:
                                rank = data[category_url][thread_url]['contributors'][entry]['rank']
                        if rank == '':
                            print(f'Rank for user {key} not found')
                            # print(f"User had information: {data[category_url][thread_url]['contributors'][entry]}")
                        
                        for message in data[category_url][thread_url]['messages'][key][str(latest)]:
                            #Try to pull edited status
                            if message[1] == last:
                                continue
                            
                            try:
                                edited = message[2]
                            except:
                                edited = 'Unedited'

                            if message[1] == '<--Deleted-->':
                                last = latest - 1
                                #print(data[category_url][thread_url]['messages'][key])
                                #try:
                                    #print(self.hist[category_url][thread_url]['messages'][key])
                                #except Exception as e:
                                    #print(e)
                                    #print('didnt find old posts for user')
                                    #pass

                                #Pull the users rank
                                
                                try:
                                    msgs = self.hist[category_url][thread_url]['messages'][key][str(last)]
                                    for msg in msgs:
                                        if msg[0] == message[0] and msg[1] != '<--Deleted-->':
                                            #print(f'Found message was deleted with text: \n {msg[1]}')
                                            f.writerow([data[category_url][thread_url]['title'],\
                                            data[category_url][thread_url]['post_date'], \
                                            msg[3], key, rank, msg[1], latest, \
                                            msg[0], '<--Deleted-->', \
                                            category_url.split('/t5/')[1].split('/')[0], thread_url])
                                            break
                                except Exception as e:
                                    print(e)
                            else:
                            #print(f'Writing message\n userid: {key}\n timestamp: {message[0]}\n message: {message[1]}')
                            #Write row to csv
                            #Pull the users rank
                                f.writerow([data[category_url][thread_url]['title'],\
                                data[category_url][thread_url]['post_date'], \
                                message[3], \
                                key, rank, message[1], latest, \
                                message[0], edited, category_url.split('/t5/')[1].split('/')[0], thread_url])
                            

        #File handler for Userdb file
        with open (os.getcwd() + f'/cache/csv/userdb/users_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            f = csv.writer(f)
            f.writerow(["user_name", "user_id", "user_url", "user_join_date", "user_rank"])

            for name in users:
                f.writerow([name, users[name]['user_id'], users[name]['user_url'], users[name]['member_since'], users[name]['rank']])

    def load_history(self):
        """Main loading function for pulling json data from cache."""

        #Get filenames in log dir
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        
        #Cleanup for irrelevant files
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

        #Try and pull the newest file
        if len(filenames) != 0:
            newest_file = str(max([datetime.datetime.strptime(x.strip('.json'), '%Y-%m-%d') for x in filenames]).date()) + '.json'

            try:
                #Open the newest file and read the data to history cache
                with open(os.getcwd() + '/cache/logs/' + newest_file, 'r') as f:
                    data = json.load(f)
                    self.hist = data
                    for category in self.hist.keys():
                        if category == 'timestamp':
                            continue
                        for thread in self.hist[category].keys():
                            for contributor in self.hist[category][thread]['contributors'].keys():
                                self.users[contributor] = self.hist[category][thread]['contributors'][contributor]
                    try:
                        self.last_scan = datetime.datetime.strptime(data['timestamp'], "%m/%d/%Y, %H:%M:%S")
                    except:
                        self.last_scan = datetime.datetime.now()
            except Exception as e:
                self.logger.critical('Error while loading history!')
                print(e)
        else:
            self.last_scan = datetime.datetime.now()

    def email_results(self, warn=False, excep=None):
        """Emails csv results to designated addresses. Consider pulling addresses to driver class member
        for portability."""

        import smtplib
        import mimetypes
        from email.mime.multipart import MIMEMultipart
        from email import encoders
        from email.message import Message
        from email.mime.audio import MIMEAudio
        from email.mime.base import MIMEBase
        from email.mime.image import MIMEImage
        from email.mime.text import MIMEText

        #Declare relvant addresses
        emailfrom = "scrapelib@gmail.com"
        dsts = ["scrapelib@gmail.com",\
            #"hatim.rahman@kellogg.northwestern.edu", \
            "grahamburleigh2022@u.northwestern.edu"]

        #For each specified destination 
        for dst in dsts:
            #Get our credentials and data ready
            emailto = dst
            if warn is False:
                fileToSend = f'./cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            else:
                fileToSend = ''
            username = "scrapelib"
            password = "scrapejapes1122!"

            #Prepare message package
            msg = MIMEMultipart()
            msg["From"] = emailfrom
            msg["To"] = emailto
            if warn is False:
                msg["Subject"] = f'{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
                msg.preamble = f'{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            else:
                msg["Subject"] = f'Geckodriver failure! {datetime.datetime.now().strftime("%Y-%m-%d")}'
                msg.preamble = 'Something went wrong while configuring the driver settings!'

            ctype, encoding = mimetypes.guess_type(fileToSend)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"

            maintype, subtype = ctype.split("/", 1)

            if maintype == "text":
                fp = open(fileToSend)
                attachment = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == "image":
                fp = open(fileToSend, "rb")
                attachment = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == "audio":
                fp = open(fileToSend, "rb")
                attachment = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(fileToSend, "rb")
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(fp.read())
                fp.close()
                encoders.encode_base64(attachment)

            if warn is False:
                body = ''

                #body += '<------------------------------------------------------------------------------>\n'
                diff = datetime.datetime.now() - self.last_scan
                dur = datetime.datetime.now() - self.scan_start
                durdays, durhours, durmins = dur.days, dur.seconds // 3600, dur.seconds // 60 % 60
                days, hours, minutes = diff.days, diff.seconds // 3600, diff.seconds // 60 % 60
                body += f'{days} days, {hours} hours, and {minutes} minutes since last scan.'
                body += f'Scan took {durhours} hours, {durmins} minutes'
                body += 'During the last scan, we encountered: \n\n'
                for tar in self.stats.keys():
                    body += f'<---- {tar} ---->'
                    deletes = self.stats[tar]['deletions']
                    body += f'{deletes} message posts deleted or no longer found\n'
                    mods = self.stats[tar]['modifications']
                    body += f'{mods} message posts modified or edited\n\n'
                
                    modsli = {}
                    sum_ = 0
                    for key in self.stats[tar]['user_mods'].keys():
                        modsli[key] = self.stats[tar]['user_mods'][key]
                        sum_ += self.stats[tar]['user_mods'][key]
                    modsavg = sum_/len(self.users.keys())
                    body += f'Out of {len(self.users.keys())} users, {len(modsli.keys())} had post(s) modified\n'
                    deleteli = {}
                    sum_ = 0
                    for key in self.stats[tar]['user_deletes'].keys():
                        deleteli[key] = self.stats[tar]['user_deletes'][key]
                        sum_ += self.stats[tar]['user_deletes'][key]
                    deleteavg = sum_/len(self.users.keys())
                    body += f'Out of {len(self.users.keys())} users, {len(deleteli.keys())} had post(s) deleted\n'
                    modranks = {}
                    delranks = {}
                    for user in self.users.keys():
                        if self.users[user]['user_id'] in self.stats[tar]['user_mods']:
                            if self.users[user]['rank'] in modranks.keys():
                                if user in modranks[self.users[user]['rank']].keys():
                                    modranks[self.users[user]['rank']][self.users[user]['user_id']] += 1
                                else:
                                    modranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                            else:
                                modranks[self.users[user]['rank']] = {}
                                modranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                        if self.users[user]['user_id'] in self.stats[tar]['user_deletes']:
                            if self.users[user]['rank'] in delranks.keys():
                                if user in delranks[self.users[user]['rank']].keys():
                                    delranks[self.users[user]['rank']][self.users[user]['user_id']] += 1
                                else:
                                    delranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                            else:
                                delranks[self.users[user]['rank']] = {}
                                delranks[self.users[user]['rank']][self.users[user]['user_id']] = 1

                    delranks['total'] = 0
                    modranks['total'] = 0
                    for rank in delranks.keys():
                        if rank == 'total':
                            continue
                        for user in delranks[rank].keys():
                            delranks['total'] += delranks[rank][user]
                        body += f"Rank {rank} had {modranks['total']} posts deleted"

                    for rank in modranks.keys():
                        if rank == 'total':
                            continue
                        for user in modranks[rank].keys():
                            modranks['total'] += modranks[rank][user]
                        body += f"Rank {rank} had {modranks['total']} posts modified"

                body = MIMEText(body)
                msg.attach(body)

                attachment.add_header("Content-Disposition", "attachment", filename=fileToSend)
                msg.attach(attachment)
            else:
                # body = 'This is a message informing you that something went wrong with Geckodriver while configuring your webdriver.\n'
                # body += "Usually this is due to processes not closing properly from previous sessions. Try using lsof [path to .wdm]/.wdm/drivers/geckodriver/linux64/v0.29.0/geckodriver' and 'kill' each pid listed"
                # body += 'You may have found this already while running manually, otherwise log onto Quest and fix it'
                # body += "We'll have a patch for this soon, thanks for bearing with me."
                if excep is not None:
                    body += f'Scan terminated due to exception: {f}'
                body += 'Something went wrong during the scan. Go fix it!'
                body = MIMEText(body)
                msg.attach(body)
            #Send package
            server = smtplib.SMTP("smtp.gmail.com:587")
            server.starttls()
            server.login(username,password)
            server.sendmail(emailfrom, emailto, msg.as_string())
            server.quit()

    def report_stats(self):
        print('<------------------------------------------------------------------------------>')
        print(f'Started at {self.scan_start}')
        print(f'Now: {datetime.datetime.now()}')
        diff = datetime.datetime.now() - self.last_scan
        dur = datetime.datetime.now() - self.scan_start
        durdays, durhours, durmins = dur.days, dur.seconds // 3600, dur.seconds // 60 % 60
        days, hours, minutes = diff.days, diff.seconds // 3600, diff.seconds // 60 % 60
        print(f'Scan took {durhours} hours, {durmins} minutes')
        print(f'{days} days, {hours} hours, and {minutes} minutes since last scan.')
        print('During the last scan, we encountered: \n')
        gdel = {}
        gmod = {}
        for tar in self.stats.keys():
            gdel[tar] = {}
            gmod[tar] = {}
        for tar in self.stats.keys():
            print(f'<---- {tar} ---->')
            deletes = self.stats[tar]['deletions']
            print(f'[{deletes} message posts deleted or no longer found]')
            mods = self.stats[tar]['modifications']
            print(f'[{mods} message posts modified or edited]\n')
            
            modsli = {}
            sum_ = 0
            for key in self.stats[tar]['user_mods'].keys():
                modsli[key] = self.stats[tar]['user_mods'][key]
                sum_ += self.stats[tar]['user_mods'][key]
            modsavg = sum_/len(self.users.keys())
            #print(f'On average, each user had {modsavg} posts modified since the last scan')
            print(f'Out of {len(self.users.keys())} users, {len(modsli.keys())} had post(s) modified')
            deleteli = {}
            sum_ = 0
            for key in self.stats[tar]['user_deletes'].keys():
                deleteli[key] = self.stats[tar]['user_deletes'][key]
                sum_ += self.stats[tar]['user_deletes'][key]
            deleteavg = sum_/len(self.users.keys())
            #print(f'On average, each user had {deleteavg} posts deleted since the last scan')
            print(f'Out of {len(self.users.keys())} users, {len(deleteli.keys())} had post(s) deleted')

            modranks = {}
            delranks = {}
            for user in self.users.keys():
                if self.users[user]['user_id'] in self.stats[tar]['user_mods']:
                    if self.users[user]['rank'] in modranks.keys():
                        if user in modranks[self.users[user]['rank']].keys():
                            modranks[self.users[user]['rank']][self.users[user]['user_id']] += 1
                        else:
                            modranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                    else:
                        modranks[self.users[user]['rank']] = {}
                        modranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                if self.users[user]['user_id'] in self.stats[tar]['user_deletes']:
                    if self.users[user]['rank'] in delranks.keys():
                        if user in delranks[self.users[user]['rank']].keys():
                            delranks[self.users[user]['rank']][self.users[user]['user_id']] += 1
                        else:
                            delranks[self.users[user]['rank']][self.users[user]['user_id']] = 1
                    else:
                        delranks[self.users[user]['rank']] = {}
                        delranks[self.users[user]['rank']][self.users[user]['user_id']] = 1

            delranks['total'] = 0
            modranks['total'] = 0
            for rank in delranks.keys():
                if rank == 'total':
                    continue
                for user in delranks[rank].keys():
                    delranks['total'] += delranks[rank][user]
                print(f"Rank {rank} had {modranks['total']} posts deleted")

            for rank in modranks.keys():
                if rank == 'total':
                    continue
                for user in modranks[rank].keys():
                    modranks['total'] += modranks[rank][user]
                print(f"Rank {rank} had {modranks['total']} posts modified")
            gmod[tar].update(modranks)
            gdel[tar].update(delranks)
           

        if '-f' not in sys.argv:
            i = input('Display deletes/mods for indiv. users? (y/n)')
        else:
            i = 'y'
        if i == 'y':
            used = []
            for tar in gmod.keys():
                for rank in gmod[tar].keys():
                    if rank == 'total':
                        continue
                    for user in gmod[tar][rank].keys():
                        name = ''
                        for u in self.users.keys():
                            if self.users[u]['user_id'] == user:
                                name = u
                                break
                        print(f'User {name}({user}) had {gmod[tar][rank][user]} posts modified in category{tar}')
            
            for tar in gdel.keys():
                for rank in gdel[tar].keys():
                    if rank == 'total':
                        continue
                    for user in gdel[tar][rank].keys():
                        name = ''
                        for u in self.users.keys():
                            if self.users[u]['user_id'] == user:
                                name = u
                                break
                        print(f'User {name}({user}) had {gdel[tar][rank][user]} posts deleted in category {tar}')
        else:
            pass
        print('<------------------------------------------------------------------------------>')

if __name__ == "__main__":
    #Run test functions
    now = datetime.datetime.now()
    if '-flush' in sys.argv:
        #d.flush()
        d = Driver(flush=True, start=now)
    else:
        d = Driver(start=now)
    try:
        if '--config' not in sys.argv:
            data = d.go()
            d.write_csv(data)
            #d.email_results()
            d.report_stats()
    except KeyboardInterrupt:
        d.close()
        os.system('deactivate')
    try:
        if '-s' in sys.argv:
            while True:
                schedule.run_pending()
    except:
        pass
    atexit.register(d.close())
    d.close()

