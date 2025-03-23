import cv2
import os 
import numpy as np
import pickle

# Face encodings

path = 'Images'

images = []
pathlist = os.listdir(path)

for img in pathlist:
    img_path = os.path.join(path, img)
    images.append(cv2.imread(img_path))
    print(os.path.splitext(img)[0])

# Face encodings ends

haar_cascade = cv2.CascadeClassifier(r'C:\Users\pranj\Downloads\haarcascade_frontalface_default.xml') 

img_background = cv2.imread(r'Resources\background.png')

active = cv2.imread(r'Resources\Modes\1.png')
mode2 = cv2.imread(r'Resources\Modes\2.png')
active = cv2.imread(r'Resources\Modes\3.png')    
Already_marked = cv2.imread(r'Resources\Modes\4.png')

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    resize_frame = cv2.resize(frame, (640, 480))

    # Convert the frame to grayscale
    frame_gray = cv2.cvtColor(resize_frame, cv2.COLOR_BGR2GRAY)

    # Detect faces in the frame using Haar Cascade
    faces = haar_cascade.detectMultiScale(frame_gray, scaleFactor=1.1, minNeighbors=5)

    # Draw rectangles around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(resize_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    img_background[162:162+480, 55:55+640] = resize_frame

    # Overlay the active image on the background
    img_background[44:44+active.shape[0], 808:808+active.shape[1]] = active

    # Display the frame with detected faces
    cv2.imshow('Video', img_background)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()