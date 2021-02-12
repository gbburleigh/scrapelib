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
        self.fh = logging.FileHandler(os.getcwd() + '/cache/logs/debug.log', 'w+')
        self.fh.setLevel(logging.DEBUG)
        self.ch = logging.StreamHandler(sys.stdout)
        self.ch.setLevel(logging.INFO)
        self.formatter = logging.Formatter('[%(levelname)s :: (%(asctime)s)]: %(message)s')
        self.fh.setFormatter(self.formatter)
        self.ch.setFormatter(self.formatter)
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)
        self.hist={}
        self.load_history()
        self.genesis = {}
        #self.read_genesis()

        #Configure webdriver
        if '-f' in sys.argv:
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager import firefox
            from webdriver_manager.firefox import GeckoDriverManager
            options = Options()
            options.add_argument('--headless')
            self.webdriver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), \
                firefox_options=options, log_path=os.getcwd()+ '/cache/logs/geckodriver.log')
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
                    self.genesis[url] = li[0]

            self.logger.info(f'Got genesis URLS: {self.genesis}')
        except Exception as e:
            self.logger.critical('Error loading genesis data!')
            self.genesis = None
            print(e)
        
    def run(self):

        """Main driver function. Inherits crawler class and functionality to scrape various threads.
        Inherited fields are webdriver and logger object. This function will execute once every day.
        Handles cache management and garbage collection."""

        #Import libraries for logging
        import socket, datetime
        self.logger.info('Beginning scan at {}'.format(socket.gethostname()))

        #Instantiate crawler
        crawler = Crawler(self.webdriver, self.hist, target='upwork', genesis=self.genesis)

        #Fetch crawler data
        data = crawler.crawl()
        
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
        sys.exit()

    def write_csv(self, data):
        if type(data) != dict:
            data = json.loads(data)
        with open(os.getcwd() + f'/cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            f = csv.writer(f)
            f.writerow(["thread_url" , "title", "post_date", "edit_date", "contributor_id", \
                    "contributor_rank", "message_text", "post_version", "post_datetime", \
                    "post_moderation"])

            users = {}

            for category_url in data:
                for thread_url in data[category_url]:
                    if data[category_url][thread_url]['update_version'] > 1:
                        #TODO: MAKE A TEXT DIFF HERE AND APPEND IT
                        pass                
                        
                    for name in data[category_url][thread_url]['contributors']:
                        users[name] = data[category_url][thread_url]['contributors'][name]

                    for key in data[category_url][thread_url]['messages']:
                        for v in data[category_url][thread_url]['messages'][key]:
                            for message in data[category_url][thread_url]['messages'][key][v]:
                                try:
                                    edited = message[2]
                                except:
                                    edited = 'Unedited'

                                for entry in users:
                                    if users[entry]['user_id'] == key:
                                        rank = users[entry]['rank']

                                f.writerow([thread_url, data[category_url][thread_url]['title'],\
                                data[category_url][thread_url]['post_date'], \
                                data[category_url][thread_url]['edit_date'], \
                                key, rank, message[1], v, \
                                message[0], edited])

        with open (os.getcwd() + f'/cache/csv/userdb/users_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv', "w") as f:
            f = csv.writer(f)
            f.writerow(["user_name", "user_id", "user_url", "user_join_date", "user_rank"])

            for name in users:
                f.writerow([name, users[name]['user_id'], users[name]['user_url'], users[name]['member_since'], users[name]['rank']])

        return 

    def load_history(self):
        _, _, filenames = next(os.walk(os.getcwd() + '/cache/logs'))
        #print(filenames)
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
        if len(filenames) != 0:
            newest_file = str(max([datetime.datetime.strptime(x.strip('.json'), '%Y-%m-%d') for x in filenames]).date()) + '.json'

            try:
                with open(os.getcwd() + '/cache/logs/' + newest_file, 'r') as f:
                    data = json.load(f)
                    self.hist = data
            except Exception as e:
                self.logger.critical('Error while loading history!')
                print(e)

    def email_results(self):
        import smtplib
        import mimetypes
        from email.mime.multipart import MIMEMultipart
        from email import encoders
        from email.message import Message
        from email.mime.audio import MIMEAudio
        from email.mime.base import MIMEBase
        from email.mime.image import MIMEImage
        from email.mime.text import MIMEText

        emailfrom = "scrapelib@gmail.com"
        dsts = ["scrapelib@gmail.com", "hatim.rahman@kellogg.northwestern.edu", \
            "grahamburleigh2022@u.northwestern.edu"]
        for dst in dsts:
            emailto = dst
            
            fileToSend = f'./cache/csv/{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            username = "scrapelib"
            password = "scrapejapes1122!"

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
                # Note: we should handle calculating the charset
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
            attachment.add_header("Content-Disposition", "attachment", filename=fileToSend)
            msg.attach(attachment)

            server = smtplib.SMTP("smtp.gmail.com:587")
            server.starttls()
            server.login(username,password)
            server.sendmail(emailfrom, emailto, msg.as_string())
            server.quit()

if __name__ == "__main__":
    #Run test functions
    d = Driver()
    if '-c' not in sys.argv:
        try:
            data = d.run()
            d.write_csv(data)
        except KeyboardInterrupt:
            d.close()
            os.system('deactivate')
        try:
            if '-s' in sys.argv:
                while True:
                    schedule.run_pending()
        except:
            pass
    else:
        d.email_results()
        #d.write_csv(d.hist)
    atexit.register(d.close())
    d.close()

