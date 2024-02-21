import cv2
import numpy as np

# Load the pre-trained MobileNet SSD model
net = cv2.dnn.readNetFromCaffe('MobileNetSSD_deploy.prototxt', 'MobileNetSSD_deploy.caffemodel')

# Set up webcams for stereo vision
left_cam = cv2.VideoCapture(0)
right_cam = cv2.VideoCapture(1)

# StereoBM settings
stereo = cv2.StereoBM_create(numDisparities=64, blockSize=15)

# Calibration parameters
focal_length = 700  # Example value, replace with your calibrated value
baseline = 0.1  # Example value, replace with your actual baseline in meters

while True:
    # Capture frames from both cameras
    ret1, left_frame = left_cam.read()
    ret2, right_frame = right_cam.read()

    if not ret1 or not ret2:
        print("Error: Could not read frames from cameras.")
        break

    # Convert frames to grayscale for disparity computation
    left_gray = cv2.cvtColor(left_frame, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right_frame, cv2.COLOR_BGR2GRAY)

    # Compute the disparity map
    disparity = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0

    # Object detection on the left frame
    blob = cv2.dnn.blobFromImage(left_frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:  # Confidence threshold
            # Get the bounding box coordinates
            box = detections[0, 0, i, 3:7] * np.array([left_frame.shape[1], left_frame.shape[0], left_frame.shape[1], left_frame.shape[0]])
            (startX, startY, endX, endY) = box.astype("int")

            # Draw the bounding box and label on the frame
            label = "Person: {:.2f}%".format(confidence * 100)
            cv2.rectangle(left_frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.putText(left_frame, label, (startX, startY - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Estimate the depth of the detected person
            person_disparity = np.mean(disparity[startY:endY, startX:endX])
            depth = (focal_length * baseline) / (person_disparity + 0.0001)  # Add a small value to avoid division by zero
            cv2.putText(left_frame, f"Depth: {depth:.2f}m", (startX, endY + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display the left frame
    cv2.imshow('Left Frame', left_frame)

    # Press 'q' to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
left_cam.release()
right_cam.release()
cv2.destroyAllWindows()
