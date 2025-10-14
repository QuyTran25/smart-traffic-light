# Entry point: chạy hệ thống
import sys
import os
import time

# Thêm đường dẫn src vào sys.path để import được modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import traci
from simulation.sumo_connector import (
    khoi_dong_sumo, dung_sumo, lay_thong_tin_mo_phong,
    lay_danh_sach_den_giao_thong, dieu_chinh_tat_ca_den,
    lay_thong_tin_den_giao_thong, dat_phase_den_giao_thong,
    tao_chuong_trinh_den
)

def nhap_thoi_gian_den():
    """Nhập thời gian đèn từ terminal."""
    print("🚦 Thiết lập thời gian đèn giao thông")
    print("=" * 40)
    
    try:
        # Nhập thời gian xanh chung cho cả 4 hướng
        xanh_chung = int(input("⏱️  Nhập thời gian xanh chung cho cả 4 hướng (giây) [mặc định 70]: ") or 70)
        
        # Nhập thời gian vàng chung cho cả 4 hướng
        vang_chung = int(input("⏱️  Nhập thời gian vàng chung cho cả 4 hướng (giây) [mặc định 3]: ") or 3)
        
        # Nhập thời gian đỏ toàn phần
        do_toan_phan = int(input("⏱️  Nhập thời gian đỏ toàn phần (giây) [mặc định 3]: ") or 3)
        
        # Validate input
        if any(t < 0 for t in [xanh_chung, vang_chung, do_toan_phan]):
            print("❌ Thời gian phải lớn hơn hoặc bằng 0!")
            return nhap_thoi_gian_den()
        
        if xanh_chung > 120:
            print("⚠️  Cảnh báo: Thời gian xanh quá dài (>120s)!")
        
        if vang_chung > 30:
            print("⚠️  Cảnh báo: Thời gian vàng quá dài (>30s)!")
        
        phase_durations = {
            'xanh_chung': xanh_chung,        # Thời gian xanh chung cho cả 2 hướng
            'vang_chung': vang_chung,        # Thời gian vàng chung cho cả 2 hướng
            'do_toan_phan': do_toan_phan     # Thời gian đỏ toàn phần
        }
        
        print(f"✅ Đã thiết lập:")
        print(f"   Xanh chung: {xanh_chung}s")
        print(f"   Vàng chung: {vang_chung}s")
        print(f"   Đỏ toàn phần: {do_toan_phan}s")
        return phase_durations
        
    except ValueError:
        print("❌ Vui lòng nhập số nguyên hợp lệ!")
        return nhap_thoi_gian_den()

def chay_mo_phong():
    """Chạy mô phỏng SUMO với đèn giao thông thông minh."""
    # Nhập thời gian từ terminal
    phase_durations = nhap_thoi_gian_den()
    
    # Đường dẫn đến file cấu hình SUMO
    config_path = os.path.join('data', 'sumo', 'test2.sumocfg')

    print("\n🚀 Khởi động hệ thống đèn giao thông thông minh...")

    # Khởi động SUMO với GUI
    if not khoi_dong_sumo(config_path, gui=True):
        print("❌ Không thể khởi động SUMO. Vui lòng kiểm tra cài đặt SUMO.")
        return

    try:
        # Lấy danh sách đèn giao thông
        den_ids = lay_danh_sach_den_giao_thong()
        print(f"📍 Đèn giao thông trong hệ thống: {den_ids}")

        # Thiết lập thời gian phase từ input
        print(f"✅ Sử dụng static traffic lights với duration tùy chỉnh qua hàm")
        dieu_chinh_tat_ca_den(phase_durations)

        # Lấy thông tin phase hiện tại
        for tls_id in den_ids:
            info = lay_thong_tin_den_giao_thong(tls_id)
            if info:
                print(f"📍 Đèn {tls_id}: Phase hiện tại = {info['phase_hien_tai']}, Thời gian = {info['thoi_gian_phase']}s")

        # Chạy mô phỏng
        step = 0
        max_steps = 1000  # Chạy tối đa 1000 bước (có thể điều chỉnh)

        print("▶️ Bắt đầu mô phỏng... (Nhấn Ctrl+C để dừng)")
        print("💡 Mẹo: Sau khi dừng (Ctrl+C), bạn có thể chạy lại với thời gian mới!")

        while step < max_steps:
            # Tiến hành một bước mô phỏng
            traci.simulationStep()

            # Hiển thị thông tin mỗi 10 bước
            if step % 10 == 0:
                thong_tin = lay_thong_tin_mo_phong()
                if thong_tin:
                    print(f"⏰ Bước {step}: Thời gian={thong_tin['thoi_gian']:.1f}s, "
                          f"Xe còn lại={thong_tin['so_xe_con_lai']}, "
                          f"Xe đã đến={thong_tin['xe_da_den']}")

            # Tạm dừng một chút để xem animation
            time.sleep(0.1)

            step += 1

        print("✅ Hoàn thành mô phỏng!")

    except KeyboardInterrupt:
        print("\n⏹️ Mô phỏng bị dừng bởi người dùng.")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình mô phỏng: {str(e)}")
    finally:
        # Đảm bảo dừng SUMO
        dung_sumo()

if __name__ == "__main__":
    print("🚦 HỆ THỐNG ĐÈN GIAO THÔNG THÔNG MINH")
    print("=" * 50)
    
    while True:
        try:
            chay_mo_phong()
            
            # Hỏi xem có muốn chạy lại không
            try:
                chay_lai = input("\n❓ Muốn chạy lại với thời gian mới không? (y/n) [n]: ").lower().strip()
                if chay_lai != 'y' and chay_lai != 'yes':
                    print("👋 Cảm ơn đã sử dụng hệ thống!")
                    break
                print("\n" + "="*50)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Cảm ơn đã sử dụng hệ thống!")
                break
                
        except KeyboardInterrupt:
            print("\n👋 Đã dừng chương trình!")
            break
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")
            break