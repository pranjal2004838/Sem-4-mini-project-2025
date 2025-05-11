import cv2
import os 
import numpy as np
import face_recognition
import pickle

# Path to the directory containing known face images
path = 'Images'
images = []
classNames = []
encodeList = []

# Load and process known face images
def load_known_faces():
    pathlist = os.listdir(path)
    
    for img in pathlist:
        # Read image
        img_path = os.path.join(path, img)
        current_img = cv2.imread(img_path)
        images.append(current_img)
        
        # Get person's name from filename (without extension)
        classNames.append(os.path.splitext(img)[0])
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB)
        
        # Find face locations in the image
        face_locations = face_recognition.face_locations(rgb_img)
        
        # Generate face encodings
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        
        if face_encodings:
            encodeList.append(face_encodings[0])
    
    # Save encodings to a file for future use
    with open('encodings.pkl', 'wb') as f:
        pickle.dump(encodeList, f)
    
    return encodeList, classNames

# Load Haar Cascade for face detection
haar_cascade = cv2.CascadeClassifier(r'C:\Users\pranj\Downloads\haarcascade_frontalface_default.xml')

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
encodeListKnown, classNames = load_known_faces()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize frame for processing
    resize_frame = cv2.resize(frame, (640, 480))
    
    # Convert frame to RGB for face recognition
    rgb_frame = cv2.cvtColor(resize_frame, cv2.COLOR_BGR2RGB)
    
    # Find face locations in the current frame
    face_locations = face_recognition.face_locations(rgb_frame)
    
    # Generate face encodings for detected faces
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Process each detected face
    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Compare with known faces
        matches = face_recognition.compare_faces(encodeListKnown, face_encoding)
        face_distances = face_recognition.face_distance(encodeListKnown, face_encoding)
        
        # Get the best match
        match_index = np.argmin(face_distances)
        
        if matches[match_index]:
            name = classNames[match_index]
            # Draw rectangle around face
            y1, x2, y2, x1 = face_location
            cv2.rectangle(resize_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Display name
            cv2.putText(resize_frame, name, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

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