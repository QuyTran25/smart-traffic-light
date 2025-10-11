import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading, time, random

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class SmartTrafficApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚦 Smart Traffic Control System")
        self.geometry("1280x720")
        self.minsize(1100, 650)
        self.running = False
        self.mode = "DEFAULT"

        self.create_layout()

    # ====================== UI Layout ======================
    def create_layout(self):
        # ---------- HEADER ----------
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#1e272e")
        header.pack(fill="x", pady=(0,2))
        ctk.CTkLabel(header, text="HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH",
                     font=("Segoe UI", 22, "bold"), text_color="white").pack(pady=12)

        # ---------- CONTROL BAR ----------
        control_bar = ctk.CTkFrame(self, fg_color="#2d3436", corner_radius=10)
        control_bar.pack(fill="x", padx=10, pady=5)

        self.mode_option = ctk.StringVar(value="DEFAULT")
        ctk.CTkSegmentedButton(control_bar, values=["DEFAULT", "AUTOMATIC"],
                               variable=self.mode_option, font=("Segoe UI", 13, "bold"),
                               command=self.change_mode).pack(side="left", padx=20, pady=10)

        btn_style = dict(font=("Segoe UI", 13, "bold"), width=100, height=35)
        ctk.CTkButton(control_bar, text="▶ RUN", fg_color="#00b894", command=self.start_sim, **btn_style).pack(side="left", padx=8)
        ctk.CTkButton(control_bar, text="⏸ PAUSE", fg_color="#fdcb6e", text_color="black", command=self.pause_sim, **btn_style).pack(side="left", padx=8)
        ctk.CTkButton(control_bar, text="⏹ STOP", fg_color="#d63031", command=self.stop_sim, **btn_style).pack(side="left", padx=8)
        ctk.CTkButton(control_bar, text="🧾 EXPORT LOG", fg_color="#0984e3", command=self.export_log, **btn_style).pack(side="left", padx=8)

        # ---------- MAIN CONTENT ----------
        main = ctk.CTkFrame(self, corner_radius=0)
        main.pack(fill="both", expand=True, padx=10, pady=(0,10))

        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        # ---------- LEFT: Case + Log ----------
        left = ctk.CTkFrame(main, fg_color="#353b48", corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=10)

        left.rowconfigure(0, weight=1)  # Case area
        left.rowconfigure(1, weight=3)  # Log area

        self.create_case(left)   # Case on top
        self.create_log(left)    # Log below

        # ---------- RIGHT: KPI + Info ----------
        right = ctk.CTkFrame(main, corner_radius=12, fg_color="#353b48")
        right.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=10)

        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)

        self.create_kpi(right)
        self.create_vehicle_info(right)

    # =======================================================
    def create_kpi(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#2d3436", corner_radius=10)
        section.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,5))
        ctk.CTkLabel(section, text="📊 KPI Thời gian thực", font=("Segoe UI", 15, "bold")).pack(pady=5)
        self.kpi_labels = {}
        for name in [
            "Độ trễ trung bình (s)", "Chiều dài hàng chờ (xe)", "Lưu lượng (xe/h)",
            "Số lần dừng/xe", "Thời gian chờ tối đa (s)",
            "Chỉ số công bằng", "Thời gian xử lý khẩn cấp (s)"
        ]:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=name, anchor="w", width=220).pack(side="left")
            val = ctk.CTkLabel(row, text="—", text_color="#00cec9")
            val.pack(side="right")
            self.kpi_labels[name] = val

    # =======================================================
    def create_vehicle_info(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#2d3436", corner_radius=10)
        section.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5,10))
        ctk.CTkLabel(section, text="🚘 Số lượng xe", font=("Segoe UI", 15, "bold")).pack(pady=5)
        self.car_labels = {}
        for name in ["Tổng số xe", "Hướng Bắc", "Hướng Đông", "Hướng Nam", "Hướng Tây"]:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=name, anchor="w", width=180).pack(side="left")
            val = ctk.CTkLabel(row, text="0", text_color="#81ecec")
            val.pack(side="right")
            self.car_labels[name] = val

    # =======================================================
    def create_log(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#2d3436", corner_radius=10)
        section.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5,10))
        ctk.CTkLabel(section, text="Sự kiện log", font=("Segoe UI", 15, "bold")).pack(pady=5)
        self.log_box = tk.Text(section, bg="#1e272e", fg="#dcdde1", wrap="word", relief="flat")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)

    # =======================================================
    def create_case(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#2d3436", corner_radius=10)
        section.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,5))
        ctk.CTkLabel(section, text="🧩 Kịch bản ưu tiên (SC1–SC6)", font=("Segoe UI", 15, "bold")).pack(pady=5)
        self.case_box = ttk.Combobox(section, values=[
            "SC1 - Xe ưu tiên từ hướng chính",
            "SC2 - Xe ưu tiên từ hướng nhánh",
            "SC3 - Nhiều xe ưu tiên 2 hướng",
            "SC4 - Báo giả",
            "SC5 - Xe ưu tiên bị kẹt",
            "SC6 - Nhiều xe ưu tiên liên tiếp"
        ])
        self.case_box.pack(fill="x", padx=10, pady=5)
        self.case_box.set("Chọn kịch bản cần xem")

    # =======================================================
    def change_mode(self, value):
        self.mode = value
        self.log(f"Chuyển sang chế độ {value}.")

    def start_sim(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.simulate, daemon=True).start()
        self.log("Bắt đầu mô phỏng.")

    def pause_sim(self):
        self.running = False
        self.log("Tạm dừng mô phỏng.")

    def stop_sim(self):
        self.running = False
        self.log("Đã dừng mô phỏng.")

    def export_log(self):
        with open("simulation_log.txt", "w", encoding="utf-8") as f:
            f.write(self.log_box.get("1.0", "end"))
        self.log("✅ Đã xuất file simulation_log.txt")

    def simulate(self):
        while self.running:
            for k in self.kpi_labels:
                self.kpi_labels[k].configure(text=f"{round(random.uniform(2,9),2)}")
            for c in self.car_labels:
                self.car_labels[c].configure(text=str(random.randint(5,25)))
            self.log("Đã cập nhật dữ liệu KPI và trạng thái đèn.")
            time.sleep(2)

    def log(self, msg):
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
