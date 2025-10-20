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

# ==============================
# 🔹 Import AdaptiveController
# ==============================
from controllers.adaptive_controller import AdaptiveController


# ============================================================== #
# 🔸 HÀM CHẾ ĐỘ MẶC ĐỊNH (STATIC)
# ============================================================== #
def nhap_thoi_gian_den():
    """Nhập thời gian đèn từ terminal."""
    print("🚦 Thiết lập thời gian đèn giao thông (mặc định)")
    print("=" * 40)

    try:
        xanh_chung = int(input("🟢 Thời gian xanh chung (giây) [mặc định 70]: ") or 70)
        vang_chung = int(input("🟡 Thời gian vàng chung (giây) [mặc định 3]: ") or 3)
        do_toan_phan = int(input("🔴 Thời gian đỏ toàn phần (giây) [mặc định 3]: ") or 3)

        return {
            'xanh_chung': xanh_chung,
            'vang_chung': vang_chung,
            'do_toan_phan': do_toan_phan
        }
    except ValueError:
        print("❌ Vui lòng nhập số hợp lệ!")
        return nhap_thoi_gian_den()


def chay_mac_dinh(config_path):
    """Chạy mô phỏng SUMO theo chế độ mặc định (static)."""
    phase_durations = nhap_thoi_gian_den()

    print("\n🚀 Khởi động mô phỏng chế độ MẶC ĐỊNH...")
    if not khoi_dong_sumo(config_path, gui=True):
        print("❌ Không thể khởi động SUMO.")
        return

    try:
        den_ids = lay_danh_sach_den_giao_thong()
        print(f"📍 Đèn giao thông trong hệ thống: {den_ids}")

        # Áp dụng thời gian nhập vào
        dieu_chinh_tat_ca_den(phase_durations)

        step = 0
        max_steps = 1000
        print("▶️ Bắt đầu mô phỏng... (Nhấn Ctrl+C để dừng)")

        while step < max_steps:
            traci.simulationStep()

            if step % 10 == 0:
                thong_tin = lay_thong_tin_mo_phong()
                if thong_tin:
                    print(f"⏰ Bước {step}: Thời gian={thong_tin['thoi_gian']:.1f}s, "
                          f"Xe còn lại={thong_tin['so_xe_con_lai']}, Xe đã đến={thong_tin['xe_da_den']}")
            time.sleep(0.1)
            step += 1

    except KeyboardInterrupt:
        print("\n⏹️ Dừng mô phỏng.")
    finally:
        dung_sumo()


# ============================================================== #
# 🔸 HÀM CHẾ ĐỘ THÔNG MINH (ADAPTIVE)
# ============================================================== #
def chay_adaptive(config_path):
    """Chạy mô phỏng SUMO với thuật toán điều khiển thích ứng."""
    print("\n🤖 Khởi động chế độ THÔNG MINH (Adaptive)...")

    if not khoi_dong_sumo(config_path, gui=True):
        print("❌ Không thể khởi động SUMO.")
        return

    try:
        den_ids = lay_danh_sach_den_giao_thong()
        print(f"📍 Đèn giao thông trong hệ thống: {den_ids}")

        # Tạo controller cho từng đèn giao thông
        controllers = []
        for tls_id in den_ids:
            controller = AdaptiveController(junction_id=tls_id)
            controller.start()
            controllers.append(controller)

        step = 0
        max_steps = 1000
        print("▶️ Bắt đầu mô phỏng thông minh...")

        while step < max_steps:
            traci.simulationStep()

            for controller in controllers:
                controller.step()

            if step % 20 == 0:
                for controller in controllers:
                    status = controller.get_status()
                    print(f"📊 Adaptive Status [{step}]: {status}")

            time.sleep(0.1)
            step += 1

        print("✅ Hoàn thành mô phỏng thông minh!")

    except KeyboardInterrupt:
        print("\n⏹️ Dừng mô phỏng thông minh.")
    finally:
        dung_sumo()


# ============================================================== #
# 🔸 CHƯƠNG TRÌNH CHÍNH
# ============================================================== #
def main():
    print("🚦 HỆ THỐNG ĐÈN GIAO THÔNG THÔNG MINH")
    print("=" * 50)
    config_path = os.path.join('data', 'sumo', 'test2.sumocfg')

    while True:
        print("\nChọn chế độ:")
        print("1️⃣  Mặc định (Static)")
        print("2️⃣  Thông minh (Adaptive)")
        print("0️⃣  Thoát")

        choice = input("👉 Nhập lựa chọn (1/2/0): ").strip()

        if choice == "1":
            chay_mac_dinh(config_path)
        elif choice == "2":
            chay_adaptive(config_path)
        elif choice == "0":
            print("👋 Cảm ơn bạn đã sử dụng hệ thống!")
            break
        else:
            print("⚠️  Vui lòng nhập đúng lựa chọn (1/2/0)!")


if __name__ == "__main__":
    main()
