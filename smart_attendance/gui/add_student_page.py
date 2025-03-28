import customtkinter as ctk
from gui.styles import BACKGROUND_COLOR, TEXT_COLOR, FONT_LARGE

def create_add_student_page(root, switch_page):
    """Creates the add student page."""
    ctk.set_appearance_mode("dark")
    root.configure(bg=BACKGROUND_COLOR)

    # Title Label
    title_label = ctk.CTkLabel(root, text="Add Student", font=FONT_LARGE, text_color=TEXT_COLOR)
    title_label.place(relx=0.5, rely=0.15, anchor="center")

    # Back Button
    back_button = ctk.CTkButton(root, text="Back", command=lambda: switch_page("home"))
    back_button.place(relx=0.5, rely=0.8, anchor="center")

