import cv2
import time
from config import IP_CAMERA_URL, WEBCAM_INDEX, WINDOW_NAME, HARDWARE_ENABLED, ESP8266_IP, ESP8266_PORT
from src.camera import Camera
from src.detector import PoseDetector
from src.gesture_analyzer import GestureAnalyzer
from src.traffic_light import TrafficLight

def main():
    # Determine source: Priority to IP Camera if set
    source = IP_CAMERA_URL if IP_CAMERA_URL else WEBCAM_INDEX
    print(f"Starting camera with source: {source}")

    try:
        cam = Camera(source).start()
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Initialize Modules
    detector = PoseDetector()
    analyzer = GestureAnalyzer()
    traffic_light = TrafficLight()

    # Initialize Hardware Bridge (ESP8266) if configured
    bridge = None
    if HARDWARE_ENABLED:
        from src.hardware_bridge import HardwareBridge
        print(f"Hardware mode enabled — connecting to ESP8266 at {ESP8266_IP}:{ESP8266_PORT}")
        bridge = HardwareBridge(ESP8266_IP, ESP8266_PORT)
    else:
        print("Hardware mode disabled — set ESP8266_IP env variable to enable")

    while True:
        frame = cam.read()

        if frame is not None:
            # 1. Detect Pose
            frame = detector.find_pose(frame)
            lmList = detector.get_position(frame, draw=False)

            # 2. Analyze Gesture
            gesture = analyzer.analyze(lmList)

            # 3. Update Traffic Light (software)
            light_state = traffic_light.set_state(gesture)

            # 4. Send to Hardware (ESP8266)
            if bridge:
                bridge.send_state(light_state, gesture)

            # 5. Visualization
            # Draw Status Text
            cv2.putText(frame, f"Gesture: {gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            
            # Draw Traffic Light Indicator (Circle in top right)
            h, w, c = frame.shape
            light_color = traffic_light.get_color()
            cv2.circle(frame, (w - 50, 50), 30, light_color, cv2.FILLED)
            cv2.putText(frame, light_state, (w - 80, 100), cv2.FONT_HERSHEY_PLAIN, 1, light_color, 2)

            # Draw hardware connection status
            if bridge:
                hw_status = "HW: Connected" if bridge.connected else "HW: Disconnected"
                hw_color = (0, 255, 0) if bridge.connected else (0, 0, 255)
                cv2.putText(frame, hw_status, (10, 85), cv2.FONT_HERSHEY_PLAIN, 1, hw_color, 2)

            cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cam.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
