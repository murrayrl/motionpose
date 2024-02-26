from ultralytics import YOLO
from ultralytics.solutions import distance_calculation
import cv2

model = YOLO("yolov8n.pt")
names = model.model.names

cap = cv2.VideoCapture("two-hip-hop-dancers-in-neon-light-dance-together-in-blue-and-purple-colors-SBV-346835903-preview.mp4")

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

    cv2.imshow('YOLOv8 Distance Calculation', im0)
    if cv2.waitKey(1) == ord('q'):  # Press 'q' to quit
        break

cap.release()
video_writer.release()
cv2.destroyAllWindows()



class DistanceCalculation:
    """A class to calculate distance between two objects in real-time video stream based on their tracks."""

    def __init__(self):
        """Initializes the distance calculation class with default values for Visual, Image, track and distance
        parameters.
        """

        # Visual & im0 information
        self.im0 = None
        self.annotator = None
        self.view_img = False
        self.line_color = (255, 255, 0)
        self.centroid_color = (255, 0, 255)

        # Predict/track information
        self.clss = None
        self.names = None
        self.boxes = None
        self.line_thickness = 2
        self.trk_ids = None

        # Distance calculation information
        self.centroids = []
        self.pixel_per_meter = 10

        # Mouse event
        self.left_mouse_count = 0
        self.selected_boxes = {}

        # Check if environment support imshow
        self.env_check = check_imshow(warn=True)

    def set_args(
        self,
        names,
        pixels_per_meter=10,
        view_img=False,
        line_thickness=2,
        line_color=(255, 255, 0),
        centroid_color=(255, 0, 255),
    ):
        """
        Configures the distance calculation and display parameters.

        Args:
            names (dict): object detection classes names
            pixels_per_meter (int): Number of pixels in meter
            view_img (bool): Flag indicating frame display
            line_thickness (int): Line thickness for bounding boxes.
            line_color (RGB): color of centroids line
            centroid_color (RGB): colors of bbox centroids
        """
        self.names = names
        self.pixel_per_meter = pixels_per_meter
        self.view_img = view_img
        self.line_thickness = line_thickness
        self.line_color = line_color
        self.centroid_color = centroid_color

    def mouse_event_for_distance(self, event, x, y, flags, param):
        """
        This function is designed to move region with mouse events in a real-time video stream.

        Args:
            event (int): The type of mouse event (e.g., cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONDOWN, etc.).
            x (int): The x-coordinate of the mouse pointer.
            y (int): The y-coordinate of the mouse pointer.
            flags (int): Any flags associated with the event (e.g., cv2.EVENT_FLAG_CTRLKEY,
                cv2.EVENT_FLAG_SHIFTKEY, etc.).
            param (dict): Additional parameters you may want to pass to the function.
        """
        global selected_boxes
        global left_mouse_count
        if event == cv2.EVENT_LBUTTONDOWN:
            self.left_mouse_count += 1
            if self.left_mouse_count <= 2:
                for box, track_id in zip(self.boxes, self.trk_ids):
                    if box[0] < x < box[2] and box[1] < y < box[3] and track_id not in self.selected_boxes:
                        self.selected_boxes[track_id] = []
                        self.selected_boxes[track_id] = box

        if event == cv2.EVENT_RBUTTONDOWN:
            self.selected_boxes = {}
            self.left_mouse_count = 0

    def extract_tracks(self, tracks):
        """
        Extracts results from the provided data.

        Args:
            tracks (list): List of tracks obtained from the object tracking process.
        """
        self.boxes = tracks[0].boxes.xyxy.cpu()
        self.clss = tracks[0].boxes.cls.cpu().tolist()
        self.trk_ids = tracks[0].boxes.id.int().cpu().tolist()

    def calculate_centroid(self, box):
        """
        Calculate the centroid of bounding box.

        Args:
            box (list): Bounding box data
        """
        return int((box[0] + box[2]) // 2), int((box[1] + box[3]) // 2)

    def calculate_distance(self, centroid1, centroid2):
        """
        Calculate distance between two centroids.

        Args:
            centroid1 (point): First bounding box data
            centroid2 (point): Second bounding box data
        """
        pixel_distance = math.sqrt((centroid1[0] - centroid2[0]) ** 2 + (centroid1[1] - centroid2[1]) ** 2)
        return pixel_distance / self.pixel_per_meter, (pixel_distance / self.pixel_per_meter) * 1000

    def start_process(self, im0, tracks):
        """
        Calculate distance between two bounding boxes based on tracking data.

        Args:
            im0 (nd array): Image
            tracks (list): List of tracks obtained from the object tracking process.
        """
        self.im0 = im0
        if tracks[0].boxes.id is None:
            if self.view_img:
                self.display_frames()
            return
        self.extract_tracks(tracks)

        self.annotator = Annotator(self.im0, line_width=2)

        for box, cls, track_id in zip(self.boxes, self.clss, self.trk_ids):
            self.annotator.box_label(box, color=colors(int(cls), True), label=self.names[int(cls)])

            if len(self.selected_boxes) == 2:
                for trk_id, _ in self.selected_boxes.items():
                    if trk_id == track_id:
                        self.selected_boxes[track_id] = box

        if len(self.selected_boxes) == 2:
            for trk_id, box in self.selected_boxes.items():
                centroid = self.calculate_centroid(self.selected_boxes[trk_id])
                self.centroids.append(centroid)

            distance_m, distance_mm = self.calculate_distance(self.centroids[0], self.centroids[1])
            self.annotator.plot_distance_and_line(
                distance_m, distance_mm, self.centroids, self.line_color, self.centroid_color
            )   

        self.centroids = []

        if self.view_img and self.env_check:
            self.display_frames()

        return im0

    def display_frames(self):
        """Display frame."""
        cv2.namedWindow("Ultralytics Distance Estimation")
        cv2.setMouseCallback("Ultralytics Distance Estimation", self.mouse_event_for_distance)
        cv2.imshow("Ultralytics Distance Estimation", self.im0)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            return