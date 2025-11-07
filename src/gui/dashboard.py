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
from simulation.sensor_manager import SensorManager

try:
    from controllers.adaptive_controller import AdaptiveController
except Exception:
    AdaptiveController = None

try:
    from controllers.priority_controller import PriorityController
except Exception:
    PriorityController = None

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
        
        # scenario spawning
        self.scenario_spawning = False
        self.scenario_thread = None

        # default timings (used in Mặc định mode)
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 3  # all-red time

        # controllers dict for adaptive mode
        self.controllers = {}
        
        # Priority controllers cho từng ngã tư
        self.priority_controllers = {}  # {junction_id: PriorityController}
        
        # Vehicle Counter instance
        self.vehicle_counter = None
        
        # Sensor Manager instance
        self.sensor_manager = None
        
        # Priority vehicle spawning control
        self.spawning_active = False
        self.spawning_thread = None

        # KPI & intersection data
        self.global_kpi_data = {
            "Độ trễ TB": 0.0,           # KPI 1: Average Delay
            "Hàng chờ TB": 0.0,         # KPI 2: Queue Length
            "Lưu lượng": 0,             # KPI 3: Throughput
            "Dừng TB": 0.0,             # KPI 4: Stops per Vehicle
            "Chờ tối đa": 0.0,          # KPI 5: Max Waiting Time
            "Chu kỳ TB": 0,             # KPI 6: Cycle Length
            "Công bằng": 0.0,           # KPI 7: Fairness Index
            "Giải phóng xe UT": 0.0        # KPI 8: Emergency Clearance Time (CẢ 2 CHẾ ĐỘ)
        }
        
        # Sensor data
        self.sensor_data = {
            "E1 Detectors": 0,
            "E2 Detectors": 0,
            "Mật độ TB": 0,
            "Queue TB": 0
        }
        
        # Emergency vehicle tracking
        self.emergency_vehicle_data = {
            "detection_time": None,
            "clearance_time": None,
            "total_clearance_time": 0.0
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

        # Priority vehicle tracking
        self.priority_vehicle_data = {
            "J1": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0},
            "J4": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}
        }
        self.has_priority_vehicles = False

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
        
        # Priority status label (hiển thị khi có xe ưu tiên)
        self.priority_status_label = ctk.CTkLabel(status_frame, text="", font=("Segoe UI", 10, "bold"),
                                                  text_color="#ef4444")
        self.priority_status_label.pack()

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
        self.content_frame.grid_rowconfigure(2, weight=0)
        self.content_frame.grid_rowconfigure(3, weight=0)
        self.content_frame.grid_rowconfigure(4, weight=0, minsize=200)
        self.content_frame.grid_columnconfigure(0, weight=1)

        kpi_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        kpi_container.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.create_global_kpi_section(kpi_container)

        # Priority Vehicle Panel (ẩn mặc định)
        self.priority_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.create_priority_vehicle_section(self.priority_container)

        intersections_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        intersections_container.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        intersections_container.grid_columnconfigure(0, weight=1)
        intersections_container.grid_columnconfigure(1, weight=1)

        self.create_intersection_section(intersections_container, "Ngã tư 1", 0, "#3b82f6")
        self.create_intersection_section(intersections_container, "Ngã tư 2", 1, "#8b5cf6")

        log_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        log_container.grid(row=3, column=0, sticky="nsew")
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
        # Sắp xếp theo thứ tự KPI 1-8 (trái → phải, trên → dưới)
        kpi_data = [
            # Hàng 1: KPI 1-4
            ("Độ trễ TB", "—", "s/xe", "#fef3c7", "#78350f", "⏱️"),       # KPI 1: Average Delay
            ("Hàng chờ TB", "—", "PCU", "#fecaca", "#991b1b", "🚗"),      # KPI 2: Queue Length
            ("Lưu lượng", "—", "xe/h", "#d1fae5", "#065f46", "🚦"),       # KPI 3: Throughput
            ("Dừng TB", "—", "lần", "#e0e7ff", "#3730a3", "⏹️"),          # KPI 4: Stops per Vehicle
            # Hàng 2: KPI 5-8
            ("Chờ tối đa", "—", "s", "#fed7aa", "#9a3412", "⏰"),          # KPI 5: Max Waiting Time
            ("Chu kỳ TB", "—", "s", "#ddd6fe", "#5b21b6", "🔄"),          # KPI 6: Cycle Length
            ("Công bằng", "—", "%", "#fce7f3", "#831843", "⚖️"),          # KPI 7: Fairness Index
            ("Giải phóng xe UT", "—", "s", "#dbeafe", "#1e3a8a", "🚨"),      # KPI 8: Emergency Clearance Time
        ]
        for idx, (name, value, unit, bg_color, text_color, icon) in enumerate(kpi_data):
            row = idx // 4  # Changed from 3 to 4 columns
            col = idx % 4
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
        for i in range(4):  # Changed from 3 to 4 columns
            kpi_grid.grid_columnconfigure(i, weight=1)

    def create_priority_vehicle_section(self, parent):
        """Tạo panel hiển thị xe ưu tiên động"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x", padx=0, pady=0)
        
        # Header với animation
        header_frame = ctk.CTkFrame(section, fg_color="#ef4444", corner_radius=8, height=40)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(expand=True)
        
        # Animated title
        self.priority_title = ctk.CTkLabel(
            header_content, 
            text="🚨 PHÁT HIỆN XE ƯU TIÊN", 
            font=("Segoe UI", 14, "bold"), 
            text_color="#ffffff"
        )
        self.priority_title.pack()
        
        # Priority vehicle grid
        priority_grid = ctk.CTkFrame(section, fg_color="transparent")
        priority_grid.pack(fill="x", padx=8, pady=8)
        priority_grid.grid_columnconfigure(0, weight=1)
        priority_grid.grid_columnconfigure(1, weight=1)
        
        self.priority_widgets = {}
        
        # J1 và J4 sections
        for idx, (junction_id, junction_name) in enumerate([("J1", "Ngã tư 1"), ("J4", "Ngã tư 2")]):
            junction_frame = ctk.CTkFrame(priority_grid, fg_color="#fef2f2", corner_radius=6)
            junction_frame.grid(row=0, column=idx, padx=4, pady=0, sticky="ew")
            
            # Junction header
            ctk.CTkLabel(
                junction_frame, 
                text=f"🚦 {junction_name}", 
                font=("Segoe UI", 12, "bold"), 
                text_color="#991b1b"
            ).pack(pady=(8, 4))
            
            # Direction grid
            dir_grid = ctk.CTkFrame(junction_frame, fg_color="transparent")
            dir_grid.pack(padx=8, pady=(0, 8))
            dir_grid.grid_columnconfigure(0, weight=1)
            dir_grid.grid_columnconfigure(1, weight=1)
            
            directions = [
                ("🔺 Bắc", "#fecaca", "#991b1b", 0, 0),
                ("🔻 Nam", "#fed7aa", "#9a3412", 0, 1),
                ("▶️ Đông", "#bbf7d0", "#14532d", 1, 0),
                ("◀️ Tây", "#fce7f3", "#831843", 1, 1),
            ]
            
            self.priority_widgets[junction_id] = {}
            
            for dir_name, bg_color, text_color, row, col in directions:
                card = ctk.CTkFrame(dir_grid, fg_color=bg_color, corner_radius=4, height=45)
                card.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
                card.pack_propagate(False)
                
                content = ctk.CTkFrame(card, fg_color="transparent")
                content.pack(expand=True)
                
                ctk.CTkLabel(content, text=dir_name, font=("Segoe UI", 9, "bold"), text_color="#0f172a").pack()
                
                val_label = ctk.CTkLabel(content, text="0", font=("Segoe UI", 16, "bold"), text_color=text_color)
                val_label.pack()
                
                dir_key = dir_name.split()[1]  # Lấy "Bắc", "Nam", etc.
                self.priority_widgets[junction_id][dir_key] = val_label

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
        section.pack(fill="both", expand=True)
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
            
            # Nếu SUMO đang chạy, áp dụng ngay fixed-time program
            if self.running:
                try:
                    import traci
                    traci.simulation.getTime()
                    
                    # Lấy thời gian hiện tại từ entry fields
                    try:
                        green = int(self.green_entry.get())
                        yellow = int(self.yellow_entry.get())
                        red = int(self.red_entry.get())
                    except ValueError:
                        green = self.green_time
                        yellow = self.yellow_time
                        red = self.red_time
                    
                    phase_durations = {
                        'xanh_chung': green,
                        'vang_chung': yellow,
                        'do_toan_phan': red
                    }
                    
                    dieu_chinh_tat_ca_den(phase_durations)
                    self.log(f"✅ Đã chuyển sang chế độ Fixed-Time (Xanh {green}s, Vàng {yellow}s, All-Red {red}s)")
                    
                except Exception as e:
                    self.log(f"⚠ Không thể áp dụng Fixed-Time: {e}")
        
        # If switching to Adaptive, hide timing and start controllers if running
        if value == "Tự động":
            self.timing_bar.pack_forget()
            if self.running:
                self.start_controllers_if_needed()
                self.log("✅ Đã kích hoạt Adaptive Controllers")

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
        
        # Khởi tạo Sensor Manager
        try:
            self.sensor_manager = SensorManager()
            e1_count, e2_count = self.sensor_manager.discover_detectors()
            self.log(f"✅ Sensor Manager đã phát hiện {e1_count} E1 detectors và {e2_count} E2 detectors")
        except Exception as e:
            self.log(f"⚠ Không thể khởi tạo Sensor Manager: {e}")
            self.sensor_manager = None

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
            
            # ✅ Khởi động PriorityController để theo dõi xe ưu tiên (không can thiệp đèn)
            self.start_priority_controllers_monitoring()

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
            
            # Khởi động Priority Controllers
            self.init_priority_controllers()
            
        except Exception as e:
            self.log(f"⚠ Lỗi khi khởi tạo controllers: {e}")

    def start_priority_controllers_monitoring(self):
        """
        Khởi động Priority Controllers ở chế độ MONITORING (không can thiệp đèn)
        Dùng cho chế độ Mặc định để theo dõi xe ưu tiên và tính KPI 8
        """
        try:
            self.init_priority_controllers()
            self.log("🚨 Khởi động Priority Controllers (monitoring mode - không can thiệp đèn)")
        except Exception as e:
            self.log(f"⚠ Lỗi khi khởi động Priority Controllers monitoring: {e}")

    def stop_all_controllers(self):
        # Stop adaptive controllers
        for tls_id, ctrl in list(self.controllers.items()):
            try:
                ctrl.stop()
            except Exception:
                pass
            self.controllers.pop(tls_id, None)
        if self.controllers:
            self.log("🛑 Dừng tất cả adaptive controllers")
        self.controllers = {}
        
        # Stop priority controllers
        if hasattr(self, 'priority_controllers') and self.priority_controllers:
            for junction_id, priority_ctrl in list(self.priority_controllers.items()):
                try:
                    priority_ctrl.stop()
                except Exception:
                    pass
            self.log("🛑 Dừng tất cả priority controllers")
            self.priority_controllers = {}

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
                    
                    # priority controllers step (xe ưu tiên)
                    if hasattr(self, 'priority_controllers') and self.priority_controllers:
                        for junction_id, priority_ctrl in list(self.priority_controllers.items()):
                            try:
                                priority_ctrl.step()
                            except Exception as e:
                                self.log(f"⚠ PriorityController {junction_id} step error: {e}")
                    
                    # ĐẢM BẢO XE ƯU TIÊN LUÔN BỎ QUA ĐÈN ĐỎ (set lại mỗi step)
                    try:
                        all_vehicles = traci.vehicle.getIDList()
                        for veh_id in all_vehicles:
                            if "priority" in veh_id or veh_id.startswith("priority_"):
                                current_speed_mode = traci.vehicle.getSpeedMode(veh_id)
                                if current_speed_mode != 0:  # Nếu bị reset, set lại
                                    traci.vehicle.setSpeedMode(veh_id, 0)
                    except Exception as e:
                        pass  # Không log để tránh spam

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
                    self.stop_scenario_spawning()
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
            "Độ trễ TB": 0.0,           # KPI 1: Average Delay
            "Hàng chờ TB": 0.0,         # KPI 2: Queue Length
            "Lưu lượng": 0,             # KPI 3: Throughput
            "Dừng TB": 0.0,             # KPI 4: Stops per Vehicle
            "Chờ tối đa": 0.0,          # KPI 5: Max Waiting Time
            "Chu kỳ TB": 0,             # KPI 6: Cycle Length
            "Công bằng": 0.0,           # KPI 7: Fairness Index
            "Giải phóng xe UT": 0.0        # KPI 8: Emergency Clearance Time
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
                # Dừng spawning xe ưu tiên nếu có
                self.stop_priority_spawning()
                # Spawn xe ưu tiên ngẫu nhiên từ MỌI hướng (khoảng 1 xe mỗi 30s)
                self.start_default_priority_spawning(interval=30)

            elif scenario_name == "SC1 - Xe ưu tiên từ hướng chính trong giờ cao điểm":
                self.log("🚓 SC1: Xe ưu tiên từ hướng chính (Bắc/Nam) - Chỉ spawn từ -E1, -E2, -E4, -E5.")
                # Xóa tất cả xe ưu tiên hiện có (từ dist_normal)
                self.clear_all_priority_vehicles()
                # Spawn xe ưu tiên từ Bắc/Nam định kỳ (hướng chính của cả 2 ngã tư)
                self.start_priority_spawning(["north", "south"], interval=20, scenario_id="SC1")

            elif scenario_name == "SC2 - Xe ưu tiên từ hướng nhánh (ít xe) sắp tới gần":
                self.log("🚙 SC2: Xe ưu tiên từ hướng nhánh (Tây) - Mô phỏng spawn xe.")
                self.clear_all_priority_vehicles()
                # Spawn xe ưu tiên từ Tây (hướng nhánh)
                self.start_priority_spawning(["west"], interval=20, scenario_id="SC2")

            elif scenario_name == "SC3 - Nhiều xe ưu tiên từ 2 hướng đối diện":
                self.log("🚒 SC3: Nhiều xe ưu tiên từ 2 hướng đối diện - Mô phỏng xung đột.")
                self.clear_all_priority_vehicles()
                # Spawn NHIỀU xe từ 2 hướng đối diện (test xung đột)
                self.start_priority_spawning(["north", "south"], interval=3, scenario_id="SC3")

            elif scenario_name == "SC4 - Báo giả":
                self.log("🚨 SC4: Báo giả - Chỉ log thông báo, không spawn xe thật.")
                self.clear_all_priority_vehicles()
                # Chỉ log thông báo báo giả, không spawn xe
                self.start_false_alarm_simulation(interval=30)

            elif scenario_name == "SC5 - Xe ưu tiên bị kẹt trong dòng xe dài":
                self.log("🚓 SC5: Xe ưu tiên bị kẹt - Spawn xe ở giữa dòng xe (departPos xa).")
                self.clear_all_priority_vehicles()
                # Spawn xe ưu tiên ở vị trí xa hơn (50-150m từ đầu route) để kẹt giữa dòng xe
                self.start_priority_spawning_stuck(["north", "south", "west"], interval=15, scenario_id="SC5")

            elif scenario_name == "SC6 - Nhiều xe ưu tiên liên tiếp":
                self.log("🚑 SC6: Nhiều xe ưu tiên liên tiếp - Spawn liên tục từ cùng hướng.")
                self.clear_all_priority_vehicles()
                # Spawn liên tiếp xe ưu tiên từ CÙNG hướng (North) mỗi 6-8s (TĂNG TẦN SUẤT)
                # Giảm interval xuống để thấy nhiều xe ưu tiên hơn
                self.start_priority_spawning_consecutive(["north"], base_interval=1, scenario_id="SC6")

            else:
                self.log("ℹ️ Không có kịch bản cụ thể, chạy mặc định.")

        except Exception as e:
            self.log(f"⚠ Không thể áp dụng kịch bản: {e}")
    
    def switch_flow_distribution(self, dist_id):
        """
        Chuyển đổi distribution type cho tất cả flows trong SUMO
        
        Args:
            dist_id: ID của distribution ("dist_normal" hoặc "dist_no_priority")
        """
        try:
            import traci
            
            # Lấy tất cả flow IDs
            all_flows = [f"flow_all_{i}" for i in range(31)]  # flow_all_0 đến flow_all_30
            
            changed_count = 0
            for flow_id in all_flows:
                try:
                    # Thay đổi type của flow sang distribution mới
                    traci.flow.setType(flow_id, dist_id)
                    changed_count += 1
                except:
                    # Flow có thể không tồn tại, bỏ qua
                    pass
            
            self.log(f"✅ Đã chuyển {changed_count} flows sang distribution '{dist_id}'")
            
        except Exception as e:
            self.log(f"⚠️ Lỗi khi chuyển distribution: {e}")
    
    def clear_all_priority_vehicles(self):
        """Xóa tất cả xe ưu tiên hiện có trong simulation"""
        try:
            import traci
            
            all_vehicles = traci.vehicle.getIDList()
            removed_count = 0
            
            for veh_id in all_vehicles:
                try:
                    veh_type = traci.vehicle.getTypeID(veh_id)
                    # Xóa xe nếu type là priority hoặc có chứa "priority" trong ID
                    if 'priority' in veh_type.lower() or 'priority' in veh_id.lower():
                        traci.vehicle.remove(veh_id)
                        removed_count += 1
                except:
                    continue
            
            if removed_count > 0:
                self.log(f"🗑️ Đã xóa {removed_count} xe ưu tiên từ simulation")
                
        except Exception as e:
            self.log(f"⚠️ Lỗi khi xóa xe ưu tiên: {e}")
    
    def init_priority_controllers(self):
        """Khởi tạo Priority Controllers cho các ngã tư - HỖ TRỢ CẢ 2 CHẾ ĐỘ"""
        if PriorityController is None:
            self.log("⚠️ PriorityController không khả dụng!")
            return
        
        # ✅ THAY ĐỔI: Cho phép khởi động ở cả 2 chế độ
        # - Chế độ Tự động: Priority Controller CAN THIỆP đèn giao thông
        # - Chế độ Mặc định: Priority Controller CHỈ THEO DÕI (monitoring) để tính KPI 8
        
        try:
            import traci
            tls_ids = traci.trafficlight.getIDList()
            
            for tls_id in tls_ids[:2]:  # J1 và J4
                junction_id = "J1" if tls_ids.index(tls_id) == 0 else "J4"
                
                # Lấy adaptive controller tương ứng nếu có (CHỈ chế độ Tự động)
                adaptive_ctrl = self.controllers.get(tls_id, None) if self.mode == "Tự động" else None
                
                # Tạo Priority Controller với UI callback
                priority_ctrl = PriorityController(
                    junction_id=junction_id, 
                    adaptive_controller=adaptive_ctrl,
                    ui_callback=self.on_priority_state_change  # Callback để update UI
                )
                
                # Khởi động controller
                if priority_ctrl.start():
                    self.priority_controllers[junction_id] = priority_ctrl
                    mode_info = "CAN THIỆP ĐÈN" if self.mode == "Tự động" else "CHỈ THEO DÕI (KPI 8)"
                    self.log(f"✅ PriorityController [{junction_id}] đã khởi động ({mode_info})")
                else:
                    self.log(f"❌ Không thể khởi động PriorityController [{junction_id}]")
        
        except Exception as e:
            self.log(f"⚠️ Lỗi khởi tạo Priority Controllers: {e}")
    
    def on_priority_state_change(self, junction_id, state, vehicle):
        """
        Callback được gọi khi PriorityController thay đổi state - CHỈ CHO CHẾ ĐỘ TỰ ĐỘNG
        Cập nhật UI để hiển thị trạng thái ưu tiên rõ ràng
        
        Args:
            junction_id: ID ngã tư (J1, J4)
            state: Trạng thái mới (NORMAL, DETECTION, PREEMPTION_GREEN, etc.)
            vehicle: EmergencyVehicle object hoặc None
        """
        # Chỉ xử lý callback khi ở chế độ Tự động
        if self.mode != "Tự động":
            return
            
        try:
            # Map state sang tiếng Việt và màu sắc
            state_info = {
                "NORMAL": ("⚪ Bình thường", "#64748b"),
                "DETECTION": ("🔍 PHÁT HIỆN XE ƯU TIÊN", "#f59e0b"),
                "SAFE_TRANSITION": ("⚠️ CHUYỂN ĐỔI AN TOÀN", "#f59e0b"),
                "PREEMPTION_GREEN": ("🚨 ƯU TIÊN ĐANG HOẠT ĐỘNG", "#ef4444"),
                "HOLD_PREEMPTION": ("⏳ GIỮ ĐÈN XANH", "#ef4444"),
                "RESTORE": ("🔄 KHÔI PHỤC", "#10b981")
            }
            
            text, color = state_info.get(state, ("", "#64748b"))
            
            # Cập nhật priority status label
            if state == "NORMAL":
                self.priority_status_label.configure(text="")
            else:
                veh_info = ""
                if vehicle:
                    veh_info = f" - {vehicle.vehicle_id}"
                self.priority_status_label.configure(
                    text=f"[{junction_id}] {text}{veh_info}",
                    text_color=color
                )
            
            # Log chi tiết với màu
            if state != "NORMAL":
                emoji_map = {
                    "DETECTION": "🔍",
                    "SAFE_TRANSITION": "🚦",
                    "PREEMPTION_GREEN": "🚨",
                    "HOLD_PREEMPTION": "⏳",
                    "RESTORE": "🔄"
                }
                emoji = emoji_map.get(state, "📍")
                
                if vehicle:
                    self.log(f"{emoji} [{junction_id}] {text} - Xe: {vehicle.vehicle_id} ({vehicle.direction})")
                else:
                    self.log(f"{emoji} [{junction_id}] {text}")
                    
        except Exception as e:
            print(f"⚠️ Error in UI callback: {e}")
    
    def handle_priority_vehicles(self, tls_ids):
        """
        Xử lý xe ưu tiên bằng Priority Controller - CHỈ CHO CHẾ ĐỘ TỰ ĐỘNG
        Gọi step() method của controller để tự động xử lý toàn bộ logic
        """
        # Chỉ xử lý xe ưu tiên khi ở chế độ Tự động
        if self.mode != "Tự động":
            return
            
        try:
            if not hasattr(self, 'priority_controllers') or not self.priority_controllers:
                return
            
            # Xử lý cho mỗi junction
            for junction_id, priority_ctrl in self.priority_controllers.items():
                try:
                    # Gọi step() - Controller tự động:
                    # 1. Quét và phát hiện xe ưu tiên (scan_for_emergency_vehicles)
                    # 2. Xác nhận xe (confirm_emergency_vehicle)
                    # 3. Chuyển đổi state machine (NORMAL → DETECTION → SAFE_TRANSITION → PREEMPTION_GREEN)
                    # 4. Áp dụng pha đèn khẩn cấp (apply_emergency_phase)
                    # 5. Khôi phục về bình thường (RESTORE)
                    success = priority_ctrl.step()
                    
                    if not success:
                        continue
                    
                    # Lấy status hiện tại và log state changes
                    status = priority_ctrl.get_status()
                    current_state = status.get('current_state', 'UNKNOWN')
                    
                    # Log state changes
                    if not hasattr(priority_ctrl, '_last_logged_state') or priority_ctrl._last_logged_state != current_state:
                        self.log(f"🚦 [{junction_id}] Priority State: {current_state}")
                        self.log(f"    Detected: {status.get('detected_vehicles', 0)}, Confirmed: {status.get('confirmed_vehicles', 0)}")
                        priority_ctrl._last_logged_state = current_state
                
                except Exception as e:
                    self.log(f"⚠️ Lỗi trong Priority Controller [{junction_id}]: {e}")
        
        except Exception as e:
            self.log(f"⚠️ Lỗi handle_priority_vehicles: {e}")
    
    def start_false_alarm_simulation(self, interval=30):
        """
        SC4: Mô phỏng báo giả - Tín hiệu phát hiện xe ưu tiên nhưng không có xe thật
        Logic: PriorityController sẽ tự động phát hiện và timeout do không xác nhận được xe thật
        Trong SC4, không spawn xe thật, controller sẽ từ chối false positive nhờ xác nhận kép
        """
        def simulate_false_alarm():
            while self.running and hasattr(self, 'false_alarm_active') and self.false_alarm_active:
                try:
                    # Chỉ log - Priority Controller sẽ tự quét và không tìm thấy xe
                    self.log("⚠️ [SC4-FALSE_ALARM] Chế độ test báo giả - PriorityController đang quét nhưng không phát hiện xe thật.")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.log(f"❌ Lỗi trong false alarm simulation: {e}")
                    break
        
        self.false_alarm_active = True
        threading.Thread(target=simulate_false_alarm, daemon=True).start()
    
    def start_default_priority_spawning(self, interval=100):
        """
        Spawn xe ưu tiên cho kịch bản Mặc định
        Mô phỏng 0.3% xe ưu tiên random từ mọi hướng
        
        Args:
            interval: Khoảng thời gian giữa các lần spawn (giây)
        """
        # Dừng spawning cũ nếu có
        self.stop_priority_spawning()
        
        # Đánh dấu spawning đang hoạt động
        self.spawning_active = True
        
        def spawn_loop():
            """Loop spawn xe ưu tiên ngẫu nhiên cho mode Mặc định"""
            import time
            import random
            
            all_directions = ["north", "south", "east", "west"]
            
            while self.spawning_active:
                try:
                    # Chọn ngẫu nhiên một hướng
                    direction = random.choice(all_directions)
                    self.spawn_priority_vehicle(direction, "DEFAULT")
                    
                    # Đợi interval giây
                    time.sleep(interval)
                    
                except Exception as e:
                    self.log(f"⚠ Lỗi trong default spawn loop: {e}")
                    time.sleep(5)
        
        # Tạo và khởi chạy thread
        import threading
        self.spawning_thread = threading.Thread(target=spawn_loop, daemon=True)
        self.spawning_thread.start()
        self.log(f"🔄 Đã bắt đầu spawn xe ưu tiên ngẫu nhiên mỗi {interval}s (mode Mặc định)")
    
    def get_direction_from_edge(self, edge_id: str, junction_id: str) -> str:
        """
        Xác định hướng dựa trên edge ID
        
        Returns:
            "north", "south", "east", "west" hoặc None
        """
        # Mapping cho J1
        if junction_id == "J1":
            if "-E1" in edge_id:
                return "north"
            elif "-E2" in edge_id:
                return "south"
            elif "E0" in edge_id and "-E0" not in edge_id:
                return "west"
            elif "-E3" in edge_id:  # Từ J4 sang
                return "east"
        
        # Mapping cho J4
        elif junction_id == "J4":
            if "-E4" in edge_id:
                return "north"
            elif "-E5" in edge_id:
                return "south"
            elif "-E6" in edge_id:
                return "west"
            elif "E3" in edge_id and "-E3" not in edge_id:  # Từ J1 sang
                return "east"
        
        return None
    
    def start_priority_spawning(self, directions, interval=15, scenario_id="SC"):
        """Bắt đầu spawn xe ưu tiên định kỳ từ các hướng chỉ định
        
        Args:
            directions: List các hướng ["north", "south", "east", "west"]
            interval: Khoảng thời gian giữa các lần spawn (giây)
            scenario_id: ID của kịch bản (SC1, SC2, ...)
        """
        # Dừng spawning cũ nếu có
        self.stop_priority_spawning()
        
        # Đánh dấu spawning đang hoạt động
        self.spawning_active = True
        
        def spawn_loop():
            """Loop chạy trong thread riêng để spawn xe định kỳ"""
            import time
            import random
            
            while self.spawning_active:
                try:
                    # Chọn ngẫu nhiên một hướng từ danh sách
                    direction = random.choice(directions)
                    self.spawn_priority_vehicle(direction, scenario_id)
                    
                    # Đợi interval giây
                    time.sleep(interval)
                    
                except Exception as e:
                    self.log(f"⚠ Lỗi trong spawn loop: {e}")
                    time.sleep(5)  # Đợi 5s nếu có lỗi
        
        # Tạo và khởi chạy thread
        import threading
        self.spawning_thread = threading.Thread(target=spawn_loop, daemon=True)
        self.spawning_thread.start()
        self.log(f"🔄 Đã bắt đầu spawn xe ưu tiên từ {directions} mỗi {interval}s")
    
    def start_priority_spawning_stuck(self, directions, interval=15, scenario_id="SC5"):
        """Bắt đầu spawn xe ưu tiên ở VỊ TRÍ XA (giữa dòng xe) để mô phỏng kẹt xe
        
        Args:
            directions: List các hướng ["north", "south", "east", "west"]
            interval: Khoảng thời gian giữa các lần spawn (giây)
            scenario_id: ID của kịch bản (mặc định SC5)
        """
        # Dừng spawning cũ nếu có
        self.stop_priority_spawning()
        
        # Đánh dấu spawning đang hoạt động
        self.spawning_active = True
        
        def spawn_stuck_loop():
            """Loop spawn xe ưu tiên SAU dòng xe bình thường (bị kẹt)"""
            import time
            import random
            import traci
            
            while self.spawning_active:
                try:
                    # Chọn ngẫu nhiên một hướng
                    direction = random.choice(directions)
                    
                    # CÁCH MỚI: Spawn nhiều xe bình thường trước, sau đó spawn xe ưu tiên
                    # → Xe ưu tiên sẽ tự động xếp SAU dòng xe → BỊ KẸT
                    
                    # Route mapping
                    j1_routes = {
                        "north": ["r5", "r6", "r7", "r8", "r9"],
                        "south": ["r10", "r11", "r12", "r13", "r14"],
                        "west": ["r0", "r1", "r2"],
                    }
                    j4_routes = {
                        "north": ["r15", "r16", "r17", "r18", "r19"],
                        "south": ["r20", "r21", "r22", "r23", "r24"],
                        "west": ["r25", "r26", "r27"]
                    }
                    
                    direction_names = {"north": "Bắc", "south": "Nam", "west": "Tây"}
                    dir_name = direction_names.get(direction, "Không xác định")
                    
                    # 1. Spawn 3-5 xe bình thường trước (tạo "dòng xe dài")
                    num_normal_cars = random.randint(3, 5)
                    for i in range(num_normal_cars):
                        if direction in j1_routes:
                            route = random.choice(j1_routes[direction])
                            normal_id = f"normal_block_{int(traci.simulation.getTime())}_{i}"
                            try:
                                traci.vehicle.add(normal_id, route, typeID="car_normal", departSpeed="max")
                                time.sleep(0.2)  # Delay nhỏ giữa các xe
                            except:
                                pass
                    
                    # 2. Đợi 1-2 giây để xe bình thường chạy xa một chút
                    time.sleep(random.uniform(1, 2))
                    
                    # 3. BÂY GIỜ spawn xe ưu tiên → nó sẽ ở SAU dòng xe bình thường → BỊ KẸT!
                    self.spawn_priority_vehicle(direction, scenario_id, depart_pos="base")
                    
                    self.log(f"🚗🚗🚓 SC5: Đã tạo dòng xe {num_normal_cars} xe + 1 xe ưu tiên BỊ KẸT từ {dir_name}")
                    
                    # Đợi interval giây
                    time.sleep(interval)
                    
                except Exception as e:
                    self.log(f"⚠ Lỗi trong spawn stuck loop: {e}")
                    time.sleep(5)
        
        # Tạo và khởi chạy thread
        import threading
        self.spawning_thread = threading.Thread(target=spawn_stuck_loop, daemon=True)
        self.spawning_thread.start()
        self.log(f"🔄 SC5: Spawn xe BỊ KẸT (spawn sau dòng xe bình thường) từ {directions} mỗi {interval}s")
    
    def start_priority_spawning_consecutive(self, directions, base_interval=12, scenario_id="SC6"):
        """SC6: Spawn nhiều xe ưu tiên LIÊN TIẾP từ cùng hướng
        
        Mô phỏng tình huống: Vừa cho xe cứu thương đi qua, 10-20s sau lại có xe khác cùng hướng.
        
        Args:
            directions: List các hướng (thường chỉ 1 hướng cho rõ ràng)
            base_interval: Khoảng thời gian cơ bản giữa các xe (giây)
            scenario_id: ID kịch bản (mặc định SC6)
        """
        # Dừng spawning cũ nếu có
        self.stop_priority_spawning()
        
        # Đánh dấu spawning đang hoạt động
        self.spawning_active = True
        
        def spawn_consecutive_loop():
            """Loop spawn xe ưu tiên liên tiếp từ cùng hướng"""
            import time
            import random
            
            consecutive_count = 0
            
            while self.spawning_active:
                try:
                    # Luôn chọn cùng 1 hướng (hoặc random từ list nhỏ)
                    direction = directions[0] if len(directions) == 1 else random.choice(directions)
                    
                    # Spawn xe ưu tiên
                    consecutive_count += 1
                    self.spawn_priority_vehicle(direction, f"{scenario_id}_consecutive_{consecutive_count}", depart_pos="base")
                    
                    direction_names = {"north": "Bắc", "south": "Nam", "west": "Tây"}
                    dir_name = direction_names.get(direction, "Không xác định")
                    
                    # Log tình huống liên tiếp
                    self.log(f"🚑🚑 SC6-CONSECUTIVE: Xe ưu tiên #{consecutive_count} từ {dir_name} (liên tiếp)")
                    
                    # Interval biến đổi nhẹ (5-9s) - NHANH HƠN để thấy nhiều xe
                    actual_interval = base_interval + random.uniform(-1, 2)
                    
                    # Đợi trước khi spawn xe tiếp theo
                    time.sleep(actual_interval)
                    
                except Exception as e:
                    self.log(f"⚠ Lỗi trong consecutive spawn loop: {e}")
                    time.sleep(5)
        
        # Tạo và khởi chạy thread
        import threading
        self.spawning_thread = threading.Thread(target=spawn_consecutive_loop, daemon=True)
        self.spawning_thread.start()
        self.log(f"🔄 SC6: Spawn xe ưu tiên LIÊN TIẾP từ {directions} mỗi ~{base_interval}s (±2-3s)")
    
    def start_false_alarm_simulation(self, interval=30):
        """Mô phỏng báo giả - spawn xe rồi xóa ngay để giả lập tín hiệu sai
        
        Args:
            interval: Khoảng thời gian giữa các lần báo giả (giây)
        """
        # Dừng spawning cũ nếu có
        self.stop_priority_spawning()
        
        # Đánh dấu spawning đang hoạt động
        self.spawning_active = True
        
        def false_alarm_loop():
            """Loop chạy trong thread để tạo tín hiệu báo giả"""
            import time
            import random
            
            directions = ["north", "south", "west"]
            direction_names = {"north": "Bắc", "south": "Nam", "west": "Tây"}
            
            while self.spawning_active:
                try:
                    # Chọn ngẫu nhiên hướng
                    direction = random.choice(directions)
                    dir_name = direction_names.get(direction, "Không xác định")
                    
                    # Spawn xe để tạo tín hiệu
                    self.log(f"⚠️ BÁOGIẢ - Phát hiện tín hiệu xe ưu tiên từ {dir_name}")
                    spawned_vehicles = self.spawn_priority_vehicle(direction, "SC4_FALSE")
                    
                    # Đợi 2-3 giây (giả lập thời gian phát hiện)
                    time.sleep(random.uniform(2, 3))
                    
                    # Xóa xe ngay (mô phỏng báo giả - xe không thật)
                    if spawned_vehicles:
                        try:
                            import traci
                            for veh_id in spawned_vehicles:
                                if veh_id in traci.vehicle.getIDList():
                                    traci.vehicle.remove(veh_id)
                            self.log(f"🗑️ BÁOGIẢ - Đã xóa xe giả [{len(spawned_vehicles)} xe] - Tín hiệu sai!")
                        except Exception as remove_err:
                            self.log(f"⚠ Lỗi khi xóa xe báo giả: {remove_err}")
                    
                    # Đợi interval giây trước lần báo giả tiếp theo
                    time.sleep(interval)
                    
                except Exception as e:
                    self.log(f"⚠ Lỗi trong false alarm loop: {e}")
                    time.sleep(5)
        
        # Tạo và khởi chạy thread
        import threading
        self.spawning_thread = threading.Thread(target=false_alarm_loop, daemon=True)
        self.spawning_thread.start()
        self.log(f"🔄 Đã bắt đầu mô phỏng báo giả mỗi {interval}s (spawn xe → xóa ngay)")
    
    def stop_priority_spawning(self):
        """Dừng việc spawn xe ưu tiên"""
        if self.spawning_active:
            self.spawning_active = False
            if self.spawning_thread:
                self.spawning_thread.join(timeout=2)
            self.log("⏹ Đã dừng spawn xe ưu tiên")
    
    def spawn_priority_vehicle(self, direction, scenario_id, depart_pos="base"):
        """Spawn một xe ưu tiên từ hướng chỉ định - ở CẢ 2 ngã tư (J1 và J4)
        
        Args:
            direction: Hướng spawn ("north", "south", "west")
            scenario_id: ID kịch bản (SC1, SC2, SC5...)
            depart_pos: Vị trí spawn - "base" (đầu route) hoặc số mét từ đầu route
        
        Returns:
            List các vehicle ID đã spawn thành công (để xóa trong trường hợp false alarm)
        """
        spawned_vehicle_ids = []
        
        try:
            import traci
            current_time = traci.simulation.getTime()
            
            # Đếm số xe ưu tiên hiện tại
            all_vehicles = traci.vehicle.getIDList()
            priority_count = sum(1 for v in all_vehicles if 'priority' in v)
            
            # Định nghĩa routes cho CẢ 2 ngã tư
            # Ngã tư J1 (giao lộ chính với E0, E1, E2, E3)
            j1_routes = {
                "north": ["r5", "r6", "r7", "r8", "r9"],     # Từ Bắc (-E1) J1 - hướng chính
                "south": ["r10", "r11", "r12", "r13", "r14"],  # Từ Nam (-E2) J1 - hướng chính
                "west": ["r0", "r1", "r2"],      # Từ Tây (E0) J1 - hướng nhánh
            }
            
            # Ngã tư J4 (giao lộ phụ với E4, E5, E6, E3)
            j4_routes = {
                "north": ["r15", "r16", "r17", "r18", "r19"],         # Từ Bắc (-E4) J4 - hướng chính
                "south": ["r20", "r21", "r22", "r23", "r24"],  # Từ Nam (-E5) J4 - hướng chính
                "west": ["r25", "r26", "r27"]    # Từ Tây (-E6) J4 - hướng nhánh
            }
            
            direction_names = {
                "north": "Bắc",
                "south": "Nam", 
                "east": "Đông",
                "west": "Tây"
            }
            
            dir_name = direction_names.get(direction, "Không xác định")
            
            # Spawn xe ở CẢNG 2 ngã tư
            import random
            spawned_count = 0
            
            # 1. Spawn ở ngã tư J1
            if direction in j1_routes:
                route_j1 = random.choice(j1_routes[direction])
                veh_id_j1 = f"priority_{scenario_id}_{direction}_J1_{int(current_time)}"
                
                try:
                    # Convert depart_pos to proper format for SUMO
                    if isinstance(depart_pos, (int, float)):
                        pos_param = str(float(depart_pos))
                    else:
                        pos_param = depart_pos
                    
                    traci.vehicle.add(
                        veh_id_j1, 
                        route_j1, 
                        typeID="priority",
                        departPos=pos_param,
                        departSpeed="random",
                        departLane="best"
                    )
                    
                    # Kiểm tra spawn thành công
                    import time
                    time.sleep(0.3)
                    if veh_id_j1 in traci.vehicle.getIDList():
                        edge = traci.vehicle.getRoadID(veh_id_j1)
                        
                        # CHO PHÉP XE ƯU TIÊN VƯỢT ĐÈN ĐỎ
                        # speedMode = 0: Bỏ qua TẤT CẢ quy tắc (aggressive mode)
                        # speedMode = 32: Chỉ bỏ qua traffic lights
                        try:
                            traci.vehicle.setSpeedMode(veh_id_j1, 0)  # Thử mode 0 - bỏ qua tất cả
                            self.log(f"🚨 [{veh_id_j1}] Đã set speedMode=0 (ignore ALL rules)")
                        except Exception as e:
                            self.log(f"❌ Lỗi set speedMode cho {veh_id_j1}: {e}")
                        
                        # ĐỔI MÀU XE ƯU TIÊN ĐỂ DỄ NHÌN - Màu đỏ nổi bật
                        traci.vehicle.setColor(veh_id_j1, (255, 0, 0, 255))  # Đỏ rực
                        
                        spawned_count += 1
                        spawned_vehicle_ids.append(veh_id_j1)
                        pos_info = f"@ {depart_pos}m" if isinstance(depart_pos, (int, float)) else "đầu route"
                        self.log(f"🚨 Spawn xe ưu tiên từ {dir_name} tại J1 [{veh_id_j1}] - Edge: {edge} ({pos_info})")
                except Exception as e:
                    # Log lỗi nếu spawn thất bại
                    if "depart" in str(e).lower():
                        self.log(f"⚠ J1: departPos {depart_pos}m quá xa, thử lại với 'base'")
                    pass
            
            # 2. Spawn ở ngã tư J4
            if direction in j4_routes:
                route_j4 = random.choice(j4_routes[direction])
                veh_id_j4 = f"priority_{scenario_id}_{direction}_J4_{int(current_time)}"
                
                try:
                    # Convert depart_pos to proper format for SUMO
                    if isinstance(depart_pos, (int, float)):
                        pos_param = str(float(depart_pos))
                    else:
                        pos_param = depart_pos
                    
                    traci.vehicle.add(
                        veh_id_j4, 
                        route_j4, 
                        typeID="priority",
                        departPos=pos_param,
                        departSpeed="random",
                        departLane="best"
                    )
                    
                    # Kiểm tra spawn thành công
                    import time
                    time.sleep(0.3)
                    if veh_id_j4 in traci.vehicle.getIDList():
                        edge = traci.vehicle.getRoadID(veh_id_j4)
                        
                        # CHO PHÉP XE ƯU TIÊN VƯỢT ĐÈN ĐỎ
                        try:
                            traci.vehicle.setSpeedMode(veh_id_j4, 0)  # Thử mode 0 - bỏ qua tất cả
                            self.log(f"🚨 [{veh_id_j4}] Đã set speedMode=0 (ignore ALL rules)")
                        except Exception as e:
                            self.log(f"❌ Lỗi set speedMode cho {veh_id_j4}: {e}")
                        
                        # ĐỔI MÀU XE ƯU TIÊN ĐỂ DỄ NHÌN - Màu đỏ nổi bật
                        traci.vehicle.setColor(veh_id_j4, (255, 0, 0, 255))  # Đỏ rực
                        
                        spawned_count += 1
                        spawned_vehicle_ids.append(veh_id_j4)
                        pos_info = f"@ {depart_pos}m" if isinstance(depart_pos, (int, float)) else "đầu route"
                        self.log(f"🚨 Spawn xe ưu tiên từ {dir_name} tại J4 [{veh_id_j4}] - Edge: {edge} ({pos_info})")
                except Exception as e:
                    # Log lỗi nếu spawn thất bại
                    if "depart" in str(e).lower():
                        self.log(f"⚠ J4: departPos {depart_pos}m quá xa, thử lại với 'base'")
                    pass
            
            if spawned_count > 0:
                self.log(f"📊 Đã spawn {spawned_count} xe ưu tiên từ hướng {dir_name} (Tổng: {priority_count + spawned_count} xe)")
                
        except Exception as e:
            # Bỏ qua lỗi tổng quát
            pass
        
        return spawned_vehicle_ids

    # ============ Update data from SUMO & UI ============
    def update_data_from_sumo(self):
        """
        Lấy dữ liệu thực từ SUMO và tính toán KPI theo CÔNG THỨC NHÓM:
        
        KPI CHÍNH (8 chỉ số - sắp xếp từ trái sang phải, trên xuống dưới):
        1. Độ trễ TB (Average Delay): travelTime - freeFlowTime (s/xe)
        2. Hàng chờ TB (Average Queue Length): Số xe chờ trung bình (PCU)
        3. Lưu lượng (Throughput): Số xe qua giao lộ/giờ (xe/h hoặc PCU/h)
        4. Dừng TB (Average Stops): Số lần dừng trung bình/xe
        5. Chờ tối đa (Maximum Waiting Time): Thời gian chờ lâu nhất (s)
        6. Chu kỳ TB (Average Cycle): Chu kỳ đèn trung bình (s)
        7. Công bằng (Fairness Index): So sánh max và trung bình wait time (%)
        8. Giải phóng xe UT (Emergency Clearance Time): Thời gian giải phóng xe ưu tiên (s) - Cả 2 chế độ
        
        METRICS PHỤ (theo ngã tư):
        - Queue length: Số xe đang chờ
        - Wait time: Thời gian chờ trung bình tại ngã tư
        - Số xe theo hướng (Bắc/Nam/Đông/Tây)
        """
        try:
            import traci
        except Exception:
            return

        try:
            tls_ids = traci.trafficlight.getIDList()
            if not tls_ids:
                return

            # ===== LẤY DỮ LIỆU TỪ TRACI =====
            current_time = traci.simulation.getTime()
            all_vehicle_ids = traci.vehicle.getIDList()
            departed_count = traci.simulation.getDepartedNumber()
            arrived_count = traci.simulation.getArrivedNumber()
            total_vehicles_in_sim = len(all_vehicle_ids)
            
            # === BƯỚC 1: Đếm xe qua VehicleCounter ===
            vehicle_counts = None
            if self.vehicle_counter is not None:
                try:
                    self.vehicle_counter.count_vehicles_on_edges()
                    vehicle_counts = self.vehicle_counter.get_current_counts()
                except Exception as vc_err:
                    vehicle_counts = None
            
            # === BƯỚC 2: Tính KPI cho TỪNG xe ===
            # PCU conversion factors (Việt Nam standard)
            PCU_FACTORS = {
                "motorcycle": 0.3,
                "car": 1.0,
                "bus": 1.5,
                "truck": 1.5,
                "emergency": 1.0
            }
            
            # Variables để tính các KPI
            total_delay = 0.0           # Sum of (travelTime - freeFlowTime)
            total_waiting_time = 0.0    # Sum of waiting time
            total_stops = 0             # Sum of stops
            max_waiting_time = 0.0      # Maximum waiting time
            total_pcu = 0.0             # Total PCU
            total_queue_pcu = 0.0       # Total queue in PCU
            vehicles_with_data = 0
            
            # Vehicle-specific tracking cho stops
            if not hasattr(self, '_vehicle_stop_tracker'):
                self._vehicle_stop_tracker = {}  # {veh_id: {"last_speed": 0, "stops": 0}}
            
            for vid in all_vehicle_ids:
                try:
                    # === 1. AVERAGE DELAY (s/xe) ===
                    # Công thức: Delay = travelTime - freeFlowTime
                    # freeFlowTime = route_length / max_speed
                    route_id = traci.vehicle.getRouteID(vid)
                    route_edges = traci.route.getEdges(route_id)
                    
                    # Tính freeFlowTime (thời gian lý tưởng không dừng)
                    free_flow_time = 0.0
                    for edge_id in route_edges:
                        try:
                            edge_length = traci.lane.getLength(f"{edge_id}_0")  # Giả sử lane 0
                            max_speed = traci.lane.getMaxSpeed(f"{edge_id}_0")
                            free_flow_time += edge_length / max_speed if max_speed > 0 else 0
                        except Exception:
                            continue
                    
                    # Tính travelTime (thời gian thực tế)
                    # SUMO không trực tiếp cho travelTime, dùng: departTime + accumulated time
                    depart_delay = traci.vehicle.getDeparture(vid)
                    if depart_delay >= 0:  # Xe đã xuất phát
                        travel_time = current_time - depart_delay
                        delay = max(0, travel_time - free_flow_time)
                        total_delay += delay
                    
                    # === 2. WAITING TIME (cho Fairness) ===
                    waiting_time = traci.vehicle.getWaitingTime(vid)
                    total_waiting_time += waiting_time
                    max_waiting_time = max(max_waiting_time, waiting_time)
                    
                    # === 3. AVERAGE STOPS (số lần dừng/xe) ===
                    speed = traci.vehicle.getSpeed(vid)
                    
                    if vid not in self._vehicle_stop_tracker:
                        self._vehicle_stop_tracker[vid] = {"last_speed": speed, "stops": 0}
                    
                    tracker = self._vehicle_stop_tracker[vid]
                    
                    # Detect stop: từ speed > 0.1 → speed < 0.1
                    if tracker["last_speed"] > 0.1 and speed < 0.1:
                        tracker["stops"] += 1
                    
                    tracker["last_speed"] = speed
                    total_stops += tracker["stops"]
                    
                    # === 4. QUEUE LENGTH (PCU) ===
                    # Xe đang chờ (speed < 0.1 m/s)
                    vtype = traci.vehicle.getTypeID(vid)
                    pcu_factor = PCU_FACTORS.get(vtype, 1.0)
                    total_pcu += pcu_factor
                    
                    if speed < 0.1:
                        total_queue_pcu += pcu_factor
                    
                    vehicles_with_data += 1
                    
                except Exception:
                    continue
            
            # Clean up departed vehicles từ tracker
            current_vehicles = set(all_vehicle_ids)
            departed_vehicles = set(self._vehicle_stop_tracker.keys()) - current_vehicles
            for departed_vid in departed_vehicles:
                del self._vehicle_stop_tracker[departed_vid]
            
            # === TÍNH CÁC KPI TRUNG BÌNH ===
            
            # 1. ĐỘ TRỄ TB (Average Delay - s/xe) - KPI 1
            avg_delay = round(total_delay / vehicles_with_data, 1) if vehicles_with_data > 0 else 0.0
            
            # 2. HÀNG CHỜ TB (Average Queue Length - PCU) - KPI 2
            avg_queue_pcu = round(total_queue_pcu, 1)
            
            # 3. LƯU LƯỢNG (Throughput - xe/giờ) - KPI 3
            if current_time > 0:
                time_hours = current_time / 3600.0
                throughput = int(arrived_count / time_hours) if time_hours > 0 else 0
            else:
                throughput = 0
            
            # 4. DỪNG TB (Average Stops per Vehicle - lần) - KPI 4
            avg_stops = round(total_stops / vehicles_with_data, 2) if vehicles_with_data > 0 else 0.0
            
            # 5. CHỜ TỐI ĐA (Maximum Waiting Time - s) - KPI 5
            # Mục tiêu: < 60s (tốt), < 120s (chấp nhận được)
            max_wait = round(max_waiting_time, 1)

            # === BƯỚC 3: Cập nhật dữ liệu cho TỪNG ngã tư ===
            intersection_wait_times = []  # Để tính Fairness
            
            for i, tls_id in enumerate(tls_ids[:2]):
                int_name = f"Ngã tư {i+1}"
                junction_id = "J1" if i == 0 else "J4"
                
                if int_name not in self.intersection_data:
                    continue

                # --- Lấy trạng thái đèn ---
                try:
                    state = traci.trafficlight.getRedYellowGreenState(tls_id)
                    if "G" in state:
                        self.intersection_data[int_name]["light_state"] = "Xanh"
                    elif "y" in state.lower():
                        self.intersection_data[int_name]["light_state"] = "Vàng"
                    elif all(ch == "r" for ch in state.lower()):
                        self.intersection_data[int_name]["light_state"] = "Đỏ Toàn Phần"
                    else:
                        self.intersection_data[int_name]["light_state"] = "Đỏ"
                except Exception:
                    self.intersection_data[int_name]["light_state"] = "Đỏ"

                # --- Sử dụng dữ liệu từ VehicleCounter ---
                if vehicle_counts and junction_id in vehicle_counts:
                    junction_vehicles = vehicle_counts[junction_id]
                    self.intersection_data[int_name]["vehicles"] = junction_vehicles.copy()
                    total_junction_vehicles = sum(junction_vehicles.values())
                    self.intersection_data[int_name]["queue"] = total_junction_vehicles
                else:
                    # Fallback
                    self.intersection_data[int_name]["vehicles"] = {
                        "Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0
                    }
                    self.intersection_data[int_name]["queue"] = 0
                
                # --- Wait time cho ngã tư này ---
                junction_wait_time = 0.0
                junction_vehicle_count = 0
                
                # Tính wait time cho các xe gần ngã tư này
                try:
                    for vid in all_vehicle_ids:
                        try:
                            edge_id = traci.vehicle.getRoadID(vid)
                            # Kiểm tra xe có thuộc junction này không
                            if junction_id == "J1" and any(e in edge_id for e in ["-E1", "-E2", "E0", "-E3"]):
                                junction_wait_time += traci.vehicle.getWaitingTime(vid)
                                junction_vehicle_count += 1
                            elif junction_id == "J4" and any(e in edge_id for e in ["-E4", "-E5", "-E6", "E3"]):
                                junction_wait_time += traci.vehicle.getWaitingTime(vid)
                                junction_vehicle_count += 1
                        except Exception:
                            continue
                    
                    avg_junction_wait = round(
                        junction_wait_time / junction_vehicle_count, 1
                    ) if junction_vehicle_count > 0 else 0.0
                    
                    self.intersection_data[int_name]["wait_time"] = avg_junction_wait
                    intersection_wait_times.append(avg_junction_wait)
                    
                except Exception:
                    self.intersection_data[int_name]["wait_time"] = 0.0
                    intersection_wait_times.append(0.0)

            # === BƯỚC 4: Tính các KPI TOÀN CỤC còn lại ===
            
            # 7. CHU KỲ TB (Average Cycle - s)
            if self.mode == "Tự động" and self.controllers:
                # Adaptive mode: Lấy từ controller history
                cycle_times = []
                for tls_id, ctrl in self.controllers.items():
                    try:
                        if hasattr(ctrl, 'phase_history') and len(ctrl.phase_history) > 0:
                            recent_phases = ctrl.phase_history[-10:]  # 10 phases gần nhất
                            cycle_time = sum(duration for _, _, duration in recent_phases) / len(recent_phases)
                            cycle_times.append(cycle_time)
                    except Exception:
                        pass
                
                avg_cycle = int(sum(cycle_times) / len(cycle_times)) if cycle_times else (self.green_time + self.yellow_time + self.red_time) * 2
            else:
                # Fixed-time mode
                avg_cycle = int((self.green_time + self.yellow_time + self.red_time) * 2)  # NS + EW
            
            # 8. CÔNG BẰNG (Fairness Index - %)
            # Công thức từ tài liệu: So sánh thời gian chờ lớn nhất và trung bình
            # Fairness = (1 - (max_wait - mean_wait) / max_wait) * 100
            # Giá trị cao (100%) = rất công bằng
            if len(intersection_wait_times) > 0 and sum(intersection_wait_times) > 0:
                mean_wait = sum(intersection_wait_times) / len(intersection_wait_times)
                max_wait_intersection = max(intersection_wait_times)
                
                if max_wait_intersection > 0:
                    fairness = round((1 - (max_wait_intersection - mean_wait) / max_wait_intersection) * 100, 1)
                    fairness = max(0, min(100, fairness))  # Clamp 0-100%
                else:
                    fairness = 100.0
            else:
                fairness = 100.0
            
            # 8. Giải phóng xe UT (Emergency Clearance Time - s) - KPI 8
            # ✅ Tính toán cho CẢ 2 CHẾ ĐỘ (Mặc định + Tự động)
            # ✅ REALTIME: Hiển thị elapsed time cho xe đang theo dõi, hoặc average cho xe đã qua
            emergency_clearance = 0.0
            if hasattr(self, 'priority_controllers') and self.priority_controllers:
                # Ưu tiên 1: Hiển thị REALTIME elapsed time cho xe đang được theo dõi (confirmed vehicles)
                realtime_elapsed = None
                for junction_id, priority_ctrl in self.priority_controllers.items():
                    if hasattr(priority_ctrl, 'confirmed_vehicles') and priority_ctrl.confirmed_vehicles:
                        # Có xe đang được theo dõi → hiển thị elapsed time từ khi phát hiện
                        for vid, vehicle in priority_ctrl.confirmed_vehicles.items():
                            if hasattr(vehicle, 'detection_time'):
                                elapsed = current_time - vehicle.detection_time  # current_time đã có sẵn từ trên
                                if realtime_elapsed is None or elapsed > realtime_elapsed:
                                    realtime_elapsed = elapsed  # Lấy xe có elapsed time cao nhất
                                print(f"⏱️ REALTIME KPI 8: Xe {vid} đang theo dõi - Elapsed = {elapsed:.1f}s")
                
                # Ưu tiên 2: Nếu không có xe realtime, hiển thị average của xe đã qua
                if realtime_elapsed is not None:
                    emergency_clearance = round(realtime_elapsed, 1)
                else:
                    # Tính average từ clearance_times (xe đã qua)
                    clearance_times = []
                    for junction_id, priority_ctrl in self.priority_controllers.items():
                        if hasattr(priority_ctrl, 'clearance_times') and len(priority_ctrl.clearance_times) > 0:
                            clearance_times.extend(priority_ctrl.clearance_times)
                            print(f"🔍 DEBUG KPI 8 [{junction_id}]: {len(priority_ctrl.clearance_times)} clearance times = {priority_ctrl.clearance_times}")
                    
                    if clearance_times:
                        emergency_clearance = round(sum(clearance_times) / len(clearance_times), 1)
                        print(f"🔍 DEBUG KPI 8: Average = {emergency_clearance}s (từ {len(clearance_times)} xe đã qua)")
                    else:
                        print(f"🔍 DEBUG KPI 8: Không có xe (chưa phát hiện xe ưu tiên)")

            # === CẬP NHẬT GLOBAL KPI ===
            self.global_kpi_data = {
                "Độ trễ TB": avg_delay,            # KPI 1
                "Hàng chờ TB": avg_queue_pcu,      # KPI 2
                "Lưu lượng": throughput,           # KPI 3
                "Dừng TB": avg_stops,              # KPI 4
                "Chờ tối đa": max_wait,            # KPI 5
                "Chu kỳ TB": avg_cycle,            # KPI 6
                "Công bằng": fairness,             # KPI 7
                "Giải phóng xe UT": emergency_clearance  # KPI 8 (CẢ 2 CHẾ ĐỘ)
            }
            
            # === BƯỚC 5: Cập nhật Sensor Data (E1/E2 Detectors) ===
            if self.sensor_manager:
                try:
                    summary = self.sensor_manager.get_summary()
                    
                    # Tính mật độ và queue trung bình từ E2 detectors
                    total_occupancy = 0
                    total_queue_length = 0
                    detector_count = 0
                    
                    for junction_id in ["J1", "J4"]:
                        densities = self.sensor_manager.get_all_junction_densities(junction_id)
                        for direction, data in densities.items():
                            if "error" not in data:
                                # Mật độ = occupancy * 100
                                occupancy = data.get("occupancy", 0) * 100
                                total_occupancy += occupancy
                                total_queue_length += data["queue_length"]
                                detector_count += 1
                    
                    avg_occupancy = round(total_occupancy / detector_count, 1) if detector_count > 0 else 0
                    avg_queue_meters = round(total_queue_length / detector_count, 1) if detector_count > 0 else 0
                    
                    self.sensor_data = {
                        "E1 Detectors": summary.get("e1_count", 0),
                        "E2 Detectors": summary.get("e2_count", 0),
                        "Mật độ TB": avg_occupancy,
                        "Queue TB": avg_queue_meters
                    }
                except Exception:
                    pass
            
            # === BƯỚC 6: Cập nhật dữ liệu xe ưu tiên ===
            self.update_priority_vehicle_data()
            
            # === LOG ĐỊNH KỲ (mỗi 10 giây) ===
            if not hasattr(self, '_last_kpi_log_time'):
                self._last_kpi_log_time = 0
            
            if current_time - self._last_kpi_log_time >= 10:
                self._last_kpi_log_time = current_time
                # Log KPI với Tổng xe ở đầu
                if emergency_clearance > 0:
                    self.log(f"📊 KPI | Xe:{total_vehicles_in_sim} | Delay:{avg_delay}s/xe | Throughput:{throughput}xe/h | Queue:{avg_queue_pcu}PCU | Stops:{avg_stops} | MaxWait:{max_wait}s | Cycle:{avg_cycle}s | Fairness:{fairness}% | EmergencyClear:{emergency_clearance}s")
                else:
                    self.log(f"📊 KPI | Xe:{total_vehicles_in_sim} | Delay:{avg_delay}s/xe | Throughput:{throughput}xe/h | Queue:{avg_queue_pcu}PCU | Stops:{avg_stops} | MaxWait:{max_wait}s | Cycle:{avg_cycle}s | Fairness:{fairness}%")

        except Exception as e:
            # Log chi tiết lỗi để debug (chỉ 1 lần)
            if not hasattr(self, '_error_logged'):
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"❌ Lỗi cập nhật KPI: {e}")
                print(f"=== CHI TIẾT LỖI KPI ===\n{error_detail}")
                self._error_logged = True

    def update_ui(self):
        """Cập nhật UI với dữ liệu mới nhất từ SUMO"""
        try:
            # === Cập nhật KPI cards ===
            for key, value in self.global_kpi_data.items():
                if key in self.global_kpi_cards:
                    # Format số cho đẹp
                    if isinstance(value, float):
                        formatted_value = f"{value:.1f}"
                    else:
                        formatted_value = str(value)
                    
                    self.global_kpi_cards[key].configure(text=formatted_value)
            
            # === Cập nhật intersection widgets ===
            for int_name, data in self.intersection_data.items():
                if int_name in self.intersection_widgets:
                    widgets = self.intersection_widgets[int_name]
                    
                    # Queue
                    widgets["queue"].configure(text=str(data["queue"]))
                    
                    # Wait time
                    wait_text = f"{data['wait_time']:.1f}" if isinstance(data['wait_time'], float) else str(data['wait_time'])
                    widgets["wait"].configure(text=wait_text)
                    
                    # Directions
                    for direction, count in data["vehicles"].items():
                        if direction in widgets["directions"]:
                            widgets["directions"][direction].configure(text=str(count))
            
            # === Cập nhật priority panel ===
            self.update_priority_ui()

        except Exception as e:
            # Log lỗi nhưng không crash UI
            if not hasattr(self, '_ui_error_logged'):
                self.log(f"⚠ Lỗi cập nhật UI: {e}")
                self._ui_error_logged = True

    def update_priority_vehicle_data(self):
        """Cập nhật dữ liệu xe ưu tiên theo hướng - CHỈ CHO CHẾ ĐỘ TỰ ĐỘNG"""
        # Chỉ cập nhật xe ưu tiên khi ở chế độ Tự động
        if self.mode != "Tự động":
            # Đảm bảo panel ẩn trong chế độ Mặc định
            if self.has_priority_vehicles:
                self.hide_priority_panel()
            return
        
        try:
            import traci
            
            # Reset data
            for junction_id in self.priority_vehicle_data:
                for direction in self.priority_vehicle_data[junction_id]:
                    self.priority_vehicle_data[junction_id][direction] = 0
            
            # Lấy tất cả xe ưu tiên
            all_vehicles = traci.vehicle.getIDList()
            priority_vehicles = [v for v in all_vehicles if 'priority' in v.lower()]
            
            total_priority = 0
            
            for veh_id in priority_vehicles:
                try:
                    edge_id = traci.vehicle.getRoadID(veh_id)
                    
                    # Xác định junction và direction
                    junction_id = None
                    direction = None
                    
                    # Improved direction detection
                    if "-E1" in edge_id:
                        junction_id, direction = "J1", "Bắc"
                    elif "-E2" in edge_id:
                        junction_id, direction = "J1", "Nam"
                    elif "E0" in edge_id and "-E0" not in edge_id:
                        junction_id, direction = "J1", "Tây"
                    elif "-E3" in edge_id:
                        junction_id, direction = "J1", "Đông"
                    elif "-E4" in edge_id:
                        junction_id, direction = "J4", "Bắc"
                    elif "-E5" in edge_id:
                        junction_id, direction = "J4", "Nam"
                    elif "-E6" in edge_id:
                        junction_id, direction = "J4", "Tây"
                    elif "E3" in edge_id and "-E3" not in edge_id:
                        junction_id, direction = "J4", "Đông"
                    
                    if junction_id and direction:
                        self.priority_vehicle_data[junction_id][direction] += 1
                        total_priority += 1
                        
                except Exception:
                    continue
            
            # Cập nhật trạng thái hiển thị
            if total_priority > 0 and not self.has_priority_vehicles:
                self.show_priority_panel()
            elif total_priority == 0 and self.has_priority_vehicles:
                self.hide_priority_panel()
                
        except Exception as e:
            pass

    def show_priority_panel(self):
        """Hiển thị panel xe ưu tiên với animation - CHỈ CHO CHẾ ĐỘ TỰ ĐỘNG"""
        # Chỉ hiển thị panel khi ở chế độ Tự động
        if self.mode != "Tự động":
            return
            
        if not self.has_priority_vehicles:
            self.has_priority_vehicles = True
            # Insert priority panel sau KPI panel (row=1)
            self.priority_container.grid(row=1, column=0, sticky="ew", pady=(0, 6))
            
            # Animation effect
            self.animate_priority_title()
            self.log("🚨 PHÁT HIỆN XE ƯU TIÊN - Hiển thị panel theo dõi")

    def hide_priority_panel(self):
        """Ẩn panel xe ưu tiên"""
        if self.has_priority_vehicles:
            self.has_priority_vehicles = False
            self.priority_container.grid_forget()
            self.log("✅ Không còn xe ưu tiên - Ẩn panel theo dõi")

    def animate_priority_title(self):
        """Animation cho title xe ưu tiên"""
        def blink():
            if self.has_priority_vehicles:
                current_color = self.priority_title.cget("text_color")
                new_color = "#ffffff" if current_color == "#ffcccb" else "#ffcccb"
                self.priority_title.configure(text_color=new_color)
                self.after(500, blink)  # Blink every 500ms
        
        blink()

    def update_priority_ui(self):
        """Cập nhật UI panel xe ưu tiên"""
        if self.has_priority_vehicles:
            for junction_id, directions in self.priority_vehicle_data.items():
                if junction_id in self.priority_widgets:
                    for direction, count in directions.items():
                        if direction in self.priority_widgets[junction_id]:
                            widget = self.priority_widgets[junction_id][direction]
                            widget.configure(text=str(count))
                            
                            # Highlight nếu có xe
                            if count > 0:
                                widget.configure(text_color="#dc2626")  # Đỏ đậm
                            else:
                                # Màu mặc định theo hướng
                                colors = {
                                    "Bắc": "#991b1b", "Nam": "#9a3412", 
                                    "Đông": "#14532d", "Tây": "#831843"
                                }
                                widget.configure(text_color=colors.get(direction, "#64748b"))


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()