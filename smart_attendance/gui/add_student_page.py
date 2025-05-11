import customtkinter as ctk
from gui.styles import *
import os
import threading
import cv2
from picamera2 import Picamera2
import shutil
from time import sleep
import subprocess
import signal
import psutil
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
from config.settings import MOUNTED_DATASET_PATH

class CameraManager:
    """
    Utility class to manage camera resources and handle reset operations.
    Provides methods to ensure the camera is in a usable state.
    """
    @staticmethod
    def reset_camera():
        """Reset and release any camera resources"""
        results = []
        
        try:
            # Method 1: Kill processes using v4l2 devices
            try:
                subprocess.run(['sudo', 'fuser', '-k', '/dev/video0'], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                results.append("Cleared camera device users")
            except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                pass
            
            # Method 2: Find and kill specific camera processes
            camera_processes = CameraManager._find_camera_processes()
            if camera_processes:
                for proc in camera_processes:
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=1)
                        results.append(f"Terminated process: {proc.name()} (PID: {proc.pid})")
                    except (ProcessLookupError, psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try:
                            os.kill(proc.pid, signal.SIGKILL)
                            results.append(f"Force killed process: {proc.name()} (PID: {proc.pid})")
                        except (ProcessLookupError, psutil.NoSuchProcess):
                            pass
            
            # Method 3: Reset the camera module (if needed)
            if not results:  # Only if previous methods didn't work
                try:
                    # Unload and reload the camera module
                    subprocess.run(['sudo', 'rmmod', 'bcm2835-v4l2'], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                    sleep(0.5)
                    subprocess.run(['sudo', 'modprobe', 'bcm2835-v4l2'], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                    results.append("Reset camera module")
                except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                    pass
            
            # Wait for camera to stabilize
            sleep(1)
            
            return True, results
        except Exception as e:
            return False, [f"Camera reset error: {str(e)}"]
    
    @staticmethod
    def _find_camera_processes():
        """Find processes that might be using the camera"""
        camera_processes = []
        keywords = ['libcamera', 'raspistill', 'raspivid', 'picamera', 'v4l2']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info
                # Check process name and command line for camera-related keywords
                if any(keyword in ''.join(proc_info['cmdline']).lower() for keyword in keywords) or \
                   any(keyword in proc_info['name'].lower() for keyword in keywords):
                    if proc.pid != os.getpid():  # Don't include our own process
                        camera_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return camera_processes

    @staticmethod
    def test_camera_availability():
        """Test if the camera is available and working"""
        try:
            # Try to initialize the camera
            picam = Picamera2()
            # Configure with minimal settings
            config = picam.create_preview_configuration()
            picam.configure(config)
            # Start and immediately stop
            picam.start()
            sleep(0.1)
            picam.close()
            return True, "Camera is available"
        except Exception as e:
            return False, f"Camera test failed: {str(e)}"


class PhotoCaptureSession:
    """
    Manages a photo capture session for student identification.
    
    This class handles camera initialization, photo capture,
    processing, and uploading to the destination folder.
    """
    def __init__(self, student_id, status_label, preview_label, 
                 foreground_frame, camera_container):
        """Initialize a new photo capture session."""
        self.student_id = student_id
        self.status_label = status_label
        self.preview_label = preview_label
        self.foreground_frame = foreground_frame
        self.camera_container = camera_container
        
        # Configuration
        self.total_photos = 25
        self.photo_count = 0
        self.preview_size = (320, 240)
        self.camera_size = (800, 600)
        
        # State tracking
        self.running = False
        self.processing_photo = False
        self.latest_frame = None
        self.auto_capture_enabled = False
        
        # Components
        self.picam2 = None
        self.capture_btn = None
        self.cancel_btn = None
        self.student_dir = None
        
    def start(self):
        """Start the photo capture session."""
        # Validate input
        if not self._validate_student_id():
            return False
            
        try:
            # Set up UI for camera mode
            self._update_status("📷 Initializing camera...")
            self.foreground_frame.lower()
            self.camera_container.lift()
            
            # Set up directory
            self._setup_directory()
            
            # Reset camera resources first
            success, reset_results = CameraManager.reset_camera()
            if not success:
                self._update_status(f"⚠️ Camera reset issue: {reset_results[0]}")
            
            # Initialize camera with retry mechanism
            if not self._initialize_camera_with_retry():
                self._handle_error("Failed to initialize camera after multiple attempts")
                return False
                
            # Start camera operations
            self.running = True
            self._start_camera_thread()
            self._start_preview_updates()
            
            # Set up UI controls
            self._setup_ui_controls()
            
            # Start auto-capture checking if enabled
            self._schedule_auto_capture_check()
            
            # Set initial status
            self._update_status("📷 Camera ready - please look directly at the camera")
            return True
            
        except Exception as e:
            self._handle_error(f"Setup error: {e}")
            return False
    
    def _validate_student_id(self):
        """Validate the student ID input."""
        import re
        
        if not self.student_id or not self.student_id.strip():
            self._update_status("❌ Student ID cannot be empty")
            return False
        
        # Clean the student ID to prevent path traversal or invalid chars
        clean_id = re.sub(r'[^\w\d-]', '', self.student_id)
        if clean_id != self.student_id:
            self._update_status("❌ Student ID contains invalid characters")
            return False
            
        self.student_id = clean_id
        return True
    
    def _setup_directory(self):
        """Set up the directory for storing photos."""
        self.student_dir = os.path.join("photos", self.student_id)
        if os.path.exists(self.student_dir):
            # Clean up old photos if they exist
            shutil.rmtree(self.student_dir)
        os.makedirs(self.student_dir, exist_ok=True)
    
    def _initialize_camera_with_retry(self):
        """Initialize the camera with multiple attempts."""
        max_attempts = 3
        delay_between_attempts = 2  # seconds
        
        for attempt in range(1, max_attempts + 1):
            self._update_status(f"📷 Initializing camera (attempt {attempt}/{max_attempts})...")
            
            # Test camera availability first
            available, message = CameraManager.test_camera_availability()
            if not available:
                self._update_status(f"⚠️ Camera test failed (attempt {attempt}): {message}")
                
                # Reset camera again before retry
                CameraManager.reset_camera()
                sleep(delay_between_attempts)
                continue
            
            # If test passed, try full initialization
            if self._initialize_camera():
                self._update_status("✅ Camera initialized successfully")
                return True
            
            # If initialization failed, reset and try again
            self._update_status(f"⚠️ Retrying camera initialization ({attempt}/{max_attempts})...")
            CameraManager.reset_camera()
            sleep(delay_between_attempts)
        
        self._update_status("❌ Failed to initialize camera after multiple attempts")
        return False
    
    def _initialize_camera(self):
        """Initialize the camera for capturing photos."""
        try:
            # Create a new Picamera2 instance
            self.picam2 = Picamera2()
            
            # Create and apply a configuration with more deliberate settings and error handling
            try:
                preview_config = self.picam2.create_preview_configuration(
                    main={"format": 'XRGB8888', "size": self.camera_size},
                    buffer_count=4  # Increase buffer for smoother preview
                )
                self.picam2.configure(preview_config)
            except Exception as config_error:
                print(f"Configuration error: {config_error}")
                # Try with default configuration as fallback
                self.picam2.configure(self.picam2.create_preview_configuration())
            
            # Start the camera with explicit error handling
            try:
                self.picam2.start()
            except Exception as start_error:
                print(f"Camera start error: {start_error}")
                # Clean up and re-raise to trigger retry
                if self.picam2:
                    self.picam2.close()
                    self.picam2 = None
                raise start_error
            
            # Allow camera to warm up and verify it's working
            sleep(1.5)
            
            # Try to capture a test frame to ensure camera is working
            try:
                test_frame = self.picam2.capture_array()
                if test_frame is None or test_frame.size == 0:
                    raise ValueError("Camera returned empty frame")
            except Exception as capture_error:
                print(f"Test capture error: {capture_error}")
                if self.picam2:
                    self.picam2.close()
                    self.picam2 = None
                raise capture_error
                
            return True
        except Exception as e:
            print(f"Camera initialization error: {e}")
            return False
    
    def _start_camera_thread(self):
        """Start the camera capture thread."""
        camera_thread = threading.Thread(
            target=self._camera_loop, 
            daemon=True
        )
        camera_thread.start()
    
    def _camera_loop(self):
        """Continuously capture frames from the camera."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                # Capture frame with timeout protection
                frame = None
                
                # Set a timeout for frame capture to prevent hanging
                def capture_with_timeout():
                    nonlocal frame
                    try:
                        frame = self.picam2.capture_array()
                    except Exception as e:
                        print(f"Frame capture error: {e}")
                
                capture_thread = threading.Thread(target=capture_with_timeout)
                capture_thread.daemon = True
                capture_thread.start()
                capture_thread.join(timeout=0.5)  # Wait for at most 0.5 seconds
                
                if frame is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self._update_status("❌ Camera not responding - please restart the application")
                        self.cancel()
                        break
                    continue
                
                # Reset error counter if successful
                consecutive_errors = 0
                
                # Add status text to the frame
                self._annotate_frame(frame)
                
                # Update the latest frame
                self.latest_frame = frame
            except Exception as e:
                print(f"Camera loop error: {e}")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    if self.running:  # Only show error if we're still supposed to be running
                        self._update_status(f"❌ Persistent camera error: {str(e)[:50]}")
                    self.cancel()
                    break
            
            sleep(0.01)  # Small sleep to prevent CPU hogging
    
    def _annotate_frame(self, frame):
        """Add text overlays to the camera frame."""
        # Show progress
        photo_text = f"Photo {self.photo_count} / {self.total_photos}"
        cv2.putText(frame, photo_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Add processing indicator if needed
        if self.processing_photo:
            height, width = frame.shape[:2]
            cv2.putText(frame, "Processing...", (width//2-80, height-30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    def _start_preview_updates(self):
        """Start the preview update cycle."""
        self._update_preview()
    
    def _update_preview(self):
        """Update the preview image with the latest frame."""
        if not self.running:
            return
            
        frame = self.latest_frame
        if frame is not None:
            try:
                # Resize for display efficiency
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img = img.resize(self.preview_size)
                img_tk = ImageTk.PhotoImage(image=img)
                self.preview_label.configure(image=img_tk)
                self.preview_label.image = img_tk
            except Exception as e:
                print(f"Preview update error: {e}")
        
        # Schedule next update
        self.preview_label.after(30, self._update_preview)
    
    def _setup_ui_controls(self):
        """Set up UI controls for the camera interface."""
        controls_frame = ctk.CTkFrame(self.camera_container, fg_color="transparent")
        controls_frame.place(relx=0.5, rely=0.95, anchor="center", relwidth=0.9)
        
        # Auto-capture checkbox
        auto_capture_var = ctk.BooleanVar(value=False)
        auto_capture_cb = ctk.CTkCheckBox(
            controls_frame, 
            text="Auto-capture", 
            variable=auto_capture_var,
            width=100,
            command=lambda: self._toggle_auto_capture(auto_capture_var.get())
        )
        auto_capture_cb.pack(side="left", padx=(0, 10))
        
        # Capture button
        self.capture_btn = ctk.CTkButton(
            controls_frame,
            text=f"📸 Capture (0/{self.total_photos})",
            command=self.capture_photo,
            width=150
        )
        self.capture_btn.pack(side="left", padx=10)
        
        # Cancel button
        self.cancel_btn = ctk.CTkButton(
            controls_frame,
            text="❌ Cancel",
            command=self.cancel,
            width=100,
            fg_color="#aa3333",
            hover_color="#cc3333"
        )
        self.cancel_btn.pack(side="left", padx=(10, 0))
        
        # Add a reset camera button
        reset_btn = ctk.CTkButton(
            controls_frame,
            text="🔄 Reset",
            command=self._handle_camera_reset,
            width=80,
            fg_color="#555555",
            hover_color="#777777"
        )
        reset_btn.pack(side="left", padx=(10, 0))
    
    def _handle_camera_reset(self):
        """Handle camera reset request from UI"""
        self._update_status("🔄 Resetting camera...")
        
        # Stop the current camera operation
        was_running = self.running
        self.running = False
        
        # Close the camera
        self._close_camera()
        
        # Reset camera
        success, messages = CameraManager.reset_camera()
        if not success:
            self._update_status(f"⚠️ Camera reset issue: {messages[0]}")
        
        # Reinitialize camera
        if self._initialize_camera():
            self._update_status("✅ Camera reset complete")
            
            # Resume operation if we were running
            if was_running:
                self.running = True
                self._start_camera_thread()
        else:
            self._update_status("❌ Failed to reinitialize camera after reset")
    
    def _toggle_auto_capture(self, enabled):
        """Toggle auto-capture mode."""
        self.auto_capture_enabled = enabled
    
    def _schedule_auto_capture_check(self):
        """Schedule checks for auto-capture."""
        self.camera_container.after(1000, self._check_auto_capture)
    
    def _check_auto_capture(self):
        """Check if we should auto-capture a photo."""
        if not self.running:
            return
            
        if (self.auto_capture_enabled and 
            not self.processing_photo and 
            self.photo_count < self.total_photos):
            self.capture_photo()
            # Schedule next capture with delay
            self.camera_container.after(1500, self._check_auto_capture)
        else:
            # Keep checking if auto is enabled
            self.camera_container.after(500, self._check_auto_capture)
    
    def capture_photo(self):
        """Capture a single photo."""
        if self.photo_count >= self.total_photos or self.processing_photo:
            return
            
        self.processing_photo = True
        frame = self.latest_frame
        
        # Start the processing in a separate thread
        processing_thread = threading.Thread(
            target=lambda: self._process_photo(frame),
            daemon=True
        )
        processing_thread.start()
    
    def _process_photo(self, frame):
        """Process and save a captured photo."""
        try:
            if frame is not None:
                # Apply image enhancement
                enhanced_frame = self._enhance_image(frame)
                
                # Save image with sequential naming
                file_path = os.path.join(
                    self.student_dir, 
                    f"{self.student_id}_{self.photo_count + 1:03d}.jpg"
                )
                cv2.imwrite(file_path, enhanced_frame)
                
                # Update counter and UI
                self.photo_count += 1
                self._update_status(f"📸 Captured {self.photo_count} of {self.total_photos}")
                
                # Update capture button text
                self._update_capture_button()
                
                # Check if we're done
                if self.photo_count >= self.total_photos:
                    self._finish_capture()
            else:
                self._update_status("❌ Failed to capture image - no frame available")
        except Exception as e:
            self._update_status(f"❌ Error saving photo: {str(e)[:50]}")
        finally:
            self.processing_photo = False
    
    def _enhance_image(self, frame):
        """Apply enhancements to the captured image."""
        enhanced_frame = frame.copy()
        
        # Convert to PIL for enhancement
        pil_img = Image.fromarray(cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB))
        
        # Apply contrast enhancement
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced_pil = enhancer.enhance(1.2)  # Slight contrast boost
        
        # Convert back to OpenCV format
        return cv2.cvtColor(np.array(enhanced_pil), cv2.COLOR_RGB2BGR)
    
    def _update_status(self, message):
        """Update the status label safely."""
        # Use after(0) if called from a non-main thread
        if threading.current_thread() is threading.main_thread():
            self.status_label.configure(text=message)
        else:
            self.status_label.after(0, lambda: self.status_label.configure(text=message))
    
    def _update_capture_button(self):
        """Update the capture button text."""
        new_text = f"📸 Capture ({self.photo_count}/{self.total_photos})"
        
        # Use after(0) if called from a non-main thread
        if threading.current_thread() is threading.main_thread():
            self.capture_btn.configure(text=new_text)
        else:
            self.capture_btn.after(0, lambda: self.capture_btn.configure(text=new_text))
    
    def _finish_capture(self):
        """Clean up and process the captured photos."""
        self.running = False
        
        # Clean up camera
        self._close_camera()
        
        # Update UI
        self._switch_to_form_view()
        self._update_status("📦 Processing and uploading photos...")
        
        # Move photos in background
        move_thread = threading.Thread(
            target=self._move_photos,
            daemon=True
        )
        move_thread.start()
    
    def _close_camera(self):
        """Close the camera safely."""
        if self.picam2:
            try:
                self.picam2.close()
                self.picam2 = None
            except Exception as e:
                print(f"Error closing camera: {e}")
    
    def _switch_to_form_view(self):
        """Switch back to the form view."""
        # Use after(0) for thread safety
        self.camera_container.after(0, self.camera_container.lower)
        self.foreground_frame.after(0, self.foreground_frame.lift)
    
    def _move_photos(self):
        """Move photos to their final destination."""
        try:
            # Move to final destination
            target_path = os.path.join(MOUNTED_DATASET_PATH, self.student_id)
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.move(self.student_dir, target_path)
            
            # Update UI
            self._update_status(f"✅ Added student {self.student_id} with {self.photo_count} photos")
        except Exception as e:
            self._update_status(f"❌ Error during upload: {str(e)[:50]}")
    
    def cancel(self):
        """Cancel the photo capture process."""
        self.running = False
        
        # Clean up resources
        self._close_camera()
        
        # Clean up temporary directory
        if os.path.exists(self.student_dir):
            try:
                shutil.rmtree(self.student_dir)
            except Exception as e:
                print(f"Error removing directory: {e}")
        
        # Update UI
        self._switch_to_form_view()
        self._update_status("❌ Photo capture cancelled")
    
    def _handle_error(self, message):
        """Handle errors during the capture process."""
        print(message)
        self._close_camera()
        self._switch_to_form_view()
        self._update_status(f"❌ {message[:50]}")


def capture_photos(student_id, status_label, preview_label, foreground_frame, camera_container):
    """
    Captures a series of photos for student identification and stores them.
    
    Args:
        student_id (str): The ID of the student being photographed
        status_label (CTkLabel): Label for displaying status messages
        preview_label (CTkLabel): Label for displaying camera preview
        foreground_frame (CTkFrame): The form frame to hide during capture
        camera_container (CTkFrame): The container for camera preview
    """
    # Pre-emptively reset camera resources before creating session
    status_label.configure(text="🔄 Checking camera resources...")
    
    # Run camera reset in a separate thread to avoid UI freezing
    def prepare_camera():
        success, messages = CameraManager.reset_camera()
        status_label.after(0, lambda: status_label.configure(
            text="📷 Starting camera session..." if success else f"⚠️ {messages[0][:50]}"
        ))
        
        # Create and start session after camera reset
        session = PhotoCaptureSession(
            student_id, 
            status_label, 
            preview_label, 
            foreground_frame, 
            camera_container
        )
        session.start()
    
    threading.Thread(target=prepare_camera, daemon=True).start()


def create_add_student_page(root, switch_page):
    """Creates the add student page."""
    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)

    header_frame = ctk.CTkFrame(
        root,
        fg_color="#2D2D2D",
        corner_radius=CARD_CORNER_RADIUS,
        width=CARD_WIDTH,
        height=int(SCREEN_HEIGHT * 0.12)
    )
    header_frame.place(relx=0.5, rely=0.07, anchor="center")

    title_label = ctk.CTkLabel(
        header_frame, 
        text="Add Student", 
        font=FONT_TITLE, 
        text_color=TEXT_COLOR
    )
    title_label.place(relx=0.5, rely=0.5, anchor="center")



    camera_container = ctk.CTkFrame(
        root,
        fg_color="#191919",
        corner_radius=CARD_CORNER_RADIUS,
        width=int(CARD_WIDTH),
        height=int(SCREEN_HEIGHT * 0.56)
    )
    camera_container.place(relx=0.5, rely=0.45, anchor="center")

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

    preview_label = ctk.CTkLabel(
        camera_border, 
        text="", 
        width=int(CARD_WIDTH * 0.83),
        height=int(SCREEN_HEIGHT * 0.4)
    )
    preview_label.place(relx=0.5, rely=0.5, anchor="center")

    foreground_frame = ctk.CTkFrame(
        root,
        fg_color="transparent",
        width=CARD_WIDTH,
        height=SCREEN_HEIGHT
    )
    foreground_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    form_card = ctk.CTkFrame(
        foreground_frame,
        fg_color="#2D2D2D",
        corner_radius=CARD_CORNER_RADIUS,
        width=int(CARD_WIDTH * 0.9),
        height=int(SCREEN_HEIGHT * 0.56)
    )
    form_card.place(relx=0.5, rely=0.45, anchor="center")

    id_label = ctk.CTkLabel(
        form_card,
        text="Student ID",
        font=FONT_SMALL,
        text_color="#AAAAAA"
    )
    id_label.place(relx=0.5, rely=0.25, anchor="center")

    # Entry for Student ID
    student_id_entry = ctk.CTkEntry(
        form_card,
        placeholder_text="Enter Student ID",
        width=250,
        height=40,
        font=FONT_MEDIUM,
        border_color=PRIMARY_COLOR,
        corner_radius=5
    )
    student_id_entry.place(relx=0.5, rely=0.35, anchor="center")

    status_frame = ctk.CTkFrame(
        form_card,
        fg_color="#222222",
        corner_radius=10,
        width=300,
        height=60
    )
    status_frame.place(relx=0.5, rely=0.58, anchor="center")

    status_label = ctk.CTkLabel(
        status_frame,
        text="Ready to capture student photos",
        font=FONT_SMALL,
        text_color="#AAAAAA",
        wraplength=280
    )
    status_label.place(relx=0.5, rely=0.5, anchor="center")
    
    
    button_frame = ctk.CTkFrame(
        form_card,
        fg_color="transparent",
        width=350,
        height=50
    )
    button_frame.place(relx=0.5, rely=0.8, anchor="center")

    foreground_frame.lift()
    camera_container.lower()
    
    # Troubleshoot Camera Button
    troubleshoot_button = ctk.CTkButton(
        button_frame,
        text="Reset Camera",
        font=FONT_SMALL,
        fg_color="#555555",
        hover_color="#666666",
        corner_radius=8,
        width=120,
        height=35,
        command=lambda: troubleshoot_camera(status_label)
    )
    troubleshoot_button.place(relx=0.2, rely=0.5, anchor="center")
    
    # Capture Button
    start_capture_button = ctk.CTkButton(
        button_frame,
        text="Start Capture",
        font=FONT_SMALL,
        fg_color=SECONDARY_COLOR,
        hover_color="#491F69",  # Darker shade for hover
        corner_radius=8,
        width=120,
        height=35,
         command=lambda: capture_photos(
            student_id_entry.get(), 
            status_label, 
            preview_label,
            foreground_frame,
            camera_container
         )
    )
    start_capture_button.place(relx=0.5, rely=0.5, anchor="center")

    # Back Button
    back_button = ctk.CTkButton(
        button_frame,
        text="Back",
        font=FONT_SMALL,
        fg_color="#444444",
        hover_color="#555555",
        corner_radius=8,
        width=90,
        height=35,
        command=lambda: switch_page("home")
    )
    back_button.place(relx=0.8, rely=0.5, anchor="center")

    control_panel = ctk.CTkFrame(
        root,
        fg_color="#1A1A1A",
        corner_radius=CARD_CORNER_RADIUS,
        width=CARD_WIDTH,
        height=int(SCREEN_HEIGHT * 0.08)
    )
    control_panel.place(relx=0.5, rely=0.92, anchor="center")

    tips_label = ctk.CTkLabel(
        control_panel,
        text="💡 Position the student facing the camera with good lighting",
        font=("Roboto", 10),
        text_color="#888888"
    )
    tips_label.place(relx=0.5, rely=0.5, anchor="center")


def troubleshoot_camera(status_label):
    """Run camera diagnostics and reset procedure"""
    status_label.configure(text="🔄 Running camera diagnostics...")
    
    def run_diagnostics():
        try:
            # Step 1: Check if camera is in use
            success, messages = CameraManager.reset_camera()
            
            # Step 2: Test if camera is now available
            available, message = CameraManager.test_camera_availability()
            
            if available:
                result = "✅ Camera is now ready for use"
            else:
                result = f"❌ Camera issue persists: {message}"
                
            status_label.after(0, lambda: status_label.configure(text=result))
        except Exception as e:
            status_label.after(0, lambda: status_label.configure(
                text=f"❌ Diagnostics error: {str(e)[:50]}"
            ))
    
    # Run diagnostics in background thread
    threading.Thread(target=run_diagnostics, daemon=True).start()




