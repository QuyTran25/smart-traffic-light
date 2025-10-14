# Smart Traffic Light System

Hệ thống đèn giao thông thông minh sử dụng mô phỏng SUMO (Simulation of Urban MObility).

## Yêu cầu hệ thống

### 1. Cài đặt SUMO
SUMO phải được cài đặt riêng biệt. Tải về từ: https://sumo.dlr.de/docs/Installing/index.html

Sau khi cài đặt, đảm bảo biến môi trường SUMO_HOME được thiết lập và thư mục bin của SUMO có trong PATH.

### 2. Cài đặt dependencies Python
```bash
pip install -r requirements.txt
```

## Cách chạy

### Chạy mô phỏng với thời gian tùy chỉnh
```bash
python main.py
```

Chương trình sẽ:
1. **Hỏi thời gian đèn**: Nhập thời gian xanh cho 2 hướng (Bắc-Nam và Đông-Tây)
2. **Khởi động SUMO GUI**: Mở cửa sổ đồ họa hiển thị bản đồ giao thông
3. **Thiết lập đèn**: Tự động áp dụng thời gian đã nhập
4. **Chạy mô phỏng**: Hiển thị tiến trình và thông tin xe
5. **Cho phép chạy lại**: Sau khi dừng, có thể nhập thời gian mới và chạy lại

### Ví dụ sử dụng:
```
🚦 Thiết lập thời gian đèn giao thông
========================================
⏱️  Nhập thời gian xanh cho hướng Bắc-Nam (giây) [mặc định 70]: 45
⏱️  Nhập thời gian xanh cho hướng Đông-Tây (giây) [mặc định 65]: 40
✅ Đã thiết lập: Bắc-Nam 45s, Đông-Tây 40s
```

### Dừng mô phỏng
- Nhấn `Ctrl+C` trong terminal để dừng mô phỏng
- Chương trình sẽ hỏi có muốn chạy lại với thời gian mới không

## Cấu trúc dự án

```
smart-traffic-light/
├── main.py                 # Điểm vào chính
├── requirements.txt        # Dependencies Python
├── setup.py               # Setup script (tùy chọn)
├── src/
│   ├── simulation/
│   │   ├── sumo_connector.py    # Kết nối và điều khiển SUMO
│   │   └── vehicle_counter.py   # Đếm xe tại ngã tư
│   ├── controllers/             # Bộ điều khiển đèn
│   ├── gui/                     # Giao diện người dùng
│   └── utils/                   # Tiện ích
├── data/sumo/              # Dữ liệu SUMO
├── test/                   # Unit tests
└── docs/                   # Tài liệu
```

## Các module chính

### SUMO Connector (`src/simulation/sumo_connector.py`)
- Khởi động/dừng mô phỏng SUMO
- Điều khiển đèn giao thông (đặt phase, thời gian)
- Lấy thông tin mô phỏng

### Vehicle Counter (`src/simulation/vehicle_counter.py`)
- Đếm số lượng xe theo hướng tại các ngã tư
- Theo dõi xe đã đếm để tránh trùng lặp

## Phát triển thêm

- Implement các bộ điều khiển thông minh (adaptive, priority)
- Phát triển giao diện GUI
- Thêm thuật toán tối ưu hóa đèn giao thông
- Tích hợp machine learning cho dự đoán lưu lượng

## License

MIT License