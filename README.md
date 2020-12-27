# Scrapelib (working title)
Small library of scrapers to detect censorship patterns on various online platforms. 

# Architecture:

<ol>
    <li>Driver runs on Northwestern clusters, autodownloading new threads and updating cached HTML data</li>
    <li>Driver sends updated filelist to crawler, which processes multiple file simultaneously on seperate processes</li>
    <li>Crawler sends raw scraped data to analyzer, which compiles a report and saves it to cache after running all necessary scripts</li>
</ol>

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