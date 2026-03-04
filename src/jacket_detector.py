import cv2
import numpy as np
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    print("Warning: ultralytics package not found. Safety jacket detection will be disabled.")

class SafetyJacketDetector:
    def __init__(self, model_path="models/best_jacket.pt", conf_threshold=0.5):
        """
        Initializes the YOLOv8 model for detecting safety jackets.
        
        Args:
            model_path (str): Path to the trained YOLOv8 weights (.pt file).
            conf_threshold (float): Minimum confidence for a detection to be valid.
        """
        self.conf_threshold = conf_threshold
        self.loaded = False

        if not ULTRALYTICS_AVAILABLE:
            return

        try:
            # We initialize YOLO with the provided weights path
            self.model = YOLO(model_path)
            self.loaded = True
            print(f"Safety Jacket Detector loaded successfully from {model_path}.")
        except Exception as e:
            print(f"Warning: Could not load Safety Jacket model from {model_path}. "
                  f"Error: {e}\nFalling back to pass-through mode (always returns True).")

    def detect(self, frame):
        """
        Detects if there is a safety jacket in the frame.
        
        Args:
            frame: The input image/frame from the camera.
            
        Returns:
            has_jacket (bool): True if jacket found, False otherwise.
            bbox (list): [x1, y1, x2, y2] of the detected jacket, or None.
            annotated_frame (numpy array): Frame with bounding box drawn.
        """
        if not self.loaded:
            # Fallback if model not trained/loaded, we assume a jacket is present 
            # so the rest of the application still functions.
            return True, None, frame

        # Run inference
        results = self.model(frame, conf=self.conf_threshold, imgsz=320, verbose=False)
        annotated_frame = frame.copy()
        
        # Debug: print detection info
        for r in results:
            if len(r.boxes) > 0:
                scores = [f"{b.conf[0].item():.2f}" for b in r.boxes]
                print(f"[JACKET DEBUG] Found {len(r.boxes)} detections, scores: {scores}")
            else:
                print("[JACKET DEBUG] No detections in this frame", end='\r')
        
        has_jacket = False
        best_bbox = None

        for result in results:
            boxes = result.boxes
            if len(boxes) > 0:
                has_jacket = True
                # Get the first box (could add logic to find most confident or largest)
                best_bbox = boxes[0].xyxy[0].cpu().numpy()
                
                # Draw the bounding box for visualization
                x1, y1, x2, y2 = map(int, best_bbox)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow box
                cv2.putText(annotated_frame, "Safety Jacket", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                break # We just need to know if at least one is present

        return has_jacket, best_bbox, annotated_frame
