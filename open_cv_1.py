import cv2
import os
import numpy as np
import face_recognition
import pyodbc
from datetime import datetime, time
import csv

# Use exactly what pyodbc.drivers() shows
driver = '{ODBC Driver 18 for SQL Server}'
server = 'rtp.database.windows.net'
database = 'rtp'
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

# Only include students 401 to 464
valid_students = [str(i) for i in range(401, 465)]

# Path to the directory containing known face images
path = r'student_images'
known_encodings = []
known_ids = []

# Load and encode known faces using face_recognition
for img_name in os.listdir(path):
    student_id = os.path.splitext(img_name)[0]
    if student_id not in valid_students:
        continue
    img_path = os.path.join(path, img_name)
    img = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(img)
    if encodings:
        known_encodings.append(encodings[0])
        known_ids.append(student_id)
    else:
        print(f"Warning: No face found in {img_name}")

# === Day-wise subject detection based on time ===
schedule = {
    'Monday': [(time(9,30), time(11,30),'GS LAB'), (time(13,45), time(15,15),'PTSP'), (time(15,15), time(16,45),'LDICA')],
    'Tuesday': [(time(9,30), time(11,0),'ECA'), (time(11,0), time(12,30),'ADC'), (time(13,45), time(15,45),'LDICA LAB')],
    'Wednesday': [(time(9,30), time(11,0),'EMTL'), (time(11,0), time(12,30),'LDICA'), (time(13,45), time(15,45),'LDICA LAB')],
    'Thursday': [(time(9,30), time(11,30),'ECA LAB'), (time(13,45), time(15,45),'ADC LAB')],
    'Friday': [(time(9,30), time(11,0),'ECA'), (time(11,0), time(12,30),'EMTL'), (time(13,45), time(15,15),'PTSP'), (time(15,15), time(16,45),'ADC')],
    'Saturday': [(time(9,30), time(11,0),'EMTL'), (time(11,0), time(12,30),'ADC'), (time(13,45), time(15,15),'PTSP'), (time(15,15), time(16,45),'LDICA')],
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

# Create attendance_logs table if not exists
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'attendance_logs')
    CREATE TABLE attendance_logs (
        id INT IDENTITY PRIMARY KEY,
        student_id NVARCHAR(50),
        subject NVARCHAR(100),
        timestamp DATETIME DEFAULT GETDATE()
    )
""")
conn.commit()

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)
seen_ids = set()

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
        student_id = "Unknown"
        if True in matches:
            student_id = known_ids[matches.index(True)]

            if student_id in valid_students and student_id not in seen_ids:
                seen_ids.add(student_id)
                cursor.execute("INSERT INTO attendance_logs (student_id, subject) VALUES (?, ?)", (student_id, subject))
                conn.commit()

        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
        cv2.putText(frame, student_id, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,255,0), 2)

    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# === Export summary attendance to CSV ===
summary_filename = "attendance_summary.csv"
subjects = ['PTSP', 'EMTL', 'ADC', 'LDICA', 'ECA', 'ECA LAB', 'LDICA LAB', 'ADC LAB', 'GS LAB']

# Prepare student data structure
summary_data = []
for idx, student_id in enumerate(valid_students, start=1):
    row = {'S.NO': idx, 'Student ID': student_id}
    for sub in subjects:
        cursor.execute("SELECT COUNT(*) FROM attendance_logs WHERE student_id = ? AND subject = ?", (student_id, sub))
        row[sub] = cursor.fetchone()[0]
    row['TOTAL'] = sum(row[sub] for sub in subjects)
    summary_data.append(row)

# Write summary CSV
with open(summary_filename, 'w', newline='') as csvfile:
    fieldnames = ['S.NO', 'Student ID'] + subjects + ['TOTAL']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in summary_data:
        writer.writerow(row)

print(f"✅ Summary exported to {summary_filename}")
