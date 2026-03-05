import threading
import time

try:
    import requests
except ImportError:
    requests = None
    print("Warning: 'requests' library not found. Install with: pip install requests")


class HardwareBridge:
    """
    Sends traffic light state to the ESP8266 over HTTP.
    
    - Only sends on state CHANGE (avoids spamming)
    - Only sends when gesture is active (not NEUTRAL) 
    - Runs HTTP calls in a background thread (non-blocking)
    - Handles connection errors gracefully
    """

    def __init__(self, esp_ip, esp_port=80):
        self.base_url = f"http://{esp_ip}:{esp_port}"
        self.last_sent_state = None
        self.connected = False
        self._check_connection()

    def _check_connection(self):
        """Test if the ESP8266 is reachable."""
        if requests is None:
            print("[HardwareBridge] 'requests' not available — hardware disabled")
            return

        try:
            resp = requests.get(f"{self.base_url}/status", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                self.connected = True
                print(f"[HardwareBridge] Connected to ESP8266 at {self.base_url}")
                print(f"[HardwareBridge] Current state: {data.get('state')} | Mode: {data.get('mode')}")
            else:
                print(f"[HardwareBridge] ESP8266 responded with status {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"[HardwareBridge] Cannot reach ESP8266 at {self.base_url}")
            print("[HardwareBridge] Continuing without hardware — check IP and WiFi")
        except Exception as e:
            print(f"[HardwareBridge] Connection check failed: {e}")

    def send_state(self, state, gesture):
        """
        Send the traffic light state to the ESP8266.
        
        Args:
            state:   The light state string ("RED", "GREEN", "YELLOW")
            gesture: The raw gesture string ("STOP", "GO", "NEUTRAL", "UNKNOWN")
        """
        if requests is None or not self.connected:
            return

        # Don't send if gesture is NEUTRAL or UNKNOWN — let ESP auto-cycle
        if gesture in ("NEUTRAL", "UNKNOWN"):
            self.last_sent_state = None  # Reset so next active gesture sends immediately
            return

        # Don't send if state hasn't changed
        if state == self.last_sent_state:
            return

        self.last_sent_state = state

        # Fire-and-forget in background thread
        thread = threading.Thread(target=self._send, args=(state,), daemon=True)
        thread.start()

    def _send(self, state):
        """Perform the actual HTTP request (runs in background thread)."""
        try:
            url = f"{self.base_url}/set?state={state}"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                print(f"[HardwareBridge] → ESP8266: {data.get('state')} ({data.get('mode')})")
            else:
                print(f"[HardwareBridge] ESP responded: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print("[HardwareBridge] Lost connection to ESP8266")
            self.connected = False
        except Exception as e:
            print(f"[HardwareBridge] Send error: {e}")

    def get_status(self):
        """Query the current state from the ESP8266."""
        if requests is None or not self.connected:
            return None
        try:
            resp = requests.get(f"{self.base_url}/status", timeout=2)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
