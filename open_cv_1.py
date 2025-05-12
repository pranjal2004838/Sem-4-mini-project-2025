import cv2
import os
import numpy as np
import pickle
import requests
from datetime import datetime, timedelta
import json

# Azure Face API configuration
endpoint = "https://rtp.cognitiveservices.azure.com/"
subscription_key = "3sBK0dd8hOkxfJv22qSlF84xPRrab0xQKpNWpqPJCWgyhwjiwKGhJQQJ99BEACGhslBXJ3w3AAAKACOGxOOZ"
detect_url = f"{endpoint}/face/v1.0/detect"
attendance = {}
last_seen = {}
lockout_period = timedelta(minutes=5)

# Path to the directory containing known face images
path = 'Images'
images = []
classNames = []
face_ids = {}

# Load and process known face images
def load_known_faces():
    pathlist = os.listdir(path)
    
    for img in pathlist:
        # Read image
        img_path = os.path.join(path, img)
        current_img = cv2.imread(img_path)
        images.append(current_img)
        
        # Get person's name from filename (without extension)
        name = os.path.splitext(img)[0]
        classNames.append(name)
        
        # Convert image to binary for API upload
        _, img_encoded = cv2.imencode('.jpg', current_img)
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-Type': 'application/octet-stream'
        }
        params = {
            'returnFaceId': 'true',
            'recognitionModel': 'recognition_04',
            'returnFaceLandmarks': 'false'
        }
        response = requests.post(detect_url, headers=headers, params=params, data=img_encoded.tobytes())
        if response.status_code == 200:
            faces = response.json()
            if faces:
                face_ids[name] = faces[0]['faceId']
        else:
            print(f"Error processing {name}: {response.status_code}, {response.text}")
    
    return face_ids, classNames

# Load background and mode images
img_background = cv2.imread(r'Resources\background.png')
active = cv2.imread(r'Resources\Modes\1.png')
mode2 = cv2.imread(r'Resources\Modes\2.png')
active = cv2.imread(r'Resources\Modes\3.png')    
Already_marked = cv2.imread(r'Resources\Modes\4.png')

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# Load known faces
face_ids, classNames = load_known_faces()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize frame for processing
    resize_frame = cv2.resize(frame, (640, 480))
    
    # Convert frame to binary for API upload
    _, img_encoded = cv2.imencode('.jpg', resize_frame)
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
    }
    params = {
        'returnFaceId': 'true',
        'recognitionModel': 'recognition_04',
        'returnFaceLandmarks': 'false'
    }
    response = requests.post(detect_url, headers=headers, params=params, data=img_encoded.tobytes())
    if response.status_code == 200:
        faces = response.json()
        for face in faces:
            face_id = face['faceId']
            face_rectangle = face['faceRectangle']
            
            # Compare detected face with known faces
            verify_url = f"{endpoint}/face/v1.0/verify"
            for name, known_face_id in face_ids.items():
                verify_data = {
                    'faceId1': face_id,
                    'faceId2': known_face_id
                }
                verify_response = requests.post(verify_url, headers={
                    'Ocp-Apim-Subscription-Key': subscription_key,
                    'Content-Type': 'application/json'
                }, data=json.dumps(verify_data))
                
                if verify_response.status_code == 200:
                    verify_result = verify_response.json()
                    if verify_result['isIdentical']:
                        # Draw rectangle around face
                        x, y, w, h = face_rectangle['left'], face_rectangle['top'], face_rectangle['width'], face_rectangle['height']
                        cv2.rectangle(resize_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        # Display name
                        cv2.putText(resize_frame, name, (x, y-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        break

    # Update background with processed frame
    img_background[162:162+480, 55:55+640] = resize_frame
    img_background[44:44+active.shape[0], 808:808+active.shape[1]] = active

    # Display the frame
    cv2.imshow('Video', img_background)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
