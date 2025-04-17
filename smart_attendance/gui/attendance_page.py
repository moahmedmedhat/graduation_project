import customtkinter as ctk
from gui.styles import *
from backend.api_client import *
import threading
import queue
from time import sleep
from core.rfid_reader import read_card

# Use threading events instead of global flags
stop_threads = threading.Event()
stop_rfid = threading.Event()
rfid_queue = queue.Queue()  # Queue for safely updating the GUI

def update_session(root, session_label):
    """ Continuously listens for session updates """
    for session_type in start_listening("+"):
        if stop_threads.is_set():
            break
        root.after(0, lambda: update_label(root, session_label, session_type))

def update_label(root, session_label, session_type):
    """ Update session label safely if the widget still exists """
    if stop_threads.is_set():
        return

    # Check if session_label still exists
    if not session_label.winfo_exists():
        return  # Widget was destroyed, so don't update

    if session_type == "check-in":
        session_label.configure(
            text="✅ Session: Check-In\n🔄 Waiting for RFID...",
            text_color=SECONDARY_COLOR
        )
        stop_rfid.clear()  # Allow RFID to run
        threading.Thread(target=handle_rfid, args=(root, session_label), daemon=True).start()
    elif session_type == "check-out":
        session_label.configure(
            text="🚪 Session: Check-Out",
            text_color=PRIMARY_COLOR
        )
        stop_rfid.set()  # Stop RFID
    elif session_type == "end-check-out":
        session_label.configure(
            text="🚪 end-Check-Out",
            text_color=PRIMARY_COLOR
        )
        stop_rfid.set()  # Stop RFID
    elif session_type == "end-check-in":
        session_label.configure(
            text="🚪 end-Check-in",
            text_color=PRIMARY_COLOR
        )
        stop_rfid.set()  # Stop RFID
    else:
        session_label.configure(
            text="❌ No Active Session",
            text_color=TEXT_COLOR
        )
        stop_rfid.set()  # Stop RFID


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

def create_attendance_page(root, switch_page):
    """Creates the attendance page."""
    stop_threads.clear()  # Reset flag when entering this page
    stop_rfid.set() # Reset flag when entering this page

    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)

    # Title Label
    title_label = ctk.CTkLabel(root, text="Attendance Page", font=FONT_LARGE, text_color=TEXT_COLOR)
    title_label.place(relx=0.5, rely=0.15, anchor="center")

    # Back Button
    def go_back():
        stop_threads.set()  # Stop all background threads
        stop_rfid.set()     # Stop RFID reading
        switch_page("home")

    back_button = ctk.CTkButton(root, text="Back", command=go_back)
    back_button.place(relx=0.5, rely=0.8, anchor="center")

    # Session Status Label
    session_label = ctk.CTkLabel(root, text="🔄 Waiting for session...",
                                 font=FONT_LARGE, text_color=TEXT_COLOR,
                                 bg_color=BACKGROUND_COLOR)
    session_label.place(relx=0.5, rely=0.30, anchor="center")

    # Start session listener in a separate thread
    threading.Thread(target=update_session, args=(root, session_label), daemon=True).start()

    # Start RFID queue processing
    root.after(100, process_rfid_queue, root, session_label)  # Run every 100ms

# ✅ Updated read_card function

