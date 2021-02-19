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
    def __init__(self):

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

        #Configure history dictionary and load data into it if possible
        self.hist={}
        self.load_history()

        #Instantiate backend tracking fields
        self.stats = {}
        self.users = {}

        """DEPRECATED"""
        self.genesis = {}
        self.find_oldest_post()
        #self.read_genesis()

        #Configure webdriver
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                firefox_options=options, log_path=os.getcwd()+ '/cache/sys/geckodriver.log')
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

    def find_oldest_post(self):
        if self.hist is not None:
            li = []
            for category_url in self.hist.keys():
                for thread_url in self.hist[category_url].keys():
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
        
    def run(self):

        """Main driver function. Inherits crawler class and functionality to scrape various threads.
        Inherited fields are webdriver and logger object. This function will execute once every day.
        Handles cache management and garbage collection."""

        #Import libraries for logging
        import socket, datetime
        self.logger.info('Beginning scan at {}'.format(socket.gethostname()))

        #Instantiate crawler
        if '-d' in sys.argv:
            crawler = Crawler(self.webdriver, self.hist, target='upwork', \
                debug=True, genesis=self.genesis)
        else:
            crawler = Crawler(self.webdriver, self.hist, target='upwork', genesis=self.genesis)

        #Fetch crawler data
        data = crawler.crawl()

        self.stats = crawler.stats
        
        #Cleanup cache
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        if len(filenames) > 100:
            dif = len(filenames) - 100
            for _ in range(dif):
                oldest_file = min(filenames, key=os.path.getctime)
                os.remove(os.path.abspath(oldest_file))
        
        #Log data
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(os.getcwd() + '/cache/logs/{}.json'.format(now), 'w') as f:
            f.write(data)
        self.logger.warning('Finished scan.')

        return data
   
    def close(self):
        #Cleans up webdriver processes and exits program
        self.webdriver.quit()
        self.logger.critical('Closing...')
        sys.exit()

    def write_csv(self, data):
        """Writes json data to csv file in cache"""
        
        #Ensure data is in json/dict format
        if type(data) != dict:
            data = json.loads(data)
        
        #Open file handler
        with open(os.getcwd() + f'/cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            #Create csv writer
            f = csv.writer(f)
            
            #Create csv header
            f.writerow(["title", "post_date", "edit_date", "contributor_id", \
                    "contributor_rank", "message_text", "post_version", "post_datetime", \
                    "post_moderation"])

            #Userdb dict
            users = {}

            #For each category URL
            for category_url in data:
                #For each thread scraped in that category
                for thread_url in data[category_url]:
                    #Add the entry to our userdb
                    for name in data[category_url][thread_url]['contributors']:
                        users[name] = data[category_url][thread_url]['contributors'][name]

                    #For each user in the cached messages
                    for key in data[category_url][thread_url]['messages']:
                        #For each version found of those messages
                        li = []
                        for v in data[category_url][thread_url]['messages'][key]:
                            li.append(int(v))
                        latest = max(li)
                        for message in data[category_url][thread_url]['messages'][key][str(latest)]:
                            #Try to pull edited status
                            try:
                                edited = message[2]
                            except:
                                edited = 'Unedited'

                            #Pull the users rank
                            for entry in users:
                                if users[entry]['user_id'] == key:
                                    rank = users[entry]['rank']

                            if message[1] == '<--Deleted-->':
                                try:
                                    msgs = data[category_url][thread_url]['messages'][key][str(latest-1)]
                                    for msg in msgs:
                                        if msg[0] == message[0]:
                                            f.writerow([data[category_url][thread_url]['title'],\
                                            data[category_url][thread_url]['post_date'], \
                                            data[category_url][thread_url]['edit_date'], \
                                            key, rank, msg[1], latest-1, \
                                            msg[0], edited])
                                            break
                                except:
                                    pass

                            #Write row to csv
                            f.writerow([data[category_url][thread_url]['title'],\
                            data[category_url][thread_url]['post_date'], \
                            data[category_url][thread_url]['edit_date'], \
                            key, rank, message[1], latest, \
                            message[0], edited])

        self.users = users
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
            except Exception as e:
                self.logger.critical('Error while loading history!')
                print(e)

    def email_results(self):
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
            fileToSend = f'./cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            username = "scrapelib"
            password = "scrapejapes1122!"

            #Prepare message package
            msg = MIMEMultipart()
            msg["From"] = emailfrom
            msg["To"] = emailto
            msg["Subject"] = f'{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            msg.preamble = f'{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'

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

            body = ''

            #body += '<------------------------------------------------------------------------------>\n'
            body += 'During the last scan, we encountered: \n\n'
            deletes = self.stats['deletions']
            body += f'{deletes} message posts deleted or no longer found\n'
            mods = self.stats['modifications']
            body += f'{mods} message posts modified or edited\n\n'
            
            modsli = {}
            sum_ = 0
            for key in self.stats['user_mods'].keys():
                modsli[key] = self.stats['user_mods'][key]
                sum_ += self.stats['user_mods'][key]
            modsavg = sum_/len(self.users.keys())
            body += f'On average, each user had {modsavg} posts modified since the last scan\n'
            deleteli = {}
            sum_ = 0
            for key in self.stats['user_deletes'].keys():
                deleteli[key] = self.stats['user_deletes'][key]
                sum_ += self.stats['user_deletes'][key]
            deleteavg = sum_/len(self.users.keys())
            body += f'On average, each user had {deleteavg} posts deleted since the last scan\n'
            #body += '<------------------------------------------------------------------------------>\n'

            body = MIMEText(body)
            msg.attach(body)

            attachment.add_header("Content-Disposition", "attachment", filename=fileToSend)
            msg.attach(attachment)

            #Send package
            server = smtplib.SMTP("smtp.gmail.com:587")
            server.starttls()
            server.login(username,password)
            server.sendmail(emailfrom, emailto, msg.as_string())
            server.quit()

    def report_stats(self):
        print('<------------------------------------------------------------------------------>')
        print('During the last scan, we encountered: \n')
        deletes = self.stats['deletions']
        print(f'[{deletes} message posts deleted or no longer found]')
        mods = self.stats['modifications']
        print(f'[{mods} message posts modified or edited]\n')
        
        modsli = {}
        sum_ = 0
        for key in self.stats['user_mods'].keys():
            modsli[key] = self.stats['user_mods'][key]
            sum_ += self.stats['user_mods'][key]
        modsavg = sum_/len(self.users.keys())
        print(f'On average, each user had {modsavg} posts modified since the last scan')
        deleteli = {}
        sum_ = 0
        for key in self.stats['user_deletes'].keys():
            deleteli[key] = self.stats['user_deletes'][key]
            sum_ += self.stats['user_deletes'][key]
        deleteavg = sum_/len(self.users.keys())
        print(f'On average, each user had {deleteavg} posts deleted since the last scan')
        i = input('Display deletes/mods for indiv. users? (y/n)')
        if i == 'y':
            used = []
            for key in modsli.keys():
                print(f'User {key} had {modsli[key]} posts modified since the last scan')
                if key in deleteli.keys():
                    print(f'User {key} also had {deleteli[key]} posts deleted since the last scan')
                    used.append(key)

            print('Remaining deletions detected w/o related mod: ')
            for key in deleteli.keys():
                if key not in used:
                    print(f'User {key} had {deleteli[key]} posts deleted since the last scan')

        else:
            pass
        print('<------------------------------------------------------------------------------>')

if __name__ == "__main__":
    #Run test functions
    d = Driver()
    try:
        if '--config' not in sys.argv:
            data = d.run()
            if '-d' not in sys.argv:
                d.write_csv(data)
                d.email_results()
                d.report_stats()
            else:
            #d.write_csv(data)
                d.email_results()
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

