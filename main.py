import cv2 as cv
import numpy as np
from ultralytics import YOLO
from ultralytics.solutions import distance_calculation

# Constants for depth detection
KNOWN_DISTANCE = 45 # inches
PERSON_WIDTH = 16 # inches
MOBILE_WIDTH = 3.0 # inches

# Object detector constants
CONFIDENCE_THRESHOLD = 0.4
NMS_THRESHOLD = 0.3

# Colors and Fonts
COLORS = [(255, 0, 0), (255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0), (255, 0, 0)]
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
FONTS = cv.FONT_HERSHEY_COMPLEX

# Load class names from classes.txt file
class_names = []
with open("./classes.txt", "r") as f:
    class_names = [cname.strip() for cname in f.readlines()]

# Set up OpenCV net for YOLOv4-tiny
yoloNet_v4_tiny = cv.dnn.readNet('yolov4-tiny.weights', 'yolov4-tiny.cfg')
yoloNet_v4_tiny.setPreferableBackend(cv.dnn.DNN_BACKEND_CUDA)
yoloNet_v4_tiny.setPreferableTarget(cv.dnn.DNN_TARGET_CUDA_FP16)
model_v4_tiny = cv.dnn_DetectionModel(yoloNet_v4_tiny)
model_v4_tiny.setInputParams(size=(416, 416), scale=1/255, swapRB=True)

# Set up the model for YOLOv8n from Ultralytics
model_v8n = YOLO("yolov8n.pt")
names_v8n = model_v8n.model.names

# Define object detector function using YOLOv4-tiny
def object_detector_v4_tiny(image):
    classes, scores, boxes = model_v4_tiny.detect(image, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
    data_list = []
    for (classid, score, box) in zip(classes, scores, boxes):
        color = COLORS[int(classid) % len(COLORS)]
        label = "%s : %f" % (class_names[classid], score)
        cv.rectangle(image, box, color, 2)
        cv.putText(image, label, (box[0], box[1] - 10), FONTS, 0.5, color, 2)
        data_list.append([class_names[classid], box[2], (box[0], box[1])])
    return data_list

# Function to find the focal length
def focal_length_finder(measured_distance, real_width, width_in_rf):
    focal_length = (width_in_rf * measured_distance) / real_width
    return focal_length

# Function to find the distance to the object
def distance_finder(focal_length, real_object_width, width_in_frame):
    distance = (real_object_width * focal_length) / width_in_frame
    return distance

# Focal length calculation based on reference images
ref_person = cv.imread('ReferenceImages/image14.png')
ref_mobile = cv.imread('ReferenceImages/image4.png')
# Use the correct object_detector function for reference images
person_data = object_detector_v4_tiny(ref_person)
mobile_data = object_detector_v4_tiny(ref_mobile)
# Extract the width in pixels from object data for focal length calculation
person_width_in_rf = person_data[0][1] if person_data else 0
mobile_width_in_rf = mobile_data[0][1] if mobile_data else 0
focal_length_person = focal_length_finder(KNOWN_DISTANCE, PERSON_WIDTH, person_width_in_rf)
focal_length_mobile = focal_length_finder(KNOWN_DISTANCE, MOBILE_WIDTH, mobile_width_in_rf)

# Initialize video capture
cap = cv.VideoCapture(0)
assert cap.isOpened(), "Error opening video stream or file"

# Initialize video writer
w, h = int(cap.get(cv.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv.CAP_PROP_FPS)
video_writer = cv.VideoWriter("output.avi", cv.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

# Init distance-calculation object
dist_obj = distance_calculation.DistanceCalculation()
dist_obj.set_args(names=names_v8n, view_img=True)

# Main processing loop
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Object detection and depth estimation using YOLOv4-tiny
    data_depth = object_detector_v4_tiny(frame)
    for d in data_depth:
        object_label = d[0]
        object_width_in_frame = d[1]
        x, y = d[2]

        # Estimating distance for different objects
        if object_label == 'person':
            distance = distance_finder(focal_length_person, PERSON_WIDTH, object_width_in_frame)
        elif object_label == 'cell phone':
            distance = distance_finder(focal_length_mobile, MOBILE_WIDTH, object_width_in_frame)

        # Overlay distance information on the frame
        cv.rectangle(frame, (x, y-3), (x+150, y+23), BLACK, -1)
        cv.putText(frame, f'Dis: {round(distance,2)} inch', (x+5, y+13), FONTS, 0.48, GREEN, 2)

    # Object tracking and distance calculation between objects using YOLOv8n
    results = model_v8n(frame)
    # Process results as needed and use dist_obj to calculate distances between objects

    # Display and write the frame
    cv.imshow('Frame', frame)
    video_writer.write(frame)

    # Break the loop on 'q' key
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
video_writer.release()
cap.release()
cv.destroyAllWindows()
