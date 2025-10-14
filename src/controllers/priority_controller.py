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

class PriorityController:
    """
    Thuật toán xử lý ưu tiên xe khẩn cấp
    """
    
    def __init__(self, junction_id: str = "J1", adaptive_controller=None):
        """
        Khởi tạo Priority Controller
        
        Args:
            junction_id: ID của ngã tư
            adaptive_controller: Tham chiếu đến Adaptive Controller
        """
        self.junction_id = junction_id
        self.adaptive_controller = adaptive_controller
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
        
        # Danh sách loại xe ưu tiên
        self.EMERGENCY_VEHICLE_TYPES = {
            'ambulance', 'emergency', 'fire', 'police', 
            'cứu_thương', 'cứu_hỏa', 'cảnh_sát'
        }
        
        # Mapping hướng với edges
        self.direction_edges = {
            "Bắc": ["-E1_0", "-E1_1", "-E1_2"],
            "Nam": ["-E2_0", "-E2_1", "-E2_2"],
            "Đông": ["-E3_0", "-E3_1", "-E3_2"],
            "Tây": ["E0_0", "E0_1", "E0_2"]
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
        self.served_vehicles: List[EmergencyVehicle] = []
        self.preemption_history: List[Dict] = []
        self.detection_confirmations: Dict[str, List[float]] = defaultdict(list)
        
        # Thống kê ưu tiên
        self.preemption_count_last_minute = deque()
        self.last_preemption_time = 0
        
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
            # Lấy tất cả xe trong mô phỏng
            all_vehicles = traci.simulation.getLoadedIDList()
            
            for vehicle_id in all_vehicles:
                try:
                    # Kiểm tra xe có phải ưu tiên không
                    if not self.is_emergency_vehicle(vehicle_id):
                        continue
                    
                    # Tính khoảng cách đến ngã tư
                    distance = self.calculate_distance_to_junction(vehicle_id)
                    
                    # Kiểm tra trong bán kính phát hiện
                    if distance <= self.DETECTION_RADIUS:
                        # Lấy thông tin xe
                        speed = traci.vehicle.getSpeed(vehicle_id)
                        direction = self.get_vehicle_direction(vehicle_id)
                        veh_type = traci.vehicle.getTypeID(vehicle_id)
                        
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
                            
                except traci.exceptions.TraCIException:
                    continue
                    
        except Exception as e:
            print(f"❌ Lỗi khi quét xe ưu tiên: {e}")
            
        return emergency_vehicles
    
    def confirm_emergency_vehicle(self, vehicle: EmergencyVehicle) -> bool:
        """
        Xác nhận xe ưu tiên để tránh báo giả
        
        Args:
            vehicle: Đối tượng EmergencyVehicle
            
        Returns:
            True nếu xe được xác nhận
        """
        current_time = traci.simulation.getTime()
        vehicle_id = vehicle.vehicle_id
        
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
        
        # Lưu lịch sử chuyển đổi
        if context:
            self.preemption_history.append({
                'from_state': self.current_state.value,
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
        """Xử lý trạng thái DETECTION"""
        # Chọn xe ưu tiên
        confirmed_vehicles = list(self.confirmed_vehicles.values())
        priority_vehicle = self.select_priority_vehicle(confirmed_vehicles)
        
        if not priority_vehicle:
            # Không có xe phù hợp, quay về NORMAL
            self.transition_to_state(PreemptionState.NORMAL, {
                'reason': 'no_eligible_vehicle'
            })
            self.confirmed_vehicles.clear()
            return
        
        # Kiểm tra có thể kích hoạt ưu tiên không
        if not self.can_activate_preemption():
            print("⚠️ Không thể kích hoạt ưu tiên do giới hạn tần suất")
            self.transition_to_state(PreemptionState.NORMAL, {
                'reason': 'rate_limited'
            })
            self.confirmed_vehicles.clear()
            return
        
        # Kiểm tra có cần chờ min_green không
        if self.should_respect_min_green():
            print("⏳ Chờ đủ thời gian xanh tối thiểu...")
            return  # Giữ nguyên trạng thái DETECTION
        
        # Chuyển sang SAFE_TRANSITION
        self.transition_to_state(PreemptionState.SAFE_TRANSITION, {
            'priority_vehicle': priority_vehicle.vehicle_id,
            'direction': priority_vehicle.direction,
            'eta': priority_vehicle.eta
        })
    
    def handle_safe_transition_state(self):
        """Xử lý trạng thái SAFE_TRANSITION"""
        current_time = traci.simulation.getTime()
        transition_duration = current_time - self.state_start_time
        
        if transition_duration <= self.YELLOW_DURATION:
            # Pha vàng - giữ nguyên hoặc áp dụng yellow
            if self.adaptive_controller:
                current_phase = self.adaptive_controller.current_phase
                if "GREEN" in current_phase.value:
                    # Chuyển sang yellow tương ứng
                    if current_phase.value == "NS_GREEN":
                        yellow_phase = 1  # NS_YELLOW
                    else:  # EW_GREEN
                        yellow_phase = 4  # EW_YELLOW
                    self.apply_emergency_phase(yellow_phase)
        
        elif transition_duration <= self.YELLOW_DURATION + self.ALL_RED_EMERGENCY:
            # Pha All-Red
            self.apply_emergency_phase(2)  # ALL_RED
        
        else:
            # Chuyển sang PREEMPTION_GREEN
            confirmed_vehicles = list(self.confirmed_vehicles.values())
            priority_vehicle = self.select_priority_vehicle(confirmed_vehicles)
            
            if priority_vehicle:
                required_phase = self.calculate_required_phase(priority_vehicle.direction)
                self.apply_emergency_phase(required_phase)
                
                self.transition_to_state(PreemptionState.PREEMPTION_GREEN, {
                    'vehicle_id': priority_vehicle.vehicle_id,
                    'direction': priority_vehicle.direction,
                    'phase': required_phase
                })
                
                # Cập nhật thống kê
                self.preemption_count_last_minute.append(current_time)
                self.last_preemption_time = current_time
            else:
                # Không còn xe ưu tiên, quay về NORMAL
                self.transition_to_state(PreemptionState.RESTORE)
    
    def handle_preemption_green_state(self):
        """Xử lý trạng thái PREEMPTION_GREEN"""
        current_time = traci.simulation.getTime()
        green_duration = current_time - self.state_start_time
        
        # Kiểm tra xe ưu tiên đã qua chưa
        confirmed_vehicles = list(self.confirmed_vehicles.values())
        active_vehicles = []
        
        for vehicle in confirmed_vehicles:
            try:
                # Kiểm tra xe còn trong mô phỏng và gần ngã tư không
                if vehicle.vehicle_id in traci.simulation.getLoadedIDList():
                    distance = self.calculate_distance_to_junction(vehicle.vehicle_id)
                    if distance <= 50.0:  # Xe vẫn gần ngã tư
                        active_vehicles.append(vehicle)
                    else:
                        # Xe đã đi qua
                        vehicle.served = True
                        self.served_vehicles.append(vehicle)
            except:
                # Xe không còn trong mô phỏng - đã đi qua
                vehicle.served = True
                self.served_vehicles.append(vehicle)
        
        # Cập nhật danh sách xe còn active
        self.confirmed_vehicles = {v.vehicle_id: v for v in active_vehicles}
        
        # Quyết định tiếp tục hay kết thúc
        if not active_vehicles and green_duration >= self.PREEMPT_MIN_GREEN:
            # Không còn xe ưu tiên và đã đủ thời gian tối thiểu
            self.transition_to_state(PreemptionState.RESTORE, {
                'served_vehicles': len(self.served_vehicles),
                'green_duration': green_duration
            })
        elif active_vehicles and green_duration >= self.PREEMPT_MIN_GREEN * 2:
            # Còn xe nhưng đã giữ quá lâu, chuyển sang HOLD_PREEMPTION
            self.transition_to_state(PreemptionState.HOLD_PREEMPTION, {
                'remaining_vehicles': len(active_vehicles)
            })
    
    def handle_hold_preemption_state(self):
        """Xử lý trạng thái HOLD_PREEMPTION"""
        current_time = traci.simulation.getTime()
        hold_duration = current_time - self.state_start_time
        
        # Giới hạn thời gian giữ ưu tiên tối đa
        MAX_HOLD_TIME = 15.0  # giây
        
        if hold_duration >= MAX_HOLD_TIME:
            # Đã giữ quá lâu, buộc phải kết thúc
            self.transition_to_state(PreemptionState.RESTORE, {
                'reason': 'max_hold_time_reached',
                'hold_duration': hold_duration
            })
        else:
            # Kiểm tra lại xe ưu tiên
            self.handle_preemption_green_state()
    
    def handle_restore_state(self):
        """Xử lý trạng thái RESTORE"""
        # Dọn dẹp dữ liệu
        self.detected_vehicles.clear()
        self.confirmed_vehicles.clear()
        
        # Quay về điều khiển adaptive
        if self.adaptive_controller:
            self.adaptive_controller.is_active = True
        
        # Chuyển về NORMAL
        self.transition_to_state(PreemptionState.NORMAL, {
            'reason': 'preemption_completed'
        })
        
        print("✅ Đã hoàn thành xử lý ưu tiên, quay về chế độ thông thường")
    
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
            
            return {
                'total_preemption_activations': total_preemptions,
                'total_vehicles_served': len(self.served_vehicles),
                'average_processing_time': round(avg_processing_time, 2),
                'successful_preemptions': len(processing_times),
                'preemption_success_rate': (len(processing_times) / max(total_preemptions, 1)) * 100
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi tính thống kê ưu tiên: {e}")
            return {'error': str(e)}