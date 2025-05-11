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

    if session_type == "start-check-out":
        face_recognizer.stop()  # Ensure camera is off
        session_label.configure(text="✅ Session: Check-Out", text_color=SECONDARY_COLOR)
        stop_rfid.clear()
        threading.Thread(target=handle_rfid, args=(root, session_label), daemon=True).start()
        foreground_frame.lift()

    elif session_type == "start-check-in":
        stop_rfid.set()
        # Force stop any existing camera thread
        face_recognizer.stop()
        # Give it a small delay before restarting
        root.after(100, lambda: face_recognizer.start())  # Start camera with slight delay
        session_label.configure(text="🚪 Session: Check-In", text_color=PRIMARY_COLOR)
        # Explicitly lower the foreground frame
        root.after(150, lambda: foreground_frame.lower())

    elif session_type in ("end-check-out", "end-check-in"):
        face_recognizer.stop()  # Force-stop camera
        session_label.configure(text=f"🚪 Session: {session_type.replace('-', ' ').title()}", text_color=PRIMARY_COLOR)
        foreground_frame.lift()  # Ensure foreground is up when session ends




def send_and_receive_attendance(root, method, card_id, session_label):
    try:
        send_student_data(method, card_id)  # Send to backend
        response = get_attendance_response(method, "4")  # Replace "4" with your device_id if needed

        def update_ui():
            if response:
                session_label.configure(text=f"✅ {response}", text_color=SECONDARY_COLOR)
            else:
                session_label.configure(text="⚠️ No response", text_color="red")

        # Safely update UI on main thread
        root.after(0, update_ui)

    except Exception as e:
        print("❌ Error in send_and_receive_attendance:", e)




def handle_rfid(root, session_label):
    """ Reads RFID cards in a background thread and updates the GUI safely """
    while not stop_threads.is_set() and not stop_rfid.is_set():
        try:
            card_id = read_card(stop_rfid)  # Pass stop_rfid event
            if card_id:
                print(f"success UID {card_id} ")
                rfid_queue.put(card_id)  # Send card ID to queue
            sleep(0.5)  # Small delay to reduce CPU usage
        except Exception as e:
            print(f"⚠️ Error in handle_rfid: {e}")

def process_rfid_queue(root, session_label):
    """ Processes RFID data from the queue and triggers attendance logic in a thread """
    while not rfid_queue.empty():
        card_id = rfid_queue.get()
        
        # Optional: update UI immediately with UID
        session_label.configure(text=f"📌 Card ID: {card_id}\n⏳ Sending to server...", text_color=SECONDARY_COLOR)
        
        # Start background thread to send and receive
        threading.Thread(
            target=send_and_receive_attendance, 
            args=(root, "check-out", card_id, session_label),
            daemon=True
        ).start()

    # Keep checking
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

    # Main layout

    header_frame = ctk.CTkFrame(root, fg_color="#2D2D2D", corner_radius=CARD_CORNER_RADIUS, width=CARD_WIDTH, height=int(SCREEN_HEIGHT * 0.12))
    header_frame.place(relx=0.5, rely=0.07, anchor="center")



    # Camera
    camera_container = ctk.CTkFrame(root, fg_color="#191919", corner_radius=CARD_CORNER_RADIUS, width=int(CARD_WIDTH * 0.9), height=int(SCREEN_HEIGHT * 0.45))
    camera_container.place(relx=0.5, rely=0.42, anchor="center")

    camera_border = ctk.CTkFrame(
        camera_container,
        fg_color="transparent",
        corner_radius=CARD_CORNER_RADIUS - 5,
        border_width=2,
        border_color=SECONDARY_COLOR,
        width=int(CARD_WIDTH * 0.85),
        height=int(SCREEN_HEIGHT * 0.42)
    )
    camera_border.place(relx=0.5, rely=0.45, anchor="center")

    camera_label = ctk.CTkLabel(
        camera_border, 
        text="", 
        width=int(CARD_WIDTH * 0.83),
        height=int(SCREEN_HEIGHT * 0.4)
    )
    camera_label.place(relx=0.5, rely=0.5, anchor="center")

    # Foreground
    foreground_frame = ctk.CTkFrame(root, fg_color="transparent", width=CARD_WIDTH, height=SCREEN_HEIGHT)
    foreground_frame.place(relx=0.5, rely=0.5, anchor="center")

    title_label = ctk.CTkLabel(foreground_frame, text="Attendance", font=FONT_TITLE, text_color=TEXT_COLOR)
    title_label.place(relx=0.5, rely=0.5, anchor="center")

    session_card = ctk.CTkFrame(foreground_frame, fg_color="#2D2D2D", corner_radius=CARD_CORNER_RADIUS, width=int(CARD_WIDTH * 0.9), height=int(SCREEN_HEIGHT * 0.15))
    session_card.place(relx=0.5, rely=0.74, anchor="center")

    session_indicator = ctk.CTkFrame(session_card, fg_color=PRIMARY_COLOR, corner_radius=5, width=10, height=int(SCREEN_HEIGHT * 0.07))
    session_indicator.place(relx=0.05, rely=0.5, anchor="center")

    session_label = ctk.CTkLabel(session_card, text="🔄 Waiting for session...", font=FONT_MEDIUM, text_color=TEXT_COLOR)
    session_label.place(relx=0.5, rely=0.35, anchor="center")

    session_status = ctk.CTkLabel(session_card, text="Ready to scan card or face", font=FONT_SMALL, text_color="#AAAAAA")
    session_status.place(relx=0.5, rely=0.7, anchor="center")

    control_panel = ctk.CTkFrame(root, fg_color="#2D2D2D", corner_radius=CARD_CORNER_RADIUS, width=CARD_WIDTH, height=int(SCREEN_HEIGHT * 0.1))
    control_panel.place(relx=0.5, rely=0.92, anchor="center")

    back_button = ctk.CTkButton(foreground_frame, text="Back to Home", font=FONT_MEDIUM, fg_color="#444444", hover_color="#555555", corner_radius=BUTTON_CORNER_RADIUS, border_width=0, width=150, height=35, command=lambda: [
        stop_threads.set(),
        stop_rfid.set(),
        face_recognizer.stop(),
        foreground_frame.lift(),
        camera_label.configure(image=None),
        setattr(camera_label, "imgtk", None),
        switch_page("home")
    ])
    back_button.place(relx=0.5, rely=0.5, anchor="center")

    # Delay frame layering to prevent overlapping glitches
    root.after(200, lambda: camera_container.lower())
    root.after(250, lambda: foreground_frame.lift())

    # Start MQTT listener in background thread, queue actions to GUI
    action_queue = queue.Queue()
    threading.Thread(target=lambda: [action_queue.put(action) for action in start_listening("+")], daemon=True).start()

    def listen_loop():
        if not stop_threads.is_set():
            try:
                if not action_queue.empty():
                    action = action_queue.get_nowait()
                    update_label(root, session_label, action, foreground_frame)
            except Exception as e:
                print("⚠️ MQTT Listen error:", e)
            root.after(500, listen_loop)

    root.after(500, listen_loop)
    root.after(100, process_face_recognition_queue, root, camera_label, foreground_frame)
    root.after(100, process_rfid_queue, root, session_label)
