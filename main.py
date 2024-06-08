import cv2
import mediapipe as mp
import asyncio
import websockets
import json
from collections import deque

# Parameters
SMOOTHING_WINDOW_SIZE = 5

# Initialize deque for smoothing
x_coords = deque(maxlen=SMOOTHING_WINDOW_SIZE)
y_coords = deque(maxlen=SMOOTHING_WINDOW_SIZE)

async def send_coordinates(x, y):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        coordinates = {'x': x, 'y': y}
        await websocket.send(json.dumps(coordinates))

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)

async def main():
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            # Choose a specific landmark, e.g., the nose (landmark index 0)
            landmark = results.pose_landmarks.landmark[0]
            x = int(landmark.x * frame.shape[1])
            y = int(landmark.y * frame.shape[0])

            # Invert the x coordinate
            x = frame.shape[1] - x

            # Add coordinates to the deque
            x_coords.append(x)
            y_coords.append(y)

            # Compute the average of the coordinates
            avg_x = sum(x_coords) // len(x_coords)
            avg_y = sum(y_coords) // len(y_coords)

            # Send smoothed coordinates to the web application
            await send_coordinates(avg_x, avg_y)

        cv2.imshow('MediaPipe Pose', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the main function using asyncio
asyncio.run(main())
