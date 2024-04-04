from ultralytics import YOLO
from ultralytics.solutions import distance_calculation
import cv2
import numpy as np
import asyncio
import websockets
import json


# This will hold the WebSocket connections
connected = set()

# The WebSocket server endpoint
async def server(websocket, path):
    global connected
    connected.add(websocket)
    try:
        # You could send a welcome message, or just pass if not needed
        # await websocket.send(json.dumps({"message": "Connected"}))
        while True:
            # Just keep the connection open
            await asyncio.sleep(0.1)
    except websockets.exceptions.ConnectionClosed:
        # If the connection closes, remove it from the set
        connected.remove(websocket)

# Start the WebSocket server
start_server = websockets.serve(server, "localhost", 5678)



model = YOLO("yolov8n.pt")
names = model.model.names

# Distance constants 
KNOWN_DISTANCE = 45 #INCHES
PERSON_WIDTH = 16 #INCHES
MOBILE_WIDTH = 3.0 #INCHES

# Object detector constant 
CONFIDENCE_THRESHOLD = 0.4
NMS_THRESHOLD = 0.3

# colors for object detected
COLORS = [(255,0,0),(255,0,255),(0, 255, 255), (255, 255, 0), (0, 255, 0), (255, 0, 0)]
GREEN =(0,255,0)
BLACK =(0,0,0)
# defining fonts 
FONTS = cv2.FONT_HERSHEY_COMPLEX

# getting class names from classes.txt file 
class_names = []
with open("./classes.txt", "r") as f:
    class_names = [cname.strip() for cname in f.readlines()]
#  setttng up opencv net
yoloNet = cv2.dnn.readNet('yolov4-tiny.weights', 'yolov4-tiny.cfg')

yoloNet.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
yoloNet.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)


depth_model = cv2.dnn_DetectionModel(yoloNet)
depth_model.setInputParams(size=(416, 416), scale=1/255, swapRB=True)

# object detector funciton /method
def object_detector(image):
    classes, scores, boxes = depth_model.detect(image, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
    # creating empty list to add objects data
    data_list =[]
    for (classid, score, box) in zip(classes, scores, boxes):
        # print(classid);
        # print(score);
        # print(type(classid), type(score))
        # print(classid, score)
        # define color of each, object based on its class id 
        color= COLORS[int(classid) % len(COLORS)]
    
        label = "%s : %f" % (class_names[classid], score)

        # draw rectangle on and label on object
        cv2.rectangle(image, box, color, 2)
        cv2.putText(image, label, (box[0], box[1]-14), FONTS, 0.5, color, 2)
    
        # getting the data 
        # 1: class name  2: object width in pixels, 3: position where have to draw text(distance)
        if classid ==0: # person class id 
            data_list.append([class_names[classid], box[2], (box[0], box[1]-2)])
        elif classid ==67:
            data_list.append([class_names[classid], box[2], (box[0], box[1]-2)])
        # if you want inclulde more classes then you have to simply add more [elif] statements here
        # returning list containing the object data. 
    return data_list


def focal_length_finder (measured_distance, real_width, width_in_rf):
    focal_length = (width_in_rf * measured_distance) / real_width

    return focal_length

# distance finder function 
def distance_finder(focal_length, real_object_width, width_in_frmae):
    distance = (real_object_width * focal_length) / width_in_frmae
    return distance

# reading the reference image from dir 
ref_person = cv2.imread('ReferenceImages/image14.png')
ref_mobile = cv2.imread('ReferenceImages/image4.png')

mobile_data = object_detector(ref_mobile)
mobile_width_in_rf = mobile_data[1][1]

person_data = object_detector(ref_person)
person_width_in_rf = person_data[0][1]

# print(f"Person width in pixels : {person_width_in_rf} mobile width in pixel: {mobile_width_in_rf}")

# finding focal length 
focal_person = focal_length_finder(KNOWN_DISTANCE, PERSON_WIDTH, person_width_in_rf)

focal_mobile = focal_length_finder(KNOWN_DISTANCE, MOBILE_WIDTH, mobile_width_in_rf)


async def main():
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    assert cap.isOpened(), "Error reading video file"
    w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

    # # Video writer
    # video_writer = cv2.VideoWriter("distance_calculation.avi",
    #                             cv2.VideoWriter_fourcc(*'mp4v'),
    #                             fps,
    #                             (w, h))

    # Init distance-calculation obj
    dist_obj = distance_calculation.DistanceCalculation()
    dist_obj.set_args(names=names, view_img=True)
    await run_server()
    
    while cap.isOpened():
        success, im0 = cap.read()
        ret, frame = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.")
            break
        
        data = object_detector(frame) 
        for d in data:
            if d[0] =='person':
                distance = distance_finder(focal_person, PERSON_WIDTH, d[1])
                x, y = d[2]
                # print("x: ", x)
                # print("y: ", y)
                
                await send_coordinates(x,y)
                # print("test")
            # elif d[0] =='cell phone':
            #     distance = distance_finder (focal_mobile, MOBILE_WIDTH, d[1])
            #     x, y = d[2]
            cv2.rectangle(frame, (x, y-3), (x+150, y+23),BLACK,-1 )
            cv2.putText(frame, f'Dis: {round(distance,2)} inch', (x+5,y+13), FONTS, 0.48, GREEN, 2)


        tracks = model.track(im0, persist=True, show=False)
        im0 = dist_obj.start_process(im0, tracks)
        # video_writer.write(im0)

        cv2.imshow('frame',frame)
        
        key = cv2.waitKey(1)
        if key ==ord('q'):
            break

    cap.release()
    # video_writer.release()
    cv2.destroyAllWindows()


# Function to send the detected coordinates to all connected clients
async def send_coordinates(x, y):
    print("waiting")
    if connected: # Check if there are any connected clients
        message = json.dumps({'x': x, 'y': y})
        print("message: ", message)
        await asyncio.wait([user.send(message) for user in connected])

        # Start the WebSocket server
async def run_server():
    server_coroutine = websockets.serve(server, "localhost", 5678)
    print("Starting WebSocket server on ws://localhost:5678")
    await server_coroutine  # This starts the server


# # Start the main function and the WebSocket server concurrently
# async def run_server_and_main():
#     server_task = asyncio.create_task(run_server())
#     main_task = asyncio.create_task(main())
#     await asyncio.gather(server_task, main_task)

# Start the main function and the WebSocket server concurrently
asyncio.get_event_loop().run_until_complete(asyncio.gather(
    websockets.serve(server, "localhost", 5678),
    main(),
))

if __name__ == "__main__":
    asyncio.run(websockets.serve(server, "localhost", 5678))
    asyncio.get_event_loop().run_forever()