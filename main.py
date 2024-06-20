import cv2
import mediapipe as mp
import numpy as np
import asyncio
import websockets
import json

# Load YOLO model and initialize MediaPipe Pose
net = cv2.dnn.readNet("yolov4-tiny.weights", "yolov4-tiny.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
# cap.set(cv2.CAP_PROP_FPS, 60)



async def send_coordinates(data):
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print("good stuff: ", data)
            # print("Data sent successfully for ID:", data['id'])  # Print ID on data send
    except Exception as e:
        print("Failed to send data:", e)
        print("failed data: ", data)

async def main():
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)

        boxes = []
        confidences = []

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
        people_data = []
        if indexes is not None and len(indexes) > 0:
            indexes = indexes.flatten()
            for i, index in enumerate(indexes):
                x, y, w, h = boxes[index]
                roi = frame[y:y + h, x:x + w]
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                results = pose.process(roi_rgb)

                person_data = {'coordinates': [], 'id': i}
                if results.pose_landmarks:
                    for landmark in results.pose_landmarks.landmark:
                        abs_x = int(landmark.x * w + x)
                        abs_y = int(landmark.y * h + y)
                        abs_z = int(landmark.z * 1000)  # Assuming Z needs scaling
                        person_data['coordinates'].append({'x': abs_x, 'y': abs_y, 'z': abs_z})
                        # print("ID:", i, "Coords:", {'x': abs_x, 'y': abs_y, 'z': abs_z})
                        cv2.circle(frame, (abs_x, abs_y), 5, (0, 255, 0), -1)

                people_data.append(person_data)
                # print("people data: ", people_data)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        if people_data:
            # print("data: ", people_data)
            await send_coordinates(people_data)

        cv2.imshow('Frame', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
