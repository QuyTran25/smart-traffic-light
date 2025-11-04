

---

## 🎯 TỔNG QUAN

Hệ thống có **2 CHẾ ĐỘ ĐIỀU KHIỂN**:

### 1️⃣ Chế độ **MẶC ĐỊNH** (Fixed-Time Control)
- **Đặc điểm**: Chu kỳ đèn cố định, không thích ứng với mật độ giao thông
- **Thời gian pha**: Được cấu hình trước và không thay đổi
- **Xử lý xe ưu tiên**: ❌ **KHÔNG HỖ TRỢ** (xe ưu tiên chỉ hoạt động ở chế độ Tự động)
- **Ưu điểm**: Đơn giản, dễ dự đoán, ổn định
- **Nhược điểm**: Không tối ưu cho lưu lượng thay đổi

### 2️⃣ Chế độ **TỰ ĐỘNG** (Adaptive Control)
- **Đặc điểm**: Điều chỉnh thời gian pha dựa trên mật độ giao thông thực tế
- **Thời gian pha**: Động, tính toán theo công thức áp suất (Pressure-based)
- **Xử lý xe ưu tiên**: ✅ **HỖ TRỢ ĐẦY ĐỦ** (6 kịch bản SC1-SC6)
- **Ưu điểm**: Tối ưu hóa thông lượng, giảm thời gian chờ, hỗ trợ xe ưu tiên
- **Nhược điểm**: Phức tạp hơn, phụ thuộc vào độ chính xác cảm biến

---

## 📋 DANH SÁCH 8 KPI

| # | Tên KPI | Đơn vị | Áp dụng cho chế độ |
|---|---------|--------|-------------------|
| 1 | **Độ trễ trung bình** (Average Delay) | giây | Cả 2 chế độ |
| 2 | **Độ dài hàng đợi** (Queue Length) | PCU | Cả 2 chế độ |
| 3 | **Thông lượng** (Throughput) | xe/giờ | Cả 2 chế độ |
| 4 | **Số lần dừng/xe** (Stops per Vehicle) | lần | Cả 2 chế độ |
| 5 | **Thời gian chờ tối đa** (Max Waiting Time) | giây | Cả 2 chế độ |
| 6 | **Độ dài chu kỳ** (Cycle Length) | giây | Cả 2 chế độ (khác nhau) |
| 7 | **Chỉ số công bằng** (Fairness Index) | % | Cả 2 chế độ |
| 8 | **Thời gian giải phóng xe ưu tiên** (Emergency Clearance Time) | giây | **CHỈ CHẾ ĐỘ TỰ ĐỘNG** |

---

## 🔢 CÔNG THỨC TÍNH CHO TỪNG CHẾ ĐỘ

---

### KPI 1️⃣: ĐỘ TRỄ TRUNG BÌNH (Average Delay)

**Định nghĩa**: Thời gian chậm trễ trung bình của mỗi xe so với thời gian di chuyển tự do

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Delay_i = TravelTime_i - FreeFlowTime_i

Average_Delay = Σ(Delay_i) / N_departed

Trong đó:
- TravelTime_i: Thời gian thực tế xe i di chuyển qua mạng (giây)
  → Lấy từ SUMO: traci.vehicle.getDeparture(), traci.simulation.getTime()
  
- FreeFlowTime_i: Thời gian di chuyển khi không có tắc nghẽn (giây)
  → Tính từ: route_length / max_speed
  → route_length = traci.vehicle.getDistance()
  → max_speed = vận tốc tối đa của loại xe (m/s)
  
- N_departed: Tổng số xe đã xuất phát (departed vehicles)
```

#### 📊 Triển khai trong Code:

```python
# Trong update_data_from_sumo():
departed_vehicles = traci.simulation.getDepartedIDList()
for veh_id in departed_vehicles:
    if veh_id not in self.vehicle_travel_data:
        self.vehicle_travel_data[veh_id] = {
            'depart_time': traci.simulation.getTime(),
            'route_length': traci.vehicle.getDistance(veh_id)
        }

arrived_vehicles = traci.simulation.getArrivedIDList()
total_delay = 0
count = 0

