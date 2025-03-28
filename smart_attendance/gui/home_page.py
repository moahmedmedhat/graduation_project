import customtkinter as ctk
from gui.styles import BACKGROUND_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, TEXT_COLOR, FONT_LARGE, FONT_MEDIUM

def create_home_page(root, switch_page):
    """Creates the home page with navigation buttons."""
    # Set background color
    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)

    # Title Label (Centered)
    title_label = ctk.CTkLabel(root, text="Smart Attendance", font=FONT_LARGE, text_color=TEXT_COLOR)
    title_label.place(relx=0.5, rely=0.15, anchor="center")  # 15% from top

    # Button Size
    button_width = 180
    button_height = 50

    # Start Attendance Button (Left)
    start_button = ctk.CTkButton(root, text="Start Attendance", font=FONT_MEDIUM, fg_color=PRIMARY_COLOR, 
                                 width=button_width, height=button_height,
                                 command=lambda: switch_page("attendance"))
    start_button.place(relx=0.30, rely=0.4, anchor="center")  # 35% from left

    # Add Student Button (Right)
    add_student_button = ctk.CTkButton(root, text="Add Student", font=FONT_MEDIUM, fg_color=SECONDARY_COLOR, 
                                       width=button_width, height=button_height,
                                       command=lambda: switch_page("add_student"))
    add_student_button.place(relx=0.70, rely=0.4, anchor="center")  # 65% from left

