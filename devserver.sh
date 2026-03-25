#!/bin/sh
if [ ! -f "clubhub-venv/bin/activate" ]; then
    python3 -m venv clubhub-venv
fi

source ./clubhub-venv/bin/activate
pip install -r requirements.txt
python run.py