for veh_id in arrived_vehicles:
    if veh_id in self.vehicle_travel_data:
        depart_time = self.vehicle_travel_data[veh_id]['depart_time']
        route_length = self.vehicle_travel_data[veh_id]['route_length']
        arrive_time = traci.simulation.getTime()
        
        travel_time = arrive_time - depart_time
        free_flow_time = route_length / 13.89  # Assuming 50 km/h = 13.89 m/s
        delay = travel_time - free_flow_time
        
        total_delay += max(0, delay)  # Chỉ tính delay dương
        count += 1

average_delay = total_delay / count if count > 0 else 0
```

#### 🎯 Mục tiêu:
- **Chế độ Mặc định**: Delay thường cao hơn vì không thích ứng
- **Chế độ Tự động**: Delay thấp hơn nhờ tối ưu hóa thời gian xanh

---

### KPI 2️⃣: ĐỘ DÀI HÀNG ĐỢI (Queue Length)

**Định nghĩa**: Tổng số xe đang chờ tại ngã tư, quy đổi theo đơn vị PCU (Passenger Car Unit)

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Queue_Length = Σ(Stopped_Vehicles_i × PCU_i)

Trong đó:
- Stopped_Vehicles_i: Số xe dừng tại làn i
  → Xe dừng: speed < 0.1 m/s
  
- PCU_i: Hệ số quy đổi theo tiêu chuẩn Việt Nam (TCVN 5729:1997)
  * motorcycle (xe máy): 0.3 PCU
  * passenger (xe con): 1.0 PCU
  * bus (xe buýt): 1.5 PCU
  * emergency (xe ưu tiên): 1.0 PCU
```

#### 📊 Triển khai trong Code:

```python
# Bảng PCU theo tiêu chuẩn Việt Nam
PCU_FACTORS = {
    'motorcycle': 0.3,
    'passenger': 1.0,
    'bus': 1.5,
    'emergency': 1.0,
    'DEFAULT': 1.0  # Nếu không xác định được loại
}

def calculate_queue_length():
    queue_pcu = 0.0
    
    for veh_id in traci.vehicle.getIDList():
        speed = traci.vehicle.getSpeed(veh_id)
        
        # Xe coi như dừng nếu speed < 0.1 m/s
        if speed < 0.1:
            vtype = traci.vehicle.getTypeID(veh_id)
            pcu_factor = PCU_FACTORS.get(vtype, PCU_FACTORS['DEFAULT'])
            queue_pcu += pcu_factor
    
    return queue_pcu
```

#### 🎯 Ý nghĩa:
- **PCU** giúp so sánh công bằng giữa các loại xe
- **Chế độ Tự động** sử dụng Queue Length để tính Pressure (Áp suất):
  ```
  Pressure = ALPHA × Queue_Length_PCU
  Green_Time = T_MIN + Pressure
  ```

---

### KPI 3️⃣: THÔNG LƯỢNG (Throughput)

**Định nghĩa**: Số lượng xe qua ngã tư trong 1 giờ

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Throughput = (N_arrived / Simulation_Time) × 3600

Trong đó:
- N_arrived: Số xe đã đến đích (arrived vehicles)
  → Lấy từ: traci.simulation.getArrivedIDList()
  
- Simulation_Time: Thời gian mô phỏng hiện tại (giây)
  → Lấy từ: traci.simulation.getTime()
  
- 3600: Hệ số chuyển đổi giây → giờ
```

#### 📊 Triển khai trong Code:

```python
def calculate_throughput():
    current_time = traci.simulation.getTime()
    arrived_count = len(traci.simulation.getArrivedIDList())
    
    # Tích lũy số xe arrived
    self.total_arrived += arrived_count
    
    # Tính throughput (xe/giờ)
    if current_time > 0:
        throughput = (self.total_arrived / current_time) * 3600
    else:
        throughput = 0
    
    return throughput
```

#### 🎯 So sánh:
- **Chế độ Mặc định**: Throughput cố định, phụ thuộc chu kỳ đèn
- **Chế độ Tự động**: Throughput cao hơn nhờ tối ưu hóa thời gian xanh

---

### KPI 4️⃣: SỐ LẦN DỪNG/XE (Stops per Vehicle)

**Định nghĩa**: Số lần dừng trung bình của mỗi xe

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Stops_per_Vehicle = Total_Stops / N_vehicles

Trong đó:
- Total_Stops: Tổng số lần dừng của tất cả xe
  → Mỗi xe: Đếm số lần chuyển từ speed > 0.1 m/s → speed < 0.1 m/s
  
- N_vehicles: Tổng số xe đã departed
```

