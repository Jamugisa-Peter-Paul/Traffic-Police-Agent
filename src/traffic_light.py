import time


class TrafficLight:
    """
    Traffic light with two modes:
      - MANUAL: Follows officer gestures (STOP → RED, GO → GREEN)
      - AUTO:   Cycles RED → YELLOW → BLUE → GREEN (4s each) when no jacket detected
    """

    # Auto-cycle sequence and duration
    AUTO_SEQUENCE = ["RED", "YELLOW", "BLUE", "GREEN"]
    AUTO_DURATION = 4.0  # Maximum 4 seconds per light

    # BGR colors for OpenCV
    COLORS = {
        "RED":    (0, 0, 255),
        "YELLOW": (0, 255, 255),
        "BLUE":   (255, 100, 0),
        "GREEN":  (0, 255, 0),
    }

    def __init__(self):
        self.state = "RED"
        self.mode = "MANUAL"  # Start in manual mode
        self.last_switch = time.time()
        self.auto_index = 0   # Current position in AUTO_SEQUENCE

    def set_state(self, gesture):
        """
        Updates the traffic light state based on the detected gesture.

        When a jacket is detected:
          - STOP  → RED   (immediate)
          - GO    → GREEN (immediate)
          - NEUTRAL/UNKNOWN → hold current state

        When NO jacket detected:
          - Auto-cycle through RED → YELLOW → BLUE → GREEN (4s each)
        """
        current_time = time.time()

        if gesture == "NO JACKET DETECTED":
            # --- AUTO-CYCLE MODE ---
            if self.mode != "AUTO":
                # Just entered auto mode — start from RED
                self.mode = "AUTO"
                self.auto_index = 0
                self.state = self.AUTO_SEQUENCE[0]
                self.last_switch = current_time
                print(f"[AUTO] No jacket — starting auto-cycle from {self.state}")

            # Check if it's time to advance to next light
            elapsed = current_time - self.last_switch
            if elapsed >= self.AUTO_DURATION:
                self.auto_index = (self.auto_index + 1) % len(self.AUTO_SEQUENCE)
                self.state = self.AUTO_SEQUENCE[self.auto_index]
                self.last_switch = current_time
                print(f"[AUTO] Switched to {self.state}")

        else:
            # --- MANUAL MODE (officer detected) ---
            if self.mode != "MANUAL":
                self.mode = "MANUAL"
                print("[MANUAL] Officer detected — switching to manual control")

            if gesture == "STOP":
                if self.state != "RED":
                    print("Switching to RED (STOP Signal)")
                    self.state = "RED"
                    self.last_switch = current_time

            elif gesture == "GO":
                if self.state != "GREEN":
                    print("Switching to GREEN (GO Signal)")
                    self.state = "GREEN"
                    self.last_switch = current_time

            # NEUTRAL / UNKNOWN → hold current state

        return self.state

    def get_color(self):
        """Returns the BGR color for visualization."""
        return self.COLORS.get(self.state, (200, 200, 200))

    def get_auto_progress(self):
        """Returns (elapsed, total) for auto-cycle progress bar."""
        if self.mode == "AUTO":
            elapsed = time.time() - self.last_switch
            return min(elapsed, self.AUTO_DURATION), self.AUTO_DURATION
        return 0, 1
