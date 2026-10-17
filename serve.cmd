@echo off
rem Starts a tiny web server so the browser is allowed to fetch products.json.
rem Requires Python 3. Then open http://localhost:8000
start "" http://localhost:8000
python -m http.server 8000
