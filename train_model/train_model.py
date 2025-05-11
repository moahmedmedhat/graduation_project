import os
import cv2
import numpy as np
import time
from datetime import datetime
import gc  # Garbage collector for memory management

# Constants
# TRAIN_PATH = "working_dataset" 
TRAIN_PATH="/home/pi5/face-dataset/graduation_project/working_dataset" # rclone mount point
MODEL_PATH = "/home/pi5/smart_attendance/train_model/lbph_model.xml"
LAST_TRAIN_FILE = "/home/pi5/smart_attendance/train_model/last_model_train_time.txt"

# Load face cascade
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def get_last_train_time():
    """Load the timestamp of the last model training"""
    if os.path.exists(LAST_TRAIN_FILE):
        with open(LAST_TRAIN_FILE, "r") as f:
            timestamp = f.read().strip()
            try:
                return float(timestamp)
            except ValueError:
                return 0
    return 0

def save_train_time():
    """Save current time as the latest training timestamp"""
    with open(LAST_TRAIN_FILE, "w") as f:
        f.write(str(time.time()))

def process_image(img_path, label):
    """Process a single image file and return face data if found"""
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)  # Direct grayscale loading
    
    if img is None:
        return None, None
        
    # Apply histogram equalization
    img = cv2.equalizeHist(img)
    
    # Detect faces with optimized parameters
    faces_detected = face_cascade.detectMultiScale(
        img,
        scaleFactor=1.1,  # Slightly increased for fewer iterations
        minNeighbors=3,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE  # Use scale image flag for optimization
    )
    
    # Return first face found (assuming one face per training image)
    if len(faces_detected) > 0:
        x, y, w, h = faces_detected[0]
        face = img[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))
        return face, label
        
    return None, None

def batch_process_data(last_train_time, batch_size=50):
    """Process images in batches to reduce memory usage"""
    all_faces = []
    all_labels = []
    batch_faces = []
    batch_labels = []
    count = 0
    
    print("🔎 Checking for new images since last training...")
    
    # First, create a list of all files that need processing
    files_to_process = []
    
    for label_name in sorted(os.listdir(TRAIN_PATH)):
        try:
            label = int(label_name)
            person_path = os.path.join(TRAIN_PATH, label_name)
            
            if not os.path.isdir(person_path):
                continue
                
            for img_file in os.listdir(person_path):
                img_path = os.path.join(person_path, img_file)
                
                # Skip old images
                if os.path.getmtime(img_path) < last_train_time:
                    continue
                    
                files_to_process.append((img_path, label))
        except ValueError:
            # Skip non-integer directory names
            continue
    
    total_files = len(files_to_process)
    if total_files == 0:
        return np.array([]), np.array([], dtype=np.int32)
    
    print(f"Found {total_files} new images to process")
    
    # Now process in batches
    for img_path, label in files_to_process:
        face, face_label = process_image(img_path, label)
        
        if face is not None:
            batch_faces.append(face)
            batch_labels.append(face_label)
            count += 1
            
        # When batch is full, add to main lists and clear batch
        if len(batch_faces) >= batch_size:
            all_faces.extend(batch_faces)
            all_labels.extend(batch_labels)
            batch_faces = []
            batch_labels = []
            gc.collect()  # Force garbage collection
            print(f"Processed {count}/{total_files} images...")
    
    # Add remaining batch
    if batch_faces:
        all_faces.extend(batch_faces)
        all_labels.extend(batch_labels)
    
    print(f"✅ Processed {len(all_faces)} faces from {total_files} images")
    
    # Convert to numpy arrays only once at the end
    if all_faces:
        return np.array(all_faces), np.array(all_labels, dtype=np.int32)
    else:
        return np.array([]), np.array([], dtype=np.int32)

def train_model():
    """Train the LBPH face recognition model with optimized data loading"""
    last_train_time = get_last_train_time()
    faces, labels = batch_process_data(last_train_time)
    
    if len(faces) == 0:
        print("⚠️ No new faces found. Skipping training.")
        return
    
    print(f"🧠 Training model on {len(faces)} face samples...")
    
    # Initialize model with optimized parameters
    model = cv2.face.LBPHFaceRecognizer_create(
        radius=2,        # Default is 1, increased for better feature extraction
        neighbors=8,     # Default is 8
        grid_x=8,        # Default is 8
        grid_y=8,        # Default is 8
        threshold=100.0  # Recognition threshold
    )
    
    # Update existing model if available
    if os.path.exists(MODEL_PATH):
        try:
            model.read(MODEL_PATH)
            print("♻️ Loading existing model for update...")
            model.update(faces, labels)
        except:
            print("⚠️ Couldn't update existing model. Training new one...")
            model.train(faces, labels)
    else:
        model.train(faces, labels)
    
    # Save model and timestamp
    model.save(MODEL_PATH)
    print(f"✅ Model saved: {MODEL_PATH}")
    save_train_time()
    
    # Clean up
    del faces, labels
    gc.collect()

if __name__ == "__main__":
    train_model()
