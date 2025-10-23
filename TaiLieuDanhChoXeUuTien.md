B. KỊCH BẢN ƯU TIÊN 
Tên SC	Mô tả (Tình huống)	Kỳ vọng	Hướng giải quyết chi tiết
SC1 — Xe ưu tiên từ hướng chính trong giờ cao điểm	Lưu lượng N–S rất đông, E–W ít. Xe cứu thương đến từ hướng Bắc, cách giao lộ 300–500 m.	Hệ thống nhận diện sớm và chuyển tín hiệu ưu tiên ≤ 15 giây để tạo luồng xanh cho xe đi qua.	- Camera/cảm biến phát hiện xe ưu tiên.
 - Nếu pha N–S đang xanh: giữ xanh đủ min_green (10s) rồi mở rộng thêm để xe đi qua an toàn. 
- Nếu N–S đang đỏ: rút ngắn pha hiện tại, chèn all-red ngắn (2–3s), bật xanh cho N–S. 
- Sau khi xe qua → quay lại adaptive (điều chỉnh thông minh).
SC2 — Xe ưu tiên từ hướng nhánh (ít xe) sắp tới gần	Hướng chính đang xanh, xe cứu thương từ hướng phụ sắp đến, ETA ≤ 12 giây.
(ETA là thời gian dự kiến đến giao lộ)	Nếu còn đủ thời gian thì nhanh chóng chuyển pha; nếu chưa đạt min_green (10s) thì phải chờ hết.	- Kiểm tra thời gian xanh còn lại của hướng chính. 
- Nếu ≥ min_green: chuyển pha → vàng → đỏ toàn bộ → xanh cho hướng ưu tiên. 
- Nếu < min_green: giữ đủ min_green rồi mới chuyển.
 - Đảm bảo an toàn cho dòng xe chính.
SC3 — Nhiều xe ưu tiên từ 2 hướng đối diện	Có 2 xe cứu thương cùng đến (ví dụ Bắc và Đông).	So sánh ETA → ưu tiên xe đến trước. 
Nếu cùng lúc: ưu tiên xe gần hơn, còn lại chờ. Nếu xung đột thì cho đi tuần tự với pha all-red.	- Hệ thống tính ETA từng xe. 
- Nếu ETA khác biệt rõ: mở pha xanh cho xe đến trước. 
- Nếu ETA gần bằng nhau: chọn hướng xe gần hơn. 
- Nếu không thể tránh xung đột: áp dụng all-red 2–3s rồi cho lần lượt từng hướng.
SC4 — Báo giả (False positive)	Hệ thống nhầm báo có xe ưu tiên nhưng thực tế không có.	Yêu cầu xác nhận nhanh; nếu sai, quay lại bình thường và ghi log.	- Dùng xác nhận kép (2 khung hình liên tiếp trong 1s hoặc nhiều sensor). 
- Nếu phát hiện báo giả trước khi đổi pha → hủy ưu tiên. 
- Nếu đã bật ưu tiên mà phát hiện báo giả → log lỗi, phục hồi điều khiển adaptive ngay.
SC5 — Xe ưu tiên bị kẹt trong dòng xe dài	Xe cứu thương xuất hiện nhưng bị chắn bởi hàng xe máy dài phía trước.	Trước khi bật xanh, phải dọn đường; nếu không giải tỏa được thì báo lỗi/chuyển dự phòng.	- Trước tiên bật all-red ngắn để “clear” ngã tư. 
- Sau đó mở xanh cho hướng xe ưu tiên, kết hợp mở upstream (pha trước đó) để giải tỏa hàng xe máy. 
- Nếu sau thời gian tối đa (ví dụ 30s) mà vẫn kẹt → báo lỗi và chuyển về fixed cycle an toàn.
SC6 — Nhiều xe ưu tiên liên tiếp	Vừa cho xe cứu thương đi qua, 20s sau lại có xe khác.	Vẫn phải cho ưu tiên nhưng có cơ chế giới hạn, đảm bảo không phá vỡ giao thông còn lại.	- Nếu xe ưu tiên thứ hai đến sớm (<30s sau xe trước): vẫn cấp ưu tiên nhưng log để áp dụng chiến lược khôi phục sau. - Khi hết luồng ưu tiên → hệ thống bù green cho các hướng bị dồn backlog. 
- Nếu có quá nhiều xe ưu tiên liên tục → chuyển sang emergency mode (ưu tiên liên tục nhưng phải điều phối khôi phục mạnh sau).

	ETA của một xe = khoảng thời gian từ lúc xe được phát hiện (cách giao lộ X mét) cho đến lúc nó tới vạch dừng/ngã tư (nếu đi với vận tốc hiện tại).
	Công thức đơn giản:
ETA=("Khoảng c" "a"  ˊ"ch đ" "e"  ˆ  ˊ"n giao lộ" )/("Vận t" "o"  ˆ  ˊ"c hiện tại" )

