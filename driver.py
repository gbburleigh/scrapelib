import doctest, sys, os, shutil
from scraper import ThreadScraper

if __name__ == "__main__":
    url = 'https://community.upwork.com/t5/Freelancers/Possible-scam/td-p/848751'
    scraper = ThreadScraper('tags.json', url)
    doctest.testmod()

