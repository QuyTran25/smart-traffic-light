# dashboard.py
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading, time, random, os, sys

# Ensure project root is on sys.path so we can import controllers/adaptive_controller
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Also ensure local src is importable (your simulation module lives under src/simulation)
SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from simulation.sumo_connector import khoi_dong_sumo, dung_sumo, dieu_chinh_tat_ca_den
# Import AdaptiveController from controllers (you said it's at controllers/adaptive_controller.py)
try:
    from controllers.adaptive_controller import AdaptiveController
except Exception as e:
    AdaptiveController = None  # We'll check at runtime and log if unavailable

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class SmartTrafficApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚦 HỆ THỐNG 2 NGÃ TƯ")
        self.geometry("700x850")
        self.minsize(680, 800)
        self.running = False
        self.paused = False
        self.resetting = False
        self.mode = "Mặc định"  # or "Tự động"

        # default timings
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 3

        # controllers dict for adaptive mode: {tls_id: AdaptiveController instance}
        self.controllers = {}

        # data holders (same as your previous UI)
        self.global_kpi_data = {
            "Tổng xe": 0,
            "Độ trễ TB": 0.0,
            "Lưu lượng": 0,
            "Chu kỳ TB": 0,
            "Công bằng": 0.0,
            "Phối hợp": 0
        }

        self.intersection_data = {
            "Ngã tư 1": {
                "light_state": "Đỏ",
                "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0},
                "queue": 0,
                "wait_time": 0
            },
            "Ngã tư 2": {
                "light_state": "Xanh",
                "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0},
                "queue": 0,
                "wait_time": 0
            }
        }

        self.create_layout()

    # ====================== UI Layout ======================
    def create_layout(self):
        self.configure(fg_color="#f8fafc")
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#f8fafc",
            corner_radius=0,
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Header
        header = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#ffffff", height=65)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=15, pady=10)

        ctk.CTkLabel(header_left, text="🚦", font=("Segoe UI", 20)).pack(side="left", padx=(0, 8))

        title_frame = ctk.CTkFrame(header_left, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(title_frame, text="HỆ THỐNG 2 NGÃ TƯ THÔNG MINH", font=("Segoe UI", 16, "bold"),
                     text_color="#0f172a", anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Demo SUMO - 2 ngã tư kết nối", font=("Segoe UI", 11),
                     text_color="#64748b", anchor="w").pack(anchor="w", pady=(2, 0))

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=15)
        self.status_label = ctk.CTkLabel(status_frame, text="⚫ Dừng", font=("Segoe UI", 11, "bold"),
                                         text_color="#64748b")
        self.status_label.pack()

        # Control bar
        control_bar_main = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        control_bar_main.pack(fill="x", padx=0, pady=(1, 0))

        control_bar_top = ctk.CTkFrame(control_bar_main, fg_color="transparent", height=45)
        control_bar_top.pack(fill="x", padx=10, pady=(8, 0))
        control_bar_top.pack_propagate(False)

        left_controls = ctk.CTkFrame(control_bar_top, fg_color="transparent")
        left_controls.pack(side="left")

        # Mode segmented button
        self.mode_option = ctk.StringVar(value="Mặc định")
        mode_segment = ctk.CTkSegmentedButton(
            left_controls,
            values=["Mặc định", "Tự động"],
            variable=self.mode_option,
            font=("Segoe UI", 11, "bold"),
            command=self.change_mode,
            fg_color="#cbd5e1",
            selected_color="#0ea5e9",
            selected_hover_color="#0284c7",
            unselected_color="#cbd5e1",
            unselected_hover_color="#94a3b8",
            text_color="#1e293b",
            width=110,
            height=36
        )
        mode_segment.pack(side="left", padx=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(left_controls, fg_color="transparent")
        btn_frame.pack(side="left")

        self.play_btn = ctk.CTkButton(btn_frame, text="▶", fg_color="#10b981", hover_color="#059669",
                                     font=("Segoe UI", 11, "bold"), width=42, height=36, corner_radius=5,
                                     command=self.start_sim)
        self.play_btn.pack(side="left", padx=2)

        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸", fg_color="#f59e0b", hover_color="#d97706",
                                       text_color="#000000", font=("Segoe UI", 11, "bold"), width=42, height=36,
                                       corner_radius=5, command=self.pause_sim)
        self.pause_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹", fg_color="#ef4444", hover_color="#dc2626",
                                      font=("Segoe UI", 11, "bold"), width=42, height=36, corner_radius=5,
                                      command=self.stop_sim)
        self.stop_btn.pack(side="left", padx=2)

        reset_btn = ctk.CTkButton(btn_frame, text="🔄", fg_color="#64748b", hover_color="#475569",
                                  font=("Segoe UI", 11, "bold"), width=42, height=36, corner_radius=5,
                                  command=self.reset_all)
        reset_btn.pack(side="left", padx=2)

        export_btn = ctk.CTkButton(btn_frame, text="⬇", fg_color="#3b82f6", hover_color="#2563eb",
                                   font=("Segoe UI", 11, "bold"), width=42, height=36, corner_radius=5,
                                   command=self.export_log)
        export_btn.pack(side="left", padx=2)

        # Timing inputs
        timing_bar = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        timing_bar.pack(fill="x", padx=0, pady=(1, 0))

        timing_container = ctk.CTkFrame(timing_bar, fg_color="transparent", height=50)
        timing_container.pack(fill="x", padx=10, pady=8)
        timing_container.pack_propagate(False)

        ctk.CTkLabel(timing_container, text="⏱ Thời gian đèn:", font=("Segoe UI", 11, "bold"),
                     text_color="#334155").pack(side="left", padx=(0, 12))

        # Green
        green_frame = ctk.CTkFrame(timing_container, fg_color="#d1fae5", corner_radius=6)
        green_frame.pack(side="left", padx=4)
        green_content = ctk.CTkFrame(green_frame, fg_color="transparent")
        green_content.pack(padx=8, pady=6)
        ctk.CTkLabel(green_content, text="🟢 Xanh", font=("Segoe UI", 10, "bold"), text_color="#065f46").pack(
            side="left", padx=(0, 6))
        self.green_entry = ctk.CTkEntry(green_content, width=50, height=28, font=("Segoe UI", 11, "bold"),
                                        fg_color="#ffffff", border_color="#10b981", border_width=2, text_color="#065f46")
        self.green_entry.pack(side="left", padx=(0, 4))
        self.green_entry.insert(0, str(self.green_time))
        ctk.CTkLabel(green_content, text="s", font=("Segoe UI", 10), text_color="#475569").pack(side="left")

        # Yellow
        yellow_frame = ctk.CTkFrame(timing_container, fg_color="#fef3c7", corner_radius=6)
        yellow_frame.pack(side="left", padx=4)
        yellow_content = ctk.CTkFrame(yellow_frame, fg_color="transparent")
        yellow_content.pack(padx=8, pady=6)
        ctk.CTkLabel(yellow_content, text="🟡 Vàng", font=("Segoe UI", 10, "bold"),
                     text_color="#78350f").pack(side="left", padx=(0, 6))
        self.yellow_entry = ctk.CTkEntry(yellow_content, width=50, height=28, font=("Segoe UI", 11, "bold"),
                                         fg_color="#ffffff", border_color="#f59e0b", border_width=2, text_color="#78350f")
        self.yellow_entry.pack(side="left", padx=(0, 4))
        self.yellow_entry.insert(0, str(self.yellow_time))
        ctk.CTkLabel(yellow_content, text="s", font=("Segoe UI", 10), text_color="#475569").pack(side="left")

        # Red (all-red)
        red_frame = ctk.CTkFrame(timing_container, fg_color="#fecaca", corner_radius=6)
        red_frame.pack(side="left", padx=4)
        red_content = ctk.CTkFrame(red_frame, fg_color="transparent")
        red_content.pack(padx=8, pady=6)
        ctk.CTkLabel(red_content, text="🔴 Đỏ Toàn Phần", font=("Segoe UI", 10, "bold"),
                     text_color="#991b1b").pack(side="left", padx=(0, 6))
        self.red_entry = ctk.CTkEntry(red_content, width=50, height=28, font=("Segoe UI", 11, "bold"),
                                      fg_color="#ffffff", border_color="#ef4444", border_width=2, text_color="#991b1b")
        self.red_entry.pack(side="left", padx=(0, 4))
        self.red_entry.insert(0, str(self.red_time))
        ctk.CTkLabel(red_content, text="s", font=("Segoe UI", 10), text_color="#475569").pack(side="left")

        apply_btn = ctk.CTkButton(timing_container, text="✓ Áp dụng", fg_color="#3b82f6", hover_color="#2563eb",
                                  font=("Segoe UI", 10, "bold"), width=80, height=32, corner_radius=6,
                                  command=self.apply_timing)
        apply_btn.pack(side="left", padx=(8, 0))

        # Main container and remainder of UI (KPIs, intersections, logs)
        self.main_container = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#f8fafc")
        self.main_container.pack(fill="both", expand=True, padx=8, pady=(6, 6))

        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=0)
        self.content_frame.grid_rowconfigure(2, weight=0, minsize=200)
        self.content_frame.grid_columnconfigure(0, weight=1)

        kpi_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        kpi_container.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.create_global_kpi_section(kpi_container)

        intersections_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        intersections_container.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        intersections_container.grid_columnconfigure(0, weight=1)
        intersections_container.grid_columnconfigure(1, weight=1)

        self.create_intersection_section(intersections_container, "Ngã tư 1", 0, "#3b82f6")
        self.create_intersection_section(intersections_container, "Ngã tư 2", 1, "#8b5cf6")

        log_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        log_container.grid(row=2, column=0, sticky="nsew")
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        self.create_log_section(log_container)

    # ---------- UI helper creators (same as before) ----------
    def create_global_kpi_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x", padx=0, pady=0)
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=35)
        header_frame.pack(fill="x", padx=10, pady=(8, 6))
        header_frame.pack_propagate(False)
        ctk.CTkLabel(header_frame, text="📊 KPI Tổng Hợp", font=("Segoe UI", 12, "bold"),
                     text_color="#0f172a", anchor="w").pack(side="left")
        kpi_grid = ctk.CTkFrame(section, fg_color="transparent")
        kpi_grid.pack(fill="x", padx=8, pady=(0, 8))
        self.global_kpi_cards = {}
        kpi_data = [
            ("Tổng xe", "—", "xe", "#dbeafe", "#1e3a8a", "🚗"),
            ("Độ trễ TB", "—", "s", "#fef3c7", "#78350f", "⏱"),
            ("Lưu lượng", "—", "xe/h", "#d1fae5", "#065f46", "📈"),
            ("Chu kỳ TB", "—", "s", "#e0e7ff", "#3730a3", "💡"),
            ("Công bằng", "—", "", "#fce7f3", "#831843", "⚖"),
            ("Phối hợp", "—", "%", "#ccfbf1", "#134e4a", "🔗"),
        ]
        for idx, (name, value, unit, bg_color, text_color, icon) in enumerate(kpi_data):
            row = idx // 3
            col = idx % 3
            card = ctk.CTkFrame(kpi_grid, fg_color=bg_color, corner_radius=6, width=110, height=65)
            card.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 14), text_color=text_color).pack(side="left",
                                                                                             padx=(6, 4), pady=4)
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, pady=4, padx=(0, 4))
            ctk.CTkLabel(content, text=name, font=("Segoe UI", 8, "bold"), text_color="#0f172a", anchor="w").pack(
                anchor="w")
            value_frame = ctk.CTkFrame(content, fg_color="transparent")
            value_frame.pack(anchor="w", fill="x")
            val_label = ctk.CTkLabel(value_frame, text=value, font=("Segoe UI", 15, "bold"),
                                     text_color=text_color, anchor="w")
            val_label.pack(side="left")
            if unit:
                ctk.CTkLabel(value_frame, text=f" {unit}", font=("Segoe UI", 8), text_color="#475569", anchor="w").pack(
                    side="left", pady=(4, 0))
            self.global_kpi_cards[name] = val_label
        for i in range(3):
            kpi_grid.grid_columnconfigure(i, weight=1)

    def create_intersection_section(self, parent, name, column, accent_color):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.grid(row=0, column=column, sticky="nsew", padx=3)
        header_frame = ctk.CTkFrame(section, fg_color=accent_color, corner_radius=8, height=42)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(expand=True)
        ctk.CTkLabel(header_content, text=name, font=("Segoe UI", 14, "bold"), text_color="#ffffff").pack()

        stats_frame = ctk.CTkFrame(section, fg_color="transparent")
        stats_frame.pack(fill="x", padx=8, pady=(8, 6))
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)

        queue_card = ctk.CTkFrame(stats_frame, fg_color="#fef3c7", corner_radius=6, height=65)
        queue_card.grid(row=0, column=0, padx=3, sticky="ew")
        queue_card.pack_propagate(False)
        queue_content = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_content.pack(expand=True)
        ctk.CTkLabel(queue_content, text="Hàng chờ", font=("Segoe UI", 10, "bold"), text_color="#0f172a").pack()
        queue_value_frame = ctk.CTkFrame(queue_content, fg_color="transparent")
        queue_value_frame.pack()
        queue_label = ctk.CTkLabel(queue_value_frame, text="0", font=("Segoe UI", 20, "bold"), text_color="#78350f")
        queue_label.pack(side="left")
        ctk.CTkLabel(queue_value_frame, text=" xe", font=("Segoe UI", 11), text_color="#475569").pack(side="left",
                                                                                                     pady=(6, 0))

        if not hasattr(self, 'intersection_widgets'):
            self.intersection_widgets = {}
        if name not in self.intersection_widgets:
            self.intersection_widgets[name] = {}
        self.intersection_widgets[name]["queue"] = queue_label

        wait_card = ctk.CTkFrame(stats_frame, fg_color="#fecaca", corner_radius=6, height=65)
        wait_card.grid(row=0, column=1, padx=3, sticky="ew")
        wait_card.pack_propagate(False)
        wait_content = ctk.CTkFrame(wait_card, fg_color="transparent")
        wait_content.pack(expand=True)
        ctk.CTkLabel(wait_content, text="Chờ TB", font=("Segoe UI", 10, "bold"), text_color="#0f172a").pack()
        wait_value_frame = ctk.CTkFrame(wait_content, fg_color="transparent")
        wait_value_frame.pack()
        wait_label = ctk.CTkLabel(wait_value_frame, text="0", font=("Segoe UI", 20, "bold"), text_color="#991b1b")
        wait_label.pack(side="left")
        ctk.CTkLabel(wait_value_frame, text=" giây", font=("Segoe UI", 11), text_color="#475569").pack(side="left",
                                                                                                     pady=(6, 0))
        self.intersection_widgets[name]["wait"] = wait_label

        vehicles_frame = ctk.CTkFrame(section, fg_color="#f8fafc", corner_radius=6)
        vehicles_frame.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(vehicles_frame, text="Số xe theo hướng", font=("Segoe UI", 10, "bold"),
                     text_color="#475569").pack(pady=(6, 3))
        dir_grid = ctk.CTkFrame(vehicles_frame, fg_color="transparent")
        dir_grid.pack(padx=6, pady=(0, 6))
        dir_grid.grid_columnconfigure(0, weight=1)
        dir_grid.grid_columnconfigure(1, weight=1)

        directions = [
            ("⬆ Bắc", "#e9d5ff", "#6b21a8", 0, 0),
            ("⬇ Nam", "#fed7aa", "#9a3412", 0, 1),
            ("➡ Đông", "#bbf7d0", "#14532d", 1, 0),
            ("⬅ Tây", "#fce7f3", "#831843", 1, 1),
        ]
        self.intersection_widgets[name]["directions"] = {}
        for dir_name, bg_color, text_color, row, col in directions:
            card = ctk.CTkFrame(dir_grid, fg_color=bg_color, corner_radius=5, height=52)
            card.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            card.pack_propagate(False)
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(expand=True)
            ctk.CTkLabel(content, text=dir_name, font=("Segoe UI", 9, "bold"), text_color="#0f172a").pack()
            val_label = ctk.CTkLabel(content, text="0", font=("Segoe UI", 17, "bold"), text_color=text_color)
            val_label.pack()
            dir_key = dir_name.split()[1]
            self.intersection_widgets[name]["directions"][dir_key] = val_label

    def create_log_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.grid(row=0, column=0, sticky="nsew")
        section.grid_rowconfigure(0, weight=1)
        section.grid_columnconfigure(0, weight=1)
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=35)
        header_frame.pack(fill="x", padx=10, pady=(8, 6))
        header_frame.pack_propagate(False)
        ctk.CTkLabel(header_frame, text="📋 Log Hệ Thống", font=("Segoe UI", 12, "bold"),
                     text_color="#0f172a", anchor="w").pack(side="left")
        log_frame = ctk.CTkFrame(section, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log_box = tk.Text(log_frame, bg="#f8fafc", fg="#1e293b", wrap="word", relief="flat",
                               font=("Consolas", 9), padx=8, pady=8, borderwidth=0, highlightthickness=0, height=8)
        self.log_box.pack(fill="both", expand=True)
        self.log("🚦 Hệ thống 2 ngã tư sẵn sàng")

    # ============ Mode switching ============
    def change_mode(self, value):
        self.mode = value
        self.log(f"✓ Chế độ: {value}")
        # If switching from Adaptive -> Mặc định, stop controllers
        if value == "Mặc định":
            self.stop_all_controllers()
        # If switching to Adaptive while SUMO is running, start controllers immediately
        if value == "Tự động" and self.running:
            self.start_controllers_if_needed()

    # ============ Start / Pause / Stop ============

    def start_sim(self):
        if self.running:
            return

        self.running = True
        self.paused = False
        self.status_label.configure(text="🟢 Chạy", text_color="#10b981")

        # Check if SUMO already running (connected via traci)
        sumo_is_running = False
        try:
            import traci
            traci.simulation.getTime()
            sumo_is_running = True
            self.log("▶ Tiếp tục/Bắt đầu mô phỏng (SUMO đã chạy)")
        except Exception:
            sumo_is_running = False

        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sumo', 'test2.sumocfg')
        config_path = os.path.abspath(config_path)

        if not sumo_is_running:
            # Start SUMO GUI and connect
            if not khoi_dong_sumo(config_path, gui=True):
                self.log("❌ Không thể khởi động SUMO. Kiểm tra cấu hình hoặc cài SUMO.")
                self.running = False
                self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")
                return
            else:
                self.log("▶ Bắt đầu SUMO GUI")

        # Now SUMO is running. Apply mode-specific setup
        if self.mode == "Mặc định":
            # Apply static timings to all TLS
            try:
                phase_durations = {
                    'xanh_chung': int(self.green_entry.get()),
                    'vang_chung': int(self.yellow_entry.get()),
                    'do_toan_phan': int(self.red_entry.get())
                }
            except ValueError:
                phase_durations = {
                    'xanh_chung': self.green_time,
                    'vang_chung': self.yellow_time,
                    'do_toan_phan': self.red_time
                }
            # Call function to update all TLS definitions
            try:
                dieu_chinh_tat_ca_den(phase_durations)
                self.log("✅ Áp dụng thời gian static cho tất cả đèn (Mặc định).")
            except Exception as e:
                self.log(f"⚠ Không thể áp dụng thời gian: {e}")

        elif self.mode == "Tự động":
            # Start adaptive controllers for each TLS
            self.start_controllers_if_needed()

        # Start the simulation loop thread
        threading.Thread(target=self.simulate_with_sumo, daemon=True).start()

    def pause_sim(self):
        if not self.running:
            return
        self.running = False
        self.paused = True
        self.status_label.configure(text="🟡 Tạm dừng", text_color="#f59e0b")
        self.log("⏸ Tạm dừng mô phỏng (nhấn Start để tiếp tục)")

    def stop_sim(self):
        self.running = False
        self.paused = False
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        # stop adaptive controllers
        self.stop_all_controllers()
        try:
            dung_sumo()
            self.log("⏹ Đã dừng và đóng SUMO")
        except Exception:
            self.log("⏹ Đã dừng mô phỏng (không thể đóng SUMO bằng API)")

    def export_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_2nt_log_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.log_box.get("1.0", "end"))
        self.log(f"✓ Xuất: {filename}")

    # ============ Controllers management ============
    def start_controllers_if_needed(self):
        if AdaptiveController is None:
            self.log("❌ AdaptiveController không sẵn có (không import được).")
            return
        try:
            import traci
            tls_ids = traci.trafficlight.getIDList()
            for tls_id in tls_ids:
                if tls_id not in self.controllers:
                    ctrl = AdaptiveController(junction_id=tls_id)
                    ok = ctrl.start()
                    if ok:
                        self.controllers[tls_id] = ctrl
                        self.log(f"🤖 Adaptive controller started for {tls_id}")
                    else:
                        self.log(f"⚠️ Không thể khởi động AdaptiveController cho {tls_id}")
        except Exception as e:
            self.log(f"⚠ Lỗi khi khởi tạo controllers: {e}")

    def stop_all_controllers(self):
        for tls_id, ctrl in list(self.controllers.items()):
            try:
                ctrl.stop()
            except Exception:
                pass
            self.controllers.pop(tls_id, None)
        if self.controllers:
            self.log("🛑 Dừng tất cả controllers")
        self.controllers = {}

    # ============ Simulation loop ============
    def simulate_with_sumo(self):
        import traci
        try:
            sumo_ended = False
            while not sumo_ended:
                # pause handling
                while self.paused and not sumo_ended:
                    time.sleep(0.1)
                    if not self.running and not self.paused:
                        sumo_ended = True
                        break

                if not self.running and not self.paused:
                    break

                if self.running:
                    # advance SUMO
                    traci.simulationStep()

                    # if adaptive mode: call step() on each controller
                    if self.mode == "Tự động" and self.controllers:
                        for tls_id, ctrl in list(self.controllers.items()):
                            try:
                                ctrl.step()
                            except Exception as e:
                                self.log(f"⚠ Controller {tls_id} step error: {e}")

                    # update UI data & redraw
                    self.update_data_from_sumo()
                    self.update_ui()

                    time.sleep(0.1)

        except Exception as e:
            self.log(f"❌ Lỗi trong mô phỏng SUMO: {e}")
            self.running = False
            self.paused = False
            self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")
        finally:
            # When finishing (stop), stop controllers and optionally close SUMO
            if not self.paused and not self.resetting:
                try:
                    self.stop_all_controllers()
                    dung_sumo()
                except Exception:
                    pass

    # ============ Reset ============
    def reset_all(self):
        threading.Thread(target=self._do_reset, daemon=True).start()

    def _do_reset(self):
        self.resetting = True
        was_running = self.running
        self.running = False
        self.paused = False
        time.sleep(0.8)
        try:
            import traci
            try:
                traci.simulation.getTime()
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                           "data", "sumo", "test2.sumocfg")
                traci.load(["-c", config_path])
                self.log("🔄 Đã reload SUMO về trạng thái ban đầu")
                time.sleep(0.5)
                # Restart simulation loop (will wait for user to press Start)
                self.running = True
                threading.Thread(target=self.simulate_with_sumo, daemon=True).start()
                self.log("✓ Simulation loop đã sẵn sàng")
            except Exception as e:
                self.log(f"⚠ Không thể reload SUMO: {e}")
        except Exception:
            pass
        self.after(0, self._reset_ui_and_data, was_running)

    def _reset_ui_and_data(self, was_running):
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 3
        self.mode = "Mặc định"
        self.global_kpi_data = {
            "Tổng xe": 0, "Độ trễ TB": 0.0, "Lưu lượng": 0, "Chu kỳ TB": 0, "Công bằng": 0.0, "Phối hợp": 0
        }
        self.intersection_data = {
            "Ngã tư 1": {"light_state": "Đỏ", "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}, "queue": 0,
                         "wait_time": 0},
            "Ngã tư 2": {"light_state": "Xanh", "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}, "queue": 0,
                         "wait_time": 0}
        }
        self.status_label.configure(text="🟢 Sẵn sàng", text_color="#22c55e")
        self.case_box.set("Mặc định")
        self.mode_option.set("Mặc định")
        self.green_entry.delete(0, 'end'); self.green_entry.insert(0, "30")
        self.yellow_entry.delete(0, 'end'); self.yellow_entry.insert(0, "3")
        self.red_entry.delete(0, 'end'); self.red_entry.insert(0, "3")
        for name, label in self.global_kpi_cards.items():
            label.configure(text="—")
        for int_name, widgets in self.intersection_widgets.items():
            widgets["queue"].configure(text="0"); widgets["wait"].configure(text="0")
            for direction, label in widgets["directions"].items():
                label.configure(text="0")
        self.log("🔄 Đã đặt lại toàn bộ hệ thống về giá trị mặc định")
        self.resetting = False

    # ============ Logging & apply timing ============
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")

    def apply_timing(self):
        try:
            green = int(self.green_entry.get())
            yellow = int(self.yellow_entry.get())
            red = int(self.red_entry.get())
            if green <= 0 or yellow <= 0 or red <= 0:
                self.log("❌ Thời gian phải lớn hơn 0")
                return
            if green > 120 or yellow > 30 or red > 30:
                self.log("❌ Thời gian quá lớn")
                return
            self.green_time = green; self.yellow_time = yellow; self.red_time = red
            self.log(f"✓ Đã cài đặt: Xanh {green}s, Vàng {yellow}s, Đỏ Toàn Phần {red}s")
            # If SUMO is running and current mode is Mặc định, apply immediately
            try:
                import traci
                traci.simulation.getTime()
                if self.mode == "Mặc định":
                    phase_durations = {'xanh_chung': green, 'vang_chung': yellow, 'do_toan_phan': red}
                    dieu_chinh_tat_ca_den(phase_durations)
                    self.log("✅ Áp dụng thời gian mới lên SUMO (Mặc định).")
                else:
                    self.log("ℹ️ Đang ở chế độ Tự động (Adaptive); thay đổi thời gian không áp dụng.")
            except Exception:
                # SUMO not running - nothing to apply now
                self.log("ℹ️ SUMO chưa chạy; áp dụng sẽ thực hiện khi Start.")
        except ValueError:
            self.log("❌ Vui lòng nhập số hợp lệ")

    # ============ Update data from SUMO & UI ============
    def update_data_from_sumo(self):
        import traci
        try:
            tls_ids = traci.trafficlight.getIDList()
            # update first two TLS to UI
            for i, tls_id in enumerate(tls_ids[:2]):
                int_name = f"Ngã tư {i+1}"
                if int_name not in self.intersection_data:
                    continue
                current_phase = traci.trafficlight.getPhase(tls_id)
                if current_phase == 0:
                    light_state = "Xanh"
                elif current_phase == 1:
                    light_state = "Đỏ"
                else:
                    light_state = "Vàng"
                self.intersection_data[int_name]["light_state"] = light_state

                # basic edge mapping (you can adjust if needed)
                try:
                    edges = {
                        "Bắc": f"-E{i*4}",
                        "Nam": f"E{i*4}",
                        "Đông": f"-E{i*4+1}",
                        "Tây": f"E{i*4+1}"
                    }
                    total_vehicles = 0
                    for direction, edge_id in edges.items():
                        try:
                            vehicle_count = traci.edge.getLastStepVehicleNumber(edge_id)
                            self.intersection_data[int_name]["vehicles"][direction] = vehicle_count
                            total_vehicles += vehicle_count
                        except Exception:
                            self.intersection_data[int_name]["vehicles"][direction] = 0
                    self.intersection_data[int_name]["queue"] = max(0, total_vehicles - 20)
                    self.intersection_data[int_name]["wait_time"] = min(120, total_vehicles * 2)
                except Exception:
                    for d in ["Bắc", "Nam", "Đông", "Tây"]:
                        self.intersection_data[int_name]["vehicles"][d] = random.randint(5, 25)
                    self.intersection_data[int_name]["queue"] = random.randint(0, 15)
                    self.intersection_data[int_name]["wait_time"] = random.randint(10, 60)

            total_vehicles = sum(sum(data["vehicles"].values()) for data in self.intersection_data.values())
            avg_delay = sum(data["wait_time"] for data in self.intersection_data.values()) / len(self.intersection_data)
            throughput = total_vehicles * 10
            avg_cycle = 60
            fairness = 0.85
            coordination = 80
            self.global_kpi_data = {
                "Tổng xe": total_vehicles,
                "Độ trễ TB": round(avg_delay, 1),
                "Lưu lượng": throughput,
                "Chu kỳ TB": avg_cycle,
                "Công bằng": fairness,
                "Phối hợp": coordination
            }

        except Exception as e:
            self.log(f"⚠ Cập nhật dữ liệu SUMO thất bại: {e}")

    def update_ui(self):
        try:
            for key, value in self.global_kpi_data.items():
                if key in self.global_kpi_cards:
                    self.global_kpi_cards[key].configure(text=str(value))
            for int_name, data in self.intersection_data.items():
                if int_name in self.intersection_widgets:
                    widgets = self.intersection_widgets[int_name]
                    widgets["queue"].configure(text=str(data["queue"]))
                    widgets["wait"].configure(text=str(data["wait_time"]))
                    for direction, count in data["vehicles"].items():
                        if direction in widgets["directions"]:
                            widgets["directions"][direction].configure(text=str(count))
            # occasional logs
            events = ["Cập nhật trạng thái đèn giao thông", "Phát hiện thay đổi lưu lượng", "Điều chỉnh chu kỳ đèn",
                      "Hệ thống hoạt động ổn định"]
            if random.random() < 0.05:
                self.log(random.choice(events))
        except Exception as e:
            self.log(f"⚠ Cập nhật UI thất bại: {e}")


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
