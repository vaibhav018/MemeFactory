@echo off
rem MemeFactory scheduled runner - generates one meme per run.
rem Registered in Windows Task Scheduler at 08:00 / 13:00 / 21:00 daily.
set PYTHONIOENCODING=utf-8
cd /d C:\Users\ASUS\Documents\MemeFactory
if not exist logs mkdir logs
C:\Python310\python.exe auto_meme.py >> logs\auto_meme.log 2>&1
