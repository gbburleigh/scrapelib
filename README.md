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