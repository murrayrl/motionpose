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
from pythonosc import udp_client

# Set up the OSC client
ip = "127.0.0.1"  # The IP address of the computer running Isadora
port = 1234      # Isadora default port
client = udp_client.SimpleUDPClient(ip, port)
address_x = "/isadora-multi/1"
address_y = "/isadora-multi/2"


# if not torch.cuda.is_available():
#     raise SystemError("CUDA is not available. Please check your installation.")

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

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

kpt_list = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']

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

def send_osc(x_list, y_list):

    for (key1, value1), (key2, value2) in zip(x_list.items(), y_list.items()):
        channel_x = str(address_x + '/' + key1)
        channel_y = str(address_y + '/' + key2)
        client.send_message(channel_x, value1)
        client.send_message(channel_y, value2)
        


async def send_coordinates(data):
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print("Data sent successfully")
    except Exception as e:
        print("data: ", data)
        print("Failed to send data:", e) 


def draw_keypoints(frame, keypoints):
    for person_keypoints in keypoints:
        kpts = person_keypoints.cpu().numpy().reshape((-1, 3))
        if kpts.size == 0:
            continue 
        for i, (x, y, conf) in enumerate(kpts):
            if conf > 0.5:  # Only consider confident keypoints
                cv2.circle(frame, (int(x), int(y)), 3, (0, 255, 0), -1)
                cv2.putText(frame, keypoint_names[i], (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                # Store the keypoint motion data
                motion_data[keypoint_names[i]].append((x, y))
        # Draw skeleton
        for connection in skeleton:
            if kpts[connection[0], 2] > 0.5 and kpts[connection[1], 2] > 0.5:
                cv2.line(frame, (int(kpts[connection[0], 0]), int(kpts[connection[0], 1])),
                         (int(kpts[connection[1], 0]), int(kpts[connection[1], 1])), (255, 0, 0), 2)
    return frame

def calculate_service_delay(D_prev_q, D_prev_s, T_a, D_curr_s):
    if (D_prev_q + D_prev_s - T_a > 0):
        return D_prev_q + D_prev_s + T_a + D_curr_s
    else:
        return D_curr_s

async def main():
    global last_processed_time
    D_prev_q = 0
    D_prev_s = 0
    T_a = frame_interval

    scaler = GradScaler()

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
                for result in results:
                    keypoints = result.keypoints  # Keypoints outputs
                    list_x = {}
                    list_y = {} 
                    # Check if keypoints are detected
                    if keypoints is not None and len(keypoints.data) > 0:
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
                                    if (keypoint_names[j] in kpt_list):
                                        list_x[keypoint_names[j]]= float(x)
                                        list_y[keypoint_names[j]] = float(y)

                            coordinates_data.append(person_data)
                        # Draw keypoints on the frame
                        frame = draw_keypoints(frame_to_process_resized, keypoints.data)
                        
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
                        send_osc(list_x, list_y)
                

            end_time = time.time()
            D_curr_s = end_time - start_time
            service_delay = calculate_service_delay(D_prev_q, D_prev_s, T_a, D_curr_s)
            D_prev_q = D_curr_s
            D_prev_s = service_delay

            print(f"Service Delay: {service_delay:.4f} seconds")
            last_processed_time = current_time
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def plot_motion():
    plt.figure(figsize=(12, 8))
    for keypoint, positions in motion_data.items():
        if positions:  # Only plot if there are positions recorded
            x_coords, y_coords = zip(*positions)
            plt.plot(x_coords, y_coords, label=keypoint)

    plt.title("Motion of Keypoints")
    plt.xlabel("X-coordinate")
    plt.ylabel("Y-coordinate")
    plt.legend()
    plt.gca().invert_yaxis()  # Invert y-axis to match the image coordinate system
    plt.savefig("motion_plot.png")
    plt.show()

def save_motion_data():
    np.savez("motion_data.npz", **motion_data)

def save_video(frame_data, filename='output.mp4', fps=30):
    height, width, layers = frame_data[0].shape
    size = (width, height)
    out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
    for frame in frame_data:
        out.write(frame)
    out.release()

def create_animation():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_title('Motion of Keypoints')
    ax.set_xlim([0, 1920])
    ax.set_ylim([0, 1080])
    ax.invert_yaxis()  # Invert y-axis to match the image coordinate system

    lines = {keypoint: ax.plot([], [], marker='o', linestyle='-', label=keypoint)[0] for keypoint in keypoint_names}
    ax.legend()

    def init():
        for line in lines.values():
            line.set_data([], [])
        return lines.values()

    def update(frame_number):
        for keypoint, line in lines.items():
            if len(motion_data[keypoint]) > frame_number:
                x, y = zip(*motion_data[keypoint][:frame_number + 1])
                line.set_data(x, y)
        return lines.values()

    ani = animation.FuncAnimation(fig, update, frames=len(frame_data), init_func=init, blit=True, interval=1000/30)
    ani.save('motion_animation.mp4', writer='ffmpeg', fps=30)
    plt.show()

if __name__ == "__main__":
    asyncio.run(main())


save_motion_data()
save_video(frame_data)
plot_motion()