import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
import threading
import time
import random

# =========================
# KHỞI TẠO CỬA SỔ CHÍNH
# =========================
window = tk.Tk()
window.title("🚦 HỆ THỐNG GIAO THÔNG THÔNG MINH")
window.geometry("1300x670")
window.resizable(True, True)
window.configure(bg="#f0f0f0")

# =========================
# BIẾN TOÀN CỤC
# =========================
timer_running = False
timer_value = 0.0
current_mode = "normal"

# =========================
# CÁC HÀM CHÍNH
# =========================
def log_event(message):
    """Ghi log sự kiện vào khung log"""
    time_now = datetime.now().strftime("[%H:%M:%S]")
    log_text.insert(tk.END, f"{time_now} {message}\n")
    log_text.see(tk.END)

def update_kpi():
    """Cập nhật dữ liệu KPI"""
    kpi_labels["Average Delay"].config(text=f"Độ trễ trung bình: {random.uniform(0, 10):.2f}")
    kpi_labels["Queue Length"].config(text=f"Độ dài hàng chờ: {random.uniform(0, 10):.2f}")
    kpi_labels["Throughput"].config(text=f"Lưu lượng: {random.uniform(0, 10):.2f}")
    kpi_labels["Stops/Vehicle"].config(text=f"Số lần dừng/xe: {random.uniform(0, 10):.2f}")
    kpi_labels["Max Waiting"].config(text=f"Thời gian chờ tối đa: {random.uniform(0, 10):.2f}")
    kpi_labels["Fairness Index"].config(text=f"Chỉ số công bằng: {random.uniform(0, 10):.2f}")
    kpi_labels["Emergency Clearance"].config(text=f"Thời gian xử lý khẩn cấp: {random.uniform(0, 10):.2f}")

def update_vehicle_counts():
    """Cập nhật số lượng xe"""
    vehicle_labels["Total"].config(text=f"Tổng số xe: {random.randint(0, 50)}")
    vehicle_labels["East"].config(text=f"Hướng Đông: {random.randint(0, 20)}")
    vehicle_labels["West"].config(text=f"Hướng Tây: {random.randint(0, 20)}")
    vehicle_labels["South"].config(text=f"Hướng Nam: {random.randint(0, 20)}")
    vehicle_labels["North"].config(text=f"Hướng Bắc: {random.randint(0, 20)}")

stop_event = threading.Event()

def timer_thread():
    global timer_value
    while not stop_event.is_set():
        time.sleep(1)
        timer_value += 1
        hrs = int(timer_value // 3600)
        mins = int((timer_value % 3600) // 60)
        secs = int(timer_value % 60)
        formatted_time = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        clock_label.config(text=formatted_time)
        update_kpi()
        update_vehicle_counts()

def start_timer():
    global timer_running
    if not timer_running:
        timer_running = True
        stop_event.clear()
        threading.Thread(target=timer_thread, daemon=True).start()
        log_event("▶️ Mô phỏng bắt đầu.")

def pause_timer():
    global timer_running
    timer_running = False
    stop_event.set()
    log_event("⏸ Mô phỏng tạm dừng.")

def reset_timer():
    global timer_value, timer_running
    timer_running = False
    stop_event.set()
    timer_value = 0.0
    clock_label.config(text="00:00:00")
    for metric, lbl in kpi_labels.items():
        lbl.config(text=f"{metric}: --")
    for name, lbl in vehicle_labels.items():
        lbl.config(text=f"{name}: --")
    log_event("🔄 Mô phỏng được reset.")

def export_log():
    """Xuất file log"""
    file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(log_text.get("1.0", tk.END))
        log_event(f"📄 Log đã được xuất ra: {file_path}")

def switch_mode():
    """Chuyển chế độ hệ thống"""
    global current_mode
    current_mode = mode_var.get()
    if current_mode == "normal":
        status_label.config(text="Trạng thái hệ thống: NORMAL", bg="#dfe6e9", fg="#2d3436")
        log_event("🔁 Chế độ mặc định được kích hoạt.")
    else:
        status_label.config(text="Trạng thái hệ thống: ADAPTIVE", bg="#00b894", fg="white")
        log_event("🤖 Chế độ tự động được kích hoạt.")

# =========================
# FRAME 1 - HEADER
# =========================
frame_header = tk.Frame(window, bg="#2d3436", pady=15)
frame_header.pack(fill="x")

title_label = tk.Label(frame_header,
    text="🚦 HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH",
    font=("Arial", 18, "bold"), bg="#2d3436", fg="white")
title_label.pack()

status_label = tk.Label(frame_header, text="Trạng thái hệ thống: NORMAL",
                        font=("Arial", 12, "bold"), bg="#dfe6e9", fg="#2d3436",
                        relief="solid", borderwidth=2, padx=10, pady=5)
status_label.pack(pady=(10, 0))

# =========================
# FRAME 2 & 3 - MIDDLE SECTION
# =========================
middle_container = tk.Frame(window, bg="#f0f0f0")
middle_container.pack(fill="both", expand=True, padx=10, pady=5)
middle_container.columnconfigure(0, weight=7)
middle_container.columnconfigure(1, weight=3)

# =========================
# LEFT - SIMULATION
# =========================
frame_left = tk.Frame(middle_container, bg="#f0f0f0")
frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

# Chế độ switch
frame_mode = tk.LabelFrame(frame_left, text="Chọn chế độ", font=("Arial", 11, "bold"))
frame_mode.pack(fill="x", pady=5)

mode_var = tk.StringVar(value="normal")
toggle_frame = tk.Frame(frame_mode, bg="#e0e0e0", relief="solid", borderwidth=2)
toggle_frame.pack(fill="x")

def toggle_normal():
    mode_var.set("normal")
    btn_normal.config(bg="#74b9ff", fg="white", relief="sunken")
    btn_smart.config(bg="#e0e0e0", fg="black", relief="raised")
    switch_mode()

def toggle_smart():
    mode_var.set("smart")
    btn_smart.config(bg="#00b894", fg="white", relief="sunken")
    btn_normal.config(bg="#e0e0e0", fg="black", relief="raised")
    switch_mode()

btn_normal = tk.Button(toggle_frame, text="MẶC ĐỊNH", command=toggle_normal, 
                       bg="#74b9ff", fg="white", relief="sunken", font=("Arial", 11, "bold"))
btn_normal.pack(side="left", fill="both", expand=True)

btn_smart = tk.Button(toggle_frame, text="TỰ ĐỘNG", command=toggle_smart, 
                      bg="#e0e0e0", fg="black", relief="raised", font=("Arial", 11, "bold"))
btn_smart.pack(side="left", fill="both", expand=True)

# =========================
# MÔ PHỎNG SUMO + ĐỒNG HỒ GÓC PHẢI
# =========================
frame_sim = tk.LabelFrame(frame_left, text="Mô phỏng SUMO", font=("Arial", 11, "bold"))
frame_sim.pack(fill="both", expand=True, pady=5)

canvas = tk.Canvas(frame_sim, bg="#ecf0f1", highlightthickness=0)
canvas.pack(fill="both", expand=True)

# Text trung tâm
canvas_text = canvas.create_text(0, 0, text="🚗 Khu vực mô phỏng giao lộ", font=("Arial", 16, "bold"))

# Đồng hồ góc phải (ô vuông)
clock_frame = tk.Frame(canvas, bg="#f5f6fa", highlightbackground="black", highlightthickness=1)
clock_label = tk.Label(clock_frame, text="00:00:00", font=("Consolas", 14, "bold"), bg="#f5f6fa", fg="#2d3436")
clock_label.pack(padx=8, pady=4)

# Đặt frame đồng hồ trong canvas
canvas_window = canvas.create_window(0, 0, window=clock_frame, anchor="ne")

def center_canvas_text(event):
    """Căn giữa text mô phỏng và đồng hồ góc phải"""
    canvas.coords(canvas_text, event.width // 2, event.height // 2)
    canvas.coords(canvas_window, event.width - 10, 10)
canvas.bind("<Configure>", center_canvas_text)


# =========================
# CÁC NÚT ĐIỀU KHIỂN
# =========================
frame_controls = tk.LabelFrame(frame_left, font=("Arial", 11, "bold"), bg="#f0f0f0")
frame_controls.pack(fill="x", pady=5)

# Khung con để căn giữa các nút
buttons_container = tk.Frame(frame_controls, bg="#f0f0f0")
buttons_container.pack(anchor="center", pady=5)

# Các nút điều khiển
btn_run = tk.Button(buttons_container, text="▶️ Run", bg="#55efc4", font=("Arial", 11, "bold"), width=10, command=start_timer)
btn_pause = tk.Button(buttons_container, text="⏸ Pause", bg="#ffeaa7", font=("Arial", 11, "bold"), width=10, command=pause_timer)
btn_reset = tk.Button(buttons_container, text="🔄 Reset", bg="#fab1a0", font=("Arial", 11, "bold"), width=10, command=reset_timer)
btn_export = tk.Button(buttons_container, text="📄 Export Log", bg="#a29bfe", font=("Arial", 11, "bold"), width=12, command=export_log)

# Sắp xếp nút nằm ngang, căn giữa
btn_run.grid(row=0, column=0, padx=8, pady=5)
btn_pause.grid(row=0, column=1, padx=8, pady=5)
btn_reset.grid(row=0, column=2, padx=8, pady=5)
btn_export.grid(row=0, column=3, padx=8, pady=5)


# =========================
# RIGHT - KPI + VEHICLES + LOG
# =========================
frame_right = tk.Frame(middle_container, bg="#f0f0f0")
frame_right.grid(row=0, column=1, sticky="nsew")

# --- Khung ngang KPI + Vehicle ---
top_right = tk.Frame(frame_right, bg="#f0f0f0")
top_right.pack(fill="x")

# KPI Frame
frame_kpi = tk.LabelFrame(top_right, text="📊 KPI Thời gian thực", font=("Arial", 11, "bold"))
frame_kpi.pack(side="left", fill="both", expand=True, padx=5, pady=5)

kpi_labels = {}
for metric in ["Average Delay", "Queue Length", "Throughput", "Stops/Vehicle",
               "Max Waiting", "Fairness Index", "Emergency Clearance"]:
    lbl = tk.Label(frame_kpi, text=f"{metric}: --", anchor="w", font=("Consolas", 9))
    lbl.pack(fill="x", padx=8)
    kpi_labels[metric] = lbl

# Vehicle Frame
frame_vehicle = tk.LabelFrame(top_right, text="🚗 Số lượng xe", font=("Arial", 11, "bold"))
frame_vehicle.pack(side="left", fill="both", expand=True, padx=5, pady=5)

vehicle_labels = {}
for name in ["Total", "East", "West", "South", "North"]:
    lbl = tk.Label(frame_vehicle, text=f"{name}: --", anchor="w", font=("Consolas", 9))
    lbl.pack(fill="x", padx=8)
    vehicle_labels[name] = lbl

# Log Frame
frame_log = tk.LabelFrame(frame_right, text="🧾 Event Log", font=("Arial", 11, "bold"))
frame_log.pack(fill="both", expand=True, padx=5, pady=5)

log_text = tk.Text(frame_log, font=("Consolas", 9))
log_text.pack(fill="both", expand=True)

# =========================
# KHỞI TẠO BAN ĐẦU
# =========================
log_event("✅ Hệ thống khởi động ở chế độ NORMAL.")
update_kpi()
update_vehicle_counts()

# =========================
window.mainloop()