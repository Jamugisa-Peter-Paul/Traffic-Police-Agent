import math

class GestureAnalyzer:
    def __init__(self):
        self.current_state = "NEUTRAL"
        # MediaPipe Pose Landmarks
        # 11: left_shoulder, 12: right_shoulder
        # 13: left_elbow, 14: right_elbow
        # 15: left_wrist, 16: right_wrist

    def find_angle(self, p1, p2, p3):
        """Calculates the angle between three points."""
        # Get coordinates
        x1, y1 = p1[1], p1[2] # p1 is [id, x, y]
        x2, y2 = p2[1], p2[2]
        x3, y3 = p3[1], p3[2]

        # Calculate angle
        angle = math.degrees(math.atan2(y3 - y2, x3 - x2) -
                             math.atan2(y1 - y2, x1 - x2))
        
        if angle < 0:
            angle += 360
            
        return angle

    def analyze(self, lmList):
        """
        Analyzes the landmark list and returns the detected gesture.
        """
        if not lmList or len(lmList) == 0:
            return "UNKNOWN"

        # Landmarks
        # 11: left_shoulder, 12: right_shoulder
        # 13: left_elbow, 14: right_elbow
        # 15: left_wrist, 16: right_wrist
        
        # Calculate angles for arms
        # Angle at shoulder (hip-shoulder-elbow) or elbow (shoulder-elbow-wrist)
        # Let's use simple geometric checks for robustness
        
        l_shldr, r_shldr = lmList[11], lmList[12]
        l_elbow, r_elbow = lmList[13], lmList[14]
        l_wrist, r_wrist = lmList[15], lmList[16]
        
        # Check arms positions relative to shoulder height
        # Note: y coordinate increases downwards
        
        # Check for GO: Arms extended horizontally (T-position)
        # Wrists and elbows roughly at shoulder level
        # Tolerance in pixels
        y_tol = 60
        left_horizontal = abs(l_wrist[2] - l_shldr[2]) < y_tol and abs(l_elbow[2] - l_shldr[2]) < y_tol
        right_horizontal = abs(r_wrist[2] - r_shldr[2]) < y_tol and abs(r_elbow[2] - r_shldr[2]) < y_tol

        # If either arm is extended horizontally, it's GO
        if left_horizontal or right_horizontal:
            self.current_state = "GO"
            return self.current_state

        # Check for STOP: Palm up (Hand raised vertically)
        # Simplified: If wrist is significantly above shoulder
        left_up = l_wrist[2] < (l_shldr[2] - 50)
        right_up = r_wrist[2] < (r_shldr[2] - 50)

        # If either hand is raised, it's STOP
        if left_up or right_up:
             self.current_state = "STOP"
             return self.current_state

        self.current_state = "NEUTRAL"
        return self.current_state
