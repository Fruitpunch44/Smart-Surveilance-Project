"""This does not work without internet by the way
program shows error at line 19"""

import datetime
import cv2
from ultralytics import YOLO
import os
import pygame
import subprocess
import platform
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from firebase_admin import db


"""Will add functionality to capture for 30 seconds and process it and store the house"""

# authenticate to firebase
cred = credentials.Certificate("Credentials.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://alarm-notification-94a3c-default-rtdb.firebaseio.com/"})

# Initialize data reference
db_ref = db.reference()

# pygame initialization alongside the audio play
pygame.init()
Audio_File_path = r"C:\Users\Olu-Ade\PycharmProjects\Yolo object detection\data\machine-gun-01.wav"
object_detected = False


# creates a function to play audio in the loop
def play_audio():
    global object_detected
    pygame.mixer.set_num_channels(1)
    # trigger conditions for the play audio function
    if not object_detected:
        pygame.mixer.Sound(Audio_File_path)
        try:
            notification_sound = pygame.mixer.Sound(Audio_File_path)
            notification_sound.play()
            # ERROR HANDLING IF THE AUDIO FILE CAN'T BE FOUND OR CORRUPTED
        except Exception as e:
            print(f"Error playing audio: {e}")


# create video directory
Vid_Directory = os.path.join('', 'videos')
if not os.path.exists(Vid_Directory):
    os.makedirs(Vid_Directory)

# select the video within the specified file path
video_path = os.path.join(Vid_Directory, 'test5.mp4')
video_path_out = '{}_out.mp4'.format(video_path)

# use the given video in the directory
cap = cv2.VideoCapture(video_path)

# read from the video
ret, frame = cap.read()

# set the height and width
H, W, _ = frame.shape

# set the video output to be in mpv4 format
out = cv2.VideoWriter(video_path_out, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), int(cap.get(cv2.CAP_PROP_FPS)),
                      (W, H))
# path to the trained model weight in the file directory
model_path = os.path.join('.', 'runs', 'detect', 'train62', 'weights', 'best.pt')
# Load a model
model = YOLO(model_path)  # load a custom model

threshold = 0.5

while ret:

    results = model(frame)[0]
    # setting the bounding box
    for result in results.boxes.data.tolist():

        # attach the box alongside the accuracy and the id in this case phone
        x1, y1, x2, y2, score, class_id = result

        # Adjust coordinates for relative position
        x_min = int(max(0, x1))  # Ensure x1 doesn't go negative
        y_min = int(max(0, y1))  # Ensure y1 doesn't go negative
        x_max = int(min(W, x2))  # Ensure x2 doesn't exceed frame width
        y_max = int(min(H, y2))  # Ensure y2 doesn't exceed frame height

        # drawing of the bounding boxes and the class assignment
        if score > threshold:
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
            cv2.putText(frame, results.names[int(class_id)].upper(), (int(x1), int(y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)

            # play audio from the play_audio function
            play_audio()
            # get current time stamp
            timestamp = datetime.datetime.now().isoformat()

            # creates the node structure that will be stored in the database
            # format{key:value} it is possible to nest keys
            device_info = {
                "OS": platform.system(),
                "Version": platform.version(),
                "processor": platform.processor(),
                "Machine architecture": platform.machine()
            }
            data = {
                "object": results.names[int(class_id)].upper(),
                "timestamp": timestamp,
                "Location": "Nigeria",
                "Device": device_info
            }

            # write data to firebase Database
            db_ref.push(data)

    out.write(frame)
    ret, frame = cap.read()

# free up the memory being used by cv2 and pygame
cap.release()
out.release()
pygame.quit()
cv2.destroyAllWindows()
