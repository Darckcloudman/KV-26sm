import tkinter as tk
from tkinter import ttk


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("KV-26cm")
        self.root.geometry("1152x648")  # Уменьшено на 10%
        self.root.minsize(1152, 648)    # Минимальный размер
        
        # Настройка весов сетки
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Основной контейнер
        self.main_container = ttk.Frame(root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Разделение: 15% и 85%
        self.main_container.grid_columnconfigure(0, weight=15)
        self.main_container.grid_columnconfigure(1, weight=85)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Создание фреймов
        self.create_devices_frame()
        self.create_main_frame()
        
        # Размещение
        self.devices_frame.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Заполнение списка
        self.fill_device_list()
    
    def create_devices_frame(self):
        self.devices_frame = ttk.Frame(self.main_container)
        
        # Рамка с заголовком
        devices_label_frame = ttk.LabelFrame(self.devices_frame, text="Список (57)")
        devices_label_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Сетка
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Холст с прокруткой
        canvas = tk.Canvas(devices_label_frame)
        scrollbar = ttk.Scrollbar(devices_label_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        canvas.grid(row=0, column=0, sticky="nsew", padx=(1, 0))
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Весы
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Фрейм для кнопок
        self.devices_button_frame = ttk.Frame(self.scrollable_frame)
        self.devices_button_frame.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Вес: колонка 0 — растягивается, кнопка — прижата к правому краю
        self.devices_button_frame.grid_columnconfigure(0, weight=1)  # Свободное пространство слева
        self.devices_button_frame.grid_columnconfigure(1, weight=0)  # Под кнопку
    
    def fill_device_list(self):
        # Первая кнопка — прижата к правому краю
        first_btn = ttk.Button(
            self.devices_button_frame,
            text="Сервера O&M SGRE",
            width=20  # Фиксированная ширина для красоты
        )
        first_btn.grid(row=0, column=1, pady=1, padx=(0, 2), sticky="e")  # Прижата к правому краю

        # Остальные кнопки
        for i in range(1, 58):
            device_btn = ttk.Button(
                self.devices_button_frame,
                text=f"Устройство {i}",
                width=20
            )
            device_btn.grid(row=i, column=1, pady=1, padx=(0, 2), sticky="e")  # Прижаты к правому краю
    
    def select_device(self, device_number):
        print(f"Выбрано устройство: {device_number}")
        self.update_main_frame_for_device(device_number)
    
    def update_main_frame_for_device(self, device_number):
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        header_frame = ttk.Frame(self.main_content_frame)
        header_frame.pack(fill="x", pady=(10, 20))
        
        ttk.Label(
            header_frame, 
            text=f"Главное окно — Детали устройства {device_number}",
            font=("Helvetica", 14, "bold")
        ).pack()
        
        info_frame = ttk.LabelFrame(self.main_content_frame, text="Подробная информация")
        info_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        ttk.Label(
            info_frame,
            text=f"Здесь отображается подробная информация об Устройстве {device_number}.\n\nЗдесь можно добавить графики, информацию о состоянии, элементы управления\nи другую специфичную для устройства функциональность.",
            justify="center"
        ).pack(pady=20, expand=True)
        
        controls_frame = ttk.LabelFrame(self.main_content_frame, text="Состояние / Управление")
        controls_frame.pack(fill="x", padx=10, pady=(0, 10), height=120)
        controls_frame.pack_propagate(False)
        
        notebook = ttk.Notebook(controls_frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Вкладка состояния
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Состояние")
        
        status_inner_frame = ttk.Frame(status_tab)
        status_inner_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Label(status_inner_frame, text="Подключение:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_inner_frame, text="Подключено", foreground="green").grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_inner_frame, text="Сигнал:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_inner_frame, text="Сильный", foreground="green").grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_inner_frame, text="Батарея:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_inner_frame, text="85%", foreground="green").grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Вкладка управления
        controls_tab = ttk.Frame(notebook)
        notebook.add(controls_tab, text="Управление")
        
        btn_frame = ttk.Frame(controls_tab)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Обновить", command=lambda: print("Нажата кнопка Обновить")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Настроить", command=lambda: print("Нажата кнопка Настроить")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Перезагрузить", command=lambda: print("Нажата кнопка Перезагрузить")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отключить", command=lambda: print("Нажата кнопка Отключить")).pack(side="left", padx=5)

    def create_main_frame(self):
        self.main_frame = ttk.LabelFrame(self.main_container, text="")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.main_content_frame = ttk.Frame(self.main_frame)
        self.main_content_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.main_content_frame.grid_rowconfigure(0, weight=0)
        self.main_content_frame.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        

        self.show_welcome_message()
    
    def show_welcome_message(self):
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(
            self.main_content_frame,
            text="Добро пожаловать в Систему управления устройствами",
            font=("Helvetica", 16, "bold")
        ).pack(pady=30)
        
        ttk.Label(
            self.main_content_frame,
            text="Пожалуйста, выберите устройство из списка слева, чтобы просмотреть его данные и элементы управления.",
            font=("Helvetica", 12)
        ).pack(pady=20)
        
        placeholder = tk.Canvas(self.main_content_frame, width=300, height=200, bg="lightgray")
        placeholder.create_text(150, 100, text="Главная панель", fill="darkgray", font=("Helvetica", 14))
        placeholder.pack(pady=20)
        
        stats_frame = ttk.Frame(self.main_content_frame)
        stats_frame.pack(pady=20)
        
        ttk.Label(stats_frame, text="Всего устройств: 57", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="В сети: 42", foreground="green", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="Не в сети: 15", foreground="red", font=("Helvetica", 10, "bold")).pack(pady=5)


def show_splash_screen():
    splash = tk.Toplevel()
    splash.title("")
    splash.geometry("400x200")
    splash.configure(bg="white")
    splash.overrideredirect(True)
    
    splash.update_idletasks()
    x = (splash.winfo_screenwidth() // 2) - (400 // 2)
    y = (splash.winfo_screenheight() // 2) - (200 // 2)
    splash.geometry(f"+{x}+{y}")
    
    label = tk.Label(
        splash,
        text="KV-26cm",
        font=("Helvetica", 24, "bold"),
        bg="white",
        fg="black"
    )
    label.pack(expand=True)
    
    def close_splash():
        splash.destroy()
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    
    splash.after(5000, close_splash)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    show_splash_screen()
    root.mainloop()