import customtkinter as ctk
from gui.home_page import create_home_page
from gui.attendance_page import create_attendance_page
from gui.add_student_page import create_add_student_page

def main():
    
    root = ctk.CTk()
    root.title("Smart Attendance System")
    root.geometry("600x400")
    ctk.set_appearance_mode("dark")
    # Page switching function
    def switch_page(page):
        # Clear the current page
        for widget in root.winfo_children():
            widget.destroy()
        
        # Load the selected page
        if page == "home":
            create_home_page(root, switch_page)
        elif page == "attendance":
            create_attendance_page(root, switch_page)
        elif page == "add_student":
            create_add_student_page(root, switch_page)

    # Start on home page
    switch_page("home")

    root.mainloop()

if __name__ == "__main__":
    main()
