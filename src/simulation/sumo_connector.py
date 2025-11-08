# -*- coding: utf-8 -*-
import traci
from sumolib import checkBinary
import sys
import os

def khoi_dong_sumo(config_path, gui=True):
    """Khởi động mô phỏng SUMO."""
    try:
        # Kiểm tra file cấu hình có tồn tại không
        if not os.path.exists(config_path):
            print(f"[ERROR] Khong tim thay file cau hinh: {config_path}")
            return False
        
        sumo_binary = checkBinary('sumo-gui' if gui else 'sumo')
        
        # Khởi động SUMO với các tham số bổ sung
        sumo_cmd = [
            sumo_binary, 
            "-c", config_path,
            "--waiting-time-memory", "10000",
            "--time-to-teleport", "300",
            "--no-step-log", "true",
            "--start", "true"  # Auto-start simulation
        ]
        
        if not gui:
            sumo_cmd.extend(["--no-warnings", "true"])
        
        traci.start(sumo_cmd)
        print(f"[OK] SUMO da duoc khoi dong voi cau hinh: {config_path}")
        
        # Kiểm tra số lượng xe trong mô phỏng
        num_vehicles = traci.simulation.getMinExpectedNumber()
        print(f"[INFO] So xe du kien trong mo phong: {num_vehicles}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Loi khi khoi dong SUMO: {str(e)}")
        import traceback
        traceback.print_exc()
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
            print("[STOP] Da dung mo phong SUMO.")
    except Exception as e:
        print(f"[WARNING] Loi khi dung SUMO: {str(e)}")

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
        print(f"[ERROR] Loi khi lay thong tin mo phong: {str(e)}")
        return None

def lay_thong_tin_den_giao_thong(tls_id):
    """Lấy thông tin hiện tại của đèn giao thông."""
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return None
        
        current_phase = traci.trafficlight.getPhase(tls_id)
        phase_duration = traci.trafficlight.getPhaseDuration(tls_id)
        next_switch = traci.trafficlight.getNextSwitch(tls_id)
        
        return {
            'phase_hien_tai': current_phase,
            'thoi_gian_phase': phase_duration,
            'thoi_gian_chuyen_tiep': next_switch
        }
    except Exception as e:
        print(f"[ERROR] Loi khi lay thong tin den giao thong: {str(e)}")
        return None

def dat_phase_den_giao_thong(tls_id, phase_index):
    """Đặt phase cho đèn giao thông."""
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return False
        
        traci.trafficlight.setPhase(tls_id, phase_index)
        print(f"[OK] Da dat phase {phase_index} cho den giao thong {tls_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Loi khi dat phase: {str(e)}")
        return False

def dat_thoi_gian_phase(tls_id, phase_index, duration):
    """Đặt thời gian cho một phase cụ thể của đèn giao thông."""
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return False
        
        traci.trafficlight.setPhaseDuration(tls_id, phase_index, duration)
        print(f"[OK] Da dat thoi gian {duration}s cho phase {phase_index} cua den {tls_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Loi khi dat thoi gian phase: {str(e)}")
        return False

def dieu_chinh_den_giao_thong(tls_id, phase_durations):
    """
    Điều chỉnh thời gian các phase của đèn giao thông bằng cách tạo chương trình mới.
    
    Args:
        tls_id: ID của traffic light system
        phase_durations: Dict với key là phase_index, value là duration (giây)
    """
    return tao_chuong_trinh_den(tls_id, phase_durations)

def lay_danh_sach_den_giao_thong():
    """Lấy danh sách tất cả đèn giao thông trong mô phỏng."""
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return []
        
        tls_ids = traci.trafficlight.getIDList()
        print(f"[INFO] Tim thay {len(tls_ids)} den giao thong: {tls_ids}")
        return tls_ids
    except Exception as e:
        print(f"[ERROR] Loi khi lay danh sach den giao thong: {str(e)}")
        return []

def dieu_chinh_nhieu_den(tls_ids, phase_durations):
    """
    Điều chỉnh thời gian các phase cho nhiều đèn giao thông.
    
    Args:
        tls_ids: List các ID của traffic light systems
        phase_durations: Dict với key là phase_index, value là duration (giây)
    """
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return False
        
        for tls_id in tls_ids:
            print(f"[INFO] Dang dieu chinh den {tls_id}...")
            if not tao_chuong_trinh_den(tls_id, phase_durations):
                return False
        
        print(f"[OK] Hoan thanh dieu chinh {len(tls_ids)} den giao thong")
        return True
    except Exception as e:
        print(f"[ERROR] Loi khi dieu chinh nhieu den giao thong: {str(e)}")
        return False

def dieu_chinh_tat_ca_den(phase_durations):
    """
    Điều chỉnh thời gian các phase cho tất cả đèn giao thông trong mô phỏng.
    
    Args:
        phase_durations: Dict với format:
            - Nếu có key 'xanh_chung', 'vang_chung', 'do_toan_phan': fixed-time mode
            - Nếu có key số (0, 1, ...): adaptive mode
    """
    tls_ids = lay_danh_sach_den_giao_thong()
    if not tls_ids:
        return False
    
    # Kiểm tra format của phase_durations
    if 'xanh_chung' in phase_durations:
        # Fixed-time mode: tạo chương trình mới với thời gian cố định
        return tao_chuong_trinh_fixed_time(tls_ids, phase_durations)
    else:
        # Adaptive mode (legacy)
        return dieu_chinh_nhieu_den(tls_ids, phase_durations)

def tao_chuong_trinh_fixed_time(tls_ids, phase_durations):
    """
    Tạo chương trình đèn giao thông fixed-time với thời gian tùy chỉnh.
    
    Args:
        tls_ids: List các ID của traffic light systems
        phase_durations: Dict với keys:
            - 'xanh_chung': thời gian xanh (giây)
            - 'vang_chung': thời gian vàng (giây)
            - 'do_toan_phan': thời gian all-red (giây)
    """
    try:
        if not traci.isLoaded():
            print("[WARNING] SUMO chua duoc khoi dong.")
            return False
        
        green_time = phase_durations.get('xanh_chung', 30)
        yellow_time = phase_durations.get('vang_chung', 3)
        all_red_time = phase_durations.get('do_toan_phan', 2)
        
        print(f"\n[SETUP] Tao chuong trinh Fixed-Time:")
        print(f"   - Xanh: {green_time}s")
        print(f"   - Vang: {yellow_time}s")
        print(f"   - All-Red: {all_red_time}s")
        
        success_count = 0
        
        for tls_id in tls_ids:
            try:
                # Lấy logic hiện tại
                all_logics = traci.trafficlight.getAllProgramLogics(tls_id)
                
                if not all_logics:
                    print(f"⚠️ {tls_id} không có program logic, bỏ qua")
                    continue
                
                # Sử dụng logic đầu tiên (thường là program "0")
                current_logic = all_logics[0]
                
                # Cấu trúc phases chuẩn cho ngã tư 4 hướng:
                # Phase 0: NS Green (Bắc-Nam xanh, Đông-Tây đỏ)
                # Phase 1: NS Yellow (Bắc-Nam vàng)
                # Phase 2: All Red
                # Phase 3: EW Green (Đông-Tây xanh, Bắc-Nam đỏ)
                # Phase 4: EW Yellow (Đông-Tây vàng)
                # Phase 5: All Red
                
                if len(current_logic.phases) >= 6:
                    # Tạo copy của logic để sửa đổi
                    import copy
                    new_logic = copy.deepcopy(current_logic)
                    
                    # Cập nhật duration cho từng phase
                    new_logic.phases[0].duration = green_time     # NS Green
                    new_logic.phases[1].duration = yellow_time    # NS Yellow
                    new_logic.phases[2].duration = all_red_time   # All Red
                    new_logic.phases[3].duration = green_time     # EW Green
                    new_logic.phases[4].duration = yellow_time    # EW Yellow
                    new_logic.phases[5].duration = all_red_time   # All Red
                    
                    # Đặt program ID về "0" (mặc định)
                    new_logic.programID = "0"
                    
                    # Áp dụng logic mới
                    traci.trafficlight.setProgram(tls_id, "0")
                    traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, new_logic)
                    
                    # Đặt phase về 0 để bắt đầu lại chu kỳ
                    traci.trafficlight.setPhase(tls_id, 0)
                    
                    print(f"[OK] {tls_id}: Da cap nhat Fixed-Time (Chu ky: {(green_time + yellow_time + all_red_time) * 2}s)")
                    success_count += 1
                    
                else:
                    print(f"[WARNING] {tls_id} chi co {len(current_logic.phases)} phases (can it nhat 6), bo qua")
                    
            except Exception as e:
                print(f"[ERROR] Loi khi cap nhat {tls_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if success_count > 0:
            print(f"[OK] Hoan thanh: {success_count}/{len(tls_ids)} den giao thong da chuyen sang Fixed-Time\n")
            return True
        else:
            print(f"[ERROR] Khong the cau hinh Fixed-Time cho bat ky den nao\n")
            return False
        
    except Exception as e:
        print(f"[ERROR] Loi khi tao chuong trinh Fixed-Time: {e}")
        import traceback
        traceback.print_exc()
        return False

def tao_chuong_trinh_den(tls_id, phase_durations):
    """
    Tạo chương trình đèn giao thông mới với thời gian phase tùy chỉnh.
    
    Args:
        tls_id: ID của traffic light system
        phase_durations: Dict với key là phase_index, value là duration (giây)
                         0: phase xanh Bắc-Nam, 1: phase xanh Đông-Tây
    """
    try:
        if not traci.isLoaded():
            print("⚠️ SUMO chưa được khởi động.")
            return False
        
        # Lấy logic hiện tại
        current_logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
        
        # Mapping phase chính: 0->0 (Bắc-Nam), 1->3 (Đông-Tây)
        phase_mapping = {0: 0, 1: 3}
        
        # Sao chép và sửa đổi duration chỉ cho phase chính
        for logical_phase, actual_phase in phase_mapping.items():
            if logical_phase in phase_durations:
                current_logic.phases[actual_phase].duration = phase_durations[logical_phase]
                print(f"[INFO] Phase chinh {logical_phase} (actual {actual_phase}): duration = {phase_durations[logical_phase]}s")
        
        # Đặt lại logic đã sửa
        traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, current_logic)
        print(f"[OK] Da cap nhat chuong trinh cho den {tls_id}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Loi khi tao chuong trinh den: {str(e)}")
        return False
