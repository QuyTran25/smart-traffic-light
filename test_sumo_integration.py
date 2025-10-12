#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script kiểm tra tích hợp SUMO - Chỉ test mở SUMO
"""

import os
import sys

# Thêm thư mục src vào Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from simulation.sumo_connector import khoi_dong_sumo, dung_sumo
import time

def test_sumo():
    """Test khởi động SUMO với file config test2"""
    print("=" * 60)
    print("🚦 KIỂM TRA TÍCH HỢP SUMO")
    print("=" * 60)
    
    # Đường dẫn đến file config
    config_path = os.path.join(
        os.path.dirname(__file__), 
        'sumo', 
        'test2.sumocfg'
    )
    
    print(f"\n📁 File config: {config_path}")
    print(f"📁 File tồn tại: {os.path.exists(config_path)}")
    
    if not os.path.exists(config_path):
        print("❌ File config không tồn tại!")
        return False
    
    print("\n🚀 Đang khởi động SUMO GUI...")
    print("⏳ Vui lòng chờ cửa sổ SUMO mở lên...")
    
    # Khởi động SUMO với GUI
    success = khoi_dong_sumo(config_path, gui=True)
    
    if success:
        print("\n✅ SUMO đã được khởi động thành công!")
        print("📌 Cửa sổ SUMO GUI sẽ mở ra.")
        print("📌 Nhấn Ctrl+C ở terminal này để dừng mô phỏng.")
        print("\n⏯️  Đang chạy mô phỏng...")
        
        try:
            # Giữ chương trình chạy
            import traci
            step = 0
            while step < 100:  # Chạy 100 bước test
                traci.simulationStep()
                step += 1
                if step % 10 == 0:
                    print(f"   Bước {step}/100 - Thời gian mô phỏng: {traci.simulation.getTime()}s")
            
            print("\n✅ Test hoàn tất! SUMO đã tích hợp thành công vào hệ thống.")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Người dùng dừng mô phỏng.")
        finally:
            print("\n🛑 Đang dừng SUMO...")
            dung_sumo()
            print("✅ Đã dừng SUMO.")
        
        return True
    else:
        print("\n❌ Không thể khởi động SUMO!")
        print("💡 Kiểm tra:")
        print("   - SUMO đã được cài đặt chưa?")
        print("   - File test2.net.xml và test2.rou.xml có trong thư mục sumo/ chưa?")
        return False

if __name__ == "__main__":
    try:
        test_sumo()
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()
