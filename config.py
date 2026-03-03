

import os
from dotenv import load_dotenv

load_dotenv()

# Camera Configuration
# Camera Configuration
# Priority:
# 1. IP_CAMERA_URL (Full URL)
# 2. Constructed URL from CAMERA_IP, CAMERA_USERNAME, CAMERA_PASSWORD
# 3. WEBCAM_INDEX (Fallback)

CAMERA_USERNAME = os.getenv("CAMERA_USERNAME")
CAMERA_PASSWORD = os.getenv("CAMERA_PASSWORD")
CAMERA_IP = os.getenv("CAMERA_IP")
CAMERA_STREAM_PATH = os.getenv("CAMERA_STREAM_PATH") # e.g. "stream1", "live"

IP_CAMERA_URL = os.getenv("IP_CAMERA_URL", None)

if not IP_CAMERA_URL and CAMERA_IP:
    creds = ""
    if CAMERA_USERNAME and CAMERA_PASSWORD:
        creds = f"{CAMERA_USERNAME}:{CAMERA_PASSWORD}@"
    
    IP_CAMERA_URL = f"rtsp://{creds}{CAMERA_IP}"
    if CAMERA_STREAM_PATH:
        IP_CAMERA_URL += f"/{CAMERA_STREAM_PATH}"

WEBCAM_INDEX = 0

# Window Configuration
WINDOW_NAME = "Traffic Officer Agent"

# Detection Thresholds
DETECTION_CONFIDENCE = 0.5
TRACKING_CONFIDENCE = 0.5

# Hardware Configuration (ESP8266 Traffic Light)
# Set ESP8266_IP env variable to enable hardware control
# e.g.  set ESP8266_IP=192.168.1.50
ESP8266_IP = os.getenv("ESP8266_IP", None)
ESP8266_PORT = int(os.getenv("ESP8266_PORT", "80"))
HARDWARE_ENABLED = ESP8266_IP is not None
