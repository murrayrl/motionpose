import cv2
import mediapipe as mp
import numpy as np
import asyncio
import websockets
import json
import time

# Load YOLO model and initialize MediaPipe Pose
net = cv2.dnn.readNet("yolov4-tiny.weights", "yolov4-tiny.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)

visibility_threshold = 0.5

async def send_coordinates(data):
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print("Data sent successfully")
    except Exception as e:
        print("Failed to send data:", e)

async def main():
    last_time_sent = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # current_time = time.time()
        # if current_time - last_time_sent < 1:
        #     continue  # Skip this iteration if it's less than a second since the last send

        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)

        boxes = []
        confidences = []
        coordinates_data = []  # Clear previous data

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.6:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = max(0, int(center_x - w / 2))
                    y = max(0, int(center_y - h / 2))
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.2, 0.3)
        if indexes is not None and len(indexes) > 0:
            indexes = indexes.flatten()
            for index in indexes:
                x, y, w, h = boxes[index]
                roi = frame[y:y + h, x:x + w]
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                results = pose.process(roi_rgb)

                if results.pose_landmarks:
                    lm = results.pose_landmarks.landmark
                    shoulders = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                                    lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]]
                    if all(shoulders):
                        # Calculate and append each point once
                        midpoint_x = int((shoulders[0].x + shoulders[1].x) * 0.5 * w + x)
                        midpoint_y = int((shoulders[0].y + shoulders[1].y) * 0.5 * h + y)
                        midpoint_z = int((shoulders[0].z + shoulders[1].z) * 0.5 * 1000)
                        coordinates_data.append({'label': 'midpoint', 'x': midpoint_x, 'y': midpoint_y, 'z': midpoint_z})

                        left_shoulder_x = int(shoulders[0].x * w + x)
                        left_shoulder_y = int(shoulders[0].y * h + y)

                        right_shoulder_x = int(shoulders[1].x * w + x)
                        right_shoulder_y = int(shoulders[1].y * h + y)

                        cv2.circle(frame, (left_shoulder_x, left_shoulder_y), 5, (0, 0, 255), -1)  # Blue for left shoulder
                        cv2.circle(frame, (right_shoulder_x, right_shoulder_y), 5, (255, 0, 0), -1)  # Red for right shoulder
                        cv2.circle(frame, (midpoint_x, midpoint_y), 5, (0, 255, 0), -1) # midpoint

                # YOLO bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if coordinates_data:
            await send_coordinates(coordinates_data)
            

        cv2.imshow('Frame', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
