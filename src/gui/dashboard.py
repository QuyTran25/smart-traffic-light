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
        self.title("🚦 HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH")
        self.geometry("1200x900")
        self.minsize(700, 600)
        self.running = False
        self.mode = "Mặc định"
        
        self.create_layout()

    # ====================== UI Layout ======================
    def create_layout(self):
        self.configure(fg_color="#f8fafc")
        
        # Create a scrollable frame for entire content
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#f8fafc",
            corner_radius=0,
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        self.scrollable_frame.pack(fill="both", expand=True)
        
        # ---------- HEADER ----------
        header = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#ffffff", height=70)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        # Header content
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=20, pady=12)
        
        # Icon + Title
        ctk.CTkLabel(
            header_left,
            text="🚦",
            font=("Segoe UI", 24),
        ).pack(side="left", padx=(0, 10))
        
        title_frame = ctk.CTkFrame(header_left, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH",
            font=("Segoe UI", 20, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Giám sát và điều khiển giao thông thời gian thực",
            font=("Segoe UI", 12),
            text_color="#64748b",
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))
        
        # Status indicator (right side)
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=20)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="⚫ Đã dừng",
            font=("Segoe UI", 12),
            text_color="#64748b"
        )
        self.status_label.pack()

        # ---------- CONTROL BAR ----------
        control_bar_main = ctk.CTkFrame(self.scrollable_frame, fg_color="#ffffff", corner_radius=0)
        control_bar_main.pack(fill="x", padx=0, pady=(1, 0))
        
        # First row - Mode and Action buttons (compact)
        control_bar_top = ctk.CTkFrame(control_bar_main, fg_color="transparent", height=60)
        control_bar_top.pack(fill="x", padx=15, pady=(10, 0))
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
            font=("Segoe UI", 12, "bold"),
            command=self.change_mode,
            fg_color="#cbd5e1",
            selected_color="#0ea5e9",
            selected_hover_color="#0284c7",
            unselected_color="#cbd5e1",
            unselected_hover_color="#94a3b8",
            text_color="#1e293b",
            width=120,
            height=38
        )
        mode_segment.pack(side="left", padx=(5, 15))

        # CONTROL BUTTONS
        btn_frame = ctk.CTkFrame(left_controls, fg_color="transparent")
        btn_frame.pack(side="left")
        
        # Play button
        self.play_btn = ctk.CTkButton(
            btn_frame,
            text="▶  Chạy",
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 12, "bold"),
            width=90,
            height=38,
            corner_radius=6,
            command=self.start_sim
        )
        self.play_btn.pack(side="left", padx=3)
        
        # Pause button
        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text="⏸  Tạm dừng",
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="#000000",
            font=("Segoe UI", 12, "bold"),
            width=110,
            height=38,
            corner_radius=6,
            command=self.pause_sim
        )
        self.pause_btn.pack(side="left", padx=3)
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹  Dừng",
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=("Segoe UI", 12, "bold"),
            width=90,
            height=38,
            corner_radius=6,
            command=self.stop_sim
        )
        self.stop_btn.pack(side="left", padx=3)
        
        # Reset button
        reset_btn = ctk.CTkButton(
            btn_frame,
            text="🔄  Đặt lại",
            fg_color="#64748b",
            hover_color="#475569",
            font=("Segoe UI", 12, "bold"),
            width=100,
            height=38,
            corner_radius=6,
            command=self.reset_all
        )
        reset_btn.pack(side="left", padx=3)
        
        # Export button
        export_btn = ctk.CTkButton(
            btn_frame,
            text="⬇  Xuất log",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=("Segoe UI", 12, "bold"),
            width=100,
            height=38,
            corner_radius=6,
            command=self.export_log
        )
        export_btn.pack(side="left", padx=3)
        
        # Second row - Scenario selector
        control_bar_bottom = ctk.CTkFrame(control_bar_main, fg_color="transparent", height=55)
        control_bar_bottom.pack(fill="x", padx=15, pady=(6, 10))
        control_bar_bottom.pack_propagate(False)
        
        scenario_frame = ctk.CTkFrame(control_bar_bottom, fg_color="transparent")
        scenario_frame.pack(side="left")
        
        ctk.CTkLabel(
            scenario_frame,
            text="Kịch bản:",
            font=("Segoe UI", 12, "bold"),
            text_color="#334155"
        ).pack(side="left", padx=(0, 8))
        
        self.case_box = ctk.CTkOptionMenu(
            scenario_frame,
            values=["Mặc định", "SC1 - Xe ưu tiên từ hướng chính", "SC2 - Xe ưu tiên từ hướng nhánh",
                    "SC3 - Nhiều xe ưu tiên 2 hướng", "SC4 - Báo giả", "SC5 - Xe ưu tiên bị kẹt",
                    "SC6 - Nhiều xe ưu tiên liên tiếp"],
            font=("Segoe UI", 12),
            dropdown_font=("Segoe UI", 11),
            fg_color="#cbd5e1",
            button_color="#0ea5e9",
            button_hover_color="#0284c7",
            dropdown_fg_color="#ffffff",
            dropdown_hover_color="#e0f2fe",
            dropdown_text_color="#0f172a",
            text_color="#0f172a",
            width=350,
            height=38,
            corner_radius=6
        )
        self.case_box.pack(side="left")
        self.case_box.set("Mặc định")

        # ---------- MAIN CONTENT ----------
        self.main_container = ctk.CTkFrame(self.scrollable_frame, corner_radius=0, fg_color="#f8fafc")
        self.main_container.pack(fill="both", expand=True, padx=12, pady=(10, 10))
        
        # Create content frame
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        
        # Layout: KPI + Vehicle trên cùng hàng, Log ở dưới full width
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=0)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        
        # ---------- TOP ROW: KPI + VEHICLE ----------

        # KPI Section (left)
        kpi_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        kpi_container.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        kpi_container.grid_columnconfigure(0, weight=1)
        kpi_container.grid_rowconfigure(0, weight=1)
        self.create_kpi_section(kpi_container)
        
        # Vehicle Section (right)
        vehicle_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        vehicle_container.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        vehicle_container.grid_columnconfigure(0, weight=1)
        vehicle_container.grid_rowconfigure(0, weight=1)
        self.create_vehicle_section(vehicle_container)
        
        # ---------- BOTTOM ROW: LOG (full width) ----------
        log_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        log_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        self.create_log_section(log_container)

    # =======================================================

    def create_kpi_section(self, parent):
        """Create KPI cards section - COMPACT with LIGHT theme"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=12)
        section.grid(row=0, column=0, sticky="nsew")
        section.grid_columnconfigure(0, weight=1)
        section.grid_rowconfigure(1, weight=1)
        
        # Header - compact
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=40)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 8))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="📊  KPI Thời gian thực",
            font=("Segoe UI", 14, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(side="left")
        
        # KPI Grid
        kpi_grid = ctk.CTkFrame(section, fg_color="transparent")
        kpi_grid.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        
        # Configure grid for 2 columns
        kpi_grid.grid_columnconfigure(0, weight=1)
        kpi_grid.grid_columnconfigure(1, weight=1)
        
        self.kpi_cards = {}
        
        kpi_data = [
            ("Độ trễ TB", "—", "s", "#ddd6fe", "#4c1d95", "⏱"),           # Pastel purple
            ("Hàng chờ", "—", "xe", "#fed7aa", "#9a3412", "🚗"),          # Pastel peach
            ("Lưu lượng", "—", "xe/h", "#bbf7d0", "#14532d", "📈"),        # Pastel mint green
            ("Dừng/xe", "—", "lần", "#e0e7ff", "#312e81", "⏸"),           # Pastel indigo
            ("Chờ tối đa", "—", "s", "#fecaca", "#991b1b", "⏰"),          # Pastel red/pink
            ("Chu kỳ đèn", "—", "s", "#a5f3fc", "#164e63", "💡"),         # Pastel cyan
            ("Công bằng", "—", "", "#fef08a", "#713f12", "⚖"),            # Pastel yellow
            ("Xử lý khẩn cấp", "—", "s", "#fbcfe8", "#831843", "⚡"),     # Pastel pink/magenta
        ]
        
        for idx, (name, value, unit, bg_color, text_color, icon) in enumerate(kpi_data):
            row = idx // 2
            col = idx % 2
            
            card = ctk.CTkFrame(
                kpi_grid,
                fg_color=bg_color,
                corner_radius=10,
                height=65
            )
            card.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            card.grid_propagate(False)
            
            # Icon
            ctk.CTkLabel(
                card,
                text=icon,
                font=("Segoe UI", 18),
                text_color=text_color
            ).pack(side="left", padx=(12, 8), pady=8)
            
            # Content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 8))
            
            ctk.CTkLabel(
                content,
                text=name,
                font=("Segoe UI", 11, "bold"),
                text_color="#0f172a",
                anchor="w"
            ).pack(anchor="w")
            
            value_frame = ctk.CTkFrame(content, fg_color="transparent")
            value_frame.pack(anchor="w", fill="x")
            
            val_label = ctk.CTkLabel(
                value_frame,
                text=value,
                font=("Segoe UI", 20, "bold"),
                text_color=text_color,
                anchor="w"
            )
            val_label.pack(side="left")
            
            if unit:
                ctk.CTkLabel(
                    value_frame,
                    text=f" {unit}",
                    font=("Segoe UI", 11),
                    text_color="#475569",
                    anchor="w"
                ).pack(side="left", pady=(8, 0))
            
            self.kpi_cards[name] = val_label

    # =======================================================

    def create_vehicle_section(self, parent):
        """Create vehicle count section - VERY COMPACT with LIGHT theme"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=12)
        section.grid(row=0, column=0, sticky="nsew")
        section.grid_rowconfigure(1, weight=1)
        section.grid_columnconfigure(0, weight=1)
        
        # Header - compact
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=40)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 8))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="🚦  Số lượng xe",
            font=("Segoe UI", 14, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(side="left")
        
        # Content frame
        content = ctk.CTkFrame(section, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        
        # Total count card (compact)
        total_card = ctk.CTkFrame(
            content,
            fg_color="#dbeafe",
            corner_radius=12,
            height=70
        )
        total_card.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        total_card.grid_propagate(False)
        
        total_content = ctk.CTkFrame(total_card, fg_color="transparent")
        total_content.pack(expand=True)
        
        ctk.CTkLabel(
            total_content,
            text="Tổng số xe",
            font=("Segoe UI", 12, "bold"),
            text_color="#0f172a"
        ).pack()
        
        self.total_vehicle_label = ctk.CTkLabel(
            total_content,
            text="0",
            font=("Segoe UI", 34, "bold"),
            text_color="#1e3a8a"
        )
        self.total_vehicle_label.pack()
        
        # Direction cards (2x2 grid) - very compact
        direction_grid = ctk.CTkFrame(content, fg_color="transparent")
        direction_grid.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        direction_grid.grid_columnconfigure(0, weight=1)
        direction_grid.grid_columnconfigure(1, weight=1)
        direction_grid.grid_rowconfigure(0, weight=1)
        direction_grid.grid_rowconfigure(1, weight=1)
        
        self.direction_labels = {}
        
        directions = [
            ("Bắc", "0", "#e9d5ff", "#6b21a8", "⬆"),    # Lavender pastel
            ("Nam", "0", "#fed7aa", "#9a3412", "⬇"),    # Peach pastel
            ("Đông", "0", "#bbf7d0", "#14532d", "➡"),   # Mint green pastel
            ("Tây", "0", "#fce7f3", "#831843", "⬅"),    # Pink pastel
        ]
        
        for idx, (direction, count, bg_color, text_color, icon) in enumerate(directions):
            row = idx // 2
            col = idx % 2
            
            card = ctk.CTkFrame(
                direction_grid,
                fg_color=bg_color,
                corner_radius=10
            )
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(expand=True, pady=12)
            
            ctk.CTkLabel(
                content_frame,
                text=f"{icon}  {direction}",
                font=("Segoe UI", 12, "bold"),
                text_color="#0f172a"
            ).pack()
            
            val_label = ctk.CTkLabel(
                content_frame,
                text=count,
                font=("Segoe UI", 24, "bold"),
                text_color=text_color
            )
            val_label.pack(pady=(2, 0))
            
            self.direction_labels[direction] = val_label
    
    # =======================================================

    def create_log_section(self, parent):
        """Create log section - VERY TALL without own scrollbar"""
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=12)
        section.grid(row=0, column=0, sticky="nsew")
        
        # Header
        header_frame = ctk.CTkFrame(section, fg_color="transparent", height=40)
        header_frame.pack(fill="x", padx=15, pady=(12, 8))
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="📋  Sự kiện Log",
            font=("Segoe UI", 14, "bold"),
            text_color="#0f172a",
            anchor="w"
        ).pack(side="left")
        
        # Log text box - TALL without scrollbar (use main scrollbar)
        log_frame = ctk.CTkFrame(section, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        self.log_box = tk.Text(
            log_frame,
            bg="#f8fafc",
            fg="#1e293b",
            wrap="word",
            relief="flat",
            font=("Consolas", 9),
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=0,
            height=25
        )
        self.log_box.pack(fill="both", expand=True)
        
        self.log("🚦 Hệ thống sẵn sàng. Nhấn 'Chạy' để bắt đầu mô phỏng.")

    # =======================================================

    def change_mode(self, value):
        self.mode = value
        self.log(f"✓ Chuyển sang chế độ: {value}")

    def start_sim(self):
        if self.running:
            return
        self.running = True
        self.status_label.configure(text="🟢 Đang chạy", text_color="#10b981")
        threading.Thread(target=self.simulate, daemon=True).start()
        self.log("▶ Bắt đầu mô phỏng giao thông")

    def pause_sim(self):
        self.running = False
        self.status_label.configure(text="🟡 Tạm dừng", text_color="#f59e0b")
        self.log("⏸ Tạm dừng mô phỏng")

    def stop_sim(self):
        self.running = False
        self.status_label.configure(text="⚫ Đã dừng", text_color="#64748b")
        self.log("⏹ Đã dừng mô phỏng")

    def export_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_log_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.log_box.get("1.0", "end"))
        self.log(f"✓ Đã xuất file: {filename}")

    def simulate(self):
        """Simulate real-time data updates"""
        while self.running:
            # Update KPI values
            kpi_updates = {
                "Độ trễ TB": f"{round(random.uniform(30, 60), 1)}",
                "Hàng chờ": f"{round(random.uniform(8, 20), 1)}",
                "Lưu lượng": f"{random.randint(280, 400)}",
                "Dừng/xe": f"{round(random.uniform(1.5, 3.5), 1)}",
                "Chờ tối đa": f"{random.randint(80, 150)}",
                "Chu kỳ đèn": f"{random.randint(60, 120)}",
                "Công bằng": f"{round(random.uniform(0.75, 0.95), 2)}",
                "Xử lý khẩn cấp": f"{random.randint(10, 25)}",
            }
            
            for name, value in kpi_updates.items():
                if name in self.kpi_cards:
                    self.kpi_cards[name].configure(text=value)
            
            # Update vehicle counts
            total = random.randint(150, 200)
            self.total_vehicle_label.configure(text=str(total))
            
            direction_counts = {
                "Bắc": random.randint(30, 60),
                "Nam": random.randint(25, 50),
                "Đông": random.randint(40, 65),
                "Tây": random.randint(30, 55),
            }
            
            for direction, count in direction_counts.items():
                if direction in self.direction_labels:
                    self.direction_labels[direction].configure(text=str(count))
            
            # Random log events
            events = [
                "Cập nhật trạng thái đèn giao thông",
                "Phát hiện tăng lưu lượng tại hướng Đông",
                "Điều chỉnh chu kỳ đèn tự động",
                "Xe ưu tiên được phát hiện - Kích hoạt ưu tiên",
                "Giảm lưu lượng tại hướng Bắc",
                "Hệ thống hoạt động ổn định",
            ]
            if random.random() < 0.3:
                self.log(random.choice(events))
            
            time.sleep(2)

    # =======================================================

    def reset_all(self):
        """Reset all interface elements"""
        self.running = False
        self.status_label.configure(text="⚫ Đã dừng", text_color="#64748b")
        self.case_box.set("Mặc định")
        self.mode_option.set("Mặc định")
        
        # Reset KPI
        for name, label in self.kpi_cards.items():
            label.configure(text="—")
        
        # Reset vehicles
        self.total_vehicle_label.configure(text="0")
        for direction, label in self.direction_labels.items():
            label.configure(text="0")
        
        # Clear log
        self.log_box.delete("1.0", "end")
        self.log("🔄 Hệ thống đã được đặt lại")
        self.log("🚦 Hệ thống sẵn sàng. Nhấn 'Chạy' để bắt đầu mô phỏng.")

    # =======================================================

    def log(self, msg):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")


if __name__ == "__main__":
    app = SmartTrafficApp()
    app.mainloop()
