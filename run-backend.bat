@echo off
REM Start VisionTrader AI backend without manual environment activation.
cd /d %~dp0\backend
python main.py
