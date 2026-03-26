import cv2
import time
from config import (
    IP_CAMERA_URL, WEBCAM_INDEX, WINDOW_NAME,
    JACKET_MODEL_PATH, JACKET_CONFIDENCE_THRESHOLD,
    DEVICE, JACKET_IMGSZ, DETECT_EVERY_N_FRAMES,
    HARDWARE_ENABLED, ESP8266_IP, ESP8266_PORT
)
from src.camera import Camera
from src.detector import PoseDetector
from src.gesture_analyzer import GestureAnalyzer
from src.traffic_light import TrafficLight
from src.jacket_detector import SafetyJacketDetector

def main():
    # Determine source: Priority to IP Camera if set
    source = IP_CAMERA_URL if IP_CAMERA_URL else WEBCAM_INDEX
    print(f"Starting camera with source: {source}")

    try:
        cam = Camera(source).start()
    except ValueError as e:
        if source != WEBCAM_INDEX:
            print(f"⚠️  IP camera failed: {e}")
            print(f"📷 Falling back to webcam (index {WEBCAM_INDEX})...")
            try:
                cam = Camera(WEBCAM_INDEX).start()
            except ValueError as e2:
                print(f"Error: Webcam also failed: {e2}")
                return
        else:
            print(f"Error: {e}")
            return

    # Initialize Modules
    detector = PoseDetector()
    analyzer = GestureAnalyzer()
    traffic_light = TrafficLight()
    jacket_detector = SafetyJacketDetector(
        model_path=JACKET_MODEL_PATH,
        conf_threshold=JACKET_CONFIDENCE_THRESHOLD,
        device=DEVICE,
        imgsz=JACKET_IMGSZ
    )

    # Frame skipping (loaded from config — CPU skips more, GPU processes every frame)
    frame_count = 0
    cached_has_jacket = False
    cached_bbox = None

    # FPS counter
    prev_time = time.time()

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
            frame_count += 1

            # 0. Detect Safety Jacket (skip frames on CPU for speed)
            if frame_count % DETECT_EVERY_N_FRAMES == 0:
                has_jacket, bbox, frame = jacket_detector.detect(frame)
                cached_has_jacket = has_jacket
                cached_bbox = bbox
            else:
                has_jacket = cached_has_jacket
                bbox = cached_bbox
                # Still draw cached bbox if we have one
                if bbox is not None:
                    x1, y1, x2, y2 = map(int, bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(frame, "Safety Jacket", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            if has_jacket:
                # 1. Detect Pose
                frame = detector.find_pose(frame)
                lmList = detector.get_position(frame, draw=False)

                # 2. Analyze Gesture
                gesture = analyzer.analyze(lmList)
            else:
                gesture = "NO JACKET DETECTED"

            # 3. Update Traffic Light (software)
            light_state = traffic_light.set_state(gesture)

            # 4. Send to Hardware (ESP8266)
            if bridge:
                bridge.send_state(light_state, gesture)

            # 5. Visualization
            # FPS counter
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time

            # Draw Status Text
            text_color = (255, 255, 0) if has_jacket else (0, 0, 255)
            cv2.putText(frame, f"Gesture: {gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
            cv2.putText(frame, f"FPS: {fps:.1f} | {DEVICE.upper()}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
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

            frame = cv2.resize(frame, (1280, 720))
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cam.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
