import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading, time, random

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class SmartTrafficApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚦 HỆ THỐNG 2 NGÃ TƯ")
        self.geometry("700x850")
        self.minsize(680, 800)
        self.running = False
        self.mode = "Mặc định"
        
        self.green_time = 30
        self.yellow_time = 3
        self.red_time = 30
        
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
        self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
        threading.Thread(target=self.simulate, daemon=True).start()
        self.log("▶ Bắt đầu mô phỏng 2 ngã tư")

    def pause_sim(self):
        self.running = False
        self.status_label.configure(text="🟡 Dừng", text_color="#f59e0b")
        self.log("⏸ Tạm dừng")

    def stop_sim(self):
        self.running = False
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        self.log("⏹ Đã dừng")

    def export_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_2nt_log_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.log_box.get("1.0", "end"))
        self.log(f"✓ Xuất: {filename}")

    def simulate(self):
        """Simulate real-time data updates for 2 intersections"""
        while self.running:
            # Update global KPIs
            total_vehicles = random.randint(250, 350)
            avg_delay = round(random.uniform(35, 65), 1)
            throughput = random.randint(400, 600)
            avg_cycle = random.randint(70, 110)
            fairness = round(random.uniform(0.75, 0.92), 2)
            coordination = random.randint(75, 95)
            
            self.global_kpi_cards["Tổng xe"].configure(text=str(total_vehicles))
            self.global_kpi_cards["Độ trễ TB"].configure(text=str(avg_delay))
            self.global_kpi_cards["Lưu lượng"].configure(text=str(throughput))
            self.global_kpi_cards["Chu kỳ TB"].configure(text=str(avg_cycle))
            self.global_kpi_cards["Công bằng"].configure(text=str(fairness))
            self.global_kpi_cards["Phối hợp"].configure(text=str(coordination))
            
            # Update each intersection
            for idx, (int_name, data) in enumerate(self.intersection_data.items()):
                # Update queue and wait time
                queue = random.randint(5, 25)
                wait = random.randint(20, 80)
                
                widgets = self.intersection_widgets[int_name]
                widgets["queue"].configure(text=str(queue))
                widgets["wait"].configure(text=str(wait))
                
                # Update vehicle counts by direction
                for direction in ["Bắc", "Nam", "Đông", "Tây"]:
                    count = random.randint(15, 45)
                    widgets["directions"][direction].configure(text=str(count))
            
            # Random log events
            events = [
                        "Cập nhật trạng thái đèn giao thông",
                        "Phát hiện tăng lưu lượng tại hướng Đông",
                        "Điều chỉnh chu kỳ đèn tự động",
                        "Xe ưu tiên được phát hiện - Kích hoạt ưu tiên",
                        "Giảm lưu lượng tại hướng Bắc",
                        "Hệ thống hoạt động ổn định",
                    ]
            if random.random() < 0.4:
                self.log(random.choice(events))
            
            time.sleep(3)

    # =======================================================

    def reset_all(self):
        """Reset all interface elements"""
        self.running = False
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        self.case_box.set("Mặc định")
        self.mode_option.set("Mặc định")
        
        # Reset global KPI
        for name, label in self.global_kpi_cards.items():
            label.configure(text="—")
        
        # Reset intersections
        for int_name, widgets in self.intersection_widgets.items():
            widgets["queue"].configure(text="0")
            widgets["wait"].configure(text="0")
            for direction, label in widgets["directions"].items():
                label.configure(text="0")
        
        # Clear log
        self.log_box.delete("1.0", "end")
        self.log("🔄 Đã đặt lại")
        self.log("🚦 Hệ thống 2 ngã tư sẵn sàng")

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


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
