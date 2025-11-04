 # Điều khiển ưu tiên xe cứu hỏa, cứu thương
# Điều khiển ưu tiên xe cứu hỏa, cứu thương
"""
Thuật toán xử lý ưu tiên (Preemption Control) cho xe khẩn cấp
Sử dụng State Machine để ghi đè thuật toán thông thường khi có xe ưu tiên
"""

import traci
import time
import math
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, deque
from enum import Enum
from datetime import datetime

class PreemptionState(Enum):
    """Trạng thái của máy trạng thái ưu tiên"""
    NORMAL = "NORMAL"                    # Chế độ thông thường (Adaptive Control)
    DETECTION = "DETECTION"              # Phát hiện xe ưu tiên
    SAFE_TRANSITION = "SAFE_TRANSITION"  # Chuyển tiếp an toàn
    PREEMPTION_GREEN = "PREEMPTION_GREEN" # Đèn xanh cho xe ưu tiên
    HOLD_PREEMPTION = "HOLD_PREEMPTION"  # Giữ ưu tiên thêm
    RESTORE = "RESTORE"                  # Khôi phục về bình thường

class EmergencyVehicle:
    """Class đại diện cho xe ưu tiên"""
    def __init__(self, vehicle_id: str, vehicle_type: str, detection_time: float, 
                 direction: str, distance: float, speed: float):
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type
        self.detection_time = detection_time
        self.direction = direction
        self.distance = distance
        self.speed = speed
        self.eta = distance / max(speed, 0.1)  # Tránh chia cho 0
        self.confirmed = False
        self.served = False
        
        # ✅ KPI: Emergency Clearance Time
        self.clearance_time: Optional[float] = None  # Thời gian từ phát hiện → qua ngã tư
        self.clearance_start_time: Optional[float] = None  # Thời gian bắt đầu clearance

