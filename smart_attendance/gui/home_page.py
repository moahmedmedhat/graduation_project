
"""
Home Page for the Smart Attendance System
"""

import customtkinter as ctk
from PIL import Image, ImageTk
import os
from gui.styles import *

def create_home_page(root, switch_page):
    """Creates a modern, card-based home page with navigation buttons."""
    # Set appearance mode
    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)
    
    # Create a main container frame
    main_frame = ctk.CTkFrame(
        root, 
        fg_color=BACKGROUND_COLOR,
        width=SCREEN_WIDTH,
        height=SCREEN_HEIGHT
    )
    main_frame.place(x=0, y=0)
    
    # Header card with title
    header_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#2D2D2D",
        corner_radius=CARD_CORNER_RADIUS,
        width=CARD_WIDTH,
        height=int(SCREEN_HEIGHT * 0.15)
    )
    header_frame.place(relx=0.5, rely=0.09, anchor="center")
    
    # Title with subtle shadow effect
    title_shadow = ctk.CTkLabel(
        header_frame, 
        text="Smart Attendance", 
        font=FONT_TITLE, 
        text_color="#333333"
    )
    title_shadow.place(relx=0.5, rely=0.51, anchor="center")
    
    title_label = ctk.CTkLabel(
        header_frame, 
        text="Smart Attendance", 
        font=FONT_TITLE, 
        text_color=TEXT_COLOR
    )
    title_label.place(relx=0.5, rely=0.5, anchor="center")
    
    # Main content card
    content_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#2D2D2D",
        corner_radius=CARD_CORNER_RADIUS,
        width=CARD_WIDTH,
        height=int(SCREEN_HEIGHT * 0.55)
    )
    content_frame.place(relx=0.5, rely=0.55, anchor="center")
    
    # Card title
    card_title = ctk.CTkLabel(
        content_frame, 
        text="Choose an Option", 
        font=FONT_MEDIUM, 
        text_color="#AAAAAA"
    )
    card_title.place(relx=0.5, rely=0.15, anchor="center")
    
    # Button size and styling
    button_width = BUTTON_WIDTH
    button_height = BUTTON_HEIGHT
    
    # Start Attendance Button with icon indicator
    start_button_frame = ctk.CTkFrame(
        content_frame, 
        fg_color=PRIMARY_COLOR,
        corner_radius=BUTTON_CORNER_RADIUS,
        width=button_width,
        height=button_height + 20
    )
    start_button_frame.place(relx=0.3, rely=0.5, anchor="center")
    
    start_button = ctk.CTkButton(
        start_button_frame,
        text="Start Attendance",
        font=FONT_MEDIUM,
        fg_color="transparent",
        hover_color="#4A86A2",  # Darker shade for hover
        width=button_width,
        height=button_height,
        corner_radius=BUTTON_CORNER_RADIUS,
        command=lambda: switch_page("attendance")
    )
    start_button.place(relx=0.5, rely=0.5, anchor="center")
    
    # Add Student Button
    add_student_frame = ctk.CTkFrame(
        content_frame, 
        fg_color=SECONDARY_COLOR,
        corner_radius=BUTTON_CORNER_RADIUS,
        width=button_width,
        height=button_height + 20
    )
    add_student_frame.place(relx=0.7, rely=0.5, anchor="center")
    
    add_student_button = ctk.CTkButton(
        add_student_frame,
        text="Add Student",
        font=FONT_MEDIUM,
        fg_color="transparent",
        hover_color="#491F69",  # Darker shade for hover
        width=button_width,
        height=button_height,
        corner_radius=BUTTON_CORNER_RADIUS,
        command=lambda: switch_page("add_student")
    )
    add_student_button.place(relx=0.5, rely=0.5, anchor="center")
    
    
    # Status bar at bottom
    status_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#1A1A1A",
        corner_radius=0,
        height=30,
        width=SCREEN_WIDTH
    )
    status_frame.place(relx=0.5, rely=0.97, anchor="center")
    
    status_label = ctk.CTkLabel(
        status_frame,
        text="System Ready",
        font=FONT_SMALL,
        text_color="#888888"
    )
    status_label.place(relx=0.5, rely=0.5, anchor="center")
    
    return main_frame

