import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import requests
from PIL import Image
from io import BytesIO
import os
from locales import LOCALES
from downloader import Downloader
from utils import send_system_notification, get_default_download_path
import threading

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT Downloader Pro")
        self.geometry("700x800")
        self.minsize(500, 700)
        
        # Данные
        self.current_lang = "ru"
        self.save_path = get_default_download_path()
        self.downloader = Downloader(self.on_progress, self.on_log)
        self.raw_image = None # Храним исходное фото для ресайза
        self.is_downloading = False

        # Сетка
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(9, weight=1) # Текстовое поле логов растягивается

        self.setup_ui()
        self.setup_menu()
        self.update_ui_texts()
        
        # Привязка изменения окна к ресайзу превью
        self.bind("<Configure>", self.on_window_resize)

    def setup_ui(self):
        # 1. Поле ввода
        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.url_frame, height=40)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.search_btn = ctk.CTkButton(self.url_frame, text="🔍", width=50, height=40, command=self.fetch_preview)
        self.search_btn.grid(row=0, column=1)

        # 2. Превью (теперь в контейнере)
        self.preview_frame = ctk.CTkFrame(self, fg_color="black", height=200)
        self.preview_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.preview_frame.grid_propagate(False) # Чтобы фрейм не раздувался
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="")
        self.preview_label.grid(row=0, column=0)

        self.video_title = ctk.CTkLabel(self, text="", font=("Arial", 13, "bold"), wraplength=400)
        self.video_title.grid(row=2, column=0, padx=20, pady=5)

        # 3. Путь
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)
        self.path_display = ctk.CTkLabel(self.path_frame, text="", font=("Arial", 11), anchor="w")
        self.path_display.grid(row=0, column=0, padx=10, sticky="ew")
        self.path_btn = ctk.CTkButton(self.path_frame, text="...", width=80, command=self.change_save_path)
        self.path_btn.grid(row=0, column=1, padx=5, pady=5)

        # 4. Настройки
        self.ask_checkbox = ctk.CTkCheckBox(self, text="", font=("Arial", 11))
        self.ask_checkbox.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1), weight=1)
        self.res_menu = ctk.CTkOptionMenu(self.control_frame, values=["1080p", "720p", "480p", "360p"])
        self.res_menu.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.ext_menu = ctk.CTkOptionMenu(self.control_frame, values=["mp4", "mkv", "mp3"])
        self.ext_menu.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # 5. Кнопка скачивания
        self.download_btn = ctk.CTkButton(self, text="", height=45, fg_color="#c4302b", hover_color="#a82925", command=self.start_download)
        self.download_btn.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        # 6. Прогресс
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11))
        self.status_label.grid(row=8, column=0, pady=(0, 10))

        # 7. Логи
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.log_box.grid(row=9, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def setup_menu(self):
        self.menu_bar = tk.Menu(self)
        # Настройки
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        
        # Языки
        self.lang_sub = tk.Menu(self.settings_menu, tearoff=0)
        for k in LOCALES.keys():
            self.lang_sub.add_command(label=k, command=lambda l=k: self.change_language(l))
        
        # Темы (Исправлено)
        self.theme_sub = tk.Menu(self.settings_menu, tearoff=0)
        themes = ["blue", "dark-blue", "green"]
        for t in themes:
            self.theme_sub.add_command(label=t.capitalize(), command=lambda theme=t: self.update_theme(theme))
        
        self.settings_menu.add_cascade(menu=self.lang_sub)
        self.settings_menu.add_cascade(menu=self.theme_sub)
        self.menu_bar.add_cascade(menu=self.settings_menu)
        
        # Справка
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(command=self.show_help)
        self.help_menu.add_command(command=self.show_about)
        self.menu_bar.add_cascade(menu=self.help_menu)
        
        self.config(menu=self.menu_bar)

    def update_theme(self, theme_name):
        ctk.set_default_color_theme(theme_name)
        messagebox.showinfo("Theme", "Theme applied! Some elements may update after restart, but colors changed.")

    def on_window_resize(self, event):
        # Вызывается при изменении размера окна
        if self.raw_image:
            # Динамически меняем размер превью под ширину окна
            new_w = max(100, self.winfo_width() - 60)
            new_h = int(new_w * 9 / 16)
            self.preview_frame.configure(height=new_h)
            img_ctk = ctk.CTkImage(light_image=self.raw_image, dark_image=self.raw_image, size=(new_w, new_h))
            self.preview_label.configure(image=img_ctk)

    def fetch_preview(self):
        url = self.url_entry.get()
        if not url: return
        def run():
            info = self.downloader.get_info(url)
            if info:
                self.video_title.configure(text=info.get('title'))
                res = requests.get(info.get('thumbnail'))
                self.raw_image = Image.open(BytesIO(res.content))
                self.on_window_resize(None) # Обновить сразу
        threading.Thread(target=run, daemon=True).start()

    def on_progress(self, d):
        if d['status'] == 'downloading':
            try:
                p_str = d.get('_percent_str', '0%')
                p = float(self.downloader.strip_ansi(p_str).replace('%',''))
                self.progress_bar.set(p/100)
                self.status_label.configure(text=f"{p_str} | {d.get('_speed_str')} | ETA: {d.get('_eta_str')}")
            except: pass
        elif d['status'] == 'finished':
            # Ожидаем конца пост-обработки
            if 'tmpfilename' not in d:
                self.is_downloading = False
                self.progress_bar.set(1)
                self.status_label.configure(text="Complete!")
                send_system_notification("YT Downloader", LOCALES[self.current_lang]["success"])

    def start_download(self):
        url = self.url_entry.get()
        if not url or self.is_downloading: return
        
        path = self.save_path
        if self.ask_checkbox.get():
            path = filedialog.askdirectory()
            if not path: return

        self.is_downloading = True
        ext = self.ext_menu.get()
        res = self.res_menu.get().replace('p', '')
        fmt = f"bestvideo[height<={res}]+bestaudio/best" if ext != "mp3" else "bestaudio/best"
        
        opts = {'format': fmt, 'ext': ext, 'outtmpl': os.path.join(path, '%(title)s.%(ext)s')}
        self.downloader.download(url, opts)

    def on_log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def change_language(self, l):
        self.current_lang = l
        self.update_ui_texts()

    def update_ui_texts(self):
        t = LOCALES[self.current_lang]
        self.download_btn.configure(text=t["download_btn"])
        self.status_label.configure(text=t["status_idle"])
        self.path_btn.configure(text=t["path_btn"])
        self.ask_checkbox.configure(text=t["always_ask_chk"])
        self.path_display.configure(text=f"{t['current_path']} {self.save_path}")
        self.menu_bar.entryconfigure(1, label=t["menu_settings"])
        self.menu_bar.entryconfigure(2, label=t["menu_help"])
        self.settings_menu.entryconfigure(0, label=t["menu_lang"])
        self.settings_menu.entryconfigure(1, label=t["menu_theme"])
        self.help_menu.entryconfigure(0, label=t["help_btn"])
        self.help_menu.entryconfigure(1, label=t["about_btn"])

    def change_save_path(self):
        p = filedialog.askdirectory()
        if p: self.save_path = p; self.update_ui_texts()

    def show_help(self): messagebox.showinfo("Help", LOCALES[self.current_lang]["help_text"])
    def show_about(self): messagebox.showinfo("About", LOCALES[self.current_lang]["about_text"])

if __name__ == "__main__":
    app = App()
    app.mainloop()