class PriorityController:
    """
    Thuật toán xử lý ưu tiên xe khẩn cấp
    """
    
    def __init__(self, junction_id: str = "J1", adaptive_controller=None, ui_callback=None):
        """
        Khởi tạo Priority Controller
        
        Args:
            junction_id: ID của ngã tư
            adaptive_controller: Tham chiếu đến Adaptive Controller
            ui_callback: Callback function để cập nhật UI (optional)
        """
        self.junction_id = junction_id
        self.adaptive_controller = adaptive_controller
        self.ui_callback = ui_callback  # Callback để cập nhật UI
        self.current_state = PreemptionState.NORMAL
        self.state_start_time = 0
        self.is_active = False
        
        # Tham số cấu hình
        self.DETECTION_RADIUS = 200.0      # Bán kính phát hiện (mét)
        self.ETA_THRESHOLD = 12.0          # Ngưỡng ETA để kích hoạt ưu tiên (giây)
        self.CONFIRMATION_WINDOW = 1.0     # Thời gian xác nhận (giây)
        self.CONFIRMATION_COUNT = 2        # Số lần xác nhận cần thiết
        self.PREEMPT_MIN_GREEN = 8.0       # Thời gian xanh tối thiểu cho ưu tiên (giây)
        self.SAFE_MIN_GREEN_BEFORE = 4.0   # Thời gian xanh tối thiểu trước khi cắt (giây)
        self.YELLOW_DURATION = 3.0         # Thời gian vàng (giây)
        self.ALL_RED_EMERGENCY = 3.0       # Thời gian All-Red khẩn cấp (giây)
        self.MAX_PREEMPT_PER_MINUTE = 2    # Giới hạn số lần ưu tiên/phút
        self.PREEMPT_COOLDOWN = 60.0       # Thời gian nghỉ giữa các lần ưu tiên (giây)
        
        # Danh sách loại xe ưu tiên (type ID và vehicle class)
        self.EMERGENCY_VEHICLE_TYPES = {
            'priority',         # typeID="priority" trong route file
            'ambulance',        # typeID="ambulance"
            'emergency',        # vClass="emergency" trong SUMO
            'fire',             # xe cứu hỏa
            'police',           # xe cảnh sát
            'cứu_thương',       # tiếng Việt
            'cứu_hỏa',          # tiếng Việt
            'cảnh_sát'          # tiếng Việt
        }
        
        # Mapping hướng với edges (SUMO network edges)
        # Bắc: Từ J2 xuống J1 (-E1)
        # Nam: Từ J3 lên J1 (-E2)  
        # Đông: Từ J1 sang J4 (E3)
        # Tây: Từ J0 sang J1 (E0)
        self.direction_edges = {
            "Bắc": ["-E1"],
            "Nam": ["-E2"],
            "Đông": ["E3"],
            "Tây": ["E0"]
        }
        
        # Mapping hướng với pha đèn
        self.direction_phases = {
            "Bắc": 0,   # NS_GREEN
            "Nam": 0,   # NS_GREEN
            "Đông": 3,  # EW_GREEN
            "Tây": 3    # EW_GREEN
        }
        
        # Dữ liệu theo dõi
        self.detected_vehicles: Dict[str, EmergencyVehicle] = {}
        self.confirmed_vehicles: Dict[str, EmergencyVehicle] = {}
        self.pending_vehicles: Dict[str, EmergencyVehicle] = {}  # SC3: Xe chờ
        self.served_vehicles: List[EmergencyVehicle] = []
        self.rejected_vehicles: List[Dict] = []  # SC6: Xe bị từ chối
        self.failed_preemptions: List[Dict] = []  # SC5: Ưu tiên thất bại
        self.false_positives: List[Dict] = []  # SC4: Báo giả
        self.preemption_history: List[Dict] = []
        self.detection_confirmations: Dict[str, List[float]] = defaultdict(list)
        
        # Thống kê ưu tiên
        self.preemption_count_last_minute = deque()
        self.last_preemption_time = 0
        self.priority_vehicle: Optional[EmergencyVehicle] = None  # Xe đang được ưu tiên
        self.preemption_start_time = 0.0
        
        # Emergency Mode (SC6)
        self.emergency_mode_active = False
        self.emergency_mode_start_time = 0.0
        
        # ✅ KPI: Emergency Clearance Time tracking
        self.clearance_times: List[float] = []  # Danh sách clearance time của tất cả xe
        self.EXCELLENT_CLEARANCE = 15.0  # ≤ 15s: Tốt
        self.ACCEPTABLE_CLEARANCE = 25.0  # ≤ 25s: Chấp nhận được
    
    def _log_false_positive(self, vehicle_id: str, reason: str, stage: str):
        """
        SC4: Ghi log báo giả (False Positive)
        
        Args:
            vehicle_id: ID của xe báo giả
            reason: Lý do (vehicle_disappeared, not_emergency_type, etc.)
            stage: Giai đoạn phát hiện (DETECTION, SAFE_TRANSITION, PREEMPTION_GREEN)
        """
        current_time = traci.simulation.getTime()
        
        log_entry = {
            'vehicle_id': vehicle_id,
            'time': current_time,
            'reason': reason,
            'stage': stage,
            'state': self.current_state.value
        }
        
        self.false_positives.append(log_entry)
        
        print(f"📝 SC4 LOG: Báo giả - Xe {vehicle_id}")
        print(f"   Lý do: {reason}")
        print(f"   Giai đoạn: {stage}")
        print(f"   Trạng thái: {self.current_state.value}")
        print(f"   Thời gian: {current_time:.1f}s")
    
    def _verify_emergency_vehicle_exists(self, vehicle_id: str, stage: str) -> bool:
        """
        SC4: Xác minh xe ưu tiên vẫn tồn tại và hợp lệ
        
        Args:
            vehicle_id: ID của xe cần kiểm tra
            stage: Giai đoạn kiểm tra (cho logging)
            
        Returns:
            True nếu xe vẫn hợp lệ, False nếu là báo giả
        """
        try:
            # Kiểm tra xe vẫn tồn tại
            if vehicle_id not in traci.vehicle.getIDList():
                self._log_false_positive(vehicle_id, 'vehicle_disappeared', stage)
                return False
            
            # Kiểm tra xe vẫn là emergency vehicle
            if not self.is_emergency_vehicle(vehicle_id):
                self._log_false_positive(vehicle_id, 'not_emergency_type', stage)
                return False
            
            return True
            
        except Exception as e:
            self._log_false_positive(vehicle_id, f'verification_error: {e}', stage)
            return False
        
    def _calculate_and_log_clearance_time(self, vehicle: EmergencyVehicle, current_time: float):
        """
        ✅ KPI: Tính và log Emergency Clearance Time
        
        Clearance Time = Thời gian từ khi phát hiện xe đến khi xe qua ngã tư
        
        Args:
            vehicle: Xe ưu tiên đã qua ngã tư
            current_time: Thời gian hiện tại
        """
        # Tính clearance time
        clearance_time = current_time - vehicle.detection_time
        vehicle.clearance_time = clearance_time
        
        # Lưu vào danh sách để tính thống kê
        self.clearance_times.append(clearance_time)
        
        # Đánh giá theo tiêu chuẩn tài liệu
        print(f"📊 EMERGENCY CLEARANCE TIME: {clearance_time:.1f}s")
        print(f"   Xe: {vehicle.vehicle_id}")
        print(f"   Hướng: {vehicle.direction}")
        print(f"   Detection time: {vehicle.detection_time:.1f}s")
        print(f"   Cleared time: {current_time:.1f}s")
        
        # Đánh giá hiệu suất
        if clearance_time <= self.EXCELLENT_CLEARANCE:
            print(f"   ✅ TỐT (≤ {self.EXCELLENT_CLEARANCE:.0f}s) - Đạt mục tiêu!")
            evaluation = "EXCELLENT"
        elif clearance_time <= self.ACCEPTABLE_CLEARANCE:
            print(f"   ⚠️ CHẤP NHẬN ĐƯỢC (≤ {self.ACCEPTABLE_CLEARANCE:.0f}s)")
            evaluation = "ACCEPTABLE"
        else:
            print(f"   ❌ VƯỢT MỤC TIÊU (> {self.ACCEPTABLE_CLEARANCE:.0f}s)")
            evaluation = "POOR"
        
        # Thêm vào statistics
        vehicle.clearance_evaluation = evaluation
        
        return clearance_time, evaluation
    
    def get_junction_position(self) -> Tuple[float, float]:
        """
        Lấy tọa độ của ngã tư
        
        Returns:
            Tuple (x, y) tọa độ ngã tư
        """
        try:
            # Lấy tọa độ từ traffic light hoặc junction
            junction_pos = traci.junction.getPosition(self.junction_id)
            return junction_pos
        except:
            # Fallback: sử dụng tọa độ mặc định cho J1
            return (0.0, 0.0)
    
    def calculate_distance_to_junction(self, vehicle_id: str) -> float:
        """
        Tính khoảng cách từ xe đến ngã tư
        
        Args:
            vehicle_id: ID của xe
            
        Returns:
            Khoảng cách (mét)
        """
        try:
            veh_pos = traci.vehicle.getPosition(vehicle_id)
            junction_pos = self.get_junction_position()
            
            # Tính khoảng cách Euclidean
            distance = math.sqrt(
                (veh_pos[0] - junction_pos[0])**2 + 
                (veh_pos[1] - junction_pos[1])**2
            )
            
            return distance
            
        except Exception as e:
            print(f"❌ Lỗi khi tính khoảng cách xe {vehicle_id}: {e}")
            return float('inf')
    
    def get_vehicle_direction(self, vehicle_id: str) -> Optional[str]:
        """
        Xác định hướng di chuyển của xe
        
        Args:
            vehicle_id: ID của xe
            
        Returns:
            Hướng di chuyển ("Bắc", "Nam", "Đông", "Tây") hoặc None
        """
        try:
            current_edge = traci.vehicle.getRoadID(vehicle_id)
            
            # Tìm hướng tương ứng với edge
            for direction, edges in self.direction_edges.items():
                if current_edge in edges:
                    return direction
                    
            return None
            
        except Exception as e:
            print(f"❌ Lỗi khi xác định hướng xe {vehicle_id}: {e}")
            return None
    
    def is_emergency_vehicle(self, vehicle_id: str) -> bool:
        """
        Kiểm tra xe có phải xe ưu tiên không
        
        Args:
            vehicle_id: ID của xe
            
        Returns:
            True nếu là xe ưu tiên
        """
        try:
            veh_type = traci.vehicle.getTypeID(vehicle_id).lower()
            veh_class = traci.vehicle.getVehicleClass(vehicle_id).lower()
            
            # Kiểm tra theo type ID và vehicle class
            return any(emergency_type in veh_type or emergency_type in veh_class 
                      for emergency_type in self.EMERGENCY_VEHICLE_TYPES)
                      
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra loại xe {vehicle_id}: {e}")
            return False
    
    def scan_for_emergency_vehicles(self) -> List[EmergencyVehicle]:
        """
        Quét tìm xe ưu tiên trong bán kính phát hiện
        
        Returns:
            Danh sách xe ưu tiên được phát hiện
        """
        emergency_vehicles = []
        current_time = traci.simulation.getTime()
        
        try:
            # Lấy tất cả xe ĐANG DI CHUYỂN trong mô phỏng
            all_vehicles = traci.vehicle.getIDList()
            
            for vehicle_id in all_vehicles:
                try:
                    # Kiểm tra xe có phải ưu tiên không
                    if not self.is_emergency_vehicle(vehicle_id):
                        continue
                    
                    print(f"🚨 Phát hiện xe ưu tiên: {vehicle_id}")
                    
                    # Tính khoảng cách đến ngã tư
                    distance = self.calculate_distance_to_junction(vehicle_id)
                    
                    print(f"📍 Khoảng cách: {distance:.1f}m (Radius: {self.DETECTION_RADIUS}m)")
                    
                    # Kiểm tra trong bán kính phát hiện
                    if distance <= self.DETECTION_RADIUS:
                        # Lấy thông tin xe
                        speed = traci.vehicle.getSpeed(vehicle_id)
                        direction = self.get_vehicle_direction(vehicle_id)
                        veh_type = traci.vehicle.getTypeID(vehicle_id)
                        
                        print(f"🧭 Hướng: {direction}, Tốc độ: {speed:.1f}m/s")
                        
                        if direction:  # Xe phải có hướng rõ ràng
                            emergency_veh = EmergencyVehicle(
                                vehicle_id=vehicle_id,
                                vehicle_type=veh_type,
                                detection_time=current_time,
                                direction=direction,
                                distance=distance,
                                speed=speed
                            )
                            
                            emergency_vehicles.append(emergency_veh)
                            print(f"✅ Đã thêm xe {vehicle_id} vào danh sách ưu tiên!")
                        else:
                            print(f"⚠️ Không xác định được hướng xe {vehicle_id}")
                            
                except traci.exceptions.TraCIException as e:
                    print(f"⚠️ TraCI exception cho xe {vehicle_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Lỗi khi quét xe ưu tiên: {e}")
            
        return emergency_vehicles
    
    def confirm_emergency_vehicle(self, vehicle: EmergencyVehicle) -> bool:
        """
        SC4: Xác nhận xe ưu tiên để tránh báo giả (False Positive)
        
        Quy trình xác nhận kép:
        - Phát hiện 2 lần liên tiếp trong cửa sổ 1 giây
        - Kiểm tra xe vẫn tồn tại và vẫn là emergency vehicle
        
        Args:
            vehicle: Đối tượng EmergencyVehicle
            
        Returns:
            True nếu xe được xác nhận
        """
        current_time = traci.simulation.getTime()
        vehicle_id = vehicle.vehicle_id
        
        # SC4: Kiểm tra xe vẫn tồn tại trong simulation
        try:
            if vehicle_id not in traci.vehicle.getIDList():
                print(f"⚠️ SC4: Xe {vehicle_id} không còn tồn tại - Báo giả!")
                self._log_false_positive(vehicle_id, 'vehicle_disappeared', 'DETECTION')
                return False
            
            # SC4: Kiểm tra xe vẫn là emergency vehicle
            if not self.is_emergency_vehicle(vehicle_id):
                print(f"⚠️ SC4: Xe {vehicle_id} không phải emergency vehicle - Báo giả!")
                self._log_false_positive(vehicle_id, 'not_emergency_type', 'DETECTION')
                return False
                
        except Exception as e:
            print(f"⚠️ SC4: Lỗi khi kiểm tra xe {vehicle_id}: {e}")
            self._log_false_positive(vehicle_id, f'verification_error: {e}', 'DETECTION')
            return False
        
        # Thêm thời điểm phát hiện vào lịch sử
        self.detection_confirmations[vehicle_id].append(current_time)
        
        # Lọc các phát hiện cũ (ngoài cửa sổ xác nhận)
        self.detection_confirmations[vehicle_id] = [
            t for t in self.detection_confirmations[vehicle_id]
            if current_time - t <= self.CONFIRMATION_WINDOW
        ]
        
        # Kiểm tra có đủ số lần xác nhận không
        if len(self.detection_confirmations[vehicle_id]) >= self.CONFIRMATION_COUNT:
            vehicle.confirmed = True
            print(f"✅ SC4: Xe {vehicle_id} đã được xác nhận ({len(self.detection_confirmations[vehicle_id])} lần)")
            return True
            
        return False
    
    def can_activate_preemption(self) -> bool:
        """
        Kiểm tra có thể kích hoạt ưu tiên không (giới hạn tần suất)
        
        Returns:
            True nếu có thể kích hoạt ưu tiên
        """
        current_time = traci.simulation.getTime()
        
        # Kiểm tra cooldown
        if current_time - self.last_preemption_time < self.PREEMPT_COOLDOWN:
            return False
        
        # Cập nhật đếm ưu tiên trong phút qua
        cutoff_time = current_time - 60.0
        while self.preemption_count_last_minute and self.preemption_count_last_minute[0] < cutoff_time:
            self.preemption_count_last_minute.popleft()
        
        # Kiểm tra giới hạn số lần ưu tiên
        if len(self.preemption_count_last_minute) >= self.MAX_PREEMPT_PER_MINUTE:
            return False
            
        return True
    
    def select_priority_vehicle(self, vehicles: List[EmergencyVehicle]) -> Optional[EmergencyVehicle]:
        """
        Chọn xe ưu tiên từ danh sách (ưu tiên xe đến trước)
        
        Args:
            vehicles: Danh sách xe ưu tiên
            
        Returns:
            Xe được chọn ưu tiên hoặc None
        """
        if not vehicles:
            return None
        
        # Lọc xe có ETA nhỏ hơn ngưỡng
        eligible_vehicles = [v for v in vehicles if v.eta <= self.ETA_THRESHOLD]
        
        if not eligible_vehicles:
            return None
            
        # Sắp xếp theo ETA (xe đến trước được ưu tiên)
        eligible_vehicles.sort(key=lambda v: v.eta)
        
        return eligible_vehicles[0]
    
    def select_priority_vehicle_smart(self) -> Optional[EmergencyVehicle]:
        """
        SC3: Chọn xe ưu tiên thông minh từ danh sách confirmed vehicles
        - So sánh ETA
        - Nếu ETA gần nhau (±2s) → Chọn xe gần hơn
        - Xe không chọn → Đưa vào pending_vehicles
        
        Returns:
            Xe được chọn ưu tiên hoặc None
        """
        if not self.confirmed_vehicles:
            return None
        
        vehicles = list(self.confirmed_vehicles.values())
        
        # Lọc xe có ETA ≤ 30s
        eligible = [v for v in vehicles if v.eta <= 30]
        
        if not eligible:
            return None
        
        # Sắp xếp theo ETA
        eligible.sort(key=lambda v: v.eta)
        
        # SC3: Nếu có 2+ xe và ETA gần nhau
        if len(eligible) >= 2:
            eta_diff = abs(eligible[0].eta - eligible[1].eta)
            if eta_diff <= 2.0:
                # ETA gần nhau (±2s) → Chọn xe gần hơn
                print(f"⚡ SC3: Có {len(eligible)} xe, ETA gần nhau ({eta_diff:.1f}s)")
                print(f"   Chọn xe gần hơn theo distance")
                eligible.sort(key=lambda v: v.distance)
        
        # Xe được chọn
        selected = eligible[0]
        
        # Xe còn lại → Đưa vào pending queue
        for v in eligible[1:]:
            self.pending_vehicles[v.vehicle_id] = v
            print(f"📝 SC3: Xe {v.vehicle_id} đưa vào pending queue")
        
        return selected
    
    def activate_emergency_mode(self, rejected_vehicle: EmergencyVehicle):
        """
        SC6: Kích hoạt Emergency Mode khi vượt rate limit
        - Từ chối xe ưu tiên
        - Điều chỉnh tham số adaptive
        - Log để phân tích
        
        Args:
            rejected_vehicle: Xe bị từ chối ưu tiên
        """
        current_time = traci.simulation.getTime()
        
        self.emergency_mode_active = True
        self.emergency_mode_start_time = current_time
        
        print(f"🚨 SC6 EMERGENCY MODE ACTIVATED")
        print(f"   Từ chối xe {rejected_vehicle.vehicle_id}")
        print(f"   Đã ưu tiên {len(self.preemption_count_last_minute)} lần trong 60s")
        
        # Log xe bị từ chối
        self.rejected_vehicles.append({
            'vehicle_id': rejected_vehicle.vehicle_id,
            'time': current_time,
            'reason': 'rate_limit_exceeded',
            'eta': rejected_vehicle.eta,
            'direction': rejected_vehicle.direction,
            'distance': rejected_vehicle.distance
        })
        
        # Điều chỉnh adaptive controller (nếu có)
        if self.adaptive_controller:
            try:
                # Tăng min_green để ổn định, giảm max_green để luân chuyển nhanh
                self.adaptive_controller.set_emergency_params(
                    min_green=12.0,
                    max_green=90.0
                )
                print(f"   Điều chỉnh adaptive: min=12s, max=90s")
            except Exception as e:
                print(f"⚠️ Không thể điều chỉnh adaptive params: {e}")
    
    def should_respect_min_green(self) -> bool:
        """
        Kiểm tra có nên tôn trọng thời gian xanh tối thiểu không
        
        Returns:
            True nếu cần chờ đủ min_green
        """
        if not self.adaptive_controller:
            return False
            
        current_time = traci.simulation.getTime()
        phase_duration = current_time - self.adaptive_controller.phase_start_time
        
        return phase_duration < self.SAFE_MIN_GREEN_BEFORE
    
    def calculate_required_phase(self, direction: str) -> int:
        """
        Tính pha đèn cần thiết cho hướng xe ưu tiên
        
        Args:
            direction: Hướng di chuyển của xe ưu tiên
            
        Returns:
            Phase number for SUMO
        """
        return self.direction_phases.get(direction, 0)
    
    def apply_emergency_phase(self, phase: int) -> bool:
        """
        Áp dụng pha đèn khẩn cấp
        
        Args:
            phase: Pha đèn cần áp dụng
            
        Returns:
            True nếu thành công
        """
        try:
            traci.trafficlight.setPhase(self.junction_id, phase)
            return True
        except Exception as e:
            print(f"❌ Lỗi khi áp dụng pha khẩn cấp: {e}")
            return False
    
    def transition_to_state(self, new_state: PreemptionState, context: Dict = None):
        """
        Chuyển đổi trạng thái máy trạng thái
        
        Args:
            new_state: Trạng thái mới
            context: Thông tin bổ sung về việc chuyển đổi
        """
        current_time = traci.simulation.getTime()
        
        print(f"🔄 Chuyển từ {self.current_state.value} → {new_state.value}")
        
        # Gọi UI callback để cập nhật trạng thái visual
        if self.ui_callback:
            try:
                self.ui_callback(self.junction_id, new_state.value, self.priority_vehicle)
            except Exception as e:
                print(f"⚠️ UI callback error: {e}")
        
        # --- QUAN TRỌNG: Pause/Resume AdaptiveController ---
        old_state = self.current_state
        
        # Khi rời NORMAL → Pause Adaptive
        if old_state == PreemptionState.NORMAL and new_state != PreemptionState.NORMAL:
            if self.adaptive_controller:
                self.adaptive_controller.is_active = False
                print("⏸️ Pause AdaptiveController")
        
        # Khi về NORMAL → Resume Adaptive
        if new_state == PreemptionState.NORMAL and old_state != PreemptionState.NORMAL:
            if self.adaptive_controller:
                self.adaptive_controller.is_active = True
                print("▶️ Resume AdaptiveController")
        
        # Lưu lịch sử chuyển đổi
        if context:
            self.preemption_history.append({
                'from_state': old_state.value,
                'to_state': new_state.value,
                'time': current_time,
                'context': context
            })
        
        self.current_state = new_state
        self.state_start_time = current_time
    
    def handle_normal_state(self):
        """Xử lý trạng thái NORMAL"""
        # Quét tìm xe ưu tiên
        detected_vehicles = self.scan_for_emergency_vehicles()
        
        if detected_vehicles:
            # Cập nhật danh sách xe được phát hiện
            for vehicle in detected_vehicles:
                self.detected_vehicles[vehicle.vehicle_id] = vehicle
                
                # Thử xác nhận xe
                if self.confirm_emergency_vehicle(vehicle):
                    self.confirmed_vehicles[vehicle.vehicle_id] = vehicle
                    
            # Chuyển sang DETECTION nếu có xe được xác nhận
            if self.confirmed_vehicles:
                self.transition_to_state(PreemptionState.DETECTION, {
                    'detected_count': len(detected_vehicles),
                    'confirmed_count': len(self.confirmed_vehicles)
                })
    
    def handle_detection_state(self):
        """
        Xử lý trạng thái DETECTION
        Logic:
        - Bước 1: Chọn xe ưu tiên (SC3)
        - Bước 2: Kiểm tra ETA
        - Bước 3: Kiểm tra rate limit (SC6)
        - Bước 4: Kiểm tra xe từ hướng đang xanh (SC1)
        - Bước 5: Kiểm tra safe_min_green (SC2)
        """
        current_time = traci.simulation.getTime()
        
        # --- BƯỚC 1: Chọn xe ưu tiên ---
        priority_vehicle = self.select_priority_vehicle_smart()
        
        if not priority_vehicle:
            # Không có xe phù hợp, quay về NORMAL
            print("ℹ️ Không có xe ưu tiên phù hợp")
            self.transition_to_state(PreemptionState.NORMAL, {
                'reason': 'no_eligible_vehicle'
            })
            self.detected_vehicles.clear()
            self.confirmed_vehicles.clear()
            return
        
        # --- BƯỚC 2: Phân loại theo ETA ---
        if priority_vehicle.eta > 30:
            # ETA quá xa → Chờ (đặt lịch)
            print(f"⏰ ETA={priority_vehicle.eta:.1f}s > 30s, chờ xe đến gần hơn...")
            return  # Giữ ở DETECTION, chờ ETA giảm
        
        if priority_vehicle.eta > 12:
            # ETA trong khoảng 12-30s → Monitor tiếp
            print(f"⏳ ETA={priority_vehicle.eta:.1f}s, tiếp tục theo dõi...")
            return  # Giữ ở DETECTION
        
        # --- BƯỚC 3: ETA ≤ 12s → Kiểm tra rate limit (SC6) ---
        if not self.can_activate_preemption():
            # Vượt giới hạn 2 lần/60s
            print(f"⛔ SC6: Vượt rate limit ({len(self.preemption_count_last_minute)}/2 trong 60s)")
            print(f"   TỪ CHỐI ưu tiên cho xe {priority_vehicle.vehicle_id}")
            
            # Kích hoạt Emergency Mode (SC6)
            self.activate_emergency_mode(priority_vehicle)
            
            # Quay về NORMAL (KHÔNG cho ưu tiên)
            self.transition_to_state(PreemptionState.NORMAL, {
                'reason': 'rate_limit_exceeded_sc6',
                'vehicle_id': priority_vehicle.vehicle_id,
                'rejected': True
            })
            self.detected_vehicles.clear()
            self.confirmed_vehicles.clear()
            return
        
        # --- BƯỚC 4: Kiểm tra SC1 (xe từ hướng đang xanh) ---
        try:
            current_phase = traci.trafficlight.getPhase(self.junction_id)
            required_phase = self.calculate_required_phase(priority_vehicle.direction)
            
            if current_phase == required_phase:
                # SC1: Xe từ hướng đang xanh → Kéo dài luôn
                print(f"=" * 60)
                print(f"🚨 SC1: XE ƯU TIÊN TỪ HƯỚNG ĐANG XANH")
                print(f"   Xe: {priority_vehicle.vehicle_id}")
                print(f"   Hướng: {priority_vehicle.direction} (Phase {current_phase})")
                print(f"   Khoảng cách: {priority_vehicle.distance:.1f}m")
                print(f"   ETA: {priority_vehicle.eta:.1f}s")
                print(f"   → KÉO DÀI ĐÈN XANH")
                print(f"=" * 60)
                
                # Chuyển thẳng PREEMPTION_GREEN (bỏ qua SAFE_TRANSITION)
                self.transition_to_state(PreemptionState.PREEMPTION_GREEN, {
                    'scenario': 'SC1',
                    'priority_vehicle': priority_vehicle.vehicle_id,
                    'direction': priority_vehicle.direction,
                    'eta': priority_vehicle.eta,
                    'skip_transition': True
                })
                
                # Cập nhật thống kê
                self.preemption_count_last_minute.append(current_time)
                self.last_preemption_time = current_time
                self.preemption_start_time = current_time  # ✅ QUAN TRỌNG cho RESTORE
                self.priority_vehicle = priority_vehicle
                self._preemption_counted = True  # ✅ Đánh dấu đã đếm (để SAFE_TRANSITION không đếm lại)
                return
                
        except Exception as e:
            print(f"⚠️ Lỗi khi kiểm tra pha đèn: {e}")
        
        # --- BƯỚC 5: Kiểm tra SC2 (safe_min_green) ---
        if self.adaptive_controller:
            try:
                phase_elapsed = self.adaptive_controller.get_phase_elapsed_time(current_time)
                
                if phase_elapsed < self.SAFE_MIN_GREEN_BEFORE:  # 4s
                    remaining = self.SAFE_MIN_GREEN_BEFORE - phase_elapsed
                    print(f"⏸️ SC2: Chờ {remaining:.1f}s để đủ safe_min_green (4s)")
                    print(f"   Pha hiện tại mới xanh được {phase_elapsed:.1f}s")
                    return  # Giữ ở DETECTION
                    
            except Exception as e:
                print(f"⚠️ Không thể kiểm tra phase_elapsed: {e}")
        
        # --- BƯỚC 6: Tất cả điều kiện OK → SAFE_TRANSITION ---
        print(f"=" * 60)
        print(f"🚦 SC2: CHUYỂN PHA AN TOÀN")
        print(f"   Xe: {priority_vehicle.vehicle_id}")
        print(f"   Hướng: {priority_vehicle.direction}")
        print(f"   ETA: {priority_vehicle.eta:.1f}s")
        print(f"   → BẮT ĐẦU QUY TRÌNH YELLOW → ALL-RED → GREEN")
        print(f"=" * 60)
        
        self.transition_to_state(PreemptionState.SAFE_TRANSITION, {
            'scenario': 'SC2',
            'priority_vehicle': priority_vehicle.vehicle_id,
            'direction': priority_vehicle.direction,
            'eta': priority_vehicle.eta
        })
        
        # Lưu xe ưu tiên đang xử lý
        self.priority_vehicle = priority_vehicle
        self.preemption_start_time = current_time  # ✅ QUAN TRỌNG cho RESTORE
    
    def handle_safe_transition_state(self):
        """
        Xử lý trạng thái SAFE_TRANSITION
        Quy trình:
        - Giai đoạn 1 (0-3s): Vàng
        - Giai đoạn 2 (3-6s): All-Red
        - Giai đoạn 3 (>6s): Chuyển PREEMPTION_GREEN
        
        SC4: Kiểm tra báo giả trong quá trình chuyển pha
        """
        current_time = traci.simulation.getTime()
        elapsed = current_time - self.state_start_time
        
        # --- SC4: Kiểm tra báo giả ---
        if self.priority_vehicle:
            if not self._verify_emergency_vehicle_exists(
                self.priority_vehicle.vehicle_id, 'SAFE_TRANSITION'
            ):
                print(f"❌ SC4: Phát hiện báo giả trong SAFE_TRANSITION!")
                print(f"   → HỦY ưu tiên, quay về RESTORE")
                
                # Hủy ưu tiên, quay về RESTORE
                self.transition_to_state(PreemptionState.RESTORE, {
                    'reason': 'false_positive_detected_sc4',
                    'vehicle_id': self.priority_vehicle.vehicle_id,
                    'cancelled': True
                })
                return
        
        # --- Giai đoạn 1: YELLOW (0-3s) ---
        if elapsed <= self.YELLOW_DURATION:
            if elapsed < 0.1:  # Lần đầu vào state
                print(f"🟡 Bật đèn vàng (Yellow phase - {self.YELLOW_DURATION}s)")
            return  # Giữ ở state này
        
        # --- Giai đoạn 2: ALL-RED (3-6s) ---
        elif elapsed <= (self.YELLOW_DURATION + self.ALL_RED_EMERGENCY):
            if elapsed < self.YELLOW_DURATION + 0.1:  # Lần đầu vào all-red
                print(f"🔴 Bật All-Red ({self.ALL_RED_EMERGENCY}s) - Dọn giao lộ")
                self.apply_all_red_phase()
            return
        
        # --- Giai đoạn 3: Hoàn tất → PREEMPTION_GREEN ---
        else:
            print("✅ Safe transition hoàn tất")
            
            # Áp dụng pha xanh cho xe ưu tiên
            if self.priority_vehicle:
                required_phase = self.calculate_required_phase(self.priority_vehicle.direction)
                self.apply_emergency_phase(required_phase)
                
                print(f"🟢 Bật xanh cho hướng {self.priority_vehicle.direction} (phase {required_phase})")
                
                self.transition_to_state(PreemptionState.PREEMPTION_GREEN, {
                    'vehicle_id': self.priority_vehicle.vehicle_id,
                    'direction': self.priority_vehicle.direction,
                    'phase': required_phase
                })
                
                # Cập nhật thống kê (nếu chưa được cập nhật ở SC1)
                if not hasattr(self, '_preemption_counted') or not self._preemption_counted:
                    self.preemption_count_last_minute.append(current_time)
                    self.last_preemption_time = current_time
                    self.preemption_start_time = current_time
                    self._preemption_counted = True
            else:
                # Không còn xe ưu tiên
                print("⚠️ Không còn xe ưu tiên, chuyển RESTORE")
                self.transition_to_state(PreemptionState.RESTORE)
    
    def apply_all_red_phase(self):
        """
        Áp dụng pha all-red (tất cả đèn đỏ)
        """
        try:
            # Tạo state string với tất cả đèn đỏ (16 ký tự 'r')
            all_red_state = "rrrrrrrrrrrrrrrr"
            traci.trafficlight.setRedYellowGreenState(self.junction_id, all_red_state)
            return True
        except Exception as e:
            print(f"❌ Lỗi khi áp dụng all-red: {e}")
            return False
    
    def handle_preemption_green_state(self):
        """
        Xử lý trạng thái PREEMPTION_GREEN
        Logic:
        - Bước 1: Áp dụng pha xanh (lần đầu)
        - Bước 2: SC4 - Kiểm tra báo giả
        - Bước 3: Theo dõi xe qua ngã tư
        - Bước 4: Kiểm tra xe bị kẹt (SC5)
        - Bước 5: Quyết định kết thúc
        """
        current_time = traci.simulation.getTime()
        elapsed = current_time - self.state_start_time
        
        # --- BƯỚC 1: Áp dụng pha xanh (chỉ lần đầu) ---
        if elapsed < 0.1:
            if self.priority_vehicle:
                required_phase = self.calculate_required_phase(self.priority_vehicle.direction)
                
                print(f"🟢 Bật xanh cho hướng {self.priority_vehicle.direction}")
                print(f"   Phase: {required_phase}, Xe: {self.priority_vehicle.vehicle_id}")
                
                # Áp dụng pha xanh
                try:
                    # Lấy state string tương ứng
                    if required_phase == 0:  # Bắc-Nam
                        green_state = "GGGgrrrrGGGgrrrr"
                    elif required_phase == 3:  # Đông-Tây
                        green_state = "rrrrGGGgrrrrGGGg"
                    else:
                        green_state = "GGGgrrrrGGGgrrrr"  # Default
                    
                    traci.trafficlight.setRedYellowGreenState(self.junction_id, green_state)
                    
                except Exception as e:
                    print(f"⚠️ Lỗi khi áp dụng pha xanh: {e}")
        
        # --- BƯỚC 2: SC4 - Kiểm tra báo giả ---
        if self.priority_vehicle:
            if not self._verify_emergency_vehicle_exists(
                self.priority_vehicle.vehicle_id, 'PREEMPTION_GREEN'
            ):
                print(f"❌ SC4: Phát hiện báo giả trong PREEMPTION_GREEN!")
                print(f"   → HỦY ưu tiên, chuyển RESTORE ngay lập tức")
                
                # Hủy ưu tiên, khôi phục adaptive ngay
                self.transition_to_state(PreemptionState.RESTORE, {
                    'reason': 'false_positive_detected_sc4',
                    'vehicle_id': self.priority_vehicle.vehicle_id,
                    'cancelled': True,
                    'green_duration': elapsed
                })
                return
        
        # --- BƯỚC 3: Theo dõi xe ---
        active_vehicles = []
        
        for vid, vehicle in list(self.confirmed_vehicles.items()):
            try:
                # Kiểm tra xe còn trong simulation không
                if vid not in traci.vehicle.getIDList():
                    # Xe đã despawn → Đã qua
                    vehicle.served = True
                    
                    # ✅ Tính Emergency Clearance Time
                    self._calculate_and_log_clearance_time(vehicle, current_time)
                    
                    self.served_vehicles.append(vehicle)
                    print(f"✅ Xe {vid} đã qua ngã tư (despawned)")
                    continue
                
                # Tính lại distance
                distance = self.calculate_distance_to_junction(vid)
                
                if distance > 50:
                    # Xe đã qua ngã tư (50m sau junction)
                    vehicle.served = True
                    
                    # ✅ Tính Emergency Clearance Time
                    self._calculate_and_log_clearance_time(vehicle, current_time)
                    
                    self.served_vehicles.append(vehicle)
                    print(f"✅ Xe {vid} đã qua ngã tư (distance={distance:.1f}m)")
                    continue
                
                # Xe vẫn còn trong vùng
                if distance < 200:
                    # --- BƯỚC 3: Kiểm tra xe bị kẹt (SC5) ---
                    speed = traci.vehicle.getSpeed(vid)
                    
                    if speed < 2.0 and elapsed > 15:
                        # Xe đi chậm sau 15s → Cảnh báo
                        print(f"⚠️ SC5: Xe {vid} có thể bị kẹt")
                        print(f"   Speed: {speed:.1f}m/s, Elapsed: {elapsed:.1f}s")
                        
                        if elapsed > 30:
                            # Kẹt quá 30s → Chuyển HOLD_PREEMPTION
                            print(f"❌ SC5: Xe {vid} kẹt quá 30s!")
                            self.transition_to_state(PreemptionState.HOLD_PREEMPTION, {
                                'reason': 'vehicle_stuck',
                                'vehicle_id': vid,
                                'speed': speed,
                                'elapsed': elapsed
                            })
                            return
                    
                    active_vehicles.append(vehicle)
                    
            except Exception as e:
                print(f"⚠️ Lỗi khi kiểm tra xe {vid}: {e}")
        
        # Cập nhật danh sách xe active
        self.confirmed_vehicles = {v.vehicle_id: v for v in active_vehicles}
        
        # --- BƯỚC 4: SC4 - Kiểm tra tất cả xe vẫn hợp lệ ---
        # Lọc ra các xe không còn hợp lệ (báo giả)
        valid_vehicles = []
        for vehicle in active_vehicles:
            if self._verify_emergency_vehicle_exists(vehicle.vehicle_id, 'PREEMPTION_GREEN'):
                valid_vehicles.append(vehicle)
            else:
                print(f"⚠️ SC4: Xe {vehicle.vehicle_id} không còn hợp lệ, loại khỏi danh sách")
        
        # Cập nhật lại danh sách xe hợp lệ
        active_vehicles = valid_vehicles
        self.confirmed_vehicles = {v.vehicle_id: v for v in active_vehicles}
        
        # --- BƯỚC 5: Kiểm tra điều kiện kết thúc ---
        if not active_vehicles:
            # Không còn xe nào → Kết thúc ngay
            print(f"✅ Tất cả xe đã qua (elapsed={elapsed:.1f}s)")
            self.transition_to_state(PreemptionState.RESTORE, {
                'reason': 'all_vehicles_cleared',
                'green_duration': elapsed,
                'served_count': len(self.served_vehicles)
            })
            return
        
        # Nếu còn xe VÀ đã đủ min_green (8s) → Kiểm tra xe gần nhất
        if elapsed >= self.PREEMPT_MIN_GREEN:
            # Tìm xe gần ngã tư nhất
            closest_distance = min(v.distance for v in active_vehicles) if active_vehicles else float('inf')
            
            # Nếu xe gần nhất đã rất gần (< 30m) → Chờ thêm
            if closest_distance < 30:
                print(f"⏳ Xe gần nhất còn {closest_distance:.1f}m, chờ thêm...")
                return  # Giữ PREEMPTION_GREEN
            
            # Nếu xe còn xa (≥30m) và đã đủ min_green → Chuyển RESTORE
            print(f"✅ Đủ {self.PREEMPT_MIN_GREEN}s min_green, xe gần nhất còn {closest_distance:.1f}m")
            print(f"   → Chuyển RESTORE (còn {len(active_vehicles)} xe chưa qua)")
            self.transition_to_state(PreemptionState.RESTORE, {
                'reason': 'min_green_reached',
                'green_duration': elapsed,
                'remaining_vehicles': len(active_vehicles)
            })
            return
        
        # Còn lại: Giữ ở PREEMPTION_GREEN, tiếp tục theo dõi
    
    def handle_hold_preemption_state(self):
        """
        SC5: Xử lý trạng thái HOLD_PREEMPTION (xe bị kẹt)
        Logic:
        - Giữ xanh thêm cho xe thoát kẹt
        - Theo dõi speed của xe
        - Timeout 30s → RESTORE với lỗi
        """
        current_time = traci.simulation.getTime()
        elapsed = current_time - self.state_start_time
        
        # Timeout 30s (theo tài liệu SC5)
        HOLD_TIMEOUT = 30.0
        
        if not self.priority_vehicle:
            # Không có xe ưu tiên, chuyển RESTORE
            print("⚠️ Không có xe ưu tiên trong HOLD_PREEMPTION")
            self.transition_to_state(PreemptionState.RESTORE)
            return
        
        vehicle_id = self.priority_vehicle.vehicle_id
        
        # Kiểm tra xe còn trong simulation không
        if vehicle_id not in traci.vehicle.getIDList():
            # Xe đã despawn → Đã qua
            print(f"✅ SC5: Xe {vehicle_id} đã qua ngã tư (despawned)")
            self.priority_vehicle.served = True
            
            # ✅ Tính Emergency Clearance Time
            self._calculate_and_log_clearance_time(self.priority_vehicle, current_time)
            
            self.served_vehicles.append(self.priority_vehicle)
            self.transition_to_state(PreemptionState.RESTORE)
            return
        
        try:
            distance = self.calculate_distance_to_junction(vehicle_id)
            speed = traci.vehicle.getSpeed(vehicle_id)
            
            # Kiểm tra xe đã thoát kẹt chưa
            if speed > 5.0:
                # Xe đã thoát kẹt (speed > 5 m/s)
                print(f"✅ SC5: Xe {vehicle_id} thoát kẹt!")
                print(f"   Speed: {speed:.1f}m/s, Elapsed: {elapsed:.1f}s")
                self.transition_to_state(PreemptionState.RESTORE, {
                    'reason': 'vehicle_unstuck',
                    'hold_duration': elapsed
                })
                return
            
            if distance > 50:
                # Xe đã qua ngã tư
                print(f"✅ SC5: Xe {vehicle_id} đã qua ngã tư")
                print(f"   Distance: {distance:.1f}m, Elapsed: {elapsed:.1f}s")
                self.priority_vehicle.served = True
                
                # ✅ Tính Emergency Clearance Time
                self._calculate_and_log_clearance_time(self.priority_vehicle, current_time)
                
                self.served_vehicles.append(self.priority_vehicle)
                self.transition_to_state(PreemptionState.RESTORE)
                return
            
            # Kiểm tra timeout
            if elapsed > HOLD_TIMEOUT:
                # Timeout 30s → Chấp nhận thất bại
                print(f"❌ SC5: TIMEOUT {HOLD_TIMEOUT}s - Xe vẫn kẹt!")
                print(f"   Speed: {speed:.1f}m/s, Distance: {distance:.1f}m")
                
                # Log lỗi
                self.failed_preemptions.append({
                    'vehicle_id': vehicle_id,
                    'scenario': 'SC5',
                    'reason': 'stuck_timeout_30s',
                    'time': current_time,
                    'final_speed': speed,
                    'final_distance': distance,
                    'hold_duration': elapsed
                })
                
                # Chuyển RESTORE (chấp nhận thất bại)
                self.transition_to_state(PreemptionState.RESTORE, {
                    'reason': 'sc5_timeout',
                    'failed': True
                })
                return
            
            # Log định kỳ mỗi 5s
            if int(elapsed) % 5 == 0 and elapsed - int(elapsed) < 0.1:
                print(f"⏳ SC5: Chờ xe thoát kẹt ({elapsed:.0f}s/{HOLD_TIMEOUT}s)")
                print(f"   Speed: {speed:.1f}m/s, Distance: {distance:.1f}m")
                
        except Exception as e:
            print(f"⚠️ Lỗi khi kiểm tra xe trong HOLD: {e}")
            self.transition_to_state(PreemptionState.RESTORE)
    
    def handle_restore_state(self):
        """
        Xử lý trạng thái RESTORE
        Logic:
        - Bước 1: Tính thời gian ưu tiên đã dùng
        - Bước 2: Xác định hướng bị ảnh hưởng
        - Bước 3: Tính thời gian bù (SC6)
        - Bước 4: Áp dụng bù cho Adaptive
        - Bước 5: Xử lý Emergency Mode (SC6)
        - Bước 6: Kiểm tra pending vehicles (SC3)
        - Bước 7: Quay về NORMAL
        """
        current_time = traci.simulation.getTime()
        
        # --- BƯỚC 1: Tính thời gian ưu tiên ---
        if hasattr(self, 'preemption_start_time') and self.preemption_start_time > 0:
            preemption_duration = current_time - self.preemption_start_time
        else:
            preemption_duration = current_time - self.state_start_time
        
        print(f"🔄 RESTORE: Khôi phục về adaptive")
        print(f"   Thời gian ưu tiên: {preemption_duration:.1f}s")
        print(f"   Xe đã phục vụ: {len(self.served_vehicles)}")
        
        # --- BƯỚC 2: Xác định hướng bị ảnh hưởng ---
        priority_direction = self.priority_vehicle.direction if self.priority_vehicle else None
        all_directions = {"Bắc", "Nam", "Đông", "Tây"}
        
        if priority_direction:
            affected_directions = all_directions - {priority_direction}
        else:
            affected_directions = all_directions
        
        print(f"   Hướng bị ảnh hưởng: {', '.join(affected_directions)}")
        
        # --- BƯỚC 3: Tính thời gian bù (SC6) ---
        # ✅ SC6-IMPROVED: Phân tích backlog và bù thông minh
        if self.adaptive_controller:
            print(f"=" * 60)
            print(f"📊 SC6-BACKLOG ANALYSIS")
            print(f"-" * 60)
            
            # Lấy báo cáo backlog toàn bộ
            backlog_report = self.adaptive_controller.get_all_backlog_report()
            
            # Phân loại theo mức độ nghiêm trọng
            critical_dirs = []
            warning_dirs = []
            ok_dirs = []
            
            for direction in affected_directions:
                info = backlog_report.get(direction, {})
                status = info.get('status', 'OK')
                severity = info.get('severity', 0)
                current_queue = info.get('current_queue', 0)
                
                print(f"   {direction}: Queue={current_queue:.1f} PCU, Severity={severity:.0f}/100 [{status}]")
                
                if status == 'CRITICAL':
                    critical_dirs.append(direction)
                elif status == 'WARNING':
                    warning_dirs.append(direction)
                else:
                    ok_dirs.append(direction)
            
            print(f"-" * 60)
        else:
            # Fallback nếu không có adaptive controller
            critical_dirs = []
            warning_dirs = []
            ok_dirs = list(affected_directions)
        
        # Hệ số bù phụ thuộc vào emergency mode
        if self.emergency_mode_active:
            base_factor = 0.4  # Bù ít hơn trong emergency mode
            print(f"   ⚠️ Emergency mode: Bù thận trọng hơn")
        else:
            base_factor = 0.6  # Bù bình thường
            print(f"   Bù thời gian dựa trên mức độ backlog")
        
        # --- BƯỚC 4: Áp dụng bù cho Adaptive ---
        if self.adaptive_controller:
            try:
                # ✅ CHIẾN LƯỢC BÙ THÔNG MINH:
                
                # 1. Hướng CRITICAL: Bù 80-100%
                for direction in critical_dirs:
                    lost_green = preemption_duration
                    compensation_time = lost_green * (base_factor + 0.30)  # +30%
                    self.adaptive_controller.add_green_debt(direction, compensation_time)
                    print(f"   🔴 CRITICAL {direction}: Bù {compensation_time:.1f}s ({int((base_factor + 0.30)*100)}%)")
                
                # 2. Hướng WARNING: Bù 60-80%
                for direction in warning_dirs:
                    lost_green = preemption_duration
                    compensation_time = lost_green * (base_factor + 0.10)  # +10%
                    self.adaptive_controller.add_green_debt(direction, compensation_time)
                    print(f"   🟡 WARNING {direction}: Bù {compensation_time:.1f}s ({int((base_factor + 0.10)*100)}%)")
                
                # 3. Hướng OK: Bù 40-60%
                for direction in ok_dirs:
                    lost_green = preemption_duration
                    compensation_time = lost_green * base_factor
                    self.adaptive_controller.add_green_debt(direction, compensation_time)
                    print(f"   🟢 OK {direction}: Bù {compensation_time:.1f}s ({int(base_factor*100)}%)")
                
                print(f"=" * 60)
                
                # Kích hoạt lại Adaptive
                self.adaptive_controller.is_active = True
                print(f"   ✅ Adaptive Controller đã được kích hoạt lại")
                
            except Exception as e:
                print(f"   ⚠️ Lỗi khi bù thời gian: {e}")
        
        # --- BƯỚC 5: Xử lý Emergency Mode (SC6) ---
        if self.emergency_mode_active:
            elapsed_emergency = current_time - self.emergency_mode_start_time
            
            # Giữ emergency mode trong 120s (2 phút)
            if elapsed_emergency < 120:
                print(f"   🚨 Emergency mode còn {120 - elapsed_emergency:.0f}s")
            else:
                # Tắt emergency mode
                self.emergency_mode_active = False
                print(f"   ✅ Tắt Emergency Mode (đã qua 120s)")
                
                # Khôi phục tham số adaptive
                if self.adaptive_controller:
                    try:
                        self.adaptive_controller.restore_normal_params()
                        print(f"   ✅ Khôi phục tham số adaptive bình thường")
                    except Exception as e:
                        print(f"   ⚠️ Lỗi khi khôi phục params: {e}")
        
        # --- BƯỚC 6: Kiểm tra pending vehicles (SC3) ---
        if self.pending_vehicles:
            print(f"   🔔 Có {len(self.pending_vehicles)} xe đang chờ trong pending queue")
            
            # Chuyển pending → confirmed
            for vid, vehicle in self.pending_vehicles.items():
                self.confirmed_vehicles[vid] = vehicle
                print(f"      - Xe {vid} từ pending → confirmed")
            
            self.pending_vehicles.clear()
            
            # Quay lại DETECTION để xử lý xe tiếp theo
            print(f"   → Chuyển DETECTION để xử lý xe pending")
            self.transition_to_state(PreemptionState.DETECTION, {
                'reason': 'pending_vehicles_exist',
                'count': len(self.confirmed_vehicles)
            })
            return
        
        # --- BƯỚC 7: Dọn dẹp và quay về NORMAL ---
        self.detected_vehicles.clear()
        self.confirmed_vehicles.clear()
        self.priority_vehicle = None
        self.preemption_start_time = 0.0
        self._preemption_counted = False
        
        print(f"   ✅ Quay về chế độ NORMAL")
        self.transition_to_state(PreemptionState.NORMAL, {
            'reason': 'preemption_completed'
        })
    
    def start(self) -> bool:
        """
        Khởi động Priority Controller
        
        Returns:
            True nếu khởi động thành công
        """
        try:
            if not traci.isLoaded():
                print("❌ SUMO chưa được khởi động!")
                return False
            
            self.current_state = PreemptionState.NORMAL
            self.state_start_time = traci.simulation.getTime()
            self.is_active = True
            
            print(f"✅ Priority Controller đã khởi động cho {self.junction_id}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi khởi động Priority Controller: {e}")
            return False
    
    def stop(self):
        """Dừng Priority Controller"""
        self.is_active = False
        print("🛑 Priority Controller đã dừng")
    
    def step(self) -> bool:
        """
        Thực hiện một bước xử lý ưu tiên
        
        Returns:
            True nếu thành công
        """
        if not self.is_active:
            return False
        
        try:
            # Xử lý theo trạng thái hiện tại
            if self.current_state == PreemptionState.NORMAL:
                self.handle_normal_state()
            elif self.current_state == PreemptionState.DETECTION:
                self.handle_detection_state()
            elif self.current_state == PreemptionState.SAFE_TRANSITION:
                self.handle_safe_transition_state()
            elif self.current_state == PreemptionState.PREEMPTION_GREEN:
                self.handle_preemption_green_state()
            elif self.current_state == PreemptionState.HOLD_PREEMPTION:
                self.handle_hold_preemption_state()
            elif self.current_state == PreemptionState.RESTORE:
                self.handle_restore_state()
            
            return True
            
        except Exception as e:
            print(f"❌ Lỗi trong bước xử lý ưu tiên: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Lấy trạng thái hiện tại của Priority Controller
        
        Returns:
            Dictionary chứa thông tin trạng thái
        """
        try:
            current_time = traci.simulation.getTime()
            state_duration = current_time - self.state_start_time
            
            return {
                'junction_id': self.junction_id,
                'current_state': self.current_state.value,
                'state_duration': round(state_duration, 1),
                'is_active': self.is_active,
                'detected_vehicles': len(self.detected_vehicles),
                'confirmed_vehicles': len(self.confirmed_vehicles),
                'served_vehicles': len(self.served_vehicles),
                'preemptions_last_minute': len(self.preemption_count_last_minute),
                'can_activate_preemption': self.can_activate_preemption(),
                'total_preemption_events': len(self.preemption_history)
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi lấy trạng thái: {e}")
            return {'error': str(e)}
    
    def get_statistics(self) -> Dict:
        """
        Lấy thống kê hiệu suất xử lý ưu tiên
        
        Returns:
            Dictionary chứa metrics thống kê
        """
        try:
            if not self.preemption_history:
                return {'message': 'Chưa có dữ liệu thống kê ưu tiên'}
            
            # Thống kê số lần ưu tiên
            total_preemptions = len([h for h in self.preemption_history 
                                   if h['to_state'] == 'PREEMPTION_GREEN'])
            
            # Thống kê thời gian xử lý trung bình
            processing_times = []
            for i, history in enumerate(self.preemption_history):
                if history['to_state'] == 'PREEMPTION_GREEN':
                    # Tìm thời điểm RESTORE tương ứng
                    for j in range(i+1, len(self.preemption_history)):
                        if self.preemption_history[j]['to_state'] == 'RESTORE':
                            processing_time = (self.preemption_history[j]['time'] - 
                                             history['time'])
                            processing_times.append(processing_time)
                            break
            
            avg_processing_time = (sum(processing_times) / len(processing_times) 
                                 if processing_times else 0)
            
            # SC4: Thống kê báo giả
            false_positive_count = len(self.false_positives)
            false_positive_by_stage = defaultdict(int)
            false_positive_by_reason = defaultdict(int)
            
            for fp in self.false_positives:
                false_positive_by_stage[fp['stage']] += 1
                false_positive_by_reason[fp['reason']] += 1
            
            # ✅ KPI: Emergency Clearance Time Statistics
            clearance_stats = {}
            if self.clearance_times:
                avg_clearance = sum(self.clearance_times) / len(self.clearance_times)
                min_clearance = min(self.clearance_times)
                max_clearance = max(self.clearance_times)
                
                # Đếm theo mức độ
                excellent_count = len([t for t in self.clearance_times if t <= self.EXCELLENT_CLEARANCE])
                acceptable_count = len([t for t in self.clearance_times 
                                       if self.EXCELLENT_CLEARANCE < t <= self.ACCEPTABLE_CLEARANCE])
                poor_count = len([t for t in self.clearance_times if t > self.ACCEPTABLE_CLEARANCE])
                
                clearance_stats = {
                    'average_clearance_time': round(avg_clearance, 2),
                    'min_clearance_time': round(min_clearance, 2),
                    'max_clearance_time': round(max_clearance, 2),
                    'excellent_count': excellent_count,  # ≤ 15s
                    'acceptable_count': acceptable_count,  # ≤ 25s
                    'poor_count': poor_count,  # > 25s
                    'excellent_rate': round((excellent_count / len(self.clearance_times)) * 100, 1),
                    'total_measured': len(self.clearance_times)
                }
            
            return {
                'total_preemption_activations': total_preemptions,
                'total_vehicles_served': len(self.served_vehicles),
                'average_processing_time': round(avg_processing_time, 2),
                'successful_preemptions': len(processing_times),
                'preemption_success_rate': (len(processing_times) / max(total_preemptions, 1)) * 100,
                # SC4 Statistics
                'false_positives_count': false_positive_count,
                'false_positives_by_stage': dict(false_positive_by_stage),
                'false_positives_by_reason': dict(false_positive_by_reason),
                # SC5 Statistics
                'failed_preemptions_count': len(self.failed_preemptions),
                # SC6 Statistics
                'rejected_vehicles_count': len(self.rejected_vehicles),
                'emergency_mode_activations': len([fp for fp in self.rejected_vehicles 
                                                   if fp.get('reason') == 'rate_limit_exceeded']),
                # ✅ KPI: Emergency Clearance Time
                'emergency_clearance_time': clearance_stats
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi tính thống kê ưu tiên: {e}")
            return {'error': str(e)}