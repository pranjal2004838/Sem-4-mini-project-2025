import streamlit as st
import cv2
import os
import numpy as np
import face_recognition
import pyodbc
from datetime import datetime, time, timedelta
import csv
from fpdf import FPDF
import pandas as pd

# === Admin Credentials ===
admin_username = "teacher"
admin_password = "Jnadmin123"

# === Streamlit Config ===
st.set_page_config(page_title="Face Recognition Attendance", layout="centered", page_icon="📸")

# === Login Flow Control ===
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state.logged_in:
    st.markdown("""
        <style>
        .main {
            background-color: #f0f2f6;
        }
        .stForm>form {
            background: #ffffff;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    # 🛡️ Teacher Login
    Please login below to access the admin dashboard.
    """)

    with st.form("login_form"):
        username_input = st.text_input("👤 Username")
        password_input = st.text_input("🔒 Password", type="password")
        login_btn = st.form_submit_button("🔓 Login")

    if login_btn:
        if username_input == admin_username and password_input == admin_password:
            st.session_state["logged_in"] = True
            st.success("✅ Login successful")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# === Main App Interface ===
if st.session_state.logged_in:
    st.markdown("""
    <h2 style='text-align: center;'>📸 Face Recognition Attendance System</h2>
    <hr style='margin-bottom: 30px;'>
    """, unsafe_allow_html=True)

    if st.button("🔒 Logout"):
        st.session_state.logged_in = False
        st.rerun()

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
        cursor = conn.cursor()
        st.success("✅ Connected to Database")
    except Exception as e:
        st.error(f"❌ Failed to connect to Database: {e}")
        st.stop()

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'students')
    CREATE TABLE students (
        student_id NVARCHAR(20) PRIMARY KEY,
        name NVARCHAR(100)
    )
