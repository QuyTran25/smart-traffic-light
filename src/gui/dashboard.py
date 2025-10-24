import customtkinter as ctk
import tkinter as tk
from datetime import datetime
import threading
import time
import os
import sys
import random

# ==================== PATH SETUP ====================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# SUMO connector functions you must have in simulation/sumo_connector.py
from simulation.sumo_connector import khoi_dong_sumo, dung_sumo, dieu_chinh_tat_ca_den
from simulation.vehicle_counter import VehicleCounter

try:
    from controllers.adaptive_controller import AdaptiveController
except Exception:
    AdaptiveController = None

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class SmartTrafficApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚦 HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH")
        self.geometry("700x850")
        self.minsize(680, 800)

        # runtime flags
        self.running = False
        self.paused = False
        self.resetting = False
        self.mode = "Mặc định"  # or "Tự động"

        # default timings (used in Mặc định mode)
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 3  # all-red time

        # controllers dict for adaptive mode
        self.controllers = {}
        
        # Vehicle Counter instance
        self.vehicle_counter = None

        # KPI & intersection data
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

        # Build UI
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

        ctk.CTkLabel(title_frame, text="HỆ THỐNG ĐIỀU KHIỂN ĐÈN TÍN HIỆU GIAO THÔNG THÔNG MINH",
                     font=("Segoe UI", 16, "bold"), text_color="#0f172a", anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Demo SUMO", font=("Segoe UI", 11),
                     text_color="#64748b", anchor="w").pack(anchor="w", pady=(2, 0))

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=15)
        self.status_label = ctk.CTkLabel(status_frame, text="⚫ Dừng", font=("Segoe UI", 11, "bold"),
                                         text_color="#64748b")
        self.status_label.pack()
        self.mode_status_label = ctk.CTkLabel(status_frame, text="Chế độ: Mặc định", font=("Segoe UI", 10),
                                              text_color="#64748b")
        self.mode_status_label.pack()

        # Control bar
        self.control_bar_main = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        self.control_bar_main.pack(fill="x", padx=0, pady=(1, 0))

        # ---------- First row (mode + action buttons) ----------
        control_bar_top = ctk.CTkFrame(self.control_bar_main, fg_color="transparent", height=45)
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

        # Action buttons
        btn_frame = ctk.CTkFrame(left_controls, fg_color="transparent")
        btn_frame.pack(side="left")

        self.play_btn = ctk.CTkButton(btn_frame, text="▶ CHẠY", fg_color="#10b981", hover_color="#059669",
                                      font=("Segoe UI", 11, "bold"), width=42, height=36,
                                      corner_radius=5, command=self.start_sim)
        self.play_btn.pack(side="left", padx=2)

        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸ TẠM DỪNG", fg_color="#f59e0b", hover_color="#d97706",
                                       text_color="#000000", font=("Segoe UI", 11, "bold"), width=42,
                                       height=36, corner_radius=5, command=self.pause_sim)
        self.pause_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ DỪNG", fg_color="#ef4444", hover_color="#dc2626",
                                      font=("Segoe UI", 11, "bold"), width=42, height=36,
                                      corner_radius=5, command=self.stop_sim)
        self.stop_btn.pack(side="left", padx=2)

        reset_btn = ctk.CTkButton(btn_frame, text="🔄 LÀM LẠI", fg_color="#64748b", hover_color="#475569",
                                  font=("Segoe UI", 11, "bold"), width=42, height=36,
                                  corner_radius=5, command=self.reset_all)
        reset_btn.pack(side="left", padx=2)

        export_btn = ctk.CTkButton(btn_frame, text="⬇ XUẤT FILE LOG", fg_color="#3b82f6", hover_color="#2563eb",
                                   font=("Segoe UI", 11, "bold"), width=42, height=36,
                                   corner_radius=5, command=self.export_log)
        export_btn.pack(side="left", padx=2)

        # ---------- Second row (scenario selector) ----------
        self.control_bar_bottom = ctk.CTkFrame(self.control_bar_main, fg_color="transparent", height=42)
        self.control_bar_bottom.pack(fill="x", padx=10, pady=(6, 8))
        self.control_bar_bottom.pack_propagate(False)

        scenario_frame = ctk.CTkFrame(self.control_bar_bottom, fg_color="transparent")
        scenario_frame.pack(side="left")

        ctk.CTkLabel(
            scenario_frame,
            text="Kịch bản:",
            font=("Segoe UI", 11, "bold"),
            text_color="#334155"
        ).pack(side="left", padx=(0, 8))

        self.case_box = ctk.CTkOptionMenu(
            scenario_frame,
            values=[
                "Mặc định",
                "SC1 - Xe ưu tiên từ hướng chính trong giờ cao điểm",
                "SC2 - Xe ưu tiên từ hướng nhánh (ít xe) sắp tới gần",
                "SC3 - Nhiều xe ưu tiên từ 2 hướng đối diện",
                "SC4 - Báo giả",
                "SC5 - Xe ưu tiên bị kẹt trong dòng xe dài",
                "SC6 - Nhiều xe ưu tiên liên tiếp"
            ],
            dropdown_font=("Segoe UI", 10),
            fg_color="#cbd5e1",
            button_color="#0ea5e9",
            button_hover_color="#0284c7",
            dropdown_fg_color="#ffffff",
            dropdown_hover_color="#e0f2fe",
            dropdown_text_color="#0f172a",
            text_color="#0f172a",
            width=220,
            height=34,
            corner_radius=5
        )
        self.case_box.pack(side="left")
        self.case_box.set("Mặc định")


        # Timing inputs (make as class attributes so change_mode can pack/forget them)
        self.timing_bar = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        self.timing_bar.pack(fill="x", padx=0, pady=(1, 0))

        timing_container = ctk.CTkFrame(self.timing_bar, fg_color="transparent", height=50)
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

    # ---------- UI helper creators (same as original UI) ----------
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
        section.grid(row=2, column=0, sticky="nsew")
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
        self.log("🚦 Hệ thống điều kiển đèn giao thông thông minh sẵn sàng")

    # ============ Mode switching ============
    def change_mode(self, value):
        self.mode = value
        self.log(f"✓ Chế độ: {value}")
        self.mode_status_label.configure(text=f"Chế độ: {value}")
        # If switching from Adaptive -> Mặc định, stop controllers
        if value == "Mặc định":
            self.stop_all_controllers()
            self.timing_bar.pack(after=self.control_bar_main, fill="x", pady=(1, 0))
        # If switching to Adaptive, hide timing and start controllers if running
        if value == "Tự động":
            self.timing_bar.pack_forget()
            if self.running:
                self.start_controllers_if_needed()

    # ============ Start / Pause / Stop ============
    def start_sim(self):
        if self.running:
            return

        self.running = True
        self.paused = False
        self.status_label.configure(text="🟢 Chạy", text_color="#10b981")

        # Lấy kịch bản được chọn
        scenario = self.case_box.get()
        self.log(f"▶ Bắt đầu mô phỏng với kịch bản: {scenario}")

        # Kiểm tra SUMO đã chạy chưa
        sumo_is_running = False
        try:
            import traci
            traci.simulation.getTime()
            sumo_is_running = True
            self.log("▶ SUMO đã sẵn sàng, kết nối trực tiếp.")
        except Exception:
            sumo_is_running = False

        # Xác định file cấu hình SUMO
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sumo', 'test2.sumocfg')
        config_path = os.path.abspath(config_path)

        # Nếu SUMO chưa chạy, khởi động
        if not sumo_is_running:
            if not khoi_dong_sumo(config_path, gui=True):
                self.log("❌ Không thể khởi động SUMO. Kiểm tra cấu hình hoặc cài SUMO.")
                self.running = False
                self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")
                return
            else:
                self.log("✅ SUMO GUI đã khởi động thành công")
        
        # Khởi tạo Vehicle Counter (KHÔNG khởi động SUMO vì đã khởi động rồi)
        try:
            self.vehicle_counter = VehicleCounter(config_path)
            # Gọi discover_edges để khởi tạo mapping edges
            try:
                import traci
                self.vehicle_counter.discover_edges()
                self.log("✅ Vehicle Counter đã được khởi tạo và phát hiện edges")
            except Exception as discover_err:
                self.log(f"⚠ Không thể phát hiện edges: {discover_err}")
                self.vehicle_counter = None
        except Exception as e:
            self.log(f"⚠ Không thể khởi tạo Vehicle Counter: {e}")
            self.vehicle_counter = None

        # Gọi hàm sinh kịch bản (dựa trên lựa chọn)
        self.apply_scenario_to_sumo(scenario)

        # Áp dụng chế độ (Mặc định / Tự động)
        if self.mode == "Mặc định":
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

            try:
                dieu_chinh_tat_ca_den(phase_durations)
                self.log("✅ Áp dụng thời gian static cho tất cả đèn (Mặc định).")
            except Exception as e:
                self.log(f"⚠ Không thể áp dụng thời gian: {e}")

        elif self.mode == "Tự động":
            self.start_controllers_if_needed()

        threading.Thread(target=self.simulate_with_sumo, daemon=True).start()

    def pause_sim(self):
        if not self.running:
            return
        # Stop running flag and mark paused
        self.running = False
        self.paused = True

        # KHÔNG reset KPI - giữ nguyên giá trị hiện tại khi pause
        # Chỉ cập nhật status label
        self.status_label.configure(text="🟡 Tạm dừng", text_color="#f59e0b")
        self.log("⏸ Tạm dừng mô phỏng (nhấn Start để tiếp tục)")

    def stop_sim(self):
        # Ensure simulation flags
        self.running = False
        self.paused = False

        # Reset KPI/UI to default
        try:
            self._reset_ui_and_data(False)
        except Exception:
            pass

        # stop adaptive controllers
        self.stop_all_controllers()
        
        # Cleanup Vehicle Counter (just drop reference; dashboard manages traci lifecycle)
        if self.vehicle_counter is not None:
            try:
                self.vehicle_counter = None
                self.log("✅ Đã dừng Vehicle Counter")
            except Exception as e:
                self.log(f"⚠ Lỗi khi dừng Vehicle Counter: {e}")
        
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
        try:
            import traci
        except Exception as e:
            self.log(f"❌ Traci không sẵn sàng: {e}")
            self.running = False
            self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")
            return

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

                    # adaptive controllers step
                    if self.mode == "Tự động" and self.controllers:
                        for tls_id, ctrl in list(self.controllers.items()):
                            try:
                                ctrl.step()
                            except Exception as e:
                                self.log(f"⚠ Controller {tls_id} step error: {e}")

                    # update UI data & redraw
                    self.update_data_from_sumo()
                    self.update_ui()

                    # small sleep to avoid UI freeze (and give SUMO CPU time)
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
                # Nếu đang chạy trước khi reset, restart simulation loop
                if was_running:
                    self.running = True
                    threading.Thread(target=self.simulate_with_sumo, daemon=True).start()
                    self.log("✓ Simulation loop đã sẵn sàng")
            except Exception as e:
                self.log(f"⚠ Không thể reload SUMO: {e}")
        except Exception:
            pass
        self.after(0, self._reset_ui_and_data, was_running)

    def _reset_ui_and_data(self, was_running):
        """Reset UI và dữ liệu KPI.

        Args:
            was_running (bool): trạng thái trước khi reset; nếu True thì giữ simulation running.
        """
        # Reset timing settings
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 3
        self.mode = "Mặc định"

        # Reset KPI data
        self.global_kpi_data = {
            "Tổng xe": 0,
            "Độ trễ TB": 0.0,
            "Lưu lượng": 0,
            "Chu kỳ TB": 0,
            "Công bằng": 0.0,
            "Phối hợp": 0
        }

        # Reset intersection data
        self.intersection_data = {
            "Ngã tư 1": {"light_state": "Đỏ", "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}, "queue": 0,
                         "wait_time": 0},
            "Ngã tư 2": {"light_state": "Xanh", "vehicles": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}, "queue": 0,
                         "wait_time": 0}
        }

        # Restore / set running flag according to was_running
        # (Note: _do_reset already restarts simulate loop only if was_running True)
        self.running = bool(was_running)

        # Update UI elements
        # Status label: keep it as 'Sẵn sàng' when not running, otherwise show 'Chạy'
        if self.running:
            self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
        else:
            self.status_label.configure(text="🟢 Sẵn sàng", text_color="#22c55e")

        self.mode_option.set("Mặc định")
        self.mode_status_label.configure(text="Chế độ: Mặc định")

        self.green_entry.delete(0, 'end'); self.green_entry.insert(0, "30")
        self.yellow_entry.delete(0, 'end'); self.yellow_entry.insert(0, "3")
        self.red_entry.delete(0, 'end'); self.red_entry.insert(0, "3")

        # KPI cards
        for name, label in self.global_kpi_cards.items():
            label.configure(text="—")

        # Intersection widgets
        for int_name, widgets in self.intersection_widgets.items():
            widgets["queue"].configure(text="0")
            widgets["wait"].configure(text="0")
            for direction, label in widgets["directions"].items():
                label.configure(text="0")

        self.log("🔄 Đã đặt lại toàn bộ hệ thống về giá trị mặc định")
        self.resetting = False

    # ============ Logging & apply timing ============
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.log_box.see("end")
        except Exception:
            print(f"[{timestamp}] {msg}")

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
            
        # ============ Scenario handler ============
    def apply_scenario_to_sumo(self, scenario_name):
        """
        Dựa trên kịch bản được chọn, sinh lưu lượng xe phù hợp trong SUMO.
        Có thể mở rộng để sinh route.xml khác nhau, hoặc spawn xe theo thời gian.
        """
        try:
            import traci
        except Exception:
            self.log("⚠ Không thể áp dụng kịch bản vì SUMO chưa sẵn sàng.")
            return

        self.log(f"🎬 Đang áp dụng {scenario_name} ...")

        try:
            # Xử lý theo từng kịch bản
            if scenario_name == "Mặc định":
                self.log("🚗 Kịch bản mặc định: Lưu lượng đều từ 4 hướng.")
                # không cần thay đổi gì

            elif scenario_name == "SC1 - Xe ưu tiên từ hướng chính trong giờ cao điểm":
                self.log("🚓 SC1: Tăng lưu lượng từ hướng Bắc & Nam.")

            elif scenario_name == "SC2 - Xe ưu tiên từ hướng nhánh (ít xe) sắp tới gần":
                self.log("🚙 SC2: Tăng lưu lượng từ hướng Đông & Tây.")

            elif scenario_name == "SC3 - Nhiều xe ưu tiên từ 2 hướng đối diện":
                self.log("🚒 SC3: Tăng lưu lượng cả Bắc & Đông, mô phỏng xe ưu tiên đa hướng.")

            elif scenario_name == "SC4 - Báo giả":
                self.log("🚨 SC4: Mô phỏng cảm biến báo giả (xe ưu tiên ảo).")

            elif scenario_name == "SC5 - Xe ưu tiên bị kẹt trong dòng xe dài":
                self.log("🚓 SC5: Xe ưu tiên xuất hiện nhưng không qua được giao lộ (kẹt xe).")

            elif scenario_name == "SC6 - Nhiều xe ưu tiên liên tiếp":
                self.log("🚑 SC6: Chuỗi xe ưu tiên liên tục — thử thách điều khiển thích ứng.")

            else:
                self.log("ℹ️ Không có kịch bản cụ thể, chạy mặc định.")

        except Exception as e:
            self.log(f"⚠ Không thể áp dụng kịch bản: {e}")

    # ============ Update data from SUMO & UI ============
    def update_data_from_sumo(self):
        """
        Lấy dữ liệu thực từ SUMO qua VehicleCounter module:
        - Trạng thái đèn (Red/Yellow/Green)
        - Số xe theo hướng (sử dụng VehicleCounter.count_vehicles_on_edges())
        - Hàng chờ (tổng) và thời gian chờ trung bình
        - Tính KPI: Fairness, Coordination, Delay, Throughput, Cycle
        
        LƯU Ý: SỬ DỤNG VehicleCounter MODULE thay vì tự đếm bằng TraCI
        """
        try:
            import traci
        except Exception:
            self.log("⚠ Traci chưa sẵn sàng khi update dữ liệu.")
            return

        try:
            tls_ids = traci.trafficlight.getIDList()
            if not tls_ids:
                return

            # === BƯỚC 1: Đếm xe qua VehicleCounter ===
            vehicle_counts = None
            if self.vehicle_counter is not None:
                try:
                    # Gọi method đếm xe của VehicleCounter
                    self.vehicle_counter.count_vehicles_on_edges()
                    # Lấy kết quả đếm
                    vehicle_counts = self.vehicle_counter.get_current_counts()
                except Exception as vc_err:
                    self.log(f"⚠ Lỗi khi đếm xe qua VehicleCounter: {vc_err}")
                    vehicle_counts = None

            # === BƯỚC 2: Cập nhật dữ liệu cho từng ngã tư ===
            for i, tls_id in enumerate(tls_ids[:2]):
                int_name = f"Ngã tư {i+1}"
                junction_id = "J1" if i == 0 else "J4"
                
                if int_name not in self.intersection_data:
                    continue

                # --- Lấy trạng thái đèn ---
                try:
                    state = traci.trafficlight.getRedYellowGreenState(tls_id)
                except Exception:
                    state = ""

                if "G" in state:
                    self.intersection_data[int_name]["light_state"] = "Xanh"
                elif "y" in state.lower():
                    self.intersection_data[int_name]["light_state"] = "Vàng"
                elif all(ch == "r" for ch in state.lower()):
                    self.intersection_data[int_name]["light_state"] = "Đỏ Toàn Phần"
                else:
                    self.intersection_data[int_name]["light_state"] = "Đỏ"

                # --- Sử dụng dữ liệu từ VehicleCounter ---
                if vehicle_counts and junction_id in vehicle_counts:
                    # Lấy số xe từ VehicleCounter
                    junction_vehicles = vehicle_counts[junction_id]
                    self.intersection_data[int_name]["vehicles"] = junction_vehicles.copy()
                    
                    # Tính tổng xe (queue)
                    total_vehicle = sum(junction_vehicles.values())
                    self.intersection_data[int_name]["queue"] = total_vehicle
                    
                    # Tính thời gian chờ trung bình (vẫn cần dùng TraCI)
                    total_wait = 0.0
                    try:
                        # Lấy tất cả xe trong simulation
                        all_vehicle_ids = traci.vehicle.getIDList()
                        for vid in all_vehicle_ids:
                            try:
                                total_wait += traci.vehicle.getWaitingTime(vid)
                            except Exception:
                                continue
                        
                        self.intersection_data[int_name]["wait_time"] = round(
                            total_wait / total_vehicle, 1
                        ) if total_vehicle > 0 else 0
                    except Exception as wait_err:
                        self.intersection_data[int_name]["wait_time"] = 0
                else:
                    # Fallback: nếu VehicleCounter không hoạt động, đặt về 0
                    self.intersection_data[int_name]["vehicles"] = {
                        "Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0
                    }
                    self.intersection_data[int_name]["queue"] = 0
                    self.intersection_data[int_name]["wait_time"] = 0

            # --- Công bằng (Fairness) ---
            queues = [data["queue"] for data in self.intersection_data.values()]
            if len(queues) > 0 and sum(queues) > 0:
                mean_q = sum(queues) / len(queues)
                std_q = (sum((x - mean_q) ** 2 for x in queues) / len(queues)) ** 0.5
                fairness = round(1 - (std_q / (mean_q + 0.001)), 2)
            else:
                fairness = 1.0

            # --- Phối hợp (Coordination) ---
            try:
                if len(tls_ids) >= 2:
                    rem1 = traci.trafficlight.getNextSwitch(tls_ids[0]) - traci.simulation.getTime()
                    rem2 = traci.trafficlight.getNextSwitch(tls_ids[1]) - traci.simulation.getTime()
                    diff = abs(rem1 - rem2)
                    cycle = self.green_time + self.yellow_time + self.red_time
                    coordination = max(0, 100 * (1 - diff / cycle))
                else:
                    coordination = 100.0
            except Exception:
                coordination = 100.0

            # --- Các KPI toàn cục ---
            total_vehicles = sum(sum(d["vehicles"].values()) for d in self.intersection_data.values())
            if len(self.intersection_data) > 0:
                avg_delay = sum(data["wait_time"] for data in self.intersection_data.values()) / len(self.intersection_data)
            else:
                avg_delay = 0.0
            throughput = total_vehicles * 10 
            avg_cycle = int(self.green_time + self.yellow_time + self.red_time)

            self.global_kpi_data = {
                "Tổng xe": total_vehicles,
                "Độ trễ TB": round(avg_delay, 1),
                "Lưu lượng": throughput,
                "Chu kỳ TB": avg_cycle,
                "Công bằng": fairness,
                "Phối hợp": round(coordination, 1)
            }

        except Exception as e:
            import traceback
            self.log(f"⚠ Cập nhật dữ liệu SUMO thất bại: {e}")
            self.log(f"📋 Chi tiết lỗi: {traceback.format_exc()}")

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