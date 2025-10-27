"""
Module đếm xe hoạt động song song với SUMO
Sử dụng TraCI để lấy dữ liệu real-time về số lượng xe tại mỗi ngã tư theo hướng
"""

import traci
import time
import json
from collections import defaultdict
from typing import Dict, Set
import threading


class VehicleCounter:
    """
    Đếm số lượng xe tại các ngã tư theo từng hướng (Bắc, Nam, Đông, Tây)
    """
    
    def __init__(self, sumo_config: str):
        """
        Khởi tạo vehicle counter
        
        Args:
            sumo_config: Đường dẫn đến file .sumocfg
        """
        self.sumo_config = sumo_config
        self.running = False
        self.thread = None
        
        # Định nghĩa mapping giữa edge và hướng cho mỗi junction
        # Junction J1 tại tọa độ (0, 0)
        self.junction_edges = {
            "J1": {
                "Bắc": ["-E1"],  # Xe từ phía Bắc vào (routes r5-r9)
                "Nam": ["-E2"],  # Xe từ phía Nam vào (routes r10-r14)
                "Đông": ["E3"],  # Xe từ phía Đông vào
                "Tây": ["E0"],   # Xe từ phía Tây vào (routes r0-r4)
            },
            "J4": {
                "Bắc": ["-E4"],  # Xe từ phía Bắc vào
                "Nam": ["-E5"],  # Xe từ phía Nam vào
                "Đông": ["-E6"], # Xe từ phía Đông vào
                "Tây": ["-E3"],  # Xe từ phía Tây vào (từ J1)
            }
        }
        
        # Dictionary để tracking xe đã đếm (tránh đếm trùng)
        self.counted_vehicles: Dict[str, Dict[str, Set[str]]] = {
            "J1": {"Bắc": set(), "Nam": set(), "Đông": set(), "Tây": set()},
            "J4": {"Bắc": set(), "Nam": set(), "Đông": set(), "Tây": set()}
        }
        
        # Kết quả đếm hiện tại
        self.current_counts: Dict[str, Dict[str, int]] = {
            "J1": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0},
            "J4": {"Bắc": 0, "Nam": 0, "Đông": 0, "Tây": 0}
        }
        
        # Thời gian reset counter (giây)
        self.reset_interval = 60  # Reset mỗi 60 giây
        self.last_reset_time = time.time()
    
    def start_sumo(self):
        """Khởi động SUMO với TraCI"""
        try:
            traci.start(["sumo", "-c", self.sumo_config, "--start"])
            print(f"✅ Đã kết nối SUMO với file config: {self.sumo_config}")
            
            # Lấy danh sách edges thực tế từ SUMO
            self.discover_edges()
            return True
        except Exception as e:
            print(f"❌ Lỗi khi khởi động SUMO: {e}")
            return False
    
    def discover_edges(self):
        """Tự động phát hiện edges từ SUMO network"""
        try:
            # Lấy tất cả edges
            all_edges = traci.edge.getIDList()
            print(f"\n📋 Phát hiện {len(all_edges)} edges trong network")
            
            # Lọc ra edges không phải internal (không bắt đầu bằng ":")
            normal_edges = [e for e in all_edges if not e.startswith(":")]
            print(f"  ├─ Normal edges: {len(normal_edges)}")
            print(f"  └─ Danh sách: {normal_edges[:10]}...")  # In 10 edges đầu
            
            # Cập nhật junction_edges
            self.auto_assign_directions(normal_edges, "J1")
            self.auto_assign_directions(normal_edges, "J4")
            
        except Exception as e:
            print(f"⚠️ Không thể tự động phát hiện edges: {e}")
    
    def auto_assign_directions(self, edges: list, junction_id: str):
        """Tự động gán edges vào các hướng Bắc/Nam/Đông/Tây"""
        if junction_id == "J1":
            # Junction J1: Edges đi VÀO junction
            bac = [e for e in edges if e == "-E1"]  # Từ J2 xuống J1 (Bắc)
            nam = [e for e in edges if e == "-E2"]  # Từ J3 lên J1 (Nam)
            dong = [e for e in edges if e == "-E3"]  # Từ J4 sang J1 (Đông)
            tay = [e for e in edges if e == "E0"]   # Từ J0 sang J1 (Tây)
        
        elif junction_id == "J4":
            # Junction J4: Edges đi VÀO junction
            bac = [e for e in edges if e == "-E4"]  # Từ J5 xuống J4 (Bắc)
            nam = [e for e in edges if e == "-E5"]  # Từ J6 lên J4 (Nam)
            dong = [e for e in edges if e == "-E6"]  # Từ J7 sang J4 (Đông)
            tay = [e for e in edges if e == "E3"]   # Từ J1 sang J4 (Tây)
        
        else:
            bac = nam = dong = tay = []
        
        self.junction_edges[junction_id] = {
            "Bắc": bac,
            "Nam": nam,
            "Đông": dong,
            "Tây": tay
        }
        
        print(f"\n🧭 Gán hướng cho {junction_id}:")
        print(f"  ├─ Bắc:  {len(bac)} edges - {bac}")
        print(f"  ├─ Nam:  {len(nam)} edges - {nam}")
        print(f"  ├─ Đông: {len(dong)} edges - {dong}")
        print(f"  └─ Tây:  {len(tay)} edges - {tay}")
    
    def count_vehicles_on_edges(self):
        """Đếm xe HIỆN TẠI trên các edge (không tích lũy)"""
        # Reset về 0 trước khi đếm (snapshot hiện tại)
        for junction_id in self.current_counts:
            for direction in self.current_counts[junction_id]:
                self.current_counts[junction_id][direction] = 0
        
        # Đếm lại từ đầu
        for junction_id, directions in self.junction_edges.items():
            for direction, edges in directions.items():
                vehicle_count = 0
                for edge in edges:
                    try:
                        # Lấy danh sách xe HIỆN TẠI trên edge này
                        vehicles = traci.edge.getLastStepVehicleIDs(edge)
                        vehicle_count += len(vehicles)
                    
                    except Exception:
                        # Edge có thể không tồn tại hoặc chưa có xe - bỏ qua
                        pass
                
                # Cập nhật số đếm hiện tại (không tích lũy)
                self.current_counts[junction_id][direction] = vehicle_count
    
    def reset_counters(self):
        """Reset bộ đếm về 0"""
        current_time = time.time()
        if current_time - self.last_reset_time >= self.reset_interval:
            print(f"\n🔄 Reset counters sau {self.reset_interval} giây")
            
            # Reset tất cả counters
            for junction_id in self.counted_vehicles:
                for direction in self.counted_vehicles[junction_id]:
                    self.counted_vehicles[junction_id][direction].clear()
                    self.current_counts[junction_id][direction] = 0
            
            self.last_reset_time = current_time
    
    def get_current_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Lấy số liệu đếm hiện tại
        
        Returns:
            Dictionary với format: {"J1": {"Bắc": 10, "Nam": 15, ...}, "J4": {...}}
        """
        return self.current_counts.copy()
    
    def get_json_output(self) -> str:
        """
        Xuất kết quả dưới dạng JSON
        
        Returns:
            JSON string
        """
        return json.dumps(self.current_counts, ensure_ascii=False, indent=2)
    
    def run(self):
        """Chạy vòng lặp chính để đếm xe liên tục"""
        if not self.start_sumo():
            return
        
        self.running = True
        print("\n🚦 Bắt đầu đếm xe theo thời gian thực...")
        print("=" * 70)
        
        try:
            step = 0
            while self.running and traci.simulation.getMinExpectedNumber() > 0:
                # Thực hiện simulation step
                traci.simulationStep()
                step += 1
                
                # Đếm xe
                self.count_vehicles_on_edges()
                
                # Reset counters theo interval
                self.reset_counters()
                
                # In kết quả mỗi 5 giây (5 bước simulation)
                if step % 5 == 0:
                    self.print_current_stats(step)
        
        except KeyboardInterrupt:
            print("\n\n⏸️  Dừng đếm xe bởi người dùng")
        
        except Exception as e:
            print(f"\n❌ Lỗi trong quá trình đếm: {e}")
        
        finally:
            self.stop()
    
    def print_current_stats(self, step: int):
        """In thống kê hiện tại ra console"""
        print(f"\n📊 Bước {step} - Thống kê số xe:")
        print("-" * 70)
        
        for junction_id, counts in self.current_counts.items():
            print(f"\n🚦 Ngã tư {junction_id}:")
            total = sum(counts.values())
            print(f"   Tổng: {total} xe")
            print(f"   ├─ Bắc:  {counts['Bắc']:3d} xe")
            print(f"   ├─ Nam:  {counts['Nam']:3d} xe")
            print(f"   ├─ Đông: {counts['Đông']:3d} xe")
            print(f"   └─ Tây:  {counts['Tây']:3d} xe")
        
        print("\n📄 JSON Output:")
        print(self.get_json_output())
        print("-" * 70)
    
    def stop(self):
        """Dừng vehicle counter và đóng kết nối TraCI"""
        self.running = False
        try:
            traci.close()
            print("\n✅ Đã đóng kết nối SUMO")
        except:
            pass
    
    def start_async(self):
        """Chạy vehicle counter trong thread riêng"""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("🔄 Vehicle counter đang chạy trong background thread")


def main():
    """Hàm main để test module"""
    import sys
    import os
    
    # Đường dẫn đến file config
    config_path = os.path.join("data", "sumo", "test2.sumocfg")
    
    if not os.path.exists(config_path):
        print(f"❌ Không tìm thấy file config: {config_path}")
        sys.exit(1)
    
    # Tạo và chạy vehicle counter
    counter = VehicleCounter(config_path)
    
    try:
        counter.run()
    except KeyboardInterrupt:
        print("\n\n👋 Tạm biệt!")


if __name__ == "__main__":
    main()
