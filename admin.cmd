@echo off
rem Opens the local admin page for editing product names, prices and visibility.
rem It binds to this machine only; admin.py opens the browser once it is listening.
rem Requires Python 3. Close this window (or press Ctrl+C) to stop it.
python "%~dp0admin.py"
pause
