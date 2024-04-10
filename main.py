import asyncio
import cv2
import json
from ultralytics import YOLO
from ultralytics.solutions import distance_calculation
# from ws_server import start_server, connected_clients
import websockets
# import sys
# import os


# sys.stdout = open('output.txt', 'w')


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


async def main_logic():
    try:
        async with websockets.connect("ws://localhost:5678") as websocket:
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

            
            while cap.isOpened():
                success, im0 = cap.read()
                ret, frame = cap.read()
                if not success:
                    print("Video frame is empty or video processing has been successfully completed.")
                    break
                
                data = object_detector(frame) 
                for d in data:
                    print(f"Detected: {d[0]}, Width: {d[1]}, Coordinates: {d[2]}")

                    if d[0] =='person':
                        distance = distance_finder(focal_person, PERSON_WIDTH, d[1])
                        x, y = d[2]
                        print("x: ", x)
                        print("y: ", y)

                        
                        await send_coordinates(websocket, distance, x, y)
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
                

                if cv2.waitKey(1) == ord('q'):
                    break
                # key = cv2.waitKey(1)
                # if key ==ord('q'):
                #     break

            cap.release()
            # video_writer.release()
            cv2.destroyAllWindows()
            await websocket.close()
    except Exception as e:
        print(f"Error: {e}")
    
async def send_coordinates(websocket, distance, x, y):
    data = {"distance": int(distance), "x": int(x), "y": int(y)}  # Convert to standard int
    # message = "Test message"
    # await websocket.send(message)
    message = json.dumps(data)
    await websocket.send(message)

async def main():
    await main_logic()


if __name__ == "__main__":
    asyncio.run(main())