#### 📊 Triển khai trong Code:

```python
# Tracking vehicle stops
self.vehicle_stops = {}  # {veh_id: {'last_speed': float, 'stop_count': int}}

def track_vehicle_stops():
    for veh_id in traci.vehicle.getIDList():
        current_speed = traci.vehicle.getSpeed(veh_id)
        
        # Khởi tạo nếu xe mới
        if veh_id not in self.vehicle_stops:
            self.vehicle_stops[veh_id] = {
                'last_speed': current_speed,
                'stop_count': 0
            }
        else:
            last_speed = self.vehicle_stops[veh_id]['last_speed']
            
            # Phát hiện stop: chuyển từ moving → stopped
            if last_speed > 0.1 and current_speed < 0.1:
                self.vehicle_stops[veh_id]['stop_count'] += 1
            
            # Cập nhật last_speed
            self.vehicle_stops[veh_id]['last_speed'] = current_speed
    
    # Tính trung bình
    total_stops = sum(v['stop_count'] for v in self.vehicle_stops.values())
    num_vehicles = len(self.vehicle_stops)
    
    stops_per_vehicle = total_stops / num_vehicles if num_vehicles > 0 else 0
    return stops_per_vehicle
```

#### 🎯 Ý nghĩa:
- **Ít dừng hơn** = Lái xe mượt mà hơn, tiết kiệm nhiên liệu
- **Chế độ Tự động** giảm stops nhờ tối ưu hóa chu kỳ đèn

---

### KPI 5️⃣: THỜI GIAN CHỜ TỐI ĐA (Max Waiting Time)

**Định nghĩa**: Thời gian chờ lâu nhất của một xe bất kỳ

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Max_Waiting_Time = max(Waiting_Time_i) for all vehicles

Trong đó:
- Waiting_Time_i: Tổng thời gian xe i đã chờ (dừng và speed < 0.1 m/s)
  → Lấy từ: traci.vehicle.getAccumulatedWaitingTime(veh_id)
```

#### 📊 Triển khai trong Code:

```python
def calculate_max_waiting_time():
    max_wait = 0
    
    for veh_id in traci.vehicle.getIDList():
        waiting_time = traci.vehicle.getAccumulatedWaitingTime(veh_id)
        max_wait = max(max_wait, waiting_time)
    
    return max_wait
```

#### 🎯 Ý nghĩa trong Chế độ Tự động:
- **Starvation Prevention**: AdaptiveController có cơ chế chống đói
  ```python
  MAX_WAITING_TIME = 120  # giây
  
  if waiting_time > MAX_WAITING_TIME:
      # Tăng debt cho hướng này → ưu tiên trong chu kỳ tiếp
      green_debt[direction] += (waiting_time - MAX_WAITING_TIME) * ALPHA
  ```

---

### KPI 6️⃣: ĐỘ DÀI CHU KỲ (Cycle Length)

**Định nghĩa**: Thời gian để tất cả các pha đèn hoàn thành 1 chu kỳ

#### 🔄 Công thức **KHÁC NHAU** giữa 2 chế độ:

---

#### ➡️ **CHẾ ĐỘ MẶC ĐỊNH** (Fixed-Time):

```
Cycle_Length = Σ(Green_i + Yellow_i + Red_i) for all phases

Trong đó:
- Green_i: Thời gian đèn xanh pha i (CỐ ĐỊNH)
- Yellow_i: Thời gian đèn vàng pha i (CỐ ĐỊNH, thường 3s)
- Red_i: Thời gian đèn đỏ pha i (CỐ ĐỊNH)

