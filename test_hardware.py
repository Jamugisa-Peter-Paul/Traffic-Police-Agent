import sys
import time
from src.hardware_bridge import HardwareBridge

def test_hardware(ip_address):
    print(f"--- Starting Hardware Bridge Test for ESP8266 at {ip_address} ---")
    bridge = HardwareBridge(esp_ip=ip_address)
    
    # Give it a moment to check connection
    time.sleep(1)
    
    if not bridge.connected:
        print("\n[!] Failed to connect to the ESP8266.")
        print("Please verify:")
        print("1. The ESP8266 is powered on.")
        print("2. It is connected to the same WiFi network as this PC.")
        print(f"3. The IP address {ip_address} is correct.")
        return

    print("\n[+] Connection successful! Beginning state sequence test...\n")
    
    states = [
        ("RED", "STOP"),
        ("YELLOW", "WARNING"),
        ("GREEN", "GO")
    ]
    
    for state, simulated_gesture in states:
        print(f"Sending State: {state} (Triggered by gesture: {simulated_gesture})")
        bridge.send_state(state, simulated_gesture)
        time.sleep(2)  # Wait for state to register
        
        status = bridge.get_status()
        if status:
            print(f"Verified ESP Status -> {status}")
        else:
            print("[!] Failed to get status back from ESP.")
            
        print("-" * 30)
        time.sleep(1)
        
    print("\n--- Hardware Test Complete ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_hardware.py <ESP_IP_ADDRESS>")
        print("Example: python test_hardware.py 192.168.1.50")
        sys.exit(1)
        
    target_ip = sys.argv[1]
    test_hardware(target_ip)
