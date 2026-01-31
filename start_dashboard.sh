#!/bin/bash
# 1. navigate to the DDS folder
cd /home/pi/Desktop/DDS\ UI\ -\ 25-26/

# 2. start the Flask app in the background
# replace 'python' with the path to your venv if we're using one
python app.py &

# 3. wait for the server to actually start
sleep 5

# 4. launch Chromium in Kiosk Mode
chromium-browser --kiosk --incognito --disable-infobars http://127.0.0.1:5001