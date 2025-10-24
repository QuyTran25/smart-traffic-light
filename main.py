# Entry point: chạy hệ thống
import sys
import os
import time

import subprocess

# Thêm đường dẫn src vào sys.path để import được modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import traci
from simulation.sumo_connector import (
    khoi_dong_sumo, dung_sumo, lay_thong_tin_mo_phong,
    lay_danh_sach_den_giao_thong, dieu_chinh_tat_ca_den,
    lay_thong_tin_den_giao_thong, dat_phase_den_giao_thong,
    tao_chuong_trinh_den
)

def mo_gui():
    """Mở giao diện GUI (dashboard.py) ở process riêng."""
    gui_path = os.path.join('src', 'gui', 'dashboard.py')
    try:
        subprocess.Popen([sys.executable, gui_path])
        print("🖥️ GUI đã được khởi động thành công!")
    except Exception as e:
        print(f"❌ Không thể mở GUI: {e}")

def chay_mo_phong():
    """Chạy mô phỏng SUMO với đèn giao thông thông minh."""
    # Đường dẫn đến file cấu hình SUMO
    config_path = os.path.join('data', 'sumo', 'test2.sumocfg')

    print("🚀 Khởi động hệ thống đèn giao thông thông minh...")

    # Khởi động SUMO với GUI
    if not khoi_dong_sumo(config_path, gui=True):
        print("❌ Không thể khởi động SUMO. Vui lòng kiểm tra cài đặt SUMO.")
        return

    try:
        # Lấy danh sách đèn giao thông
        den_ids = lay_danh_sach_den_giao_thong()
        print(f"📍 Đèn giao thông trong hệ thống: {den_ids}")

        # Thiết lập thời gian phase ban đầu cho tất cả đèn
        phase_durations = {
            0: 30,  # Phase 0: xanh cho Bắc-Nam (30 giây)
            1: 25   # Phase 1: xanh cho Đông-Tây (25 giây)
        }
        # Với static traffic lights, chúng ta sẽ để SUMO tự chuyển phase
        # nhưng có thể điều chỉnh duration qua hàm tao_chuong_trinh_den
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
    import sys
    
    print("=" * 70)
    print("🚦 HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH")
    print("=" * 70)
    print("\nChọn chế độ chạy:")
    print("1. 🖥️  Mở GUI Dashboard (Khuyến nghị)")
    print("2. 🔧 Chạy mô phỏng console (Không GUI)")
    print("3. ❌ Thoát")
    print("=" * 70)
    
    try:
        choice = input("\nNhập lựa chọn (1/2/3): ").strip()
        
        if choice == "1":
            print("\n🚀 Đang mở GUI Dashboard...")
            # Import trực tiếp và chạy GUI
            from src.gui.dashboard import SmartTrafficApp
            app = SmartTrafficApp()
            app.mainloop()
            
        elif choice == "2":
            print("\n🚀 Chạy mô phỏng console...")
            chay_mo_phong()
            
        elif choice == "3":
            print("\n👋 Tạm biệt!")
            sys.exit(0)
            
        else:
            print("\n❌ Lựa chọn không hợp lệ!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Tạm biệt!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        sys.exit(1)