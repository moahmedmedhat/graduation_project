import os
import threading
import time
import cv2
from picamera2 import Picamera2
import numpy as np
from config.settings import train_path , model_path
import queue
import atexit


image_classes=os.listdir(train_path)
sort_classes=np.sort(image_classes)
print(sort_classes)
import queue







class FaceRecognizer:
    def __init__(self):
        self.queue = queue.Queue(maxsize=2)
        self.event = threading.Event()
        self.camera = None
        self.lock = threading.Lock()
        self.thread = None
        self.recognizer = None
        self.face_cascade = None
        self.last_label = None
        self.last_time = time.time()
        self.prediction_interval = 2
        self.face_box = None
        atexit.register(self._cleanup)

    def _initialize_models(self):
        """Initialize face recognition models"""
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(model_path)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def _cleanup(self):
        """Clean up resources"""
        with self.lock:
            if self.camera:
                self.camera.stop()
                self.camera.close()
                self.camera = None
            cv2.destroyAllWindows()

    def _process_frame(self, frame):
        """Process a single frame for face detection and recognition"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(100, 100)
        )
        
        current_time = time.time()

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            self.face_box = (x, y, w, h)

            if current_time - self.last_time > self.prediction_interval:
                face = gray[y:y+h, x:x+w]
                face_resized = cv2.resize(face, (200, 200))
                label, confidence = self.recognizer.predict(face_resized)

                if confidence < 70 :
                    self.last_label = f"ID: {label} ({confidence:.0f})"
                    print(f"ID: {label} ({confidence:.0f})")
                else:
                    self.last_label = "Unknown"
                    print(f" {label} ({confidence:.0f})")
                self.last_time = current_time

        if self.face_box:
            (x, y, w, h) = self.face_box
            color = (0, 255, 0) if "ID" in (self.last_label or "") else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            if self.last_label:
                cv2.putText(frame, self.last_label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        return frame

    def _run(self):
        """Main camera capture and processing loop"""
        try:
            with self.lock:
                if not self.recognizer:
                    self._initialize_models()
                
                self.camera = Picamera2()
                config = self.camera.create_preview_configuration(
                    main={"format": 'XRGB8888', "size": (800, 600)},
                    buffer_count=2
                )
                self.camera.configure(config)
                self.camera.start()

            while self.event.is_set():
                frame = self.camera.capture_array()
                processed_frame = self._process_frame(frame)
                
                if not self.queue.full():
                    self.queue.put(processed_frame)
                
                time.sleep(0.02)  # ~50 FPS

        except Exception as e:
            print(f"Camera error: {e}")
        finally:
            self._cleanup()

    def start(self):
        """Start face recognition"""
        if not self.event.is_set():
            self.event.set()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop face recognition and clean up"""
        self.event.clear()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self._cleanup()
        with self.queue.mutex:
            self.queue.queue.clear()

# Global instance
face_recognizer = FaceRecognizer()
