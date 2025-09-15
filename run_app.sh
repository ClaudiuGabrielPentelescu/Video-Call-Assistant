#!/usr/bin/env bash
# Video Call Assistant — quick runner (macOS/Linux)
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 main_tk2.py
