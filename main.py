from ultralytics import YOLO
from ultralytics.solutions import distance_calculation
import cv2

model = YOLO("yolov8n.pt")
names = model.model.names

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

assert cap.isOpened(), "Error reading video file"
w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

# Video writer
video_writer = cv2.VideoWriter("distance_calculation.avi",
                               cv2.VideoWriter_fourcc(*'mp4v'),
                               fps,
                               (w, h))

# Init distance-calculation obj
dist_obj = distance_calculation.DistanceCalculation()
dist_obj.set_args(names=names, view_img=True)

while cap.isOpened():
    success, im0 = cap.read()
    if not success:
        print("Video frame is empty or video processing has been successfully completed.")
        break

    tracks = model.track(im0, persist=True, show=False)
    im0 = dist_obj.start_process(im0, tracks)
    video_writer.write(im0)

cap.release()
video_writer.release()
cv2.destroyAllWindows()