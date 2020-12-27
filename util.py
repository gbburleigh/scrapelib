import sys, os, time, json
from datetime import datetime

def read_json(fn):
    # Reads JSON file and converts it to a dictionary
    with open(fn, 'r') as f:
        obj = json.load(f)
        return obj

def merge_dictionaries(root, branch):
    # Root: Dictionary of dictionaries
    # Branch: Dictionary of dictionaries
    # Find shared keys in nested dictionaries, update them
    # on root. 
    for child in branch.items():
        for key in child[1].keys():
            if key in root[child[0]].keys():
                root[child[0]][key] = child[1][key]
    return root
    
def generate_xpath(name, type, class_or_id):
    # Generate valid xpath pased on type of div and classnames
    # TODO: Handle nested/child divs
    return f"//{type}[@{class_or_id}='{name}']"

def fetch_page(self, url):
    """Util function for fetching and writing HTML data
    for threads in cache to be processed by scraper"""
    import urllib2
    response = urllib2.urlopen(url)
    data = response.read()
    try:
        domain = url.split('https://')[1][:32]
    except:
        domain = url.split('htttp://')[1][:32]
    filename = f'{domain}:{datetime.now()}'
    file_ = open(f'cache/scraped_html/{filename}', 'w')
    file_.write(data)
    file_.close()
