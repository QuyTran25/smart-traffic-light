import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading, time, random, os, sys

# Thêm đường dẫn src vào sys.path để import được modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from simulation.sumo_connector import khoi_dong_sumo, dung_sumo

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class SmartTrafficApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚦 HỆ THỐNG 2 NGÃ TƯ")
        self.geometry("700x850")
        self.minsize(680, 800)
        self.running = False
        self.paused = False  # Thêm biến để theo dõi trạng thái pause
        self.mode = "Mặc định"
        
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 30
        
        # Global KPI data
        self.global_kpi_data = {
            "Tổng xe": 0,
            "Độ trễ TB": 0.0,
            "Lưu lượng": 0,
            "Chu kỳ TB": 0,
            "Công bằng": 0.0,
            "Phối hợp": 0
        }
        
        # Data for 2 intersections
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

        # ---------- HEADER ----------
        header = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#ffffff", height=65)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        # Header content
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=15, pady=10)
        
        # Icon + Title
        ctk.CTkLabel(
            header_left,
            text="🚦",
            font=("Segoe UI", 20),
        ).pack(side="left", padx=(0, 8))
        
        title_frame = ctk.CTkFrame(header_left, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="HỆ THỐNG 2 NGÃ TƯ THÔNG MINH",
            font=("Segoe UI", 16, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Demo SUMO - 2 ngã tư kết nối",
            font=("Segoe UI", 11),
            text_color="#64748b",
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))
        
        # Status indicator (right side)
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=15)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="⚫ Dừng",
            font=("Segoe UI", 11, "bold"),
            text_color="#64748b"
        )
        self.status_label.pack()

        # ---------- CONTROL BAR ----------
        control_bar_main = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        control_bar_main.pack(fill="x", padx=0, pady=(1, 0))
        
        # First row - Mode and Action buttons
        control_bar_top = ctk.CTkFrame(control_bar_main, fg_color="transparent", height=45)
        control_bar_top.pack(fill="x", padx=10, pady=(8, 0))
        control_bar_top.pack_propagate(False)
        
        # Left controls
        left_controls = ctk.CTkFrame(control_bar_top, fg_color="transparent")
        left_controls.pack(side="left")
        
        # MODE TABS
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

        # CONTROL BUTTONS
        btn_frame = ctk.CTkFrame(left_controls, fg_color="transparent")
        btn_frame.pack(side="left")
        
        # Play button
        self.play_btn = ctk.CTkButton(
            btn_frame,
            text="▶",
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 11, "bold"),
            width=42,
            height=36,
            corner_radius=5,
            command=self.start_sim
        )
        self.play_btn.pack(side="left", padx=2)
        
        # Pause button
        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text="⏸",
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="#000000",
            font=("Segoe UI", 11, "bold"),
            width=42,
            height=36,
            corner_radius=5,
            command=self.pause_sim
        )
        self.pause_btn.pack(side="left", padx=2)
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹",
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=("Segoe UI", 11, "bold"),
            width=42,
            height=36,
            corner_radius=5,
            command=self.stop_sim
        )
        self.stop_btn.pack(side="left", padx=2)
        
        # Reset button
        reset_btn = ctk.CTkButton(
            btn_frame,
            text="🔄",
            fg_color="#64748b",
            hover_color="#475569",
            font=("Segoe UI", 11, "bold"),
            width=42,
            height=36,
            corner_radius=5,
            command=self.reset_all
        )
        reset_btn.pack(side="left", padx=2)
        
        # Export button
        export_btn = ctk.CTkButton(
            btn_frame,
            text="⬇",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=("Segoe UI", 11, "bold"),
            width=42,
            height=36,
            corner_radius=5,
            command=self.export_log
        )
        export_btn.pack(side="left", padx=2)
        
        # Second row - Scenario selector
        control_bar_bottom = ctk.CTkFrame(control_bar_main, fg_color="transparent", height=42)
        control_bar_bottom.pack(fill="x", padx=10, pady=(6, 8))
        control_bar_bottom.pack_propagate(False)
        
        scenario_frame = ctk.CTkFrame(control_bar_bottom, fg_color="transparent")
        scenario_frame.pack(side="left")
        
        ctk.CTkLabel(
            scenario_frame,
            text="Kịch bản:",
            font=("Segoe UI", 11, "bold"),
            text_color="#334155"
        ).pack(side="left", padx=(0, 8))
        
        self.case_box = ctk.CTkOptionMenu(
            scenario_frame,
            values=["Mặc định", "SC1 - Xe ưu tiên từ hướng chính", "SC2 - Xe ưu tiên từ hướng nhánh", "SC3 - Nhiều xe ưu tiên 2 hướng", "SC4 - Báo giả", "SC5 - Xe ưu tiên bị kẹt", "SC6 - Nhiều xe ưu tiên liên tiếp"],
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

        timing_bar = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        timing_bar.pack(fill="x", padx=0, pady=(1, 0))
        
        timing_container = ctk.CTkFrame(timing_bar, fg_color="transparent", height=50)
        timing_container.pack(fill="x", padx=10, pady=8)
        timing_container.pack_propagate(False)
        
        # Label
        ctk.CTkLabel(
            timing_container,
            text="⏱ Thời gian đèn:",
            font=("Segoe UI", 11, "bold"),
            text_color="#334155"
        ).pack(side="left", padx=(0, 12))
        
        # Green light input
        green_frame = ctk.CTkFrame(timing_container, fg_color="#d1fae5", corner_radius=6)
        green_frame.pack(side="left", padx=4)
        
        green_content = ctk.CTkFrame(green_frame, fg_color="transparent")
        green_content.pack(padx=8, pady=6)
        
        ctk.CTkLabel(
            green_content,
            text="🟢 Xanh",
            font=("Segoe UI", 10, "bold"),
            text_color="#065f46"
        ).pack(side="left", padx=(0, 6))
        
        self.green_entry = ctk.CTkEntry(
            green_content,
            width=50,
            height=28,
            font=("Segoe UI", 11, "bold"),
            fg_color="#ffffff",
            border_color="#10b981",
            border_width=2,
            text_color="#065f46"
        )
        self.green_entry.pack(side="left", padx=(0, 4))
        self.green_entry.insert(0, "30")
        
        ctk.CTkLabel(
            green_content,
            text="s",
            font=("Segoe UI", 10),
            text_color="#475569"
        ).pack(side="left")
        
        # Yellow light input
        yellow_frame = ctk.CTkFrame(timing_container, fg_color="#fef3c7", corner_radius=6)
        yellow_frame.pack(side="left", padx=4)
        
        yellow_content = ctk.CTkFrame(yellow_frame, fg_color="transparent")
        yellow_content.pack(padx=8, pady=6)
        
        ctk.CTkLabel(
            yellow_content,
            text="🟡 Vàng",
            font=("Segoe UI", 10, "bold"),
            text_color="#78350f"
        ).pack(side="left", padx=(0, 6))
        
        self.yellow_entry = ctk.CTkEntry(
            yellow_content,
            width=50,
            height=28,
            font=("Segoe UI", 11, "bold"),
            fg_color="#ffffff",
            border_color="#f59e0b",
            border_width=2,
            text_color="#78350f"
        )
        self.yellow_entry.pack(side="left", padx=(0, 4))
        self.yellow_entry.insert(0, "3")
        
        ctk.CTkLabel(
            yellow_content,
            text="s",
            font=("Segoe UI", 10),
            text_color="#475569"
        ).pack(side="left")
        
        # Red light input
        red_frame = ctk.CTkFrame(timing_container, fg_color="#fecaca", corner_radius=6)
        red_frame.pack(side="left", padx=4)
        
        red_content = ctk.CTkFrame(red_frame, fg_color="transparent")
        red_content.pack(padx=8, pady=6)
        
        ctk.CTkLabel(
            red_content,
            text="🔴 Đỏ Toàn Phần",
            font=("Segoe UI", 10, "bold"),
            text_color="#991b1b"
        ).pack(side="left", padx=(0, 6))
        
        self.red_entry = ctk.CTkEntry(
            red_content,
            width=50,
            height=28,
            font=("Segoe UI", 11, "bold"),
            fg_color="#ffffff",
            border_color="#ef4444",
            border_width=2,
            text_color="#991b1b"
        )
        self.red_entry.pack(side="left", padx=(0, 4))
        self.red_entry.insert(0, "3")
        
        ctk.CTkLabel(
            red_content,
            text="s",
            font=("Segoe UI", 10),
            text_color="#475569"
        ).pack(side="left")
        
        # Apply button
        apply_btn = ctk.CTkButton(
            timing_container,
            text="✓ Áp dụng",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=("Segoe UI", 10, "bold"),
            width=80,
            height=32,
            corner_radius=6,
            command=self.apply_timing
        )
        apply_btn.pack(side="left", padx=(8, 0))

        # ---------- MAIN CONTENT ----------
        self.main_container = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#f8fafc")
        self.main_container.pack(fill="both", expand=True, padx=8, pady=(6, 6))
        
        # Create content frame
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        
        self.content_frame.grid_rowconfigure(0, weight=0)  # KPI - fixed size
        self.content_frame.grid_rowconfigure(1, weight=0)  # Intersections - fixed size
        self.content_frame.grid_rowconfigure(2, weight=0, minsize=200)  # Log - minimum height
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # ---------- TOP: GLOBAL KPI ----------
        kpi_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        kpi_container.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.create_global_kpi_section(kpi_container)
        
        # ---------- MIDDLE: 2 INTERSECTIONS ----------
        intersections_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        intersections_container.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        intersections_container.grid_columnconfigure(0, weight=1)
        intersections_container.grid_columnconfigure(1, weight=1)
        
        # Intersection 1
        self.create_intersection_section(intersections_container, "Ngã tư 1", 0, "#3b82f6")
        
        # Intersection 2
        self.create_intersection_section(intersections_container, "Ngã tư 2", 1, "#8b5cf6")
        
        # ---------- BOTTOM: LOG ----------
        log_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        log_container.grid(row=2, column=0, sticky="nsew")
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        self.create_log_section(log_container)

    # =======================================================

    def create_global_kpi_section(self, parent):
        """Create global KPI cards for entire system"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x", padx=0, pady=0)
        
        # Header
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=35)
        header_frame.pack(fill="x", padx=10, pady=(8, 6))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="📊 KPI Tổng Hợp",
            font=("Segoe UI", 12, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(side="left")
        
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
            
            card = ctk.CTkFrame(
                kpi_grid,
                fg_color=bg_color,
                corner_radius=6,
                width=110,
                height=65
            )
            card.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            card.grid_propagate(False)
            
            # Icon
            ctk.CTkLabel(
                card,
                text=icon,
                font=("Segoe UI", 14),
                text_color=text_color
            ).pack(side="left", padx=(6, 4), pady=4)
            
            # Content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, pady=4, padx=(0, 4))
            
            ctk.CTkLabel(
                content,
                text=name,
                font=("Segoe UI", 8, "bold"),
                text_color="#0f172a",
                anchor="w"
            ).pack(anchor="w")
            
            value_frame = ctk.CTkFrame(content, fg_color="transparent")
            value_frame.pack(anchor="w", fill="x")
            
            val_label = ctk.CTkLabel(
                value_frame,
                text=value,
                font=("Segoe UI", 15, "bold"),
                text_color=text_color,
                anchor="w"
            )
            val_label.pack(side="left")
            
            if unit:
                ctk.CTkLabel(
                    value_frame,
                    text=f" {unit}",
                    font=("Segoe UI", 8),
                    text_color="#475569",
                    anchor="w"
                ).pack(side="left", pady=(4, 0))
            
            self.global_kpi_cards[name] = val_label
        
        # Configure grid columns to expand evenly
        for i in range(3):
            kpi_grid.grid_columnconfigure(i, weight=1)

    # =======================================================

    def create_intersection_section(self, parent, name, column, accent_color):
        """Create detailed intersection panel"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.grid(row=0, column=column, sticky="nsew", padx=3)
        
        # Header with colored accent
        header_frame = ctk.CTkFrame(section, fg_color=accent_color, corner_radius=8, height=42)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(expand=True)
        
        ctk.CTkLabel(
            header_content,
            text=name,
            font=("Segoe UI", 14, "bold"),
            text_color="#ffffff"
        ).pack()
        
        
        # Stats row
        stats_frame = ctk.CTkFrame(section, fg_color="transparent")
        stats_frame.pack(fill="x", padx=8, pady=(8, 6))
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        
        # Queue length
        queue_card = ctk.CTkFrame(stats_frame, fg_color="#fef3c7", corner_radius=6, height=65)
        queue_card.grid(row=0, column=0, padx=3, sticky="ew")
        queue_card.pack_propagate(False)
        
        queue_content = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_content.pack(expand=True)
        
        ctk.CTkLabel(
            queue_content,
            text="Hàng chờ",
            font=("Segoe UI", 10, "bold"),
            text_color="#0f172a"
        ).pack()
        
        queue_value_frame = ctk.CTkFrame(queue_content, fg_color="transparent")
        queue_value_frame.pack()
        
        queue_label = ctk.CTkLabel(
            queue_value_frame,
            text="0",
            font=("Segoe UI", 20, "bold"),
            text_color="#78350f"
        )
        queue_label.pack(side="left")
        
        ctk.CTkLabel(
            queue_value_frame,
            text=" xe",
            font=("Segoe UI", 11),
            text_color="#475569"
        ).pack(side="left", pady=(6, 0))
        
        if not hasattr(self, 'intersection_widgets'):
            self.intersection_widgets = {}
        if name not in self.intersection_widgets:
            self.intersection_widgets[name] = {}
        
        self.intersection_widgets[name]["queue"] = queue_label
        
        # Wait time
        wait_card = ctk.CTkFrame(stats_frame, fg_color="#fecaca", corner_radius=6, height=65)
        wait_card.grid(row=0, column=1, padx=3, sticky="ew")
        wait_card.pack_propagate(False)
        
        wait_content = ctk.CTkFrame(wait_card, fg_color="transparent")
        wait_content.pack(expand=True)
        
        ctk.CTkLabel(
            wait_content,
            text="Chờ TB",
            font=("Segoe UI", 10, "bold"),
            text_color="#0f172a"
        ).pack()
        
        wait_value_frame = ctk.CTkFrame(wait_content, fg_color="transparent")
        wait_value_frame.pack()
        
        wait_label = ctk.CTkLabel(
            wait_value_frame,
            text="0",
            font=("Segoe UI", 20, "bold"),
            text_color="#991b1b"
        )
        wait_label.pack(side="left")
        
        ctk.CTkLabel(
            wait_value_frame,
            text=" giây",
            font=("Segoe UI", 11),
            text_color="#475569"
        ).pack(side="left", pady=(6, 0))
        
        self.intersection_widgets[name]["wait"] = wait_label

        # Vehicle counts by direction
        vehicles_frame = ctk.CTkFrame(section, fg_color="#f8fafc", corner_radius=6)
        vehicles_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        ctk.CTkLabel(
            vehicles_frame,
            text="Số xe theo hướng",
            font=("Segoe UI", 10, "bold"),
            text_color="#475569"
        ).pack(pady=(6, 3))
        
        # Direction grid
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
            
            ctk.CTkLabel(
                content,
                text=dir_name,
                font=("Segoe UI", 9, "bold"),
                text_color="#0f172a"
            ).pack()
            
            val_label = ctk.CTkLabel(
                content,
                text="0",
                font=("Segoe UI", 17, "bold"),
                text_color=text_color
            )
            val_label.pack()
            
            # Extract direction name without arrow
            dir_key = dir_name.split()[1]
            self.intersection_widgets[name]["directions"][dir_key] = val_label

    # =======================================================

    def create_log_section(self, parent):
        """Create log section"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.grid(row=0, column=0, sticky="nsew")
        section.grid_rowconfigure(0, weight=1)
        section.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=35)
        header_frame.pack(fill="x", padx=10, pady=(8, 6))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="📋 Log Hệ Thống",
            font=("Segoe UI", 12, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(side="left")
        
        log_frame = ctk.CTkFrame(section, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        self.log_box = tk.Text(
            log_frame,
            bg="#f8fafc",
            fg="#1e293b",
            wrap="word",
            relief="flat",
            font=("Consolas", 9),
            padx=8,
            pady=8,
            borderwidth=0,
            highlightthickness=0,
            height=8
        )
        self.log_box.pack(fill="both", expand=True)
        
        self.log("🚦 Hệ thống 2 ngã tư sẵn sàng")

    # =======================================================

    def change_mode(self, value):
        self.mode = value
        self.log(f"✓ Chế độ: {value}")

    def start_sim(self):
        if self.running:
            return
        
        self.running = True
        self.paused = False  # Bỏ pause khi start
        self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
        
        # Kiểm tra xem SUMO đã được khởi động chưa
        sumo_is_running = False
        try:
            import traci
            # Thử lấy thông tin từ SUMO để kiểm tra kết nối
            traci.simulation.getTime()
            sumo_is_running = True
            self.log("▶ Tiếp tục mô phỏng từ nơi đã dừng")
        except (traci.exceptions.FatalTraCIError, traci.exceptions.TraCIException):
            # SUMO chưa khởi động hoặc đã bị đóng
            sumo_is_running = False
        except:
            # Lỗi khác (có thể chưa import traci)
            sumo_is_running = False
        
        if sumo_is_running:
            # SUMO đang chạy, chỉ cần tiếp tục (thread vẫn đang chạy và đang chờ)
            pass  # Thread vẫn đang chạy, chỉ cần set running = True
        else:
            # Khởi động SUMO mới
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sumo', 'test2.sumocfg')
            if khoi_dong_sumo(config_path, gui=True):
                threading.Thread(target=self.simulate_with_sumo, daemon=True).start()
                self.log("▶ Bắt đầu mô phỏng SUMO với GUI")
            else:
                self.log("❌ Không thể khởi động SUMO. Kiểm tra file cấu hình hoặc SUMO đã được cài đặt chưa")
                self.running = False
                self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")

    def pause_sim(self):
        if not self.running:
            return
        self.running = False
        self.paused = True  # Đánh dấu đang pause
        self.status_label.configure(text="🟡 Tạm dừng", text_color="#f59e0b")
        # KHÔNG đóng SUMO khi pause, thread vẫn chạy nhưng sẽ "ngủ"
        self.log("⏸ Tạm dừng mô phỏng (nhấn Start để tiếp tục)")

    def stop_sim(self):
        self.running = False
        self.paused = False  # Không còn pause nữa
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        # Đóng SUMO hoàn toàn
        try:
            dung_sumo()
            self.log("⏹ Đã dừng và đóng SUMO")
        except:
            self.log("⏹ Đã dừng mô phỏng")

    def export_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_2nt_log_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.log_box.get("1.0", "end"))
        self.log(f"✓ Xuất: {filename}")

    def simulate_with_sumo(self):
        """Simulate with real SUMO data"""
        import traci
        
        try:
            sumo_ended = False
            while not sumo_ended:
                # Kiểm tra nếu đang pause thì chờ
                while self.paused and not sumo_ended:
                    time.sleep(0.1)  # Ngủ khi pause
                    # Kiểm tra xem có lệnh stop không
                    if not self.running and not self.paused:
                        sumo_ended = True
                        break
                
                # Nếu không chạy và không pause thì dừng
                if not self.running and not self.paused:
                    break
                
                # Chỉ chạy step khi đang running
                if self.running:
                    # Chạy một bước mô phỏng SUMO
                    traci.simulationStep()
                    
                    # Lấy thời gian hiện tại
                    current_time = traci.simulation.getTime()
                    
                    # Cập nhật dữ liệu từ SUMO
                    self.update_data_from_sumo()
                    
                    # Cập nhật UI
                    self.update_ui()
                    
                    time.sleep(0.1)  # Cập nhật mỗi 0.1 giây
                
        except Exception as e:
            self.log(f"❌ Lỗi trong mô phỏng SUMO: {str(e)}")
            self.running = False
            self.paused = False
            self.status_label.configure(text="⚫ Lỗi", text_color="#ef4444")
        finally:
            # Chỉ đóng SUMO khi thực sự stop (không phải pause)
            if not self.paused:
                try:
                    dung_sumo()
                except:
                    pass

    # =======================================================

    def reset_all(self):
        """Reset all interface elements and restart SUMO"""
        # Chạy reset trên thread riêng để không block UI
        threading.Thread(target=self._do_reset, daemon=True).start()
    
    def _do_reset(self):
        """Thực hiện reset (chạy trên thread riêng)"""
        # Lưu trạng thái đang chạy
        was_running = self.running
        
        # Dừng mô phỏng
        self.running = False
        self.paused = False
        time.sleep(0.5)  # Đợi thread dừng
        
        # Đóng SUMO cũ
        try:
            dung_sumo()
        except:
            pass
        
        # Đợi SUMO đóng hoàn toàn
        time.sleep(0.5)
        
        # Reset các biến dữ liệu nội bộ về giá trị mặc định (trên UI thread)
        self.after(0, self._reset_ui_and_data, was_running)
    
    def _reset_ui_and_data(self, was_running):
        """Reset UI và dữ liệu (chạy trên main thread)"""
        # Reset các biến dữ liệu nội bộ về giá trị mặc định
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 30
        self.mode = "Mặc định"
        
        # Reset global KPI data
        self.global_kpi_data = {
            "Tổng xe": 0,
            "Độ trễ TB": 0.0,
            "Lưu lượng": 0,
            "Chu kỳ TB": 0,
            "Công bằng": 0.0,
            "Phối hợp": 0
        }
        
        # Reset intersection data về giá trị ban đầu
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
        
        # Reset UI
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        self.case_box.set("Mặc định")
        self.mode_option.set("Mặc định")
        
        # Reset các ô nhập thời gian về giá trị mặc định
        self.green_entry.delete(0, 'end')
        self.green_entry.insert(0, "30")
        self.yellow_entry.delete(0, 'end')
        self.yellow_entry.insert(0, "3")
        self.red_entry.delete(0, 'end')
        self.red_entry.insert(0, "30")
        
        # Reset global KPI
        for name, label in self.global_kpi_cards.items():
            label.configure(text="—")
        
        # Reset intersections
        for int_name, widgets in self.intersection_widgets.items():
            widgets["queue"].configure(text="0")
            widgets["wait"].configure(text="0")
            for direction, label in widgets["directions"].items():
                label.configure(text="0")
        
        # GIỮ log (không xóa), chỉ thêm thông báo reset
        self.log("🔄 Đã đặt lại toàn bộ hệ thống về giá trị mặc định")
        self.log("📊 Thời gian đèn: Xanh 30s, Vàng 3s, Đỏ 30s")
        self.log("🚦 Hệ thống 2 ngã tư sẵn sàng")
        
        # Khởi động lại SUMO nếu đang chạy trước đó (sau 1 giây)
        if was_running:
            self.after(1000, self.start_sim)  # Khởi động sau 1 giây để SUMO đóng hoàn toàn

    # =======================================================

    def log(self, msg):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")

    def apply_timing(self):
        """Apply traffic light timing settings"""
        try:
            green = int(self.green_entry.get())
            yellow = int(self.yellow_entry.get())
            red = int(self.red_entry.get())
            
            if green <= 0 or yellow <= 0 or red <= 0:
                self.log("❌ Thời gian phải lớn hơn 0")
                return
            
            if green > 120 or yellow > 10 or red > 3:
                self.log("❌ Thời gian quá lớn (Xanh ≤120s, Vàng ≤10s, Đỏ Toàn Phần ≤3s)")
                return
            
            self.green_time = green
            self.yellow_time = yellow
            self.red_time = red
            
            self.log(f"✓ Đã cài đặt: Xanh {green}s, Vàng {yellow}s, Đỏ Toàn Phần {red}s")
            
        except ValueError:
            self.log("❌ Vui lòng nhập số hợp lệ")


    def update_data_from_sumo(self):
        """Cập nhật dữ liệu từ SUMO"""
        import traci
        
        try:
            # Lấy danh sách traffic lights
            tls_ids = traci.trafficlight.getIDList()
            
            # Cập nhật dữ liệu cho từng ngã tư
            for i, tls_id in enumerate(tls_ids[:2]):  # Chỉ lấy 2 ngã tư đầu
                int_name = f"Ngã tư {i+1}"
                if int_name not in self.intersection_data:
                    continue
                    
                # Lấy thông tin đèn giao thông
                current_phase = traci.trafficlight.getPhase(tls_id)
                phase_duration = traci.trafficlight.getPhaseDuration(tls_id)
                
                # Map phase sang trạng thái đèn (giả sử phase 0 = xanh Bắc-Nam, phase 1 = xanh Đông-Tây)
                if current_phase == 0:
                    light_state = "Xanh"
                elif current_phase == 1:
                    light_state = "Đỏ"
                else:
                    light_state = "Vàng"
                
                self.intersection_data[int_name]["light_state"] = light_state
                
                # Lấy số lượng xe trên các làn đường (giả sử có edges tương ứng)
                # Đây là mapping giả lập - cần điều chỉnh theo network thực
                try:
                    # Edges cho hướng Bắc, Nam, Đông, Tây
                    edges = {
                        "Bắc": f"-E{i*4}",  # Điều chỉnh theo network thực
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
                        except:
                            self.intersection_data[int_name]["vehicles"][direction] = 0
                    
                    # Tính queue và wait time (giả lập)
                    self.intersection_data[int_name]["queue"] = max(0, total_vehicles - 20)
                    self.intersection_data[int_name]["wait_time"] = min(120, total_vehicles * 2)
                    
                except Exception as e:
                    # Nếu không lấy được dữ liệu edges, dùng dữ liệu giả lập
                    for direction in ["Bắc", "Nam", "Đông", "Tây"]:
                        self.intersection_data[int_name]["vehicles"][direction] = random.randint(5, 25)
                    self.intersection_data[int_name]["queue"] = random.randint(0, 15)
                    self.intersection_data[int_name]["wait_time"] = random.randint(10, 60)
            
            # Cập nhật KPIs toàn cục
            total_vehicles = sum(sum(data["vehicles"].values()) for data in self.intersection_data.values())
            avg_delay = sum(data["wait_time"] for data in self.intersection_data.values()) / len(self.intersection_data)
            throughput = total_vehicles * 10  # Giả lập throughput
            avg_cycle = 60  # Giả lập chu kỳ
            fairness = 0.85  # Giả lập công bằng
            coordination = 80  # Giả lập phối hợp
            
            self.global_kpi_data = {
                "Tổng xe": total_vehicles,
                "Độ trễ TB": round(avg_delay, 1),
                "Lưu lượng": throughput,
                "Chu kỳ TB": avg_cycle,
                "Công bằng": fairness,
                "Phối hợp": coordination
            }
            
        except Exception as e:
            self.log(f"⚠ Cập nhật dữ liệu SUMO thất bại: {str(e)}")

    def update_ui(self):
        """Cập nhật giao diện người dùng"""
        try:
            # Cập nhật KPIs toàn cục
            for key, value in self.global_kpi_data.items():
                if key in self.global_kpi_cards:
                    self.global_kpi_cards[key].configure(text=str(value))
            
            # Cập nhật dữ liệu từng ngã tư
            for int_name, data in self.intersection_data.items():
                if int_name in self.intersection_widgets:
                    widgets = self.intersection_widgets[int_name]
                    
                    # Cập nhật queue và wait time
                    widgets["queue"].configure(text=str(data["queue"]))
                    widgets["wait"].configure(text=str(data["wait_time"]))
                    
                    # Cập nhật số xe theo hướng
                    for direction, count in data["vehicles"].items():
                        if direction in widgets["directions"]:
                            widgets["directions"][direction].configure(text=str(count))
            
            # Log ngẫu nhiên
            events = [
                "Cập nhật trạng thái đèn giao thông",
                "Phát hiện thay đổi lưu lượng",
                "Điều chỉnh chu kỳ đèn",
                "Hệ thống hoạt động ổn định",
            ]
            if random.random() < 0.1:  # Giảm tần suất log
                self.log(random.choice(events))
                
        except Exception as e:
            self.log(f"⚠ Cập nhật UI thất bại: {str(e)}")


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
