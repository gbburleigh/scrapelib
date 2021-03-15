#!/bin/bash
source scrape-env/bin/activate
python3 newdriver.py
echo "Completed first scan, continuing..."
pkill -f chromedriver
python3 newdriver.py
echo "Completed second scan, exiting..."
