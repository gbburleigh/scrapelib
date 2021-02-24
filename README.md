# Scrapelib (working title)
Small library of scrapers to detect censorship patterns on various online platforms. 

# Setup:

This modulle requires pip and Python3 downloaded. Upon cloning this repository, use 'pip3 install -r requirements.txt' to download all necessary 3rd party packages. Alternatively, use 'resources/activate.sh', or run the driver file and the necessary configurations will be made.

# Usage:

Bot is evoked in the following manner:

<pre>python3 driver.py</pre>


# Driver

The main driver file will be the primary way users interact with Scrapelib. Users can generate a Driver object that will handle the scheduling of tasks and delegating of operations for the different subclasses. Users will be able to specify fields such as refresh frequency, maximum post cache size, report formatting, among others. Subclasses can be instantiated for specific testing (see ThreadScraper description) and for customization past those within the Driver object. Driver will also support addition of new objects to observe different websites outside of the scope of this project.

# Thread Scraper

This class is used to parse through cached HTML data for posted threads. Using BeautifulSoup, this class will be responsible for determining changes in existing threads, and finding important information on new threads such as OP, post date, etc. This class will be used by a Crawler object that uses a webdriver to find threads on the main forum page and sends them to the Scraper (tentative).

# Crawler

This class is used to crawl over category pages and find threads to send to the Scraper object. This object inherits a variety of fields from the Driver parent class, such as loaded history, webdriver, and statistics. 