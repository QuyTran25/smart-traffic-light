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
        self.T_MIN_GREEN = 10.0    # Thời gian xanh tối thiểu (giây)
        self.T_MAX_GREEN = 120.0   # Thời gian xanh tối đa (giây) 
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
            TrafficDirection.NORTH: ["-E1_0", "-E1_1", "-E1_2"],  # Từ J2 → J1
            TrafficDirection.SOUTH: ["-E2_0", "-E2_1", "-E2_2"],  # Từ J3 → J1  
            TrafficDirection.EAST: ["-E3_0", "-E3_1", "-E3_2"],   # Từ J4 → J1
            TrafficDirection.WEST: ["E0_0", "E0_1", "E0_2"]       # Từ J0 → J1
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
        
        Công thức: G = T_min + α × Queue_length(PCU)
        
        Args:
            direction: Hướng cần tính thời gian xanh
            
        Returns:
            Thời gian xanh (giây, float)
        """
        queue_pcu = self.convert_to_pcu(direction)
        green_time = self.T_MIN_GREEN + (self.ALPHA * queue_pcu)
        
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
        
        # Đảm bảo đã đủ thời gian xanh tối thiểu
        if phase_duration < self.T_MIN_GREEN:
            return False, None
            
        priorities = self.get_direction_priorities()
        
        # Tính áp lực tổng cho từng nhóm pha
        ns_pressure = priorities[TrafficDirection.NORTH] + priorities[TrafficDirection.SOUTH]
        ew_pressure = priorities[TrafficDirection.EAST] + priorities[TrafficDirection.WEST]
        
        # Logic chuyển pha
        if self.current_phase == TrafficPhase.NS_GREEN:
            # Hiện tại Bắc-Nam đang xanh
            if ew_pressure > ns_pressure * 1.2:  # Ngưỡng chuyển pha 20%
                return True, TrafficPhase.NS_YELLOW
            elif phase_duration >= self.T_MAX_GREEN:  # Đã đạt thời gian tối đa
                return True, TrafficPhase.NS_YELLOW
                
        elif self.current_phase == TrafficPhase.EW_GREEN:
            # Hiện tại Đông-Tây đang xanh
            if ns_pressure > ew_pressure * 1.2:  # Ngưỡng chuyển pha 20%
                return True, TrafficPhase.EW_YELLOW
            elif phase_duration >= self.T_MAX_GREEN:  # Đã đạt thời gian tối đa
                return True, TrafficPhase.EW_YELLOW
                
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