Ví dụ với 2 pha (NS/EW):
- Phase NS: Green=30s, Yellow=3s, Red=33s → 66s
- Phase EW: Green=30s, Yellow=3s, Red=33s → 66s
- Cycle_Length = 66s (mỗi pha lặp lại sau 66s)
```

**Đặc điểm**:
- ✅ **Dự đoán được**: Chu kỳ luôn cố định
- ✅ **Ổn định**: Không thay đổi theo thời gian
- ❌ **Không linh hoạt**: Không thích ứng với lưu lượng

---

#### ➡️ **CHẾ ĐỘ TỰ ĐỘNG** (Adaptive):

```
Cycle_Length = Average(Last_N_Cycles)

Trong đó:
- Last_N_Cycles: Lịch sử N chu kỳ gần nhất (thường N=10)
- Mỗi chu kỳ được tính động dựa trên Pressure:

  Green_Time_i = T_MIN + ALPHA × Queue_Length_PCU_i
  Green_Time_i = min(max(Green_Time_i, T_MIN), T_MAX)
  
  Cycle = Σ(Green_Time_i + Yellow_i) for all phases

Trong đó:
- T_MIN = 10s (thời gian xanh tối thiểu)
- T_MAX = 120s (thời gian xanh tối đa)
- ALPHA = 0.5 s/PCU (hệ số điều chỉnh)
- Queue_Length_PCU_i: Độ dài hàng đợi hướng i (PCU)
```

**Đặc điểm**:
- ✅ **Linh hoạt**: Thay đổi theo mật độ giao thông
- ✅ **Tối ưu**: Hướng đông xe → xanh lâu hơn
- ❌ **Khó dự đoán**: Chu kỳ thay đổi liên tục

#### 📊 Triển khai trong Code:

```python
# CHẾ ĐỘ MẶC ĐỊNH (Fixed-Time)
def calculate_fixed_cycle_length():
    # Đọc từ file cấu hình SUMO (.sumocfg hoặc .net.xml)
    # Hoặc hard-code nếu biết trước
    phase_durations = {
        'NS': {'green': 30, 'yellow': 3},
        'EW': {'green': 30, 'yellow': 3}
    }
    
    cycle = sum(phase['green'] + phase['yellow'] for phase in phase_durations.values())
    return cycle  # = 66s

# CHẾ ĐỘ TỰ ĐỘNG (Adaptive)
def calculate_adaptive_cycle_length():
    if not hasattr(self, 'adaptive_controllers'):
        return 0
    
    total_cycle = 0
    count = 0
    
    for controller in self.adaptive_controllers.values():
        # Lấy lịch sử chu kỳ từ controller
        if hasattr(controller, 'phase_history') and len(controller.phase_history) > 0:
            # Lấy 10 chu kỳ gần nhất
            recent_cycles = controller.phase_history[-10:]
            avg_cycle = sum(recent_cycles) / len(recent_cycles)
            total_cycle += avg_cycle
            count += 1
    
    return total_cycle / count if count > 0 else 0
```

#### 🎯 So sánh:
| Tiêu chí | Mặc định | Tự động |
|----------|----------|---------|
| **Giá trị** | Cố định (VD: 66s) | Động (VD: 45-90s) |
| **Tính dự đoán** | Cao | Thấp |
| **Tối ưu hóa** | Không | Có |

---

### KPI 7️⃣: CHỈ SỐ CÔNG BẰNG (Fairness Index)

**Định nghĩa**: Đo lường mức độ công bằng trong phân phối thời gian chờ giữa các hướng

#### ✅ Công thức (Giống nhau cho cả 2 chế độ):

```
Fairness = (1 - (Max_Wait - Mean_Wait) / Max_Wait) × 100%

Trong đó:
- Max_Wait: Thời gian chờ tối đa của bất kỳ hướng nào
- Mean_Wait: Thời gian chờ trung bình của tất cả các hướng

