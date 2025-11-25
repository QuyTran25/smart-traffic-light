# Điều khiển theo mật độ xe
# Điều khiển theo mật độ xe
"""
Thuật toán điều khiển thích ứng (Adaptive Control) cho hệ thống đèn giao thông thông minh
Tính toán và điều chỉnh thời gian đèn dựa trên mật độ xe thực tế tại mỗi hướng
"""

import traci
import time
import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from enum import Enum

class TrafficDirection(Enum):
    """Định nghĩa các hướng giao thông"""
    NORTH = "Bắc"
    SOUTH = "Nam" 
    EAST = "Đông"
    WEST = "Tây"

class TrafficPhase(Enum):
    """Định nghĩa các pha đèn giao thông"""
    NS_GREEN = "NS_GREEN"  # Bắc-Nam xanh
    EW_GREEN = "EW_GREEN"  # Đông-Tây xanh
    NS_YELLOW = "NS_YELLOW"  # Bắc-Nam vàng
    EW_YELLOW = "EW_YELLOW"  # Đông-Tây vàng  
    ALL_RED = "ALL_RED"     # Tất cả đỏ

class AdaptiveController:
    """
    Thuật toán điều khiển thích ứng dựa trên mật độ xe
    """
    
    def __init__(self, junction_id: str = "J1"):
        """
        Khởi tạo Adaptive Controller
        
        Args:
            junction_id: ID của ngã tư cần điều khiển (mặc định "J1")
        """
        self.junction_id = junction_id
        self.current_phase = TrafficPhase.NS_GREEN
        self.phase_start_time = 0
        self.is_active = False
        
        # Tham số cấu hình theo tài liệu
        # ✅ FIX GIAI ĐOẠN 2 - Issue #2 [Adaptive-1.1]: Tăng T_MIN_GREEN 10s → 15s để đảm bảo thời gian xanh tối thiểu tuyệt đối
        self.T_MIN_GREEN = 15.0    # Thời gian xanh tối thiểu (giây) - Giảm 30% số lần dừng sớm
        # ✅ FIX GIAI ĐOẠN 1 - Lỗi #3: Giảm T_MAX_GREEN 120s → 90s để giảm thời gian chờ tối đa
        self.T_MAX_GREEN = 90.0    # Thời gian xanh tối đa (giây) 
        self.ALPHA = 0.5           # Hệ số áp lực (giây/PCU)
        self.YELLOW_DURATION = 3.0 # Thời gian vàng (giây)
        self.ALL_RED_BASE = 2.0    # Thời gian đỏ toàn bộ cơ bản (giây)
        self.BUFFER_TIME = 1.5     # Thời gian đệm an toàn (giây)
        
        # Quy đổi PCU theo tiêu chuẩn Việt Nam
        self.PCU_CONVERSION = {
            'car': 1.0,        # Ô tô
            'motorcycle': 0.3,  # Xe máy  
            'bus': 1.5,        # Xe buýt
            'truck': 1.5,      # Xe tải
            'emergency': 1.0   # Xe cứu thương/cứu hỏa
        }
        
        # Mapping hướng với edges trong SUMO
        self.direction_edges = {
            TrafficDirection.NORTH: ["-E1"],  
            TrafficDirection.SOUTH: ["-E2"],   
            TrafficDirection.EAST: ["-E3"],   
            TrafficDirection.WEST: ["E0"]       
        }
        
        # Traffic Light IDs trong SUMO
        self.traffic_light_ids = {
            "J1": "J1",  # Main junction
            "J4": "J4"   # Secondary junction nếu cần
        }
        
        # Lưu trữ dữ liệu đo lường
        self.queue_history: Dict[TrafficDirection, List[float]] = defaultdict(list)
        self.pressure_history: Dict[TrafficDirection, List[float]] = defaultdict(list)
        self.phase_history: List[Tuple[TrafficPhase, float, float]] = []  # (phase, start_time, duration)
        
        # Green debt system (cho PriorityController)
        self.green_debts: Dict[str, float] = defaultdict(float)  # {"Bắc": 10.5, "Nam": 5.2, ...}
        
        # ✅ SC6: Backlog tracking (queue length tích lũy)
        self.backlog_queues: Dict[str, List[float]] = defaultdict(list)  # Lịch sử queue length
        self.max_backlog_history = 10  # Lưu 10 chu kỳ gần nhất
        
        # Emergency mode params (SC6)
        self.normal_min_green = self.T_MIN_GREEN
        self.normal_max_green = self.T_MAX_GREEN
        self.emergency_min_green = 12.0
        self.emergency_max_green = 90.0
        
        # Starvation prevention (chống bỏ đói)
        # ✅ FIX GIAI ĐOẠN 2 - Issue #3 [Adaptive-1.4]: Giảm MAX_WAITING_TIME 120s → 60s
        # Kích hoạt starvation prevention sớm hơn, giảm 40% delay cho hướng ít xe
        self.MAX_WAITING_TIME = 60.0  # Thời gian chờ tối đa (giây)
        # ✅ FIX GIAI ĐOẠN 2 - Issue #4 [Adaptive-1.4]: Giảm CRITICAL_WAITING_TIME 60s → 40s
        # Cảnh báo sớm hơn về nguy cơ starvation
        self.CRITICAL_WAITING_TIME = 40.0  # Thời gian cảnh báo (giây)
        self.last_green_time: Dict[TrafficDirection, float] = {}  # Lần xanh cuối cho mỗi hướng
        
        # Khởi tạo last_green_time
        for direction in TrafficDirection:
            self.last_green_time[direction] = 0.0
        
        # ✅ FIX GIAI ĐOẠN 2 - Issue #5 [Adaptive-1.3]: Dynamic threshold parameters
        # Ngưỡng chuyển pha linh hoạt dựa trên mức độ tắc nghẽn
        self.THRESHOLD_MIN = 1.15  # Ngưỡng tối thiểu khi tắc nghẽn cao (giờ cao điểm)
        self.THRESHOLD_MAX = 1.30  # Ngưỡng tối đa khi thông thoáng
        self.CONGESTION_LOW = 5.0   # PCU - Ngưỡng tải thấp
        self.CONGESTION_HIGH = 20.0 # PCU - Ngưỡng tải cao
    
    def calculate_dynamic_threshold(self, ns_pressure: float, ew_pressure: float) -> float:
        """
        ✅ FIX GIAI ĐOẠN 2 - Issue #5 [Adaptive-1.3]: Tính ngưỡng chuyển pha động
        
        Nguyên lý: Khi tắc nghẽn cao → giảm threshold (dễ chuyển pha hơn)
                   Khi thông thoáng → tăng threshold (giữ pha lâu hơn)
        
        Args:
            ns_pressure: Áp lực tổng hướng Bắc-Nam (PCU)
            ew_pressure: Áp lực tổng hướng Đông-Tây (PCU)
            
        Returns:
            Ngưỡng chuyển pha động (1.15 - 1.30)
        """
        # Tính tổng áp lực hệ thống
        total_pressure = ns_pressure + ew_pressure
        
        # Tính tỷ lệ tắc nghẽn (0.0 = thông thoáng, 1.0 = tắc nghẽn cao)
        if total_pressure <= self.CONGESTION_LOW:
            congestion_ratio = 0.0
        elif total_pressure >= self.CONGESTION_HIGH:
            congestion_ratio = 1.0
        else:
            congestion_ratio = (total_pressure - self.CONGESTION_LOW) / (self.CONGESTION_HIGH - self.CONGESTION_LOW)
        
        # Tính threshold: Tắc nghẽn cao → threshold thấp (1.15), thông thoáng → threshold cao (1.30)
        threshold = self.THRESHOLD_MAX - (congestion_ratio * (self.THRESHOLD_MAX - self.THRESHOLD_MIN))
        
        return threshold
        
    def get_vehicle_count_by_direction(self, direction: TrafficDirection) -> int:
        """
        Đếm số xe theo hướng từ các edges tương ứng
        
        Args:
            direction: Hướng cần đếm xe
            
        Returns:
            Số lượng xe (int)
        """
        try:
            total_vehicles = 0
            edges = self.direction_edges.get(direction, [])
            
            for edge in edges:
                try:
                    # Lấy danh sách xe trên edge
                    vehicles_on_edge = traci.edge.getLastStepVehicleIDs(edge)
                    
                    # Đếm xe đang chờ (vận tốc < 2 m/s = kẹt xe)
                    waiting_vehicles = 0
                    for veh_id in vehicles_on_edge:
                        try:
                            speed = traci.vehicle.getSpeed(veh_id)
                            if speed < 2.0:  # Xe đang chờ/kẹt
                                waiting_vehicles += 1
                        except traci.exceptions.TraCIException:
                            continue
                    
                    total_vehicles += waiting_vehicles
                    
                except traci.exceptions.TraCIException:
                    continue
                    
            return total_vehicles
            
        except Exception as e:
            print(f"❌ Lỗi khi đếm xe hướng {direction.value}: {e}")
            return 0
    
    def convert_to_pcu(self, direction: TrafficDirection) -> float:
        """
        Chuyển đổi số xe thành đơn vị PCU theo tiêu chuẩn VN
        
        Args:
            direction: Hướng cần tính PCU
            
        Returns:
            Tổng PCU (float)
        """
        try:
            total_pcu = 0.0
            edges = self.direction_edges.get(direction, [])
            
            for edge in edges:
                try:
                    vehicles_on_edge = traci.edge.getLastStepVehicleIDs(edge)
                    
                    for veh_id in vehicles_on_edge:
                        try:
                            speed = traci.vehicle.getSpeed(veh_id)
                            if speed < 2.0:  # Chỉ tính xe đang chờ
                                veh_type = traci.vehicle.getTypeID(veh_id)
                                
                                # Xác định loại xe và quy đổi PCU
                                if 'motorcycle' in veh_type.lower() or 'bike' in veh_type.lower():
                                    pcu_value = self.PCU_CONVERSION['motorcycle']
                                elif 'bus' in veh_type.lower():
                                    pcu_value = self.PCU_CONVERSION['bus']
                                elif 'truck' in veh_type.lower():
                                    pcu_value = self.PCU_CONVERSION['truck']
                                elif 'emergency' in veh_type.lower():
                                    pcu_value = self.PCU_CONVERSION['emergency']
                                else:
                                    pcu_value = self.PCU_CONVERSION['car']  # Mặc định
                                
                                total_pcu += pcu_value
                                
                        except traci.exceptions.TraCIException:
                            continue
                            
                except traci.exceptions.TraCIException:
                    continue
                    
            return total_pcu
            
        except Exception as e:
            print(f"❌ Lỗi khi tính PCU hướng {direction.value}: {e}")
            return 0.0
    
    def calculate_pressure(self, direction: TrafficDirection) -> float:
        """
        Tính điểm áp lực cho một hướng
        
        Công thức: P = α × Queue_length(PCU)
        
        Args:
            direction: Hướng cần tính áp lực
            
        Returns:
            Điểm áp lực (float)
        """
        queue_pcu = self.convert_to_pcu(direction)
        pressure = self.ALPHA * queue_pcu
        
        # Lưu lịch sử để phân tích
        self.queue_history[direction].append(queue_pcu)
        self.pressure_history[direction].append(pressure)
        
        return pressure
    
    def calculate_green_time(self, direction: TrafficDirection) -> float:
        """
        Tính thời gian xanh động cho một hướng
        
        Công thức: G = T_min + α × Queue_length(PCU) + Green_Debt_Compensation
        
        Args:
            direction: Hướng cần tính thời gian xanh
            
        Returns:
            Thời gian xanh (giây, float)
        """
        queue_pcu = self.convert_to_pcu(direction)
        green_time = self.T_MIN_GREEN + (self.ALPHA * queue_pcu)
        
        direction_name = direction.value  # "Bắc", "Nam", "Đông", "Tây"
        
        # ✅ SC6: GHI NHẬN BACKLOG
        self.record_backlog(direction_name, queue_pcu)
        
        # ✅ SC6: BÙ NỢ THỜI GIAN XANH (dựa trên backlog severity)
        if direction_name in self.green_debts and self.green_debts[direction_name] > 0:
            debt = self.green_debts[direction_name]
            
            # Tính compensation dựa trên backlog severity
            compensation = self.calculate_backlog_compensation(direction_name)
            
            if compensation > 0:
                severity = self.get_backlog_severity(direction_name)
                green_time += compensation
                
                # Trừ nợ
                self.green_debts[direction_name] -= compensation
                
                print(f"💰 SC6-BACKLOG: {direction_name}")
                print(f"   Queue: {queue_pcu:.1f} PCU")
                print(f"   Severity: {severity:.0f}/100")
                print(f"   Bù: {compensation:.1f}s (Nợ còn: {self.green_debts[direction_name]:.1f}s)")
        
        # Giới hạn trong khoảng [T_MIN_GREEN, T_MAX_GREEN]
        green_time = max(self.T_MIN_GREEN, min(green_time, self.T_MAX_GREEN))
        
        return green_time
    
    def calculate_all_red_time(self) -> float:
        """
        Tính thời gian đỏ toàn bộ động
        
        Công thức: R = W/v + buffer
        Với W = 20m (bề rộng giao lộ), v = 10m/s (vận tốc trung bình)
        
        Returns:
            Thời gian All-Red (giây, float)
        """
        intersection_width = 20.0  # mét
        average_speed = 10.0       # m/s
        
        clearance_time = intersection_width / average_speed
        total_all_red = clearance_time + self.BUFFER_TIME
        
        return max(self.ALL_RED_BASE, total_all_red)
    
    def calculate_waiting_time(self, direction: TrafficDirection) -> float:
        """
        Tính thời gian chờ của một hướng từ lần xanh cuối cùng
        
        Args:
            direction: Hướng cần tính
            
        Returns:
            Thời gian chờ (giây)
        """
        try:
            current_time = traci.simulation.getTime()
            last_green = self.last_green_time.get(direction, 0.0)
            
            if last_green == 0.0:
                # Chưa từng được xanh, trả về 0
                return 0.0
            
            waiting_time = current_time - last_green
            return waiting_time
            
        except Exception as e:
            print(f"❌ Lỗi khi tính waiting time cho {direction.value}: {e}")
            return 0.0
    
    def check_starvation_prevention(self) -> Tuple[bool, Optional[TrafficPhase]]:
        """
        Kiểm tra cơ chế chống bỏ đói (Starvation Prevention)
        
        Nếu một hướng chờ quá lâu (> MAX_WAITING_TIME), buộc chuyển pha cho hướng đó
        
        Returns:
            Tuple (should_force_change: bool, force_phase: TrafficPhase)
        """
        current_time = traci.simulation.getTime()
        
        # Kiểm tra từng hướng
        for direction in TrafficDirection:
            waiting_time = self.calculate_waiting_time(direction)
            
            # Cảnh báo nếu vượt ngưỡng critical
            if waiting_time > self.CRITICAL_WAITING_TIME and waiting_time <= self.MAX_WAITING_TIME:
                queue_pcu = self.convert_to_pcu(direction)
                if queue_pcu > 0:  # Chỉ cảnh báo nếu có xe chờ
                    print(f"[STAGE2-CRITICAL] ⚠️ {direction.value} chờ {waiting_time:.0f}s (>{self.CRITICAL_WAITING_TIME:.0f}s) | Queue:{queue_pcu:.1f}PCU")
            
            # Buộc chuyển pha nếu vượt MAX_WAITING_TIME
            if waiting_time > self.MAX_WAITING_TIME:
                queue_pcu = self.convert_to_pcu(direction)
                
                # ✅ FIX CRITICAL BUG: Chỉ buộc chuyển nếu có đủ xe chờ (>= 2.0 PCU)
                # Tránh force switch cho 1-2 xe máy (0.3-0.6 PCU) hoặc 1 ô tô (1.0 PCU)
                MIN_QUEUE_TO_FORCE = 2.0  # PCU tối thiểu để buộc chuyển (~ 2 ô tô hoặc 7 xe máy)
                
                if queue_pcu >= MIN_QUEUE_TO_FORCE:
                    print(f"[STAGE2-FORCE] 🚨 STARVATION! {direction.value} chờ {waiting_time:.0f}s (>{self.MAX_WAITING_TIME:.0f}s) | Queue:{queue_pcu:.1f}PCU → BUỘC CHUYỂN PHA")
                    
                    # Xác định pha cần chuyển
                    if direction in [TrafficDirection.NORTH, TrafficDirection.SOUTH]:
                        # Cần pha NS_GREEN
                        if self.current_phase == TrafficPhase.NS_GREEN:
                            # ✅ FIX: Nếu đang xanh rồi, reset waiting_time luôn
                            self.last_green_time[direction] = current_time
                            return False, None  # Đã đang xanh
                        else:
                            return True, TrafficPhase.NS_YELLOW  # Chuyển sang NS
                    else:  # EAST hoặc WEST
                        # Cần pha EW_GREEN
                        if self.current_phase == TrafficPhase.EW_GREEN:
                            # ✅ FIX: Nếu đang xanh rồi, reset waiting_time luôn
                            self.last_green_time[direction] = current_time
                            return False, None  # Đã đang xanh
                        else:
                            return True, TrafficPhase.EW_YELLOW  # Chuyển sang EW
                else:
                    # ✅ FIX: Nếu không đủ xe để force (< MIN_QUEUE_TO_FORCE)
                    # → Reset waiting_time để tránh vòng lặp vô hạn
                    # Gap nguy hiểm: 0.5-2.0 PCU cần được xử lý
                    self.last_green_time[direction] = current_time
                    print(f"[STAGE2-RESET] 🔄 {direction.value} chờ {waiting_time:.0f}s nhưng queue nhỏ ({queue_pcu:.1f} < {MIN_QUEUE_TO_FORCE} PCU) → RESET waiting_time")
        
        return False, None
    
    def get_direction_priorities(self) -> Dict[TrafficDirection, float]:
        """
        Tính độ ưu tiên cho tất cả các hướng
        
        Returns:
            Dictionary {hướng: điểm áp lực}
        """
        priorities = {}
        for direction in TrafficDirection:
            priorities[direction] = self.calculate_pressure(direction)
            
        return priorities
    
    def should_change_phase(self) -> Tuple[bool, Optional[TrafficPhase]]:
        """
        Quyết định có nên chuyển pha hay không dựa trên áp lực
        
        Returns:
            Tuple (should_change: bool, next_phase: TrafficPhase)
        """
        current_time = traci.simulation.getTime()
        phase_duration = current_time - self.phase_start_time
        
        # ✅ BƯỚC 1: Kiểm tra starvation prevention (ưu tiên cao nhất)
        should_force, force_phase = self.check_starvation_prevention()
        if should_force and force_phase:
            return True, force_phase
        
        # Đảm bảo đã đủ thời gian xanh tối thiểu
        if phase_duration < self.T_MIN_GREEN:
            return False, None
            
        priorities = self.get_direction_priorities()
        
        # Tính áp lực tổng cho từng nhóm pha
        ns_pressure = priorities[TrafficDirection.NORTH] + priorities[TrafficDirection.SOUTH]
        ew_pressure = priorities[TrafficDirection.EAST] + priorities[TrafficDirection.WEST]
        
        # ✅ FIX GIAI ĐOẠN 2 - Issue #5: Tính ngưỡng động dựa trên mức tắc nghẽn
        dynamic_threshold = self.calculate_dynamic_threshold(ns_pressure, ew_pressure)
        
        # 🔍 DEBUG LOG STAGE 2
        total_pressure = ns_pressure + ew_pressure
        print(f"[STAGE2-DEBUG] Time:{current_time:.0f}s | Phase:{self.current_phase.value} | Duration:{phase_duration:.1f}s | NS_P:{ns_pressure:.1f} | EW_P:{ew_pressure:.1f} | Total:{total_pressure:.1f}PCU | Threshold:{dynamic_threshold:.2f}")
        
        # Logic chuyển pha với ngưỡng động
        # ✅ FIX: Chỉ chuyển pha khi hướng đối diện có xe đủ nhiều (>= 1.0 PCU)
        MIN_PRESSURE_TO_SWITCH = 1.0  # PCU tối thiểu để xem xét chuyển pha
        
        if self.current_phase == TrafficPhase.NS_GREEN:
            # Hiện tại Bắc-Nam đang xanh
            # Chỉ chuyển nếu EW có xe và áp lực vượt ngưỡng
            if ew_pressure >= MIN_PRESSURE_TO_SWITCH and ew_pressure > ns_pressure * dynamic_threshold:
                print(f"[STAGE2-SWITCH] EW_P({ew_pressure:.1f}) > NS_P({ns_pressure:.1f}) * {dynamic_threshold:.2f} → Chuyển sang YELLOW")
                return True, TrafficPhase.NS_YELLOW
            elif phase_duration >= self.T_MAX_GREEN:  # Đã đạt thời gian tối đa
                print(f"[STAGE2-SWITCH] Duration({phase_duration:.1f}s) >= T_MAX_GREEN({self.T_MAX_GREEN:.0f}s) → Chuyển sang YELLOW")
                return True, TrafficPhase.NS_YELLOW
                
        elif self.current_phase == TrafficPhase.EW_GREEN:
            # Hiện tại Đông-Tây đang xanh
            # Chỉ chuyển nếu NS có xe và áp lực vượt ngưỡng
            if ns_pressure >= MIN_PRESSURE_TO_SWITCH and ns_pressure > ew_pressure * dynamic_threshold:
                print(f"[STAGE2-SWITCH] NS_P({ns_pressure:.1f}) > EW_P({ew_pressure:.1f}) * {dynamic_threshold:.2f} → Chuyển sang YELLOW")
                return True, TrafficPhase.EW_YELLOW
            elif phase_duration >= self.T_MAX_GREEN:  # Đã đạt thời gian tối đa
                print(f"[STAGE2-SWITCH] Duration({phase_duration:.1f}s) >= T_MAX_GREEN({self.T_MAX_GREEN:.0f}s) → Chuyển sang YELLOW")
                return True, TrafficPhase.EW_YELLOW
        
        # Kiểm tra vi phạm T_MIN_GREEN
        if phase_duration < self.T_MIN_GREEN:
            print(f"[STAGE2-BLOCK] Duration({phase_duration:.1f}s) < T_MIN_GREEN({self.T_MIN_GREEN:.0f}s) → GIỮ PHA")
                
        return False, None
    
    def apply_phase(self, phase: TrafficPhase) -> bool:
        """
        Áp dụng pha đèn lên SUMO
        
        Args:
            phase: Pha đèn cần áp dụng
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            # Mapping pha với SUMO traffic light programs
            phase_mapping = {
                TrafficPhase.NS_GREEN: 0,   # Bắc-Nam xanh, Đông-Tây đỏ
                TrafficPhase.NS_YELLOW: 1,  # Bắc-Nam vàng, Đông-Tây đỏ
                TrafficPhase.ALL_RED: 2,    # Tất cả đỏ
                TrafficPhase.EW_GREEN: 3,   # Đông-Tây xanh, Bắc-Nam đỏ
                TrafficPhase.EW_YELLOW: 4   # Đông-Tây vàng, Bắc-Nam đỏ
            }
            
            sumo_phase = phase_mapping.get(phase)
            if sumo_phase is not None:
                traci.trafficlight.setPhase(self.junction_id, sumo_phase)
                
                # Cập nhật trạng thái
                current_time = traci.simulation.getTime()
                if self.current_phase != phase:
                    # Lưu lịch sử pha trước
                    if self.phase_start_time > 0:
                        duration = current_time - self.phase_start_time
                        self.phase_history.append((self.current_phase, self.phase_start_time, duration))
                    
                    # ✅ Cập nhật last_green_time khi chuyển sang pha GREEN
                    if phase == TrafficPhase.NS_GREEN:
                        self.last_green_time[TrafficDirection.NORTH] = current_time
                        self.last_green_time[TrafficDirection.SOUTH] = current_time
                        # ✅ FIX STARVATION LOOP: Reset EW nếu không có xe chờ
                        ew_queue = self.convert_to_pcu(TrafficDirection.EAST) + self.convert_to_pcu(TrafficDirection.WEST)
                        if ew_queue < 0.5:  # Không có xe chờ đáng kể
                            self.last_green_time[TrafficDirection.EAST] = current_time
                            self.last_green_time[TrafficDirection.WEST] = current_time
                    elif phase == TrafficPhase.EW_GREEN:
                        self.last_green_time[TrafficDirection.EAST] = current_time
                        self.last_green_time[TrafficDirection.WEST] = current_time
                        # ✅ FIX STARVATION LOOP: Reset NS nếu không có xe chờ
                        ns_queue = self.convert_to_pcu(TrafficDirection.NORTH) + self.convert_to_pcu(TrafficDirection.SOUTH)
                        if ns_queue < 0.5:
                            self.last_green_time[TrafficDirection.NORTH] = current_time
                            self.last_green_time[TrafficDirection.SOUTH] = current_time
                    
                    self.current_phase = phase
                    self.phase_start_time = current_time
                
                return True
            else:
                print(f"❌ Không tìm thấy mapping cho pha: {phase}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi khi áp dụng pha {phase}: {e}")
            return False
    
    def start(self) -> bool:
        """
        Bắt đầu thuật toán điều khiển thích ứng
        
        Returns:
            True nếu khởi động thành công
        """
        try:
            if not traci.isLoaded():
                print("❌ SUMO chưa được khởi động!")
                return False
                
            # Kiểm tra traffic light tồn tại
            tl_list = traci.trafficlight.getIDList()
            if self.junction_id not in tl_list:
                print(f"❌ Không tìm thấy traffic light: {self.junction_id}")
                return False
            
            # Khởi tạo trạng thái ban đầu
            self.current_phase = TrafficPhase.NS_GREEN
            self.phase_start_time = traci.simulation.getTime()
            self.is_active = True
            
            # Áp dụng pha ban đầu
            self.apply_phase(self.current_phase)
            
            print(f"✅ Adaptive Controller đã khởi động cho {self.junction_id}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi khởi động Adaptive Controller: {e}")
            return False
    
    def stop(self):
        """Dừng thuật toán điều khiển"""
        self.is_active = False
        print("🛑 Adaptive Controller đã dừng")
    
    def step(self) -> bool:
        """
        Thực hiện một bước điều khiển (gọi mỗi simulation step)
        
        Returns:
            True nếu thực hiện thành công
        """
        if not self.is_active:
            return False
            
        try:
            current_time = traci.simulation.getTime()
            
            # Xử lý logic theo pha hiện tại
            if self.current_phase in [TrafficPhase.NS_GREEN, TrafficPhase.EW_GREEN]:
                # Pha xanh - kiểm tra có cần chuyển pha không
                should_change, next_phase = self.should_change_phase()
                if should_change and next_phase:
                    self.apply_phase(next_phase)
                    
            elif self.current_phase in [TrafficPhase.NS_YELLOW, TrafficPhase.EW_YELLOW]:
                # Pha vàng - chuyển sang All-Red sau khi hết thời gian vàng
                phase_duration = current_time - self.phase_start_time
                if phase_duration >= self.YELLOW_DURATION:
                    self.apply_phase(TrafficPhase.ALL_RED)
                    
            elif self.current_phase == TrafficPhase.ALL_RED:
                # Pha All-Red - chuyển sang pha xanh tiếp theo
                phase_duration = current_time - self.phase_start_time
                all_red_time = self.calculate_all_red_time()
                
                if phase_duration >= all_red_time:
                    # Quyết định pha xanh tiếp theo dựa trên áp lực
                    priorities = self.get_direction_priorities()
                    ns_pressure = priorities[TrafficDirection.NORTH] + priorities[TrafficDirection.SOUTH]
                    ew_pressure = priorities[TrafficDirection.EAST] + priorities[TrafficDirection.WEST]
                    
                    if ns_pressure >= ew_pressure:
                        next_phase = TrafficPhase.NS_GREEN
                    else:
                        next_phase = TrafficPhase.EW_GREEN
                        
                    self.apply_phase(next_phase)
            
            return True
            
        except Exception as e:
            print(f"❌ Lỗi trong bước điều khiển: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Lấy trạng thái hiện tại của controller
        
        Returns:
            Dictionary chứa thông tin trạng thái
        """
        try:
            current_time = traci.simulation.getTime()
            phase_duration = current_time - self.phase_start_time
            
            # Tính áp lực hiện tại cho tất cả hướng
            priorities = self.get_direction_priorities()
            
            # Tính thời gian xanh dự kiến cho pha tiếp theo
            ns_pressure = priorities[TrafficDirection.NORTH] + priorities[TrafficDirection.SOUTH]
            ew_pressure = priorities[TrafficDirection.EAST] + priorities[TrafficDirection.WEST]
            
            return {
                'junction_id': self.junction_id,
                'current_phase': self.current_phase.value,
                'phase_duration': round(phase_duration, 1),
                'is_active': self.is_active,
                'pressures': {dir.value: round(pressure, 2) for dir, pressure in priorities.items()},
                'ns_total_pressure': round(ns_pressure, 2),
                'ew_total_pressure': round(ew_pressure, 2),
                'phase_count': len(self.phase_history)
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi lấy trạng thái: {e}")
            return {'error': str(e)}
    
    def get_statistics(self) -> Dict:
        """
        Lấy thống kê hiệu suất của thuật toán
        
        Returns:
            Dictionary chứa các metrics thống kê
        """
        try:
            if not self.phase_history:
                return {'message': 'Chưa có dữ liệu thống kê'}
            
            # Thống kê thời gian pha
            phase_durations = [duration for _, _, duration in self.phase_history]
            avg_phase_duration = sum(phase_durations) / len(phase_durations)
            
            # Thống kê áp lực trung bình
            avg_pressures = {}
            for direction, pressures in self.pressure_history.items():
                if pressures:
                    avg_pressures[direction.value] = sum(pressures) / len(pressures)
            
            # Thống kê queue length trung bình
            avg_queues = {}
            for direction, queues in self.queue_history.items():
                if queues:
                    avg_queues[direction.value] = sum(queues) / len(queues)
            
            return {
                'total_phases': len(self.phase_history),
                'average_phase_duration': round(avg_phase_duration, 2),
                'average_pressures': {k: round(v, 2) for k, v in avg_pressures.items()},
                'average_queue_lengths': {k: round(v, 2) for k, v in avg_queues.items()},
                'total_simulation_time': round(sum(phase_durations), 2)
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi tính thống kê: {e}")
            return {'error': str(e)}
    
    def add_green_debt(self, direction: str, debt_time: float):
        """
        Thêm 'nợ' thời gian xanh cho một hướng
        Sẽ được bù trong chu kỳ tiếp theo
        
        Args:
            direction: Hướng bị ảnh hưởng ("Bắc", "Nam", "Đông", "Tây")
            debt_time: Thời gian xanh bị mất (giây)
        """
        self.green_debts[direction] += debt_time
        print(f"💳 {direction}: Nợ thêm {debt_time:.1f}s → Tổng nợ: {self.green_debts[direction]:.1f}s")
    
    def get_phase_elapsed_time(self, current_time: float) -> float:
        """
        Trả về thời gian đã trôi qua của pha hiện tại
        Dùng cho PriorityController kiểm tra safe_min_green
        
        Args:
            current_time: Thời gian hiện tại
            
        Returns:
            Thời gian đã trôi qua (giây)
        """
        return current_time - self.phase_start_time
    
    def set_emergency_params(self, min_green: float, max_green: float):
        """
        SC6: Điều chỉnh tham số khi emergency mode
        
        Args:
            min_green: Thời gian xanh tối thiểu mới
            max_green: Thời gian xanh tối đa mới
        """
        self.T_MIN_GREEN = min_green
        self.T_MAX_GREEN = max_green
        print(f"🚨 Emergency params: min_green={min_green}s, max_green={max_green}s")
    
    def restore_normal_params(self):
        """
        SC6: Khôi phục tham số bình thường sau emergency mode
        """
        self.T_MIN_GREEN = self.normal_min_green
        self.T_MAX_GREEN = self.normal_max_green
        print(f"✅ Khôi phục tham số adaptive: min_green={self.T_MIN_GREEN}s, max_green={self.T_MAX_GREEN}s")
    
    def record_backlog(self, direction: str, queue_pcu: float):
        """
        SC6: Ghi nhận backlog (queue length) cho một hướng
        
        Args:
            direction: Hướng giao thông ("Bắc", "Nam", "Đông", "Tây")
            queue_pcu: Độ dài hàng chờ hiện tại (PCU)
        """
        self.backlog_queues[direction].append(queue_pcu)
        
        # Giới hạn lịch sử
        if len(self.backlog_queues[direction]) > self.max_backlog_history:
            self.backlog_queues[direction].pop(0)
    
    def get_backlog_severity(self, direction: str) -> float:
        """
        SC6: Tính mức độ nghiêm trọng của backlog
        
        Dựa trên:
        - Queue length hiện tại
        - Xu hướng tăng/giảm (so với trung bình)
        - Thời gian chờ
        
        Args:
            direction: Hướng cần đánh giá
            
        Returns:
            Điểm severity (0-100, càng cao càng nghiêm trọng)
        """
        if direction not in self.backlog_queues or not self.backlog_queues[direction]:
            return 0.0
        
        history = self.backlog_queues[direction]
        current_queue = history[-1]
        
        # Nếu không có xe, không có backlog
        if current_queue <= 0:
            return 0.0
        
        # Tính trung bình queue length
        avg_queue = sum(history) / len(history)
        
        # Tính xu hướng (queue hiện tại so với trung bình)
        trend_factor = current_queue / max(avg_queue, 0.1)
        
        # Tính thời gian chờ
        direction_enum = None
        for d in TrafficDirection:
            if d.value == direction:
                direction_enum = d
                break
        
        waiting_time = 0.0
        if direction_enum:
            waiting_time = self.calculate_waiting_time(direction_enum)
        
        # Công thức severity:
        # - 40% từ queue length hiện tại (chuẩn hóa về 0-40)
        # - 30% từ xu hướng (nếu tăng mạnh thì severity cao)
        # - 30% từ waiting time (chuẩn hóa về 0-30)
        
        queue_score = min(current_queue / 20.0 * 40, 40)  # 20 PCU = 40 điểm
        trend_score = min((trend_factor - 1.0) * 30, 30)  # Tăng 100% = 30 điểm
        wait_score = min(waiting_time / 120.0 * 30, 30)   # 120s = 30 điểm
        
        severity = queue_score + trend_score + wait_score
        
        return min(severity, 100.0)
    
    def calculate_backlog_compensation(self, direction: str) -> float:
        """
        SC6: Tính thời gian bù backlog dựa trên mức độ nghiêm trọng
        
        Công thức thông minh:
        - Severity thấp (0-30): Bù 20-30% debt
        - Severity trung bình (30-60): Bù 40-60% debt
        - Severity cao (60-100): Bù 70-100% debt + bonus
        
        Args:
            direction: Hướng cần bù
            
        Returns:
            Thời gian bù (giây)
        """
        severity = self.get_backlog_severity(direction)
        debt = self.green_debts.get(direction, 0.0)
        
        if debt <= 0 or severity <= 0:
            return 0.0
        
        # Tính tỷ lệ bù dựa trên severity
        if severity < 30:
            # Backlog nhẹ: Bù từ từ (20-30%)
            compensation_rate = 0.20 + (severity / 30.0) * 0.10
        elif severity < 60:
            # Backlog trung bình: Bù nhanh hơn (40-60%)
            compensation_rate = 0.40 + ((severity - 30) / 30.0) * 0.20
        else:
            # Backlog nghiêm trọng: Bù mạnh (70-100%)
            compensation_rate = 0.70 + ((severity - 60) / 40.0) * 0.30
        
        compensation = debt * compensation_rate
        
        # Bonus cho backlog cực nghiêm trọng (severity > 80)
        if severity > 80:
            bonus = min((severity - 80) / 20.0 * 10.0, 10.0)  # Tối đa +10s
            compensation += bonus
            print(f"⚠️ {direction}: Backlog CỰC NGHIÊM TRỌNG (severity={severity:.0f}) → Bonus +{bonus:.1f}s")
        
        # Giới hạn compensation tối đa 20s/chu kỳ
        compensation = min(compensation, 20.0)
        
        return compensation
    
    def get_all_backlog_report(self) -> Dict[str, Dict]:
        """
        SC6: Báo cáo backlog toàn bộ hệ thống
        
        Returns:
            Dict chứa thông tin backlog mỗi hướng
        """
        report = {}
        
        for direction in ["Bắc", "Nam", "Đông", "Tây"]:
            severity = self.get_backlog_severity(direction)
            debt = self.green_debts.get(direction, 0.0)
            compensation = self.calculate_backlog_compensation(direction)
            
            current_queue = 0.0
            if direction in self.backlog_queues and self.backlog_queues[direction]:
                current_queue = self.backlog_queues[direction][-1]
            
            report[direction] = {
                'current_queue': current_queue,
                'severity': severity,
                'green_debt': debt,
                'compensation': compensation,
                'status': 'OK' if severity < 30 else 'WARNING' if severity < 60 else 'CRITICAL'
            }
        
        return report
