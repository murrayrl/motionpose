from ultralytics import YOLO
import cv2
import time
import websockets
import json
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import torch
from torch.cuda.amp import autocast, GradScaler

# get device used = cpu
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

#set up yolo ML model
model = YOLO('yolov8s-pose.pt').to(device)
cap = cv2.VideoCapture(0)
buffer = []
buffer_size = 10  # Adjust buffer size as needed
last_processed_time = time.time()
frame_interval = 1 / 30  # Target 30 FPS

keypoint_names = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip', 'left_knee',
    'right_knee', 'left_ankle', 'right_ankle'
]

# Define the skeleton structure based on the COCO keypoints
skeleton = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # Head
    (5, 6),  # Shoulders
    (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
    (5, 11), (6, 12), (11, 12),  # Torso
    (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
]

# Initialize a dictionary to store the motion of keypoints
motion_data = {name: [] for name in keypoint_names}
frame_data = []  # To store the frames for video

# sends keypoint coordinates to frontend WS server
async def send_coordinates(data):
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print("Data sent successfully")
    except Exception as e:
        print("data: ", data)
        print("Failed to send data:", e)

#draws keypoints on frames, draws skeleton, id, and color
def draw_keypoints(frame, person_tracker, current_keypoints):
    # Check if person_tracker is a dictionary
    if not isinstance(person_tracker, dict):
        raise TypeError("Expected person_tracker to be a dictionary")

    # Draw keypoints for currently detected keypoints
    for person_id, data in person_tracker.items():
        # Get the corresponding keypoints from current_keypoints using the person_id
        keypoints = current_keypoints[person_id - 1] if person_id - 1 < len(current_keypoints) else None

        # Skip if keypoints are not valid or empty
        if keypoints is None or len(keypoints) == 0:
            continue
        
        color = data.get('color', (0, 0, 0))  # Get the assigned color for the person

        # Draw keypoints for the current person's keypoints
        for (x, y, conf) in keypoints:
            if conf > 0.5:  # Only consider confident keypoints
                cv2.circle(frame, (int(x), int(y)), 3, color, -1)

        # Draw skeleton lines, ensuring keypoints are valid
        if keypoints.shape[0] > max(max(connection) for connection in skeleton):
            for connection in skeleton:
                if keypoints[connection[0], 2] > 0.5 and keypoints[connection[1], 2] > 0.5:
                    cv2.line(
                        frame,
                        (int(keypoints[connection[0], 0]), int(keypoints[connection[0], 1])),
                        (int(keypoints[connection[1], 0]), int(keypoints[connection[1], 1])),
                        color,
                        2
                    )

        # Display the person ID near the first keypoint (e.g., the nose), if available
        if keypoints.shape[0] > 0 and keypoints[0, 2] > 0.5:
            # Get the person ID from the person tracker
            person_id = data.get('id', 0)
            cv2.putText(frame, f"ID: {person_id}", (int(keypoints[0, 0]), int(keypoints[0, 1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return frame


# get colors from a palette, can add more to reduce duplicate colors
color_palette = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (255, 0, 255), (0, 255, 255)
]
person_tracker = {}  # Dictionary to store keypoints, color, and id
next_person_id = 1  # Counter for assigning new IDs

# calculates mean distance between all keypoints from. compares last keypoints from when someone enters/leaves the frame to current
# keypoints, meant to increase accuracy and consistent tracking when someone enters or leaves the frame
def calculate_keypoint_similarity(kp1, kp2):
    """Calculate similarity between two sets of keypoints using Euclidean distance."""
    if len(kp1) != len(kp2):
        return float('inf')  # Return a large distance if keypoints length doesn't match

    distances = [
        np.linalg.norm(np.array(kp1[i][:2]) - np.array(kp2[i][:2]))
        for i in range(len(kp1))
        if kp1[i][2] > 0.5 and kp2[i][2] > 0.5  # Only consider confident keypoints
    ]

    return np.mean(distances) if distances else float('inf')

# updates person tracker
def update_person_tracker(keypoints_data, current_count, previous_count):
    global person_tracker
    global next_person_id
    #determine if person has left or entered frame
    difference = current_count - previous_count

    # If there are new people in the frame, add them
    if difference > 0:
        print("Person joined")
        for i in range(previous_count, current_count):
            current_kpts = keypoints_data[i].cpu().numpy()
            best_match_id = None
            lowest_distance = 45.0 #arbitrary minimum distance that keypoint comparison needs to meet

            # Compare with existing keypoints in person_tracker
            for person_id, data in person_tracker.items():
                existing_kpts = data['keypoints']
                distance = calculate_keypoint_similarity(existing_kpts, current_kpts)

                if distance < lowest_distance:
                    lowest_distance = distance
                    best_match_id = person_id

            # If a good match is found, use the existing ID; otherwise, assign a new one
            if best_match_id is not None and lowest_distance < 50:  # Threshold distance
                person_tracker[best_match_id]['keypoints'] = current_kpts
            else:
                color = color_palette[i % len(color_palette)]
                person_tracker[next_person_id] = {
                    'keypoints': current_kpts,
                    'color': color,
                    'id': next_person_id
                }
                next_person_id += 1

    # If people have left the frame, remove them
    elif difference < 0:
        print("Person left")
        for i in range(current_count, previous_count):
            if (i + 1) in person_tracker:
                del person_tracker[i + 1]
            next_person_id -= 1

    # log the updated tracker state
    print("Updated person tracker:", person_tracker)


async def main():
    global last_processed_time
    global person_tracker
    prev_num_people = 0 #initialize the number of people in the frame
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        buffer.append((frame, current_time))

        coordinates_data = []

        # Drop older frames if buffer exceeds size
        if len(buffer) > buffer_size:
            buffer.pop(0)

        # Process the frame if enough time has passed
        if current_time - last_processed_time >= frame_interval:
            frame_to_process, timestamp = buffer.pop(0)
            start_time = time.time()

            # Pre-process the frame
            frame_to_process_resized = cv2.resize(frame_to_process, (640, 640))
            frame_to_process_rgb = cv2.cvtColor(frame_to_process_resized, cv2.COLOR_BGR2RGB)
            frame_to_process = frame_to_process_rgb.transpose(2, 0, 1)  # HWC to CHW
            frame_to_process = np.ascontiguousarray(frame_to_process)
            frame_to_process = torch.from_numpy(frame_to_process).float().div(255.0).unsqueeze(0).to(device)

            with autocast():
                results = model(frame_to_process)

            if results:
                keypoint_count = {name: 0 for name in keypoint_names}
                for result in results:
                    keypoints = result.keypoints  # Keypoints outputs
                    # Check if keypoints are detected
                    if keypoints is not None and len(keypoints.data) > 0:
                        for person_keypoints in keypoints.data:
                            kpts = person_keypoints.cpu().numpy().reshape((-1, 3))
                            for idx, (x, y, conf) in enumerate(kpts):
                                if conf > 0.5:  # Check if keypoint is confident
                                    keypoint_name = keypoint_names[idx]
                                    keypoint_count[keypoint_name] += 1

                        # Determine the number of people as the max count of any keypoint
                        num_people = max(keypoint_count.values(), default=0)
                        print("number of people in frame: ", num_people)
                        #update tracker if person leaves or enters frame
                        if num_people != prev_num_people:
                            update_person_tracker(keypoints.data, num_people, prev_num_people)
                            print("tracker updated")
                            prev_num_people = num_people
                            
                        for i, person_keypoints in enumerate(keypoints.data):
                            kpts = person_keypoints.cpu().numpy().reshape((-1, 3))
                            person_data = {'person': i+1, 'keypoints': []}
                            #print(f"Person {i+1} Keypoints:")
                            person_data = {'person': i+1, 'keypoints': []}
                            for j, (x, y, conf) in enumerate(kpts):
                                if conf > 0.5:  # Only consider confident keypoints
                                    #print(f"  {keypoint_names[j]}: ({x:.2f}, {y:.2f}), confidence: {conf:.2f}")
                                    person_data['keypoints'].append({
                                        'label': keypoint_names[j],
                                        'x': float(x),
                                        'y': float(y),
                                        'confidence': float(conf)
                                    })
                            coordinates_data.append(person_data)
                        # Draw keypoints on the frame
                        frame = draw_keypoints(frame_to_process_resized, person_tracker, keypoints.data)
                        
                        # Ensure the frame has the correct format for imshow
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                        # Display the frame
                        cv2.imshow('YOLO Pose Estimation', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                        # Save the result frame
                        frame_data.append(frame)
                        cv2.imwrite("result.jpg", frame)
                    
                    if coordinates_data:
                        await send_coordinates(coordinates_data)
                        
            last_processed_time = current_time
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
#run main loop of the program
if __name__ == "__main__":
    asyncio.run(main())
