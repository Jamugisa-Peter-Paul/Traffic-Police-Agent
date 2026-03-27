import threading
import time
import json

try:
    import serial
    import serial.tools.list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False
    print("Warning: 'pyserial' not found. Install with: pip install pyserial")


class SerialBridge:
    """
    Sends traffic light state to the ESP8266 over USB Serial.
    Fallback for when WiFi (HardwareBridge) is not available.
    
    - Auto-detects ESP8266 COM port if not specified
    - Only sends on state CHANGE (avoids spamming)
    - Only sends when gesture is active (not NEUTRAL)
    - Runs serial writes in a background thread (non-blocking)
    - Same interface as HardwareBridge
    """

    # Common USB-to-Serial chip identifiers for ESP8266 boards
    ESP_IDENTIFIERS = ["CH340", "CP210", "FTDI", "CH9102", "USB-SERIAL", "USB Serial"]

    def __init__(self, port=None, baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.last_sent_state = None
        self.connected = False
        self.lock = threading.Lock()

        if not PYSERIAL_AVAILABLE:
            print("[SerialBridge] pyserial not available — serial disabled")
            return

        # Auto-detect port if not specified
        if not self.port:
            self.port = self._auto_detect_port()

        if self.port:
            self._connect()
        else:
            print("[SerialBridge] No ESP8266 serial port found")

    def _auto_detect_port(self):
        """Scan COM ports for common ESP8266 USB-Serial chips."""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            desc = (p.description or "").upper()
            mfr = (p.manufacturer or "").upper()
            for ident in self.ESP_IDENTIFIERS:
                if ident.upper() in desc or ident.upper() in mfr:
                    print(f"[SerialBridge] Auto-detected ESP8266 on {p.device} ({p.description})")
                    return p.device

        # If only one serial port exists, use it as a guess
        if len(ports) == 1:
            p = ports[0]
            print(f"[SerialBridge] Only one serial port found, using {p.device} ({p.description})")
            return p.device

        if ports:
            print(f"[SerialBridge] Multiple serial ports found but none matched ESP8266:")
            for p in ports:
                print(f"  - {p.device}: {p.description}")
        return None

    def _connect(self):
        """Open the serial connection."""
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(2)  # Wait for ESP8266 to finish booting/resetting
            # Flush any boot messages
            self.ser.reset_input_buffer()
            # Test with a STATUS command
            self.ser.write(b"STATUS\n")
            time.sleep(0.5)
            response = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if response and "state" in response.lower():
                try:
                    data = json.loads(response)
                    self.connected = True
                    print(f"[SerialBridge] Connected via {self.port} @ {self.baud} baud")
                    print(f"[SerialBridge] Current state: {data.get('state')} | Mode: {data.get('mode')}")
                except json.JSONDecodeError:
                    # Got a response but not valid JSON — might be boot messages
                    self.connected = True
                    print(f"[SerialBridge] Connected via {self.port} (initial response: {response})")
            else:
                # Port opened but no valid response — could still work
                self.connected = True
                print(f"[SerialBridge] Connected via {self.port} (no STATUS response yet, may need reset)")
        except serial.SerialException as e:
            print(f"[SerialBridge] Failed to open {self.port}: {e}")
        except Exception as e:
            print(f"[SerialBridge] Connection error: {e}")

    def send_state(self, state, gesture):
        """
        Send the traffic light state to the ESP8266 over serial.
        
        Args:
            state:   The light state string ("RED", "GREEN", "YELLOW")
            gesture: The raw gesture string ("STOP", "GO", "NEUTRAL", "UNKNOWN")
        """
        if not self.connected or self.ser is None:
            return

        # Don't send if gesture is NEUTRAL or UNKNOWN — let ESP auto-cycle
        if gesture in ("NEUTRAL", "UNKNOWN"):
            self.last_sent_state = None
            return

        # Don't send if state hasn't changed
        if state == self.last_sent_state:
            return

        self.last_sent_state = state

        # Fire-and-forget in background thread
        thread = threading.Thread(target=self._send, args=(state,), daemon=True)
        thread.start()

    def _send(self, state):
        """Perform the actual serial write (runs in background thread)."""
        try:
            with self.lock:
                cmd = f"SET:{state}\n"
                self.ser.write(cmd.encode("utf-8"))
                self.ser.flush()
                time.sleep(0.1)
                
                # Read response
                response = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if response:
                    try:
                        data = json.loads(response)
                        print(f"[SerialBridge] → ESP8266: {data.get('state')} ({data.get('mode')})")
                    except json.JSONDecodeError:
                        print(f"[SerialBridge] Response: {response}")
        except serial.SerialException:
            print("[SerialBridge] Lost connection to ESP8266")
            self.connected = False
        except Exception as e:
            print(f"[SerialBridge] Send error: {e}")

    def get_status(self):
        """Query the current state from the ESP8266 over serial."""
        if not self.connected or self.ser is None:
            return None
        try:
            with self.lock:
                self.ser.write(b"STATUS\n")
                self.ser.flush()
                time.sleep(0.1)
                response = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if response:
                    return json.loads(response)
        except Exception:
            pass
        return None

    def close(self):
        """Close the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[SerialBridge] Serial connection closed")
