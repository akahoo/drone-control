import time
import threading
import numpy as np
import cv2

class MockFrameRead:
    def __init__(self):
        self.running = True
        # Remove self.frame initialization since it's a property now

    @property
    def frame(self):
        # Generate a changing frame to simulate video
        img = np.zeros((720, 960, 3), dtype=np.uint8)
        # Random background color to visualize updates
        # Use a fixed seed or slow change to not be too seizure-inducing, but random is fine for test
        color = np.random.randint(0, 100, 3).tolist()
        cv2.rectangle(img, (0,0), (960, 720), color, -1)
        cv2.putText(img, f"Mock Tello Video: {time.time():.2f}", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        return img

    def stop(self):
        self.running = False

class MockTello:
    def __init__(self, host='192.168.10.1'):
        self.host = host
        self.is_flying = False
        self.battery = 100
        self.stream_on = False
        self.frame_reader = None

    def connect(self):
        print(f"[MockTello] Connecting to {self.host}...")
        time.sleep(1) # Simulate connection delay
        print("[MockTello] Connected.")
        return True

    def streamon(self):
        print("[MockTello] Stream ON")
        self.stream_on = True
        self.frame_reader = MockFrameRead()

    def streamoff(self):
        print("[MockTello] Stream OFF")
        self.stream_on = False
        if self.frame_reader:
            self.frame_reader.stop()
            self.frame_reader = None

    def get_frame_read(self):
        if not self.stream_on:
            self.streamon()
        return self.frame_reader

    def takeoff(self):
        print("[MockTello] Takeoff command received.")
        time.sleep(1)
        self.is_flying = True
        print("[MockTello] Taken off.")

    def land(self):
        print("[MockTello] Land command received.")
        time.sleep(1)
        self.is_flying = False
        print("[MockTello] Landed.")

    def emergency(self):
        print("[MockTello] EMERGENCY STOP!")
        self.is_flying = False

    def send_rc_control(self, lr, fb, ud, y):
        print(f"[MockTello] RC Control: lr={lr}, fb={fb}, ud={ud}, yaw={y}")

    def get_battery(self):
        # Simulate battery drain
        if self.battery > 0:
            self.battery -= 1
        return self.battery

    def get_current_state(self):
        return {}
