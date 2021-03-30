#!/bin/bash

source scrape-env/bin/activate

python3 driver.py -r -c

python3 driver.py -c

python3 driver.py -c

python3 driver.py -c
