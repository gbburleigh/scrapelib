#!/bin/bash
source scrape-env/bin/activate
python3 newdriver.py -flush
python3 newdriver.py -d