""")
    conn.commit()

    # === Student Management ===
    st.subheader("👨‍🎓 Add / Remove / Modify Students")
    with st.form("student_form"):
        student_id = st.text_input("Student ID (e.g. 401)")
        action = st.selectbox("Action", ["Add", "Remove", "Modify"])
        name = st.text_input("Full Name (only for Add/Modify)")
        photo = st.file_uploader("Upload Student Image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Submit")
        if submitted:
            image_folder = 'student_images'
            os.makedirs(image_folder, exist_ok=True)
            image_path = os.path.join(image_folder, f"{student_id}.jpg")

            if action == "Add":
                if os.path.exists(image_path):
                    st.error("❌ Student already present. Kindly modify or delete.")
                else:
                    cursor.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
                    conn.commit()
                    if photo is not None:
                        with open(image_path, "wb") as f:
                            f.write(photo.read())
                        st.success("✅ Student and image added successfully.")
                    else:
                        st.warning("Student added, but no image uploaded.")
            elif action == "Remove":
                cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
                conn.commit()
                # Remove image if exists
                if os.path.exists(image_path):
                    os.remove(image_path)
                st.success("🗑️ Student and image removed successfully.")
            elif action == "Modify":
                cursor.execute("UPDATE students SET name = ? WHERE student_id = ?", (name, student_id))
                conn.commit()
                # Update image if new photo uploaded
                if photo is not None:
                    with open(image_path, "wb") as f:
                        f.write(photo.read())
                    st.success("✏️ Student and image updated successfully.")
                else:
                    st.success("✏️ Student info updated (no image change).")

    # === Face Recognition Attendance ===
    st.subheader("📷 Start Webcam Attendance")
    if st.button("Start Attendance Session"):
        subject = None
        now = datetime.now()
        today = now.strftime('%A')
        current_time = now.time()

        schedule = {
            'Monday': [(time(9,30), time(11,30),'GS LAB'), (time(13,45), time(15,15),'PTSP'), (time(15,15), time(16,45),'LDICA')],
            'Tuesday': [(time(9,30), time(11,0),'ECA'), (time(11,0), time(12,30),'ADC')],
            'Wednesday': [(time(9,30), time(11,0),'EMTL'), (time(11,0), time(12,30),'LDICA'), (time(13,45), time(15,45),'LDICA LAB')],
            'Thursday': [(time(9,30), time(11,30),'ECA LAB'), (time(13,45), time(15,45),'ADC LAB')],
<<<<<<< HEAD
            'Sunday': [(time(9,30), time(11,00),'ECA'), (time(11,00), time(12,30),'EMTL'), (time(13,45), time(15,15),'PTSP'), (time(17,15), time(18,45),'ADC')]
=======
            'Friday': [(time(9,30), time(11,00),'ECA'), (time(11,00), time(12,30),'EMTL'), (time(13,45), time(15,15),'PTSP'), (time(15,15), time(16,45),'ADC')]
>>>>>>> aea2343c5e305e7cfa1c2b7970788d202f1c1f00
        }

        for start, end, subj in schedule.get(today, []):
            # Allow attendance only within 15 minutes from class start
            attendance_window_end = (datetime.combine(datetime.today(), start) + 
                         timedelta(minutes=30)).time()
            if start <= current_time <= attendance_window_end:
                subject = subj
                break
        else:
            st.warning("Attendance window closed.")
            st.stop()

        if subject is None:
            st.warning("No class at this time.")
            st.stop()

        image_folder = 'student_images'
        known_encodings = []
        known_ids = []
        for img_name in os.listdir(image_folder):
            student_id = os.path.splitext(img_name)[0]
            img_path = os.path.join(image_folder, img_name)
            img = face_recognition.load_image_file(img_path)
            enc = face_recognition.face_encodings(img)
            if enc:
                known_encodings.append(enc[0])
                known_ids.append(student_id)

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        seen = set()
        stframe = st.empty()
        if "stop_camera" not in st.session_state:
            st.session_state["stop_camera"] = False
        if st.button("⏹️ Stop Camera", key="stop_camera_btn"):
            st.session_state["stop_camera"] = True

        while not st.session_state["stop_camera"]:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, faces)
            for (top, right, bottom, left), enc in zip(faces, encodings):
                matches = face_recognition.compare_faces(known_encodings, enc)
                student_id = "Unknown"
                if True in matches:
                    student_id = known_ids[matches.index(True)]
                    if student_id not in seen:
                        cursor.execute("""
                            SELECT COUNT(*) FROM attendance_logs
                            WHERE student_id=? AND subject=? AND CAST(timestamp AS DATE)=CAST(GETDATE() AS DATE)
                        """, (student_id, subject))
                        already = cursor.fetchone()[0]
                        if not already:
                            cursor.execute("INSERT INTO attendance_logs (student_id, subject) VALUES (?, ?)", (student_id, subject))
                            conn.commit()
                            seen.add(student_id)
                cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
                cv2.putText(frame, student_id, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,255,0), 2)
            stframe.image(frame, channels="BGR")
            
        cap.release()
        cv2.destroyAllWindows()
        ...
        st.success("✅ Attendance marked successfully.")

    # === Full CSV and PDF Summary Export ===
    st.subheader("📄 Download Attendance Summary")
    if st.button("📤 Generate CSV & PDF Report", key="generate_report"):
        subjects = ['PTSP', 'EMTL', 'ADC', 'LDICA', 'ECA', 'ECA LAB', 'LDICA LAB', 'ADC LAB', 'GS LAB']
        students = [str(i) for i in range(401, 465)]
        summary_data = []
        subject_totals = {}

        # Calculate total number of classes conducted for each subject
        for subj in subjects:
            cursor.execute("SELECT COUNT(DISTINCT CAST(timestamp AS DATE)) FROM attendance_logs WHERE subject = ?", (subj,))
            subject_totals[subj] = cursor.fetchone()[0]

        total_classes = sum(subject_totals.values())

        for idx, student_id in enumerate(students, start=1):
            row = {'S.NO': idx, 'Student ID': student_id}
            attended_total = 0
            for subj in subjects:
                cursor.execute("SELECT COUNT(DISTINCT CAST(timestamp AS DATE)) FROM attendance_logs WHERE student_id = ? AND subject = ?", (student_id, subj))
                attended = cursor.fetchone()[0]
                row[subj] = attended
                attended_total += attended
            row['TOTAL'] = attended_total
            row['PERCENTAGE'] = round((attended_total / total_classes) * 100, 2) if total_classes else 0
            summary_data.append(row)

        # Add last row for class totals
        total_row = {'S.NO': '', 'Student ID': 'CLASSES HELD'}
        total_sum = 0
        for subj in subjects:
            total_row[subj] = subject_totals[subj]
            total_sum += subject_totals[subj]
        total_row['TOTAL'] = total_sum
        total_row['PERCENTAGE'] = ''

        csv_file = 'attendance_summary.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['S.NO', 'Student ID'] + subjects + ['TOTAL', 'PERCENTAGE'])
            writer.writeheader()
            for row in summary_data:
                writer.writerow(row)
            writer.writerow(total_row)

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=8)
        pdf.cell(200, 10, txt="Semester Attendance Report", ln=True, align='C')
        with open(csv_file, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                line = " | ".join(row)
                pdf.cell(0, 6, txt=line, ln=True)
        pdf_file = 'attendance_summary.pdf'
        pdf.output(pdf_file)

        st.success("✅ Attendance report generated!")
        with open(csv_file, "rb") as f:
            st.download_button("⬇️ Download CSV", key="download_csv", data=f, file_name=csv_file, mime="text/csv")
        with open(pdf_file, "rb") as f:
            st.download_button("⬇️ Download PDF", key="download_pdf", data=f, file_name=pdf_file, mime="application/pdf")