C. CÁCH CHUYỂN ĐÈN — STATE MACHINE CHI TIẾT & THAM SỐ ĐỀ XUẤT (PHÙ HỢP VN)
1) Các trạng thái (priority state machine)
	NORMAL: Chế độ điều khiển thông minh (adaptive) dựa trên mật độ xe.
	DETECTION: Phát hiện xe ưu tiên (cứu thương, cứu hỏa), tính toán thời gian dự kiến đến (ETA), xác nhận để tránh báo sai.
	SAFE_TRANSITION: Chuyển pha an toàn → từ xanh hiện tại sang vàng → đỏ toàn bộ (all-red) để dọn nút giao.
	PREEMPTION_GREEN: Bật đèn xanh cho hướng xe ưu tiên, có thể mở thêm các hướng không xung đột.
	HOLD_PREEMPTION: Giữ xanh thêm nếu còn nhiều xe ưu tiên phía sau hoặc xe bị kẹt trong hàng dài.
	RESTORE: Xe ưu tiên qua hết → quay lại chế độ NORMAL (adaptive). Có thể có bước cân bằng lại các chu kỳ để hệ thống không bị lệch.


2) Tham số thời gian gợi ý 
	Tmin_green = 10 giây → xanh tối thiểu cho một pha.
	Tmax_green = 120 giây → xanh tối đa cho một pha.
	alpha = 0.5 giây/PCU → hệ số tính thêm thời gian xanh theo mật độ xe (1 xe máy = 0.3 PCU, 1 ô tô = 1 PCU).
	yellow_duration = 3 giây → thời gian vàng (phổ biến ở VN).
	all_red_base = 2–3 giây → đỏ toàn bộ để dọn giao lộ.
	safe_min_green_before_preempt = 4 giây → nếu pha hiện tại mới xanh < 4s thì chờ đủ rồi mới cắt sang ưu tiên.
	detection_confirmation_window = 1 giây (2 lần đọc liên tiếp) → tránh báo sai.
	preempt_min_green = 8 giây → xanh tối thiểu cho xe ưu tiên.
	max_back_to_back_preempt = 2 trong 60 giây → giới hạn số lần ưu tiên liên tiếp để không làm loạn hệ thống.
3) Công thức tính All-Red (khuyến nghị động, an toàn)
R=W/v+"buffer" 
	W: bề rộng giao lộ (m)
	v: vận tốc xe trung bình (m/s)
	buffer: khoảng đệm an toàn (1–2 giây)
=> Ý nghĩa: vừa tính toán theo giao lộ, vừa cộng thêm thời gian đệm cho chắc chắn.
Giả sử:
	Giao lộ rộng W=20m
	Vận tốc xe v=10m/s(≈ 36 km/h)
	Buffer = 2s
Áp dụng công thức 3:
R=20/10+2=4" gi" "a"  ˆ"y"

=> Vậy cần 4 giây đỏ toàn bộ trước khi cho hướng khác xanh.
4) Luồng chuyển khi có xe ưu tiên
	Nếu phát hiện xe ưu tiên → kiểm tra nó đi hướng nào.
	Nếu đang xanh → kéo dài xanh.
	Nếu chưa xanh → tính ETA:
	Nếu ETA còn xa (≥30s) → đặt lịch ưu tiên sau.
	Nếu ETA gần (≤12s) → lập tức chuẩn bị chuyển pha an toàn (vàng → đỏ → xanh cho xe ưu tiên).
	Sau khi xe qua → trở về chế độ adaptive bình thường.
1. Cần tính toán gì?
ETA (Estimated Time of Arrival) cho xe ưu tiên:
ETA=(Khoảng cách đến giao lộ )/(Vận tốc hiện tại)

Điểm áp lực (Pressure) cho mỗi hướng:
P=α×"Queue(PCU)"

Thời gian xanh (Green time) động:
G=Tmin+α×"Queue(PCU)"

Thời gian All-Red (R) để dọn giao lộ:
R=W/v+"buffer"

(W: bề rộng giao lộ, v: vận tốc xe, buffer: 1–2s an toàn).
2. Cần nhận diện gì?
	Mật độ xe/queue ở từng hướng (dùng induction loop trong SUMO).
	Xe ưu tiên (ambulance, fire truck) bằng typeID trong SUMO.
	Báo giả (false positive) → cần xác nhận kép (≥2 lần trong 1s).
	Tình huống đặc biệt: xe ưu tiên bị kẹt, nhiều xe ưu tiên liên tiếp, nhiều hướng xung đột.
	Trạng thái hệ thống:
NORMAL (adaptive bình thường).
DETECTION (phát hiện ưu tiên).
SAFE_TRANSITION (vàng + all-red).
PREEMPTION_GREEN (bật xanh cho xe ưu tiên).
HOLD_PREEMPTION (giữ xanh thêm nếu cần).
RESTORE (khôi phục lại adaptive).
3. Muốn thành công thì cần gì?
	Mô phỏng SUMO chuẩn (map, luồng xe, vType xe ưu tiên).
	Thuật toán adaptive hợp lý (tính queue, phân bổ green time).
	Thuật toán preemption an toàn (state machine rõ ràng, có tham số min_green, max_green, all_red…).
	Xác nhận ưu tiên chính xác (tránh báo giả).
	Ghi log đầy đủ để tính KPI và đánh giá.
	Chạy nhiều lần với random seed để có kết quả Mean ± 95% CI.
	Chiến lược khôi phục sau khi ưu tiên để tránh làm loạn giao thông.
	Dashboard trực quan để quan sát (GUI).
	Giới hạn ưu tiên liên tiếp (max_back_to_back_preempt) để hệ thống không rối.
