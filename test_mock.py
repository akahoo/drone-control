from tello_mock import MockTello
import time

def test_mock_logic():
    tello = MockTello()
    print(f"Initial Battery: {tello.get_battery()}")

    tello.connect()
    assert tello.get_battery() <= 100

    tello.takeoff()
    assert tello.is_flying == True

    tello.land()
    assert tello.is_flying == False

    frame_read = tello.get_frame_read()
    frame = frame_read.frame
    assert frame.shape == (720, 960, 3)

    tello.streamoff()
    assert tello.stream_on == False

    print("Mock Logic Verified.")

if __name__ == "__main__":
    test_mock_logic()
