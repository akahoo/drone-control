from tello_gui import TelloGUI
from tello_mock import MockTello
import time
import threading
import queue
import tkinter as tk

def test_blocking_logic():
    print("Testing Blocking Logic...")

    # 1. Setup minimal headless Mock App
    root = tk.Tk()
    app = TelloGUI(root)
    app.use_mock_var.set(True)

    # Bypass full connect thread to just set up what we need
    app.tello = MockTello()
    app.is_connected = True

    # 2. Define a blocking mock function
    def slow_task():
        print("Task Start")
        time.sleep(2)
        print("Task End")

    # 3. Send Blocking Command
    print("Sending Blocking Command...")
    app.send_command(slow_task, blocking=True)

    # Allow worker to pick it up
    time.sleep(0.5)

    # 4. Verify UI is Busy
    # We can check the internal flag since we can't see the buttons
    if app.is_executing_blocking_cmd:
        print("SUCCESS: UI is locked (Busy state active).")
    else:
        print("FAILURE: UI should be locked.")
        exit(1)

    # 5. Try to send another command immediately
    print("Attempting second command (should be rejected)...")

    # We'll use a queue or flag to see if this second task runs
    second_task_run = False
    def quick_task():
        nonlocal second_task_run
        second_task_run = True
        print("Quick Task Ran")

    app.send_command(quick_task, blocking=True)

    # 6. Verify second command did NOT queue/run immediately
    # The current logic REJECTS input if busy.
    # So the queue should be empty (or the task not run).
    # Since send_command returns immediately, we check if it was accepted.
    # Actually, send_command logs "Command rejected" but returns None.
    # We can check if `quick_task` runs.

    time.sleep(0.5)
    if second_task_run:
        print("FAILURE: Second command ran but should have been rejected.")
        exit(1)
    else:
         print("SUCCESS: Second command was ignored/rejected.")

    # 7. Wait for first task to finish
    print("Waiting for task to finish...")
    time.sleep(2.0)

    # UI should unlock
    # Note: `_set_ui_busy` uses `root.after`, so we need to process events
    for _ in range(10):
        root.update()
        time.sleep(0.1)

    if not app.is_executing_blocking_cmd:
        print("SUCCESS: UI is unlocked.")
    else:
        print("FAILURE: UI is still locked.")
        exit(1)

    # 8. Now send second task
    print("Sending second command again (should run)...")
    app.send_command(quick_task, blocking=True)

    time.sleep(0.5)
    if second_task_run:
        print("SUCCESS: Command ran after unlock.")
    else:
        # Worker might take a moment
        time.sleep(1)
        if second_task_run:
             print("SUCCESS: Command ran after unlock.")
        else:
             print("FAILURE: Command did not run.")
             exit(1)

    # Clean up
    app.queue_thread_running = False
    root.destroy()
    print("Blocking Logic Test Complete.")

if __name__ == "__main__":
    test_blocking_logic()
