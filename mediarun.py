import cv2
import mediapipe as mp

class MediaPipePoseEstimator:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()

    def process_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False  # Improve performance by marking the image as not writeable
        results = self.pose.process(frame_rgb)

        frame_rgb.flags.writeable = True  # Allow drawing on the frame
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)  # Convert back to BGR

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame_bgr, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            # Output keypoints for each detected person
            for landmark in results.pose_landmarks.landmark:
                print(f'X: {landmark.x}, Y: {landmark.y}, Z: {landmark.z}, Visibility: {landmark.visibility}')

        return frame_bgr

    def release(self):
        self.pose.close()

def mediapipe_run():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video capture.")
        return

    pose_estimator = MediaPipePoseEstimator()

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break

            frame = cv2.resize(frame, (640, 480))  
            processed_frame = pose_estimator.process_frame(frame)

            cv2.imshow('Pose Estimation', processed_frame)
            if cv2.waitKey(5) & 0xFF == 27:  
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        pose_estimator.release()

if __name__ == "__main__":
    mediapipe_run()
