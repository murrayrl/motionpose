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

mp_drawing = mp.solutions.drawing_utils
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

            #  Use landmarks such as the shoulders or hips for more stability
            # right_hip = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP]
            # left_hip = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP]
            # mid_hip_x = (right_hip.x + left_hip.x) * 0.5 * frame.shape[1]
            # mid_hip_y = (right_hip.y + left_hip.y) * 0.5 * frame.shape[0]
            # mid_hip_z = (right_hip.z + left_hip.z) * 0.5 * Z_SCALING_FACTOR

            # Invert the x coordinate
            # mid_hip_x = frame.shape[1] - mid_hip_x


            landmark = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
            x = landmark.x * frame.shape[1]
            y = landmark.y * frame.shape[0]
            z = landmark.z * Z_SCALING_FACTOR  # Scaling factor for visibility

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

            # Draw pose landmarks using the correct reference for pose connections
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)

        cv2.imshow('MediaPipe Pose', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the main function using asyncio
asyncio.run(main())
