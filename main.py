import tkinter as tk
from tkinter import ttk


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Two Frames Application")
        self.root.geometry("1000x700")
        
        # Configure grid weights for proper resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create the main container
        self.main_container = ttk.Frame(root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure main container grid - devices frame on right gets fixed width
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=4)  # Main frame (larger)
        self.main_container.grid_columnconfigure(1, weight=1)  # Devices frame column
        
        # Create frames
        self.create_main_frame()  # Create main frame (on left)
        self.create_devices_frame()  # Create devices frame (on right)
        
        # Position frames - main frame on left, devices frame on right
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.devices_frame.grid(row=0, column=1, sticky="nsew")
        
        # Fill the device list
        self.fill_device_list()
    
    def create_devices_frame(self):
        # Frame for devices list (on right side, vertical arrangement)
        self.devices_frame = ttk.Frame(self.main_container)
        
        # Create label frame for the border and title
        devices_label_frame = ttk.LabelFrame(self.devices_frame, text="Devices List (58)")
        devices_label_frame.pack(fill="both", expand=True)
        
        # Configure grid weights for the devices frame
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Create canvas with scrollbar for the list
        canvas = tk.Canvas(devices_label_frame)
        scrollbar = ttk.Scrollbar(devices_label_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid the canvas and scrollbar
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure canvas grid weights
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Create a frame to hold the device buttons
        self.devices_button_frame = ttk.Frame(self.scrollable_frame)
        self.devices_button_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid for device buttons
        self.devices_button_frame.grid_columnconfigure(0, weight=1)

    def fill_device_list(self):
        # Add 58 devices to the list
        for i in range(1, 59):
            device_btn = ttk.Button(
                self.devices_button_frame,
                text=f"Device {i}",
                width=15,
                command=lambda dev=i: self.select_device(dev)
            )
            device_btn.grid(row=i-1, column=0, pady=1, sticky="ew")
    
    def select_device(self, device_number):
        print(f"Selected device: {device_number}")
        # Update the main frame to show device details
        self.update_main_frame_for_device(device_number)
    
    def update_main_frame_for_device(self, device_number):
        # Clear current content of main frame
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Add content specific to the selected device
        ttk.Label(
            self.main_content_frame, 
            text=f"Main Window - Device {device_number} Details",
            font=("Helvetica", 14, "bold")
        ).pack(pady=20)
        
        ttk.Label(
            self.main_content_frame,
            text=f"This is the main window showing detailed information for Device {device_number}.\n\nYou can add charts, status information, controls,\nand other device-specific functionality here.",
            justify="center"
        ).pack(pady=10)
        
        # Create a notebook (tabbed interface) for different types of information
        notebook = ttk.Notebook(self.main_content_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Status tab
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Status")
        
        # Create a frame for status indicators
        status_frame = ttk.LabelFrame(status_tab, text="Device Status")
        status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add some status indicators
        ttk.Label(status_frame, text="Connection:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        connection_status = ttk.Label(status_frame, text="Connected", foreground="green")
        connection_status.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(status_frame, text="Signal:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        signal_status = ttk.Label(status_frame, text="Strong", foreground="green")
        signal_status.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(status_frame, text="Battery:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        battery_status = ttk.Label(status_frame, text="85%", foreground="green")
        battery_status.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Controls tab
        controls_tab = ttk.Frame(notebook)
        notebook.add(controls_tab, text="Controls")
        
        controls_frame = ttk.LabelFrame(controls_tab, text="Device Controls")
        controls_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add control buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Refresh", command=lambda: print("Refresh clicked")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Configure", command=lambda: print("Configure clicked")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Restart", command=lambda: print("Restart clicked")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Disconnect", command=lambda: print("Disconnect clicked")).pack(side="left", padx=5)
        
        # Add a progress bar to simulate some operation
        progress_frame = ttk.Frame(controls_tab)
        progress_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(progress_frame, text="Operation Progress:").pack(anchor="w")
        progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=300)
        progress_bar.pack(pady=5)
        progress_bar.start(10)
        
        # When a device is selected, stop the progress bar animation
        self.root.after(2000, lambda: progress_bar.stop())

    def create_main_frame(self):
        # Main frame that takes most of the space (on left)
        self.main_frame = ttk.LabelFrame(self.main_container, text="Main Window")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create a frame for main content
        self.main_content_frame = ttk.Frame(self.main_frame)
        self.main_content_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid weights
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        
        # Initially display welcome message
        self.show_welcome_message()
    
    def show_welcome_message(self):
        # Clear current content
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Add welcome content
        ttk.Label(
            self.main_content_frame,
            text="Welcome to Device Management System",
            font=("Helvetica", 16, "bold")
        ).pack(pady=30)
        
        ttk.Label(
            self.main_content_frame,
            text="Please select a device from the list on the right to view its details and controls.",
            font=("Helvetica", 12)
        ).pack(pady=20)
        
        # Add an image placeholder or logo if needed
        # For now, just a simple rectangle as placeholder
        placeholder = tk.Canvas(self.main_content_frame, width=300, height=200, bg="lightgray")
        placeholder.create_text(150, 100, text="System Dashboard", fill="darkgray", font=("Helvetica", 14))
        placeholder.pack(pady=20)
        
        # Add some statistics
        stats_frame = ttk.Frame(self.main_content_frame)
        stats_frame.pack(pady=20)
        
        # Create a few labels to simulate statistics
        ttk.Label(stats_frame, text="Total Devices: 58", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="Online: 42", foreground="green", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="Offline: 16", foreground="red", font=("Helvetica", 10, "bold")).pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()