import tkinter as tk
from tello_gui import TelloGUI
import threading
import time

def test_gui_startup():
    print("Initializing Root...")
    root = tk.Tk()
    print("Initializing App...")
    app = TelloGUI(root)

    # Set to Mock Mode
    app.use_mock_var.set(True)

    # Simulate Click Connect
    print("Simulating Connect Click...")
    app.on_connect()

    # Wait a bit for connection thread
    start = time.time()
    while not app.is_connected and time.time() - start < 5:
        root.update()
        time.sleep(0.1)

    if app.is_connected:
        print("SUCCESS: Connected to Mock Tello")
    else:
        print("FAILURE: Could not connect to Mock Tello")
        exit(1)

    # Check if video thread is running
    if app.video_thread_running:
         print("SUCCESS: Video thread started")
    else:
         print("FAILURE: Video thread not started")
         exit(1)

    # Simulate Takeoff
    print("Simulating Takeoff...")
    app.send_command(app.tello.takeoff)

    # Run loop briefly
    for _ in range(20):
        root.update()
        time.sleep(0.1)

    print("Closing...")
    app.on_disconnect()
    root.destroy()
    print("Test Complete.")

if __name__ == "__main__":
    test_gui_startup()
