import random
from flask import Flask, render_template, jsonify
from serial_reader_modularized import start_background_thread, get_latest_data

app = Flask(__name__)

# --- TOGGLE THIS FOR MOCK DATA OR LIVE DATA ---
MOCK_MODE = True 
# -------------------

# 1. INITIALIZE MOCK STATE
# these values persist between function calls
mock_state = {
    "rpm": 2500,
    "speed": 60.0,
    "temp": 110.5,
    "level": 98.0,
    "discharge": 45.0,
    "gx": 0.0,
    "gy": 0.0
}

if not MOCK_MODE:
    # start real background serial reading
    thread = start_background_thread()

def generate_mock_data():
    """Gently drifts values to simulate real physics."""
    global mock_state
    
    # drift RPM: +/- 30 units
    mock_state["rpm"] += random.randint(-30, 30)
    mock_state["rpm"] = max(1000, min(8000, mock_state["rpm"]))

    # drift Speed: +/- 0.2 units
    mock_state["speed"] += random.uniform(-0.2, 0.2)
    mock_state["speed"] = max(0, min(140, mock_state["speed"]))

    # drift Temp: +/- 0.05 units 
    mock_state["temp"] += random.uniform(-0.05, 0.05)
    mock_state["temp"] = max(80, min(160, mock_state["temp"]))

    # drift Battery Level: constant slow drain
    mock_state["level"] -= 0.005
    if mock_state["level"] < 0: mock_state["level"] = 100

    # drift g-Force: +/- 0.02 units
    mock_state["gx"] += random.uniform(-0.02, 0.02)
    mock_state["gy"] += random.uniform(-0.02, 0.02)

    return {
        "engine": {
            "rpm": mock_state["rpm"],
            "speed": mock_state["speed"]
        },
        "battery": {
            "level": mock_state["level"],
            "temp": mock_state["temp"],
            "discharge": mock_state["discharge"]
        },
        "accel": {
            "x": mock_state["gx"],
            "y": mock_state["gy"]
        }
    }

@app.route("/")
def index():
    return render_template("racing.html")

import time

# track when we last saw real data for each device
last_update_times = {"engine": 0, "battery": 0, "accel": 0}
STALE_THRESHOLD = 2.0 # seconds before switching to mock


# get the data, check device connections 
@app.route("/data")
def data():
    real_data = get_latest_data()
    mock_data = generate_mock_data()
    
    final_telemetry = {}
    status_map = {}

    for device in ["engine", "battery", "accel"]:
        # check if we have real data and it's not empty
        if device in real_data and real_data[device]:
            last_update_times[device] = time.time()
            
        # if the device was updated recently, use real data
        if time.time() - last_update_times[device] < STALE_THRESHOLD:
            final_telemetry[device] = real_data.get(device, mock_data[device])
            status_map[device] = "live"
        else:
            # device is missing/unplugged, use mock
            final_telemetry[device] = mock_data[device]
            status_map[device] = "mock"

    return jsonify({
        "telemetry": final_telemetry,
        "status": status_map
    })


# route for the menu to swap screens
@app.route("/menu")
def menu():
    return render_template("menu.html")

# route for battery testing screen
@app.route("/test/battery")
def test_battery():
    return render_template("test_battery.html")

# route for accelerometer testing screen
@app.route("/test/accel")
def test_accel():
    return render_template("test_accel.html")

# route for motor testing screen
@app.route("/test/motor")
def test_motor():
    return render_template("test_motor.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)