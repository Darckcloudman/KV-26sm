import tkinter as tk
from tkinter import ttk


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Двухфреймовое приложение")
        self.root.geometry("1280x720")  # Установка размера окна 1280x720
        self.root.minsize(1280, 720)  # Минимальный размер окна
        
        # Настройка весов сетки для правильного изменения размеров
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Создание основного контейнера
        self.main_container = ttk.Frame(root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Настройка сетки основного контейнера
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=0)  # Левый фрейм (фиксированная ширина)
        self.main_container.grid_columnconfigure(1, weight=1)  # Правый фрейм (расширяемый)
        
        # Создание фреймов
        self.create_devices_frame()  # Создание фрейма устройств (слева)
        self.create_main_frame()  # Создание основного фрейма (справа)
        
        # Размещение фреймов - фрейм устройств слева, основной фрейм справа
        self.devices_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 0), pady=0, width=260)  # Ширина 260px
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)  # Оставшееся пространство
        
        # Заполнение списка устройств
        self.fill_device_list()
    
    def create_devices_frame(self):
        # Фрейм для списка устройств (слева, ширина 260px)
        self.devices_frame = ttk.Frame(self.main_container, width=260)
        self.devices_frame.pack_propagate(False)  # Сохранять заданный размер
        
        # Создание рамки с заголовком для границы и названия
        devices_label_frame = ttk.LabelFrame(self.devices_frame, text="Список устройств (58)")
        devices_label_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Настройка весов сетки для фрейма устройств
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Создание холста с полосой прокрутки для списка
        canvas = tk.Canvas(devices_label_frame)
        scrollbar = ttk.Scrollbar(devices_label_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Размещение холста и полосы прокрутки по сетке
        canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0))
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Настройка весов сетки холста
        devices_label_frame.grid_rowconfigure(0, weight=1)
        devices_label_frame.grid_columnconfigure(0, weight=1)
        
        # Создание фрейма для размещения кнопок устройств
        self.devices_button_frame = ttk.Frame(self.scrollable_frame)
        self.devices_button_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Настройка сетки для кнопок устройств
        self.devices_button_frame.grid_columnconfigure(0, weight=1)


    def fill_device_list(self):
        # Добавление 58 устройств в список
        for i in range(1, 59):
            device_btn = ttk.Button(
                self.devices_button_frame,
                text=f"Устройство {i}",
                width=20,
                command=lambda dev=i: self.select_device(dev)
            )
            device_btn.grid(row=i-1, column=0, pady=1, sticky="ew")
    
    def select_device(self, device_number):
        print(f"Выбрано устройство: {device_number}")
        # Обновление основного фрейма для отображения информации об устройстве
        self.update_main_frame_for_device(device_number)
    
    def update_main_frame_for_device(self, device_number):
        # Очистка текущего содержимого основного фрейма
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Добавление контента, специфичного для выбранного устройства
        header_frame = ttk.Frame(self.main_content_frame)
        header_frame.pack(fill="x", pady=(10, 20))
        
        ttk.Label(
            header_frame, 
            text=f"Главное окно — Детали устройства {device_number}",
            font=("Helvetica", 14, "bold")
        ).pack()
        
        # Блок подробной информации (примерно 300px высоты)
        info_frame = ttk.LabelFrame(self.main_content_frame, text="Подробная информация")
        info_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        ttk.Label(
            info_frame,
            text=f"Здесь отображается подробная информация об Устройстве {device_number}.\n\nЗдесь можно добавить графики, информацию о состоянии, элементы управления\nи другую специфичную для устройства функциональность.",
            justify="center"
        ).pack(pady=20, expand=True)
        
        # Блок "Состояние / Управление" (примерно 120px высоты)
        controls_frame = ttk.LabelFrame(self.main_content_frame, text="Состояние / Управление")
        controls_frame.pack(fill="x", padx=10, pady=(0, 10), height=120)
        controls_frame.pack_propagate(False)  # Сохранять заданную высоту
        
        # Создание интерфейса с вкладками для разных типов информации
        notebook = ttk.Notebook(controls_frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Вкладка состояния
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Состояние")
        
        # Создание фрейма для индикаторов состояния
        status_inner_frame = ttk.Frame(status_tab)
        status_inner_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Добавление некоторых индикаторов состояния
        ttk.Label(status_inner_frame, text="Подключение:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        connection_status = ttk.Label(status_inner_frame, text="Подключено", foreground="green")
        connection_status.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_inner_frame, text="Сигнал:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        signal_status = ttk.Label(status_inner_frame, text="Сильный", foreground="green")
        signal_status.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_inner_frame, text="Батарея:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        battery_status = ttk.Label(status_inner_frame, text="85%", foreground="green")
        battery_status.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
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
        # Основной фрейм, занимающий большую часть пространства (справа)
        self.main_frame = ttk.LabelFrame(self.main_container, text="")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        
        # Настройка весов сетки
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Создание фрейма для основного содержимого
        self.main_content_frame = ttk.Frame(self.main_frame)
        self.main_content_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Настройка весов сетки
        self.main_content_frame.grid_rowconfigure(0, weight=0)  # Заголовок
        self.main_content_frame.grid_rowconfigure(1, weight=1)  # Блок подробной информации
        self.main_content_frame.grid_rowconfigure(2, weight=0)  # Блок управления
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        
        # Изначально отобразить приветственное сообщение
        self.show_welcome_message()
    
    def show_welcome_message(self):
        # Очистка текущего содержимого
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Добавление приветственного контента
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
        
        # Добавление временного изображения или логотипа при необходимости
        # Пока просто простой прямоугольник в качестве заглушки
        placeholder = tk.Canvas(self.main_content_frame, width=300, height=200, bg="lightgray")
        placeholder.create_text(150, 100, text="Главная панель", fill="darkgray", font=("Helvetica", 14))
        placeholder.pack(pady=20)
        
        # Добавление статистики
        stats_frame = ttk.Frame(self.main_content_frame)
        stats_frame.pack(pady=20)
        
        # Создание нескольких меток для имитации статистики
        ttk.Label(stats_frame, text="Всего устройств: 58", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="В сети: 42", foreground="green", font=("Helvetica", 10, "bold")).pack(pady=5)
        ttk.Label(stats_frame, text="Не в сети: 16", foreground="red", font=("Helvetica", 10, "bold")).pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()