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
        # Nhập thời gian cho phase Bắc-Nam
        bac_nam = int(input("⏱️  Nhập thời gian xanh cho hướng Bắc-Nam (giây) [mặc định 70]: ") or 30)
        print("Thời gian đèn vàng là 5s vui lòng trừ hao thời gian đèn.")
        
        # Nhập thời gian cho phase Đông-Tây
        dong_tay = int(input("⏱️  Nhập thời gian xanh cho hướng Đông-Tây (giây) [mặc định 65]: ") or 25)
        
        # Validate input
        if bac_nam <= 0 or dong_tay <= 0:
            print("❌ Thời gian phải lớn hơn 0!")
            return nhap_thoi_gian_den()
        
        if bac_nam > 120 or dong_tay > 120:
            print("⚠️  Cảnh báo: Thời gian quá dài (>120s) có thể gây ùn tắc!")
        
        phase_durations = {
            0: bac_nam,   # Phase Bắc-Nam
            1: dong_tay   # Phase Đông-Tây
        }
        
        print(f"✅ Đã thiết lập: Bắc-Nam {bac_nam}s, Đông-Tây {dong_tay}s")
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