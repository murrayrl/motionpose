import cv2
import torch
import numpy as np
from ultralytics import YOLO

# Load the YOLOv8 model
model_yolo = YOLO('yolov8n.pt')

# Load the MiDaS v3 model for depth estimation
model_midas = torch.hub.load("intel-isl/MiDaS", "MiDaS")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_midas.to(device)
model_midas.eval()

# Prepare the MiDaS transformation
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.default_transform

# Open the video file or camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()
    if success:
        # Convert the frame to RGB (MiDaS works with RGB images)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run YOLOv8 inference on the frame
        results = model_yolo(frame, classes=[0], conf=0.5)

        # Prepare frame for MiDaS depth estimation
        input_batch = transform(frame_rgb).to(device)

        # Predict depth
        with torch.no_grad():
            depth = model_midas(input_batch)
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(1),
                size=frame.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        
        # Normalize depth for visualization (not needed for depth value extraction)
        depth_normalized = cv2.normalize(depth.cpu().numpy(), None, 0, 255, cv2.NORM_MINMAX)
        depth_colored = cv2.applyColorMap(depth_normalized.astype(np.uint8), cv2.COLORMAP_JET)

        if len(results) > 0 and hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
            for r in results:
                boxes = r.boxes.xywh  # Assuming r.boxes.xywh is the correct way to access the boxes
                for box in boxes:
                    x_center, y_center = box[0], box[1]  # Unpack the center coordinates
                    
                    # Map the center coordinates to depth map scale
                    x_depth = int(x_center * depth.shape[1] / frame.shape[1])
                    y_depth = int(y_center * depth.shape[0] / frame.shape[0])
                    
                    # Extract depth value at the center of the detected person
                    depth_value = depth[y_depth, x_depth].item()
                    originalShape = r.boxes.orig_shape
                    print(f"Center coordinates: x={x_center}, y={y_center}, depth={depth_value}, Original Shape={originalShape}")

            # Visualize the results on the frame
            annotated_frame = results[0].plot()

            # Display the annotated frame and the depth map
            #cv2.imshow("YOLOv8 Inference", annotated_frame)
            cv2.imshow("Depth Map", depth_colored)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        break

# Release the video capture object and close the display window
cap.release()
cv2.destroyAllWindows()