Giải thích:
- Fairness = 100%: Hoàn toàn công bằng (tất cả hướng chờ như nhau)
- Fairness = 0%: Rất bất công (một hướng chờ rất lâu, các hướng khác không chờ)
```

#### 📊 Triển khai trong Code:

```python
def calculate_fairness():
    # Tính waiting time trung bình cho mỗi hướng
    direction_wait_times = {
        'J1_N': 0, 'J1_S': 0, 'J1_E': 0, 'J1_W': 0,
        'J4_N': 0, 'J4_S': 0, 'J4_E': 0, 'J4_W': 0
    }
    
    direction_vehicle_counts = {key: 0 for key in direction_wait_times}
    
    # Tính tổng waiting time mỗi hướng
    for veh_id in traci.vehicle.getIDList():
        edge_id = traci.vehicle.getRoadID(veh_id)
        waiting_time = traci.vehicle.getAccumulatedWaitingTime(veh_id)
        
        # Xác định hướng từ edge_id
        direction = map_edge_to_direction(edge_id)  # VD: "J1_N"
        
        if direction in direction_wait_times:
            direction_wait_times[direction] += waiting_time
            direction_vehicle_counts[direction] += 1
    
    # Tính trung bình mỗi hướng
    avg_wait_per_direction = []
    for direction in direction_wait_times:
        count = direction_vehicle_counts[direction]
        if count > 0:
            avg_wait = direction_wait_times[direction] / count
            avg_wait_per_direction.append(avg_wait)
    
    if len(avg_wait_per_direction) == 0:
        return 100.0  # Không có xe → coi như công bằng
    
    max_wait = max(avg_wait_per_direction)
    mean_wait = sum(avg_wait_per_direction) / len(avg_wait_per_direction)
    
    if max_wait == 0:
        return 100.0
    
    fairness = (1 - (max_wait - mean_wait) / max_wait) * 100
    return fairness
```

#### 🎯 Ý nghĩa:
- **Chế độ Mặc định**: Fairness phụ thuộc vào cấu hình thời gian xanh cố định
  - Nếu cấu hình cân bằng (VD: NS=30s, EW=30s) → Fairness cao
  - Nếu cấu hình lệch (VD: NS=50s, EW=10s) → Fairness thấp
  
- **Chế độ Tự động**: Fairness được tối ưu hóa bằng Green Debt Mechanism
  ```python
  # Trong AdaptiveController:
  if waiting_time > MAX_WAITING_TIME:
      green_debt[direction] += (waiting_time - MAX_WAITING_TIME) * ALPHA
  ```
  → Hướng chờ lâu sẽ được ưu tiên trong chu kỳ tiếp

---

### KPI 8️⃣: THỜI GIAN GIẢI PHÓNG XE ƯU TIÊN (Emergency Clearance Time)

**Định nghĩa**: Thời gian từ khi phát hiện xe ưu tiên đến khi xe qua ngã tư

#### ⚠️ **CHỈ ÁP DỤNG CHO CHẾ ĐỘ TỰ ĐỘNG**

```
⛔ CHẾ ĐỘ MẶC ĐỊNH: KPI NÀY KHÔNG TỒN TẠI
   Lý do: Chế độ Mặc định không hỗ trợ phát hiện và xử lý xe ưu tiên

✅ CHẾ ĐỘ TỰ ĐỘNG: KPI NÀY ĐƯỢC TÍNH TOÁN ĐẦY ĐỦ
```

#### ✅ Công thức (CHỈ CHẾ ĐỘ TỰ ĐỘNG):

```
Emergency_Clearance_Time = T_crossed - T_detected

Trong đó:
- T_detected: Thời điểm PriorityController phát hiện xe ưu tiên
  → State transition: NORMAL → DETECTION
  → Điều kiện: vehicle.typeID == "priority" AND distance_to_junction < DETECTION_RADIUS (200m)
  
- T_crossed: Thời điểm xe ưu tiên vượt qua trung tâm ngã tư
  → Điều kiện: vehicle.position vượt qua junction center

Clearance_Time = T_crossed - T_detected (giây)
```

#### 📊 Quy trình tính toán chi tiết:

**Bước 1: PHÁT HIỆN (DETECTION)**
```python
# Trong PriorityController.scan_for_emergency_vehicles():

DETECTION_RADIUS = 200  # mét

