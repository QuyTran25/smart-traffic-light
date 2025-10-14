import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading, time, random
import os
import sys
import traci
from sumolib import checkBinary

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
        
        # SUMO integration variables
        self.sumo_connected = False
        self.sumo_paused = False
        
        # Path to SUMO configuration file
        self.sumo_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "sumo", "test2.sumocfg"
        )
        
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
        
        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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
            text="HỆ THỐNG ĐIỀU CHỈNH ĐÈN GIAO THÔNG THÔNG MINH",
            font=("Segoe UI", 20, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Giám sát và điều khiển đèn giao thông dựa trên mật độ xe",
            font=("Segoe UI", 12),
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
            values=["Mặc định", "SC1 - Xe ưu tiên NT1", "SC2 - Xe ưu tiên NT2",
                    "SC3 - Nhiều xe ưu tiên", "SC4 - Kẹt xe NT1", "SC5 - Kẹt xe NT2",
                    "SC6 - Điều phối", "SC7 - Sóng xanh"],
            font=("Segoe UI", 10),
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
            font=("Segoe UI", 14, "bold"),
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
                font=("Segoe UI", 14, "bold"),
                text_color="#0f172a",
                anchor="w"
            ).pack(anchor="w")
            
            value_frame = ctk.CTkFrame(content, fg_color="transparent")
            value_frame.pack(anchor="w", fill="x")
            
            val_label = ctk.CTkLabel(
                value_frame,
                text=value,
                font=("Segoe UI", 18, "bold"),
                text_color=text_color,
                anchor="w"
            )
            val_label.pack(side="left")
            
            if unit:
                ctk.CTkLabel(
                    value_frame,
                    text=f" {unit}",
                    font=("Segoe UI", 12),
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
            font=("Segoe UI", 14, "bold"),
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
            font=("Segoe UI", 12),
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
            font=("Segoe UI", 14, "bold"),
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
            font=("Segoe UI", 14, "bold"),
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
                font=("Segoe UI", 14, "bold"),
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
            font=("Segoe UI", 14, "bold"),
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
            font=("Consolas", 12),
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
        """Khởi động mô phỏng - Kết nối với SUMO và hiển thị GUI"""
        if self.running:
            self.log("⚠ Mô phỏng đã đang chạy")
            return
        
        # Khởi động SUMO với GUI lần đầu
        if not self.sumo_connected:
            self.log("🔌 Đang kết nối với SUMO...")
            threading.Thread(target=self._start_sumo, daemon=True).start()
        elif self.sumo_paused:
            # Nếu đang pause, chỉ cần resume (tiếp tục chạy)
            self.sumo_paused = False
            self.running = True
            self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
            self.log("▶ Tiếp tục mô phỏng")
            threading.Thread(target=self.simulate, daemon=True).start()
        else:
            # Nếu đã dừng hẳn (stopped), reload mô phỏng để bắt đầu lại
            try:
                self.log("🔄 Đang tải lại mô phỏng...")
                # Load lại cấu hình SUMO (giữ nguyên delay đã set)
                traci.load(["-c", self.sumo_config_path])
                self.sumo_paused = False
                self.running = True
                self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
                self.log("✅ Đã tải lại - Bấm play trong SUMO để bắt đầu")
                threading.Thread(target=self.simulate, daemon=True).start()
            except Exception as e:
                self.log(f"❌ Lỗi khi tải lại: {str(e)}")
                self.sumo_connected = False
    
    def _start_sumo(self):
        """Khởi động SUMO trong thread riêng"""
        try:
            # Kiểm tra file cấu hình
            if not os.path.exists(self.sumo_config_path):
                self.log(f"❌ Không tìm thấy file cấu hình: {self.sumo_config_path}")
                return
            
            # Lấy đường dẫn SUMO-GUI
            sumo_binary = checkBinary('sumo-gui')
            
            # Các tham số khởi động SUMO
            sumo_cmd = [
                sumo_binary,
                "-c", self.sumo_config_path,
                # KHÔNG dùng --start để SUMO mở ở chế độ DỪNG (không tự động chạy)
                "--quit-on-end",
                "--waiting-time-memory", "10000",
                "--time-to-teleport", "300",
                "--delay", "100"  # Delay mặc định 100ms, người dùng có thể thay đổi
            ]
            
            # Khởi động SUMO
            traci.start(sumo_cmd)
            self.sumo_connected = True
            self.running = True
            self.sumo_paused = False
            
            # Cập nhật giao diện
            self.status_label.configure(text="🟢 Chạy", text_color="#10b981")
            self.log("✅ SUMO đã khởi động - Vui lòng điều chỉnh delay và bấm play trong SUMO")
            
            # Bắt đầu vòng lặp mô phỏng
            threading.Thread(target=self.simulate, daemon=True).start()
            
        except Exception as e:
            self.log(f"❌ Lỗi khi khởi động SUMO: {str(e)}")
            self.sumo_connected = False
            self.running = False

    def pause_sim(self):
        """Tạm dừng mô phỏng - SUMO vẫn giữ trạng thái hiện tại"""
        if not self.running:
            self.log("⚠ Mô phỏng chưa chạy")
            return
        
        self.running = False
        self.sumo_paused = True
        self.status_label.configure(text="🟡 Tạm dừng", text_color="#f59e0b")
        self.log("⏸ Tạm dừng mô phỏng")
        self.log("💡 Bấm '▶ Chạy' để tiếp tục (không reset)")

    def stop_sim(self):
        """Dừng mô phỏng nhưng giữ nguyên cửa sổ SUMO"""
        self.running = False
        self.sumo_paused = False
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        
        # Chỉ dừng vòng lặp, không đóng SUMO
        if self.sumo_connected:
            self.log("⏹ Đã dừng mô phỏng (cửa sổ SUMO vẫn mở)")
            self.log("💡 Bấm '▶ Chạy' để tải lại và chạy lại test")
        else:
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
            try:
                # Nếu kết nối SUMO, lấy dữ liệu thực từ SUMO
                if self.sumo_connected:
                    # Thực hiện một bước mô phỏng
                    traci.simulationStep()
                    
                    # Lấy thông tin từ SUMO
                    current_time = traci.simulation.getTime()
                    num_vehicles = len(traci.vehicle.getIDList())
                    departed = traci.simulation.getDepartedNumber()
                    arrived = traci.simulation.getArrivedNumber()
                    
                    # Cập nhật KPI từ dữ liệu SUMO
                    self.global_kpi_cards["Tổng xe"].configure(text=str(num_vehicles))
                    
                    # Tính toán các KPI khác
                    avg_delay = round(random.uniform(35, 65), 1)  # Có thể tính từ waiting time
                    throughput = arrived * 3600 / max(current_time, 1)  # xe/giờ
                    
                    self.global_kpi_cards["Độ trễ TB"].configure(text=str(avg_delay))
                    self.global_kpi_cards["Lưu lượng"].configure(text=str(int(throughput)))
                    
                    # Log thông tin định kỳ
                    if int(current_time) % 30 == 0 and current_time > 0:
                        self.log(f"[SUMO] Thời gian: {int(current_time)}s - Xe: {num_vehicles} - Đã đến: {arrived}")
                    
                    # Kiểm tra xem mô phỏng còn chạy không
                    if traci.simulation.getMinExpectedNumber() <= 0:
                        self.log("✓ Mô phỏng SUMO đã hoàn thành")
                        self.running = False
                        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
                
                else:
                    # Nếu không kết nối SUMO, dùng dữ liệu giả
                    total_vehicles = random.randint(250, 350)
                    avg_delay = round(random.uniform(35, 65), 1)
                    throughput = random.randint(400, 600)
                    
                    self.global_kpi_cards["Tổng xe"].configure(text=str(total_vehicles))
                    self.global_kpi_cards["Độ trễ TB"].configure(text=str(avg_delay))
                    self.global_kpi_cards["Lưu lượng"].configure(text=str(throughput))
                
                # Cập nhật các KPI khác
                avg_cycle = random.randint(70, 110)
                fairness = round(random.uniform(0.75, 0.92), 2)
                coordination = random.randint(75, 95)
                
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
                
                # Random log events (chỉ khi không kết nối SUMO)
                if not self.sumo_connected and random.random() < 0.4:
                    events = [
                        "[NT1] Cập nhật chu kỳ đèn",
                        "[NT2] Cập nhật chu kỳ đèn",
                        "[Hệ thống] Điều phối hoạt động",
                        "[NT1] Tăng lưu lượng hướng Đông",
                        "[NT2] Xe ưu tiên phát hiện",
                        "[Hệ thống] Tối ưu tự động",
                        "[NT1→NT2] Sóng xanh kích hoạt",
                        "[Hệ thống] Cân bằng tải",
                    ]
                    self.log(random.choice(events))
                
                time.sleep(0.1 if self.sumo_connected else 3)
                
            except traci.exceptions.FatalTraCIError:
                self.log("⚠ Mất kết nối với SUMO")
                self.sumo_connected = False
                self.running = False
                self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
                break
            except Exception as e:
                self.log(f"❌ Lỗi trong vòng lặp mô phỏng: {str(e)}")
                break

    # =======================================================

    def reset_all(self):
        """Reset về trạng thái ban đầu nhưng GIỮ SUMO và delay"""
        # Dừng mô phỏng trước
        self.running = False
        self.sumo_paused = False
        
        self.status_label.configure(text="⚫ Dừng", text_color="#64748b")
        self.case_box.set("Mặc định")
        self.mode_option.set("Mặc định")
        
        # Reload SUMO (giống Stop) - KHÔNG đóng SUMO
        if self.sumo_connected:
            try:
                # Reload về trạng thái ban đầu, giữ nguyên delay
                traci.load(["-c", self.sumo_config_path])
                self.log("🔄 Đã reset về trạng thái ban đầu (SUMO vẫn mở, delay giữ nguyên)")
            except Exception as e:
                self.log(f"⚠ Lỗi khi reload SUMO: {str(e)}")
        
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
        self.log("🔄 Đã reset về trạng thái ban đầu")
        self.log("� Bấm '▶ Chạy' và Play trong SUMO để chạy lại")
        self.log("� Hệ thống 2 ngã tư sẵn sàng")

    # =======================================================

    def on_closing(self):
        """Xử lý khi đóng cửa sổ"""
        self.running = False
        
        # Đóng kết nối SUMO nếu đang mở
        if self.sumo_connected:
            try:
                traci.close()
                self.log("✓ Đã đóng kết nối SUMO")
            except:
                pass
        
        # Đóng cửa sổ
        self.destroy()

    def log(self, msg):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
