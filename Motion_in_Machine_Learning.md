# 📄 Motion in Machine Learning: Facial Recognition Progress Journal

## 🧠 Overview

This project integrates **facial recognition** and **pose estimation** for tracking people using a webcam. It uses:

- `MTCNN` for face detection  
- `InceptionResnetV1` (VGGFace2) for facial recognition  
- `YOLOv8` for 2D pose estimation  
- `OpenCV` + `Torch` for processing  
- `WebSockets` for real-time frontend updates  

---

## 📆 Weekly Progress

### Week 1 — Research
> ✅ Identified existing models for facial recognition.

### Week 2 — Initial Setup
> ✅ Implemented webcam-based face detection using `MTCNN` and face recognition using `InceptionResnetV1`.

```python
import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1

mtcnn = MTCNN(keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()
cap = cv2.VideoCapture(0)
def cosine_similarity(embedding1, embedding2):
    dot = np.dot(embedding1, embedding2.T)
    return dot / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
```

### Week 3 — Matching IDs with Similarity
> ✅ Added cosine similarity comparison and timeout logic for consistent ID matching.

```python
current_faces = {}
SIMILARITY_THRESHOLD = 0.4
TIMEOUT_THRESHOLD = 30
next_id = 1
```

### Week 4 — Consistency Testing
> 🔄 Increased thresholds for better stability and added moving average for embeddings.

```python
SIMILARITY_THRESHOLD = 0.6
TIMEOUT_THRESHOLD = 100
```

### Week 5 — Multiple Embeddings
> ✅ Stored up to 5 embeddings per ID to improve accuracy.

```python
if len(previous_faces[matched_id]['embeddings']) > 5:
    previous_faces[matched_id]['embeddings'].pop(0)
```

### Week 7 — Abstract
> Facial recognition added for consistent tracking using InceptionResnet. Built a real-time recognition system using webcam footage.

---

## 🚀 Final Code (Integrated Pose + Face Tracking)

### cosine_similarity()
```python
def cosine_similarity(embedding1, embedding2):
    dot = np.dot(embedding1, embedding2.T)
    return dot / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
```

### run_face_rec(rgb_frame)
```python
def run_face_rec(rgb_frame):
    global current_faces, next_person_id
    faces, confidences = mtcnn.detect(rgb_frame)
    if faces is not None:
        for box in faces:
            x1, y1, x2, y2 = [int(b) for b in box]
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            face = rgb_frame[y1:y2, x1:x2]
            face_resized = cv2.resize(face, (160, 160))
            face_tensor = torch.from_numpy(face_resized).permute(2, 0, 1).float() / 255.0
            face_tensor = face_tensor.unsqueeze(0).to(device)
            face_embedding = resnet(face_tensor).detach().cpu().numpy().flatten()

            matched_face_id = None
            max_similarity = -1
            for face_id, data in current_faces.items():
                for stored_embedding in data['embeddings']:
                    similarity = cosine_similarity(face_embedding, stored_embedding)
                    if similarity > SIMILARITY_THRESHOLD and similarity > max_similarity:
                        matched_face_id = face_id
                        max_similarity = similarity

            if matched_face_id is None:
                matched_face_id = next_person_id
                current_faces[matched_face_id] = {'embeddings': [], 'center': (center_x, center_y)}
                next_person_id += 1

            current_faces[matched_face_id]['embeddings'].append(face_embedding)
            if len(current_faces[matched_face_id]['embeddings']) > 5:
                current_faces[matched_face_id]['embeddings'].pop(0)
            current_faces[matched_face_id]['center'] = (center_x, center_y)
```

### update_person_tracker(keypoints)
```python
def update_person_tracker(keypoints):
    global person_tracker, current_faces, next_person_id
    if keypoints is not None and len(keypoints.data) > 0:
        for person_keypoints in keypoints.data:
            kpts = person_keypoints.cpu().numpy().reshape((-1, 3))
            x_aggr = sum(x for x, y, c in kpts if c > 0.5)
            y_aggr = sum(y for x, y, c in kpts if c > 0.5)
            count = sum(1 for _, _, c in kpts if c > 0.5)
            kpts_center = (x_aggr / count, y_aggr / count) if count else (0, 0)
            match_id = None
            min_dist = float('inf')
            for face_id, data in current_faces.items():
                fx, fy = data['center']
                dist = ((fx - kpts_center[0])**2 + (fy - kpts_center[1])**2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    match_id = face_id
            color = color_palette[match_id % len(color_palette)]
            person_tracker[match_id] = {
                'keypoints': person_keypoints,
                'color': color,
                'id': match_id,
                'faceCenter': current_faces[match_id]['center'],
                'kptsCenter': kpts_center,
                'embeddings': current_faces[match_id]['embeddings']
            }
```

### send_coordinates()
```python
async def send_coordinates(data):
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print("Data sent successfully")
    except Exception as e:
        print("Failed to send data:", e)
```

### main()
```python
async def main():
    global last_processed_time
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        current_time = time.time()
        buffer.append((frame, current_time))
        if len(buffer) > buffer_size:
            buffer.pop(0)
        if current_time - last_processed_time >= frame_interval:
            frame_to_process, _ = buffer.pop(0)
            frame_resized = cv2.resize(frame_to_process, (640, 640))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            input_tensor = torch.from_numpy(frame_rgb.transpose(2, 0, 1)).float().div(255.0).unsqueeze(0).to(device)

            with autocast():
                results = model(input_tensor)
                coordinates_data, keypoints = get_keypoints(results)
                run_face_rec(frame_rgb)
                update_person_tracker(keypoints)
                final_frame = draw_keypoints(frame_resized, person_tracker, keypoints.data)
                final_frame = cv2.cvtColor(final_frame, cv2.COLOR_RGB2BGR)
                cv2.imshow("Pose + Face Recognition", final_frame)
                if coordinates_data:
                    await send_coordinates(coordinates_data)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            last_processed_time = current_time

    cap.release()
    cv2.destroyAllWindows()
```

---

## 🏁 How to Run

```bash
pip install facenet-pytorch opencv-python numpy websockets matplotlib torch torchvision
```
Make sure `yolov8s-pose.pt` is downloaded and in your directory.

---