def scan_for_emergency_vehicles():
    for veh_id in traci.vehicle.getIDList():
        vtype = traci.vehicle.getTypeID(veh_id)
        
        # Chỉ xử lý xe ưu tiên
        if 'priority' not in vtype.lower():
            continue
        
        # Kiểm tra khoảng cách đến ngã tư
        distance = calculate_distance_to_junction(veh_id)
        
        if distance < DETECTION_RADIUS:
            # GHI NHẬN THỜI ĐIỂM PHÁT HIỆN
            detection_time = traci.simulation.getTime()
            
            emergency_vehicle = EmergencyVehicle(
                vehicle_id=veh_id,
                detection_time=detection_time,
                direction=get_vehicle_direction(veh_id)
            )
            
            # Chuyển state: NORMAL → DETECTION
            self.state = PriorityState.DETECTION
            self.log(f"🔍 PHÁT HIỆN XE ƯU TIÊN: {veh_id} tại {detection_time:.1f}s")
```

**Bước 2: XÁC NHẬN (CONFIRMATION)**
```python
# Để tránh false positive, cần xác nhận xe trong CONFIRMATION_WINDOW

CONFIRMATION_WINDOW = 1.0  # giây
CONFIRMATION_COUNT = 2     # số lần confirm

def confirm_emergency_vehicle(vehicle):
    # Kiểm tra xe vẫn còn trong phạm vi và đang tiến gần
    if is_vehicle_approaching(vehicle.vehicle_id):
        vehicle.confirmation_count += 1
        
        if vehicle.confirmation_count >= CONFIRMATION_COUNT:
            # XÁC NHẬN THÀNH CÔNG
            self.state = PriorityState.SAFE_TRANSITION
            self.log(f"✅ XÁC NHẬN XE ƯU TIÊN: {vehicle.vehicle_id}")
```

**Bước 3: CHUYỂN ĐỔI AN TOÀN (SAFE_TRANSITION)**
```python
# Chờ đèn hiện tại hết vàng trước khi chuyển sang ưu tiên

def safe_transition():
    current_phase = traci.trafficlight.getPhase(self.junction_id)
    
    # Nếu đang ở pha vàng, chờ hết vàng
    if is_yellow_phase(current_phase):
        return
    
    # Chuyển sang PREEMPTION_GREEN
    self.state = PriorityState.PREEMPTION_GREEN
    self.apply_emergency_phase(vehicle)
```

**Bước 4: ƯU TIÊN ĐANG HOẠT ĐỘNG (PREEMPTION_GREEN)**
```python
# Áp dụng pha đèn khẩn cấp cho hướng xe ưu tiên

def apply_emergency_phase(vehicle):
    # Tìm pha đèn phù hợp với hướng xe
    emergency_phase = get_emergency_phase_for_direction(vehicle.direction)
    
    # Chuyển sang pha khẩn cấp
    traci.trafficlight.setPhase(self.junction_id, emergency_phase)
    
    # Đảm bảo thời gian xanh tối thiểu
    min_green_time = PREEMPT_MIN_GREEN  # 8 giây
    traci.trafficlight.setPhaseDuration(self.junction_id, min_green_time)
    
    self.log(f"🚨 ÁP DỤNG PHA KHẨN CẤP: {vehicle.direction}")
```

**Bước 5: GIẢI PHÓNG HOÀN TẤT (CLEARANCE COMPLETE)**
```python
# Kiểm tra xe đã qua ngã tư chưa

def check_clearance_complete(vehicle):
    junction_pos = traci.junction.getPosition(self.junction_id)
    vehicle_pos = traci.vehicle.getPosition(vehicle.vehicle_id)
    
    # Tính khoảng cách xe đến tâm ngã tư
    distance = calculate_distance(vehicle_pos, junction_pos)
    
    # Nếu xe đã qua tâm ngã tư (đang đi xa)
    if has_crossed_junction(vehicle, junction_pos):
        # GHI NHẬN THỜI ĐIỂM QUA NGA TƯ
        crossed_time = traci.simulation.getTime()
        
        # TÍNH CLEARANCE TIME
        clearance_time = crossed_time - vehicle.detection_time
        vehicle.clearance_time = clearance_time
        
        # Lưu vào lịch sử
        self.clearance_times.append(clearance_time)
        
        self.log(f"✅ XE ƯU TIÊN ĐÃ QUA: {vehicle.vehicle_id}")
        self.log(f"   Clearance Time: {clearance_time:.2f}s")
        
        # Chuyển sang RESTORE để khôi phục bình thường
        self.state = PriorityState.RESTORE
```

