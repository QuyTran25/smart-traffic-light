"""
Test script cho vehicle counter module
Chạy script này để test việc đếm xe real-time từ SUMO
"""

import sys
import os

# Thêm thư mục src vào Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from simulation.vehicle_counter import VehicleCounter


def main():
    """Chạy test vehicle counter"""
    print("=" * 70)
    print("🚗 TEST MODULE ĐẾM XE SONG SONG VỚI SUMO")
    print("=" * 70)
    print("\nModule này sẽ:")
    print("  ✓ Khởi động SUMO simulation")
    print("  ✓ Đếm xe theo thời gian thực tại 2 ngã tư (J1, J4)")
    print("  ✓ Phân loại theo 4 hướng: Bắc, Nam, Đông, Tây")
    print("  ✓ Xuất kết quả JSON mỗi 5 giây")
    print("  ✓ Reset bộ đếm mỗi 60 giây")
    print("\nNhấn Ctrl+C để dừng...\n")
    
    # Đường dẫn đến file config
    config_path = os.path.join("data", "sumo", "test2.sumocfg")
    
    if not os.path.exists(config_path):
        print(f"❌ Không tìm thấy file config: {config_path}")
        return
    
    # Tạo vehicle counter
    counter = VehicleCounter(config_path)
    
    # Chạy counter
    try:
        counter.run()
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng test!")
    
    # In thống kê cuối cùng
    print("\n" + "=" * 70)
    print("📊 THỐNG KÊ CUỐI CÙNG")
    print("=" * 70)
    print(counter.get_json_output())
    print("\n✅ Test hoàn tất!")


if __name__ == "__main__":
    main()
