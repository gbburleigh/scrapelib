#!/bin/bash
python3 -m venv scrape-env
source scrape-env/bin/activate
pip3 install -r requirements.txt
echo "VENV configured"