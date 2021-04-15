# Scrapelib (working title)
Small library of scrapers to detect censorship patterns on various online platforms. 

# Setup:

This modulle requires pip and Python3 downloaded. Upon cloning this repository, use 'pip3 install -r requirements.txt' to download all necessary 3rd party packages. Alternatively, use 'resources/activate.sh', or run the driver file and the necessary configurations will be made.

# Usage:

Bot is evoked in the following manner:

<pre>python3 driver.py</pre>


# Components

<h1>Driver</h1>
This is the main interface for the Crawler and Scraper classes. Running driver.py will create a driver object that handles webdriver creation, process management, DB comparison, and loading/writing on the cached data. Running driver.py with any of the following arguments will change the configuration of the webdriver object.

<ul>
    <li>"-f" will open a FireFox webdriver through Webdriver Manager. Geckodriver binary will be downloaded and configured by this module and can be used when Chromedriver binary isn't available.
    </li>

    <li>
    "-c" will open a Chromedriver instance in Selenium using the chromedriver_binary module. This is separate from WDM and can be used when config issues arise with this module.
    </li>
</ul>

<h1>Crawler</h1>

<h1>Scraper</h1>

# Included Classes

<h2>User</h2>
Main object used to represent all user data in backend.

<h2>UserList</h2>
Abstraction of simple Python list for managing groups of users.

<h2>Post</h2>
Object for storing necessary information about a post on a thread, including lower level user objects.

<h2>PostList</h2>

<h2>DeleteList</h2>

<h2>Thread</h2>

<h2>Category</h2>

<h2>StatTracker</h2>

<h2>SiteDB</h2>