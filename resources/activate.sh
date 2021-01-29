#!/bin/bash
if [ ! -d ./scrape-env ]; then
    python3 -m venv scrape-env
    echo "Created VENV folder"
fi
source scrape-env/bin/activate
echo "Activated VENV"
pip3 install --upgrade pip
pip3 install -r requirements.txt
echo "VENV configured"