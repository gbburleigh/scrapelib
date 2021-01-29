# Scrapelib (working title)
Small library of scrapers to detect censorship patterns on various online platforms. 

# Setup:

This modulle requires pip and Python3 downloaded. Upon cloning this repository, use 'pip3 install -r requirements.txt' to download all necessary 3rd party packages.

# Usage:

Bot is evoked in the following manner:

<pre>python3 driver.py</pre>

# TODO:

- Automating thread pulling/updating
- Fitting abstracted Scraper class to different forums using cached XPaths stored in json files
- Scraping target information using XPaths
- Statistical analysis and reports for raw data

# Driver

The main driver file will be the primary way users interact with Scrapelib. Users can generate a DriverBot object that will handle the scheduling of tasks and delegating of operations for the different subclasses. Users will be able to specify fields such as refresh frequency, maximum post cache size, report formatting, among others. Subclasses can be instantiated for specific testing (see ThreadScraper description) and for customization past those within the DriverBot object. DriverBot will also support addition of new objects to observe different websites outside of the scope of this project.

# Updater

The Updater class will be used for refreshing the DriverBot's currently cached HTML data. New or modified threads will be added accordingly to be parsed by ThreadScraper objects. This class is responsible for the exchange of new and old data, all analysis and parsing will be handled by other objects.

# Thread Scraper

This class is used to parse through cached HTML data for posted threads. Using BeautifulSoup, this class will be responsible for determining changes in existing threads, and finding important information on new threads such as OP, post date, etc. This class will be used by a Crawler object that uses a webdriver to find threads on the main forum page and sends them to the Scraper (tentative).

# Analyzer

The Analyzer object performs different analyses on the data returned by ThreadScrapers. Data will be represented using JSON and parsed in various ways. Meant to be instantiated within ThreadScraper object.

# Reporter

Compiles report of current state saved by DriverBot and sends them to user at an interval of their choosing. Logs failures, errors, and other important information. 

# Changelog

<h2>(1/10/21)</h2>
<p>Added the DriverBot class. This is the main interface through which users will interact with the library. Added the Schedule module to handle the processing of jobs automatically at intervals. Added the Crawler class. Inherits DriverBot webdriver in order to crawl different forums and find raw HTML data for forum posts. HTML data is saved to cache and sent to ThreadScraper for parsing.</p>

<h2>(1/11/21)</h2>
<p> Added temporary ThreadScraper file to hold testing class. Added URL scraping on Crawler for finding new posts. Implemented BeautifulSoup object in scraper for HTML parsing. Added logging and fixed Chrome processes not closing after program is closed. Adjusted config on webdriver-manager module for reduced clutter on CLI at runtime. </p>

<h2>(1/13/21)</h2>
<p>Added JSON logging of scraped data. Revamped the ThreadScraper class to include additional BS4 elements and properly scrape URLs and text. Added the atexit module. Cleaned up old code. Added cache directory and removed saving of entire HTML documents to reduce disk space usage.</p>

<h2>(1/15/21)</h2>
<p>Rough prototype of Driver class and functionality complete. Fetches posts, users, profile URLs, metadata, and edit status from recent posts on Upwork. Consider removing the Threadscraper class and adding its methods into the Crawler class, since all HTML parsing is done using BeautifulSoup rather than a Webdriver object. Discuss with Hatim about additional fields that should be recorded and parameters for caching.</p>

<h2>(1/18/21)</h2>
<p>Added support for additional forum categories. Configured repository on QUEST server. Added
KeyInterrupt check to close all processes. Added Firefox driver support for use on QUEST. Added
command line options controlling package dependencies.</p>

<h2>(1/21/21)</h2>
<p>Added activation script. Activates VENV if necessary (or creates on) and configures required packages.
Added cache cleaning based on filecount and oldest files found. Added package creation stamp to parsed data
packets for comparison when parsing oldest file (for finding genesis post).
</p>

<h2>(1/24/21)</h2>
<p>Fixed activation script not properly running/configuring environment on program execution. Fixed broken
function for finding oldest file in cache. Added JSON parsing to find oldest encountered link for genesis
post. </p>

<h2>(1/27/21)</h2>
<p>Added preliminary page scrolling functionality. Added next page link generator. Added traceback logging 
for debugging. Consider using 'next page' button instead of crafting new link for next page.</p>

<h2>(1/29/21</h2>
<p>Fixed page scrolling functionality/broken parsing. Consider adding some sort of filter to the links to 
make sure page that aren't threads aren't accidentally parsed as though they were.</p>