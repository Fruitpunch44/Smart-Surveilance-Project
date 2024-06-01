from flask import Flask, Response, redirect, url_for, jsonify, request, flash, render_template, session
from flask_socketio import SocketIO
from functools import wraps
import datetime
import platform
import os
import cv2
import RPI.GPIO as GPIO
import numpy as np
import yaml
import requests
from ultralytics import YOLO
from picamera.array import PiRGBArray
from picamera import PiCamera
from playsound import playsound
import firebase_admin
from firebase_admin import credentials, db

# Firebase configuration
Firebase_api_key = 'AIzaSyCEL8kSwSyX4eIk6SeCQMtPGwCyzApvM2c'
FIREBASE_SIGN_UP = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={Firebase_api_key}'
FIREBASE_SIGN_in = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={Firebase_api_key}'

# Flask app and SocketIO setup
app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = 'ILIKEEGGS'

# Firebase credentials and initialization
cred = credentials.Certificate("Credentials.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://alarm-notification-94a3c-default-rtdb.firebaseio.com/"})
db_ref = db.reference()

# Audio file path
Audio_File_path = ""

# Authentication and route protection
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_token' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/Video_page')
@login_required
def video_page():
    return render_template('Video.html')

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data')
@login_required
def data():
    try:
        data = db_ref.get()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        payload = {'email': email, 'password': password, 'returnSecureToken': True}
        try:
            response = requests.post(FIREBASE_SIGN_UP, json=payload)
            response_data = response.json()
            if 'idToken' in response_data:
                flash('user registered')
                return redirect(url_for('login'))
            else:
                error_message = response_data.get('error', {}).get('message', 'Unknown error')
                flash(f"Error creating user: {error_message}")
        except Exception as e:
            flash(f"error creating user :{str(e)}")
    return render_template('Register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        payload = {'email': email, 'password': password, 'returnSecureToken': True}
        try:
            response = requests.post(FIREBASE_SIGN_in, json=payload)
            response_data = response.json()
            if 'idToken' in response_data:
                session['id_token'] = response_data['idToken']
                flash('login worked yh')
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error=response_data.get('error', {}).get('message', 'Unknown error'))
        except Exception as e:
            return render_template('login.html', error=str(e))
    return render_template('Login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('you have logged out')
    return redirect(url_for('login'))

def play_audio():
    try:
        playsound(Audio_File_path)
    except Exception as e:
        print(f"Error playing audio: {e}")

with open('config.yaml', 'r') as file:
    class_labels = yaml.safe_load(file)
LABELS = [class_labels['names'][i] for i in range(len(class_labels['names']))]
print(LABELS)
COLORS = np.random.randint(0, 255, size=(len(LABELS), 3), dtype="uint8")

model_path = os.path.join('.', 'runs', 'detect', 'train60', 'weights', 'best.pt')
try:
    model = YOLO(model_path)
    print("MODEL LOADED")
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
rawCapture = PiRGBArray(camera, size=(640, 480))
import time
time.sleep(0.1)

PIR_SENSOR_PIN =17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_SENSOR_PIN,GPIO.IN)

threshold = 0.5

def generate_frames():
if GPIO.input(PIR_SENSOR_PIN):
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        image = frame.array
        h, w, _ = image.shape
        results = model(image)[0]
        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = result
            if score > threshold:
                socketio.emit('object_detected', {'message': f"{results.names[int(class_id)].upper()} detected!"})
                cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
                cv2.putText(image, results.names[int(class_id)].upper(), (int(x1), int(y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)
                play_audio()
                timestamp = datetime.datetime.now().isoformat()
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
                try:
                    db_ref.push(data)
                    print("Data pushed successfully!")
                except Exception as e:
                    print(f"Error pushing data to database: {e}")
        ret, buffer = cv2.imencode('.jpg', image)
        frame_bytes = buffer.tobytes()
        rawCapture.truncate(0)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame_bytes + b'\r\n')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)

camera.close()
