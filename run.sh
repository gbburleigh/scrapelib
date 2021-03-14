#!/bin/bash
source scrape-env/bin/activate
python3 newdriver.py
echo "Completed first scan, continuing..."
python3 newdriver.py
echo "Completed second scan, exiting..."
# python3 newdriver.py
# echo "Completed third scan, exiting"