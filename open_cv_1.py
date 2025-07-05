import cv2
import os
import numpy as np
import face_recognition
import pyodbc
from datetime import datetime, time
import csv
import flask

# Use exactly what pyodbc.drivers() shows
driver = '{ODBC Driver 18 for SQL Server}'
server = 'rtp-2-2.database.windows.net'
database = 'sem-2-rtp-project'
username = 'user22'
password = 'Azuresql22*'

conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=300;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Connected to Azure SQL!")
    cursor = conn.cursor()
except Exception as e:
    print("❌ Connection failed:", e)

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

# === Day-wise subject detection based on time ===
schedule = {
    'Monday': [(time(9,30), time(11,30),'GS LAB'),
                (time(13,45), time(15,15),'PTSP'),
                (time(15,15), time(16,45),'LDICA')],
    'Tuesday': [(time(9,30), time(11,00),'ECA'),
                (time(11,00), time(12,30),'ADC'),  
                (time(13,45), time(15,45),'LDICA Lab')],
    'Wednesday': [(time(9,30), time(11,00),'EMTL'),
                  (time(11,00), time(12,30),'LDICA'),
                  (time(13,45), time(15,45),'LDICA Lab')],
    'Thursday': [(time(9,30), time(11,30),'ECA LAB'),
                 (time(13,45), time(15,45),'ADC LAB'),
            ],
    'Friday': [(time(9,30), time(11,00),'ECA'),
               (time(11,00), time(12,30),'EMTL'),
               (time(13,45), time(15,15),'PTSP'),
               (time(15,15), time(16,45),'ADC')
               ],
    'Saturday': [(time(9,30), time(11,00),'EMTL'),
                 (time(11,00), time(12,30),'ADC'),
                 (time(13,45), time(15,15),'PTSP'),
                 (time(15,15), time(16,45),'LDICA')],
}
now = datetime.now()
today = now.strftime('%A')
current_time = now.time()
subject = None

for start, end, subj in schedule.get(today, []):
    if start <= current_time <= end:
        subject = subj
        break
print(f"Today: {today}, Current time: {current_time}")

if subject is None:
    print("No class at this time.")
    exit()


# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

seen_names = set()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame from camera.")
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    for (top, right, bottom, left), face_encoding in zip(face_locations, encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            name = known_names[matches.index(True)]

            if name not in seen_names:
                seen_names.add(name)
                cursor = conn.cursor()
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'attendance_logs')
                    CREATE TABLE attendance_logs (
                        id INT IDENTITY PRIMARY KEY,
                        student_name NVARCHAR(100),
                        subject NVARCHAR(100),
                        timestamp DATETIME DEFAULT GETDATE()
                    )
                """)
                cursor.execute("INSERT INTO attendance_logs (student_name, subject) VALUES (?, ?)", (name, subject))
                conn.commit()

        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
        cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,255,0), 2)

    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# === Export attendance logs to CSV ===
export_file = f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
cursor.execute("SELECT student_name, subject, timestamp FROM attendance_logs")
rows = cursor.fetchall()

with open(export_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Student Name', 'Subject', 'Timestamp'])
    for row in rows:
        writer.writerow(row)

print(f"✅ Attendance exported to {export_file}")
