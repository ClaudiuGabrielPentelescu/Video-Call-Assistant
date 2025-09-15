
@echo off
REM Video Call Assistant — quick runner (Windows)
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
python main_tk2.py
pause
