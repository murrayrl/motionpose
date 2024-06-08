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
z_coords = deque(maxlen=SMOOTHING_WINDOW_SIZE)  # For distance

# Scaling factor to amplify z-coordinates
Z_SCALING_FACTOR = 1000  # Adjust this based on observations

async def send_coordinates(x, y, z):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        coordinates = {'x': x, 'y': y, 'z': z}
        await websocket.send(json.dumps(coordinates))

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
holistic = mp_holistic.Holistic()
cap = cv2.VideoCapture(0)

async def main():
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = holistic.process(frame_rgb)

        if results.pose_landmarks:
            # Choose a specific landmark, e.g., the nose (landmark index 0)
            landmarks = results.pose_landmarks.landmark
            nose_landmark = landmarks[0]
            x = int(nose_landmark.x * frame.shape[1])
            y = int(nose_landmark.y * frame.shape[0])
            z = nose_landmark.z * Z_SCALING_FACTOR  # Scale z-coordinate

            # Invert the x coordinate
            x = frame.shape[1] - x

            # Add coordinates to the deque
            x_coords.append(x)
            y_coords.append(y)
            z_coords.append(z)

            # Compute the average of the coordinates
            avg_x = sum(x_coords) // len(x_coords)
            avg_y = sum(y_coords) // len(y_coords)
            avg_z = sum(z_coords) / len(z_coords)

            # Send smoothed coordinates to the web application
            await send_coordinates(avg_x, avg_y, avg_z)

            # Draw pose landmarks
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

        cv2.imshow('MediaPipe Holistic', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the main function using asyncio
asyncio.run(main())
