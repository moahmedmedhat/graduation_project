from picamera2 import Picamera2
import cv2
import numpy as np
import time
import os

train_path="working_dataset"
image_classes=os.listdir(train_path)
sort_classes=np.sort(image_classes)
print(sort_classes)

def recognize_faces_rpi():
    # Load the trained LBPH model
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("lbph_model (2).xml")

    # Load Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Initialize PiCamera2
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'XRGB8888',"size": (800, 600)})
    picam2.configure(config)
    picam2.start()

    print("? Raspberry Pi Face Recognition started. Press Ctrl+C to stop.")

    last_label = None
    last_time = time.time()
    prediction_interval = 2
    face_box = None

    try:
        while True:
            frame = picam2.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
            current_time = time.time()

            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                face_box = (x, y, w, h)

                if current_time - last_time > prediction_interval:
                    face = gray[y:y+h, x:x+w]
                    face_resized = cv2.resize(face, (200, 200))
                    label, confidence = recognizer.predict(face_resized)

                    if confidence < 100 :
                        last_label = f"ID: {label} ({confidence:.0f})"
                        print(f"ID: {label} ({confidence:.0f})")
                    else:
                        last_label = "Unknown"
                        print(f" {label} ({confidence:.0f})")
                    last_time = current_time

            if face_box:
                (x, y, w, h) = face_box
                color = (0, 255, 0) if "ID" in (last_label or "") else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                if last_label:
                    cv2.putText(frame, last_label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            cv2.imshow("Raspberry Pi Recognition", frame)
            if cv2.waitKey(1) == ord('q'):
                break

    except KeyboardInterrupt:
        print("? Stopped by user.")
    finally:
        picam2.stop()
        cv2.destroyAllWindows()

recognize_faces_rpi()
