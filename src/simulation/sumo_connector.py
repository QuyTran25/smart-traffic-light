import traci
from sumolib import checkBinary
import sys
import os

def khoi_dong_sumo(config_path, gui=True):
    """Khởi động mô phỏng SUMO."""
    try:
        # Kiểm tra file cấu hình có tồn tại không
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Không tìm thấy file cấu hình: {config_path}")
        
        sumo_binary = checkBinary('sumo-gui' if gui else 'sumo')
        
        # Khởi động SUMO với các tham số bổ sung
        sumo_cmd = [
            sumo_binary, 
            "-c", config_path,
            "--waiting-time-memory", "10000",
            "--time-to-teleport", "300",
            "--no-step-log", "true"
        ]
        
        if not gui:
            sumo_cmd.extend(["--no-warnings", "true"])
        
        traci.start(sumo_cmd)
        print(f"✅ SUMO đã được khởi động với cấu hình: {config_path}")
        
        # Kiểm tra số lượng xe trong mô phỏng
        num_vehicles = traci.simulation.getMinExpectedNumber()
        print(f"📊 Số xe dự kiến trong mô phỏng: {num_vehicles}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi khởi động SUMO: {str(e)}")
        return False

def kiem_tra_mo_phong_con_chay():
    """Kiểm tra xem mô phỏng còn đang chạy hay không."""
    try:
        # Kiểm tra số xe hiện tại và số xe tối thiểu còn lại
        num_vehicles = traci.simulation.getMinExpectedNumber()
        current_time = traci.simulation.getTime()
        
        # Trả về True nếu còn xe hoặc thời gian chưa hết
        return num_vehicles > 0 or current_time < 3600
    except traci.exceptions.FatalTraCIError:
        return False
    except Exception:
        return False

def dung_sumo():
    """Dừng mô phỏng."""
    try:
        if traci.isLoaded():
            traci.close()
            print("🛑 Đã dừng mô phỏng SUMO.")
    except Exception as e:
        print(f"⚠️ Lỗi khi dừng SUMO: {str(e)}")

def lay_thong_tin_mo_phong():
    """Lấy thông tin hiện tại của mô phỏng."""
    try:
        current_time = traci.simulation.getTime()
        num_vehicles = traci.simulation.getMinExpectedNumber()
        departed_vehicles = traci.simulation.getDepartedNumber()
        arrived_vehicles = traci.simulation.getArrivedNumber()
        
        return {
            'thoi_gian': current_time,
            'so_xe_con_lai': num_vehicles,
            'xe_da_khoi_hanh': departed_vehicles,
            'xe_da_den': arrived_vehicles
        }
    except Exception as e:
        print(f"❌ Lỗi khi lấy thông tin mô phỏng: {str(e)}")
        return None
