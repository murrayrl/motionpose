import cv2
import numpy as np

# Load YOLO
net = cv2.dnn.readNet('yolov3.weights', 'yolov3.cfg')

classes = []
with open("classes.txt", "r") as f:
    classes = f.read().splitlines()

# Start video capture
cap = cv2.VideoCapture(0)
font = cv2.FONT_HERSHEY_PLAIN
colors = np.random.uniform(0, 255, size=(100, 3))

# Initialize VideoWriter
# Note: Adjust 'XVID' and frame size (640, 480) as needed
fourcc = cv2.VideoWriter_fourcc(*'XVID')
ret, frame = cap.read()
if ret:
    height, width, _ = frame.shape
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (width, height))

while True:
    _, img = cap.read()
    height, width, _ = img.shape

    blob = cv2.dnn.blobFromImage(img, 1/255, (416, 416), (0,0,0), swapRB=True, crop=False)
    net.setInput(blob)
    output_layers_names = net.getUnconnectedOutLayersNames()
    layerOutputs = net.forward(output_layers_names)

    boxes = []
    confidences = []
    class_ids = []

    for output in layerOutputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.2:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append((float(confidence)))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.2, 0.4)

    if len(indexes) > 0:
        for i in indexes.flatten():
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            confidence = str(round(confidences[i], 2))
            color = colors[i]
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv2.putText(img, label + " " + confidence, (x, y + 20), font, 2, (255, 255, 255), 2)

    # Write the frame with detections to the video file
    out.write(img)

    cv2.imshow('Image', img)
    key = cv2.waitKey(1)
    if key == 27:  # ESC key to break
        break

# Release everything when job is finished
cap.release()
out.release()
cv2.destroyAllWindows()
