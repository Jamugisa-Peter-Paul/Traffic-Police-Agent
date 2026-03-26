

import os
import torch
from dotenv import load_dotenv

load_dotenv()

# ─── Device & Performance Mode ───────────────────────────────────────────────
# Auto-detect: uses GPU (CUDA/MPS) if available, otherwise falls back to CPU.
# You can override by setting DEVICE_MODE=cpu or DEVICE_MODE=gpu in .env

def _detect_device():
    """Auto-detect the best available device."""
    override = os.getenv("DEVICE_MODE", "auto").lower()
    if override == "cpu":
        return "cpu"
    if override == "gpu":
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        print("Warning: GPU requested but not available. Falling back to CPU.")
        return "cpu"
    # Auto mode
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

DEVICE = _detect_device()
IS_GPU = DEVICE in ("cuda", "mps")

# Performance settings tuned per device
if IS_GPU:
    JACKET_IMGSZ = 640          # Full resolution for GPU
    DETECT_EVERY_N_FRAMES = 1   # Every frame on GPU
    JACKET_CONFIDENCE_THRESHOLD = 0.4
else:
    JACKET_IMGSZ = 320          # Half resolution for CPU speed
    DETECT_EVERY_N_FRAMES = 5   # Skip frames on CPU
    JACKET_CONFIDENCE_THRESHOLD = 0.25

print(f"⚡ Device: {DEVICE.upper()} | imgsz={JACKET_IMGSZ} | skip={DETECT_EVERY_N_FRAMES} | conf={JACKET_CONFIDENCE_THRESHOLD}")

# ─── Camera Configuration ────────────────────────────────────────────────────
# Priority:
# 1. IP_CAMERA_URL (Full URL)
# 2. Constructed URL from CAMERA_IP, CAMERA_USERNAME, CAMERA_PASSWORD
# 3. WEBCAM_INDEX (Fallback)

CAMERA_USERNAME = os.getenv("CAMERA_USERNAME", "").strip("'\"")
CAMERA_PASSWORD = os.getenv("CAMERA_PASSWORD", "").strip("'\"")
CAMERA_IP = os.getenv("CAMERA_IP", "").strip("'\"/")
if CAMERA_IP.startswith("http://"):
    CAMERA_IP = CAMERA_IP[7:]
CAMERA_STREAM_PATH = os.getenv("CAMERA_STREAM_PATH", "").strip("'\"/")

IP_CAMERA_URL = os.getenv("IP_CAMERA_URL", "").strip("'\"")

if not IP_CAMERA_URL and CAMERA_IP:
    creds = ""
    if CAMERA_USERNAME and CAMERA_PASSWORD:
        creds = f"{CAMERA_USERNAME}:{CAMERA_PASSWORD}@"
    
    IP_CAMERA_URL = f"rtsp://{creds}{CAMERA_IP}"
    if CAMERA_STREAM_PATH:
        IP_CAMERA_URL += f"/{CAMERA_STREAM_PATH}"

WEBCAM_INDEX = 0

# ─── Window Configuration ────────────────────────────────────────────────────
WINDOW_NAME = "Traffic Officer Agent"

# ─── Pose Detection Thresholds ───────────────────────────────────────────────
DETECTION_CONFIDENCE = 0.5
TRACKING_CONFIDENCE = 0.5

# ─── Safety Jacket Detection ─────────────────────────────────────────────────
JACKET_MODEL_PATH = "models/best_jacket.pt"

# Hardware Configuration (ESP8266 Traffic Light)
# Set ESP8266_IP env variable to enable hardware control
# e.g.  set ESP8266_IP=192.168.1.50
ESP8266_IP = os.getenv("ESP8266_IP", None)
ESP8266_PORT = int(os.getenv("ESP8266_PORT", "80"))
HARDWARE_ENABLED = ESP8266_IP is not None
