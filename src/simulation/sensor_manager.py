"""
Sensor Manager - Quản lý và đọc dữ liệu từ cảm biến SUMO

Module này đọc dữ liệu từ:
- E1 Detectors (Induction Loops): Đếm xe, đo tốc độ tức thời
- E2 Detectors (Area Detectors): Đo mật độ, queue length, occupancy

Sử dụng cho hệ thống điều khiển đèn giao thông thông minh dựa trên mật độ xe.
"""

import traci
from typing import Dict, List, Tuple


class SensorManager:
    """Quản lý cảm biến E1 và E2 trong SUMO"""
    
    def __init__(self):
        """Khởi tạo Sensor Manager"""
        self.e1_detectors = {}  # {detector_id: {lane, position, junction}}
        self.e2_detectors = {}  # {detector_id: {lane, position, junction}}
        
        # Mapping detector IDs theo junction và hướng
        self.detector_mapping = {
            "J1": {
                "north": {"e1": ["e1_J1_north_0", "e1_J1_north_1", "e1_J1_north_2"],
                         "e2": ["e2_J1_north", "e2_J1_north_lane1", "e2_J1_north_lane2"]},
                "south": {"e1": ["e1_J1_south_0", "e1_J1_south_1", "e1_J1_south_2"],
                         "e2": ["e2_J1_south", "e2_J1_south_lane1", "e2_J1_south_lane2"]},
                "west":  {"e1": ["e1_J1_west_0", "e1_J1_west_1", "e1_J1_west_2"],
                         "e2": ["e2_J1_west", "e2_J1_west_lane1", "e2_J1_west_lane2"]},
                "east":  {"e1": ["e1_J1_east_0", "e1_J1_east_1"],
                         "e2": ["e2_J1_east", "e2_J1_east_lane1"]},
            },
            "J4": {
                "north": {"e1": ["e1_J4_north_0", "e1_J4_north_1", "e1_J4_north_2"],
                         "e2": ["e2_J4_north", "e2_J4_north_lane1", "e2_J4_north_lane2"]},
                "south": {"e1": ["e1_J4_south_0", "e1_J4_south_1", "e1_J4_south_2"],
                         "e2": ["e2_J4_south", "e2_J4_south_lane1", "e2_J4_south_lane2"]},
                "west":  {"e1": ["e1_J4_west_0", "e1_J4_west_1", "e1_J4_west_2"],
                         "e2": ["e2_J4_west", "e2_J4_west_lane1", "e2_J4_west_lane2"]},
                "east":  {"e1": ["e1_J4_east_0", "e1_J4_east_1"],
                         "e2": ["e2_J4_east", "e2_J4_east_lane1"]},
            }
        }
    
    def discover_detectors(self) -> Tuple[int, int]:
        """
        Tự động phát hiện tất cả E1 và E2 detectors trong SUMO
        
        Returns:
            Tuple[int, int]: (số E1 detectors, số E2 detectors)
        """
        try:
            # Lấy danh sách E1 detectors (Induction Loops)
            e1_ids = traci.inductionloop.getIDList()
            for det_id in e1_ids:
                lane = traci.inductionloop.getLaneID(det_id)
                pos = traci.inductionloop.getPosition(det_id)
                self.e1_detectors[det_id] = {
                    "lane": lane,
                    "position": pos,
                    "junction": "J1" if "J1" in det_id else "J4"
                }
            
            # Lấy danh sách E2 detectors (Lane Area Detectors)
            e2_ids = traci.lanearea.getIDList()
            for det_id in e2_ids:
                lane = traci.lanearea.getLaneID(det_id)
                self.e2_detectors[det_id] = {
                    "lane": lane,
                    "junction": "J1" if "J1" in det_id else "J4"
                }
            
            return len(self.e1_detectors), len(self.e2_detectors)
            
        except Exception as e:
            print(f"⚠ Lỗi khi phát hiện detectors: {e}")
            return 0, 0
    
    def get_e1_data(self, detector_id: str) -> Dict:
        """
        Lấy dữ liệu từ E1 detector (Induction Loop)
        
        Args:
            detector_id: ID của detector
            
        Returns:
            Dict chứa: vehicle_count, speed, occupancy, last_step_count
        """
        try:
            return {
                "vehicle_count": traci.inductionloop.getLastStepVehicleNumber(detector_id),
                "speed": traci.inductionloop.getLastStepMeanSpeed(detector_id),
                "occupancy": traci.inductionloop.getLastStepOccupancy(detector_id),
                "last_step_count": traci.inductionloop.getLastStepVehicleNumber(detector_id),
                "vehicle_ids": traci.inductionloop.getLastStepVehicleIDs(detector_id)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_e2_data(self, detector_id: str) -> Dict:
        """
        Lấy dữ liệu từ E2 detector (Area Detector)
        
        Args:
            detector_id: ID của detector
            
        Returns:
            Dict chứa: vehicle_count, speed, occupancy, jam_length, max_jam_length
        """
        try:
            return {
                "vehicle_count": traci.lanearea.getLastStepVehicleNumber(detector_id),
                "halting_number": traci.lanearea.getLastStepHaltingNumber(detector_id),
                "speed": traci.lanearea.getLastStepMeanSpeed(detector_id),
                "occupancy": traci.lanearea.getLastStepOccupancy(detector_id),
                "jam_length": traci.lanearea.getJamLengthMeters(detector_id),
                "jam_length_vehicle": traci.lanearea.getJamLengthVehicle(detector_id),
                "vehicle_ids": traci.lanearea.getLastStepVehicleIDs(detector_id)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_junction_density(self, junction_id: str, direction: str) -> Dict:
        """
        Tính toán mật độ xe tại một hướng của ngã tư
        
        Args:
            junction_id: "J1" hoặc "J4"
            direction: "north", "south", "east", "west"
            
        Returns:
            Dict chứa: total_vehicles, avg_speed, queue_length, density_pcu
        """
        if junction_id not in self.detector_mapping:
            return {"error": "Invalid junction"}
        if direction not in self.detector_mapping[junction_id]:
            return {"error": "Invalid direction"}
        
        # Lấy E2 detectors cho hướng này
        e2_list = self.detector_mapping[junction_id][direction]["e2"]
        
        total_vehicles = 0
        total_speed = 0
        total_jam_length = 0
        speed_count = 0
        
        for det_id in e2_list:
            data = self.get_e2_data(det_id)
            if "error" not in data:
                total_vehicles += data["vehicle_count"]
                if data["speed"] > 0:
                    total_speed += data["speed"]
                    speed_count += 1
                total_jam_length += data["jam_length"]
        
        avg_speed = total_speed / speed_count if speed_count > 0 else 0
        
        # Tính density theo PCU (Passenger Car Unit)
        # Giả sử: 1 xe máy = 0.3 PCU, 1 ô tô = 1 PCU, 1 bus = 2 PCU
        density_pcu = total_vehicles  # Simplified - có thể cải thiện bằng cách check vehicle type
        
        return {
            "total_vehicles": total_vehicles,
            "avg_speed": round(avg_speed, 2),
            "queue_length": round(total_jam_length, 2),
            "density_pcu": density_pcu,
            "junction": junction_id,
            "direction": direction
        }
    
    def get_all_junction_densities(self, junction_id: str) -> Dict:
        """
        Lấy mật độ xe của TẤT CẢ hướng tại một ngã tư
        
        Args:
            junction_id: "J1" hoặc "J4"
            
        Returns:
            Dict với keys: north, south, east, west
        """
        directions = ["north", "south", "east", "west"]
        result = {}
        
        for direction in directions:
            result[direction] = self.get_junction_density(junction_id, direction)
        
        return result
    
    def detect_emergency_vehicles(self, junction_id: str) -> List[Dict]:
        """
        Phát hiện xe ưu tiên từ tất cả cảm biến của một ngã tư
        
        Args:
            junction_id: "J1" hoặc "J4"
            
        Returns:
            List các xe ưu tiên detected với thông tin: vehicle_id, direction, distance
        """
        emergency_vehicles = []
        
        if junction_id not in self.detector_mapping:
            return emergency_vehicles
        
        for direction, detectors in self.detector_mapping[junction_id].items():
            # Check E2 detectors (xa hơn)
            for det_id in detectors["e2"]:
                data = self.get_e2_data(det_id)
                if "error" not in data and "vehicle_ids" in data:
                    for veh_id in data["vehicle_ids"]:
                        try:
                            veh_type = traci.vehicle.getTypeID(veh_id)
                            if "priority" in veh_type.lower():
                                emergency_vehicles.append({
                                    "vehicle_id": veh_id,
                                    "direction": direction,
                                    "detector": det_id,
                                    "detector_type": "E2",
                                    "junction": junction_id
                                })
                        except:
                            pass
        
        return emergency_vehicles
    
    def get_summary(self) -> Dict:
        """
        Lấy tóm tắt trạng thái tất cả cảm biến
        
        Returns:
            Dict chứa thông tin tổng quan
        """
        return {
            "e1_count": len(self.e1_detectors),
            "e2_count": len(self.e2_detectors),
            "junctions": list(self.detector_mapping.keys()),
            "status": "active" if len(self.e1_detectors) > 0 else "inactive"
        }


# Example usage
if __name__ == "__main__":
    print("SensorManager module - Quản lý cảm biến SUMO")
    print("Sử dụng trong hệ thống điều khiển đèn giao thông dựa trên mật độ xe")
