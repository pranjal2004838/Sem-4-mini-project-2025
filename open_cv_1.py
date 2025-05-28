import cv2
import os
import numpy as np
import requests
import face_recognition
import pyodbc

import pyodbc

# Use exactly what pyodbc.drivers() shows
driver = '{ODBC Driver 18 for SQL Server}'
server = 'pranjal-sem2-rtp-project.database.windows.net'
database = 'pranjal_project_sem2'
username = 'pranjal'  # ← From your Azure SQL server info
password = 'Mysql875#'  # ← Enter your real password here

conn_str = f"""
    DRIVER={driver};
    SERVER={server};
    DATABASE={database};
    UID={username};
    PWD={password};
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
"""

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Connected to Azure SQL!")
except Exception as e:
    print("❌ Connection failed:", e)






# Azure Face API configuration
endpoint = "https://rtp.cognitiveservices.azure.com/"
subscription_key = "3sBK0dd8hOkxfJv22qSlF84xPRrab0xQKpNWpqPJCWgyhwjiwKGhJQQJ99BEACGhslBXJ3w3AAAKACOGxOOZ"
detect_url = f"{endpoint}/face/v1.0/detect"

# Path to the directory containing known face images
path = r'student_images'
known_encodings = []
known_names = []

# Load and encode known faces using face_recognition
for img_name in os.listdir(path):
    img_path = os.path.join(path, img_name)
    img = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(img)
    if encodings:
        known_encodings.append(encodings[0])
        known_names.append(os.path.splitext(img_name)[0])
    else:
        print(f"Warning: No face found in {img_name}")

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame from camera.")
        break

    # Use Azure Face API to detect faces
    _, img_encoded = cv2.imencode('.jpg', frame)
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
    }
    params = {
        'returnFaceId': 'false',
        'recognitionModel': 'recognition_04',
        'returnFaceLandmarks': 'false'
    }
    response = requests.post(detect_url, headers=headers, params=params, data=img_encoded.tobytes())
    face_locations = []
    if response.status_code == 200:
        faces = response.json()
        for face in faces:
            rect = face['faceRectangle']
            # Azure gives left, top, width, height
            top = rect['top']
            right = rect['left'] + rect['width']
            bottom = rect['top'] + rect['height']
            left = rect['left']
            face_locations.append((top, right, bottom, left))
    else:
        print(f"Azure error: {response.status_code}, {response.text}")

    # Use dlib/face_recognition for encoding and identification
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    for (top, right, bottom, left), face_encoding in zip(face_locations, encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            name = known_names[matches.index(True)]
        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
        cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,255,0), 2)

    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()