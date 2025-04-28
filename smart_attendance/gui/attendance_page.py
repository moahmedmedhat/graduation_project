import customtkinter as ctk
from gui.styles import *
from backend.api_client import *
import threading
import queue
from time import sleep
from core.rfid_reader import read_card
from core.face_recognition import *
from PIL import Image, ImageTk
# Use threading events instead of global flags
stop_threads = threading.Event()
stop_rfid = threading.Event()
rfid_queue = queue.Queue()  # Queue for safely updating the GUI
camera_opened = threading.Event()


def update_session(root, session_label ,foreground_frame):
    """ Continuously listens for session updates """
    for session_type in start_listening("+"):
        if stop_threads.is_set():
            break
        root.after(0, lambda: update_label(root, session_label, session_type , foreground_frame))

def update_label(root, session_label, session_type,foreground_frame):
    if stop_threads.is_set() or not session_label.winfo_exists():
        return

    if session_type == "start-check-in":
        face_recognizer.stop()  # Ensure camera is off
        session_label.configure(text="✅ Session: Check-In", text_color=SECONDARY_COLOR)
        stop_rfid.clear()
        threading.Thread(target=handle_rfid, args=(root, session_label), daemon=True).start()

    elif session_type == "start-check-out":
        stop_rfid.set()
        # Force stop any existing camera thread
        face_recognizer.stop()
        # Give it a small delay before restarting
        root.after(100, lambda: face_recognizer.start())  # Start camera with slight delay
        session_label.configure(text="🚪 Session: Check-Out", text_color=PRIMARY_COLOR)
        # Explicitly lower the foreground frame
        root.after(150, lambda: foreground_frame.lower())

    elif session_type in ("end-check-out", "end-check-in"):
        face_recognizer.stop()  # Force-stop camera
        session_label.configure(text=f"🚪 Session: {session_type.replace('-', ' ').title()}", text_color=PRIMARY_COLOR)
        foreground_frame.lift()  # Ensure foreground is up when session ends




def handle_rfid(root, session_label):
    """ Reads RFID cards in a background thread and updates the GUI safely """
    while not stop_threads.is_set() and not stop_rfid.is_set():
        try:
            card_id = read_card(stop_rfid)  # Pass stop_rfid event
            if card_id:
                print(f"📡 Sending UID {card_id} to backend...")
                rfid_queue.put(card_id)  # Send card ID to queue
            sleep(0.5)  # Small delay to reduce CPU usage
        except Exception as e:
            print(f"⚠️ Error in handle_rfid: {e}")

def process_rfid_queue(root, session_label):
    """ Processes RFID data from the queue to update the GUI safely """
    while not rfid_queue.empty():
        card_id = rfid_queue.get()
        session_label.configure(text=f"📌 Card ID: {card_id}\n✅ Session: Check-In", text_color=SECONDARY_COLOR)

    # Schedule this function to run every 100ms
    root.after(100, process_rfid_queue, root, session_label)



def process_face_recognition_queue(root, camera_label, foreground_frame):
    if stop_threads.is_set():
        return

    try:
        if not face_recognizer.queue.empty():
            frame = face_recognizer.queue.get()
            
            # Only show camera if we're in check-out mode (stop_rfid is set)
            if stop_rfid.is_set():  # Check-out mode
                # Resize frame to fit the camera_label
                frame = cv2.resize(frame, (camera_label.winfo_width(), camera_label.winfo_height()))
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                imgtk = ImageTk.PhotoImage(image=img)
                camera_label.imgtk = imgtk
                camera_label.configure(image=imgtk)
                foreground_frame.lower()  # Show camera
            else:
                camera_label.configure(image=None)
                foreground_frame.lift()  # Hide camera during check-in
                
        

    except Exception as e:
        print(f"Error in process_face_recognition_queue: {e}")
    finally:
        root.after(10, process_face_recognition_queue, root, camera_label, foreground_frame)


def create_attendance_page(root, switch_page):
    stop_threads.clear()
    stop_rfid.set()
    face_recognizer.stop()

    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)

    # ==== Camera container (background layer) ====
    camera_container = ctk.CTkFrame(root, width=400, height=300, fg_color="transparent")
    camera_container.place(relx=0.5, rely=0.5, anchor="center")
    # camera_container.pack()

    camera_label = ctk.CTkLabel(camera_container, text=" ", width=400, height=300)
    camera_label.pack(fill="both", expand=True)

    # ==== Foreground container (above camera) ====
    foreground_frame = ctk.CTkFrame(root, width=400, height=300, fg_color="transparent")
    foreground_frame.place(relx=0.5, rely=0.5, anchor="center")

    # ==== UI Elements inside the foreground_frame ====
    title_label = ctk.CTkLabel(foreground_frame, text="Attendance Page", font=FONT_LARGE, text_color=TEXT_COLOR)
    title_label.place(relx=0.5, rely=0.15, anchor="center")

    session_label = ctk.CTkLabel(foreground_frame, text="🔄 Waiting for session...", font=FONT_LARGE, text_color=TEXT_COLOR)
    session_label.place(relx=0.5, rely=0.30, anchor="center")

    back_button = ctk.CTkButton(foreground_frame, text="Back", command=lambda: [
    stop_threads.set(),
    stop_rfid.set(),
    face_recognizer.stop(),
    foreground_frame.lift(),  # <-- Lift it back
    camera_label.configure(image=None),
    setattr(camera_label, "imgtk", None),
    switch_page("home")
])
    back_button.place(relx=0.5, rely=0.8, anchor="center")
    camera_container.lower()  # Camera at bottom
    foreground_frame.lift() 

    # ==== Start background services ====
    threading.Thread(target=update_session, args=(root, session_label , foreground_frame), daemon=True).start()

    # root.after(100, process_face_recognition_queue, root, camera_label)
    root.after(100, process_face_recognition_queue, root, camera_label, foreground_frame)
    root.after(100, process_rfid_queue, root, session_label)
