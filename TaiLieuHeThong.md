HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG THÔNG MINH DỰA TRÊN MẬT ĐỘ XE
I.GIỚI THIỆU ĐỀ TÀI
Nói một cách đơn giản, chúng ta sẽ xây dựng một mô hình giả lập trên máy tính để chứng minh hai ý tưởng cốt lõi có hiệu quả:
•	Điều khiển đèn giao thông linh hoạt dựa trên mật độ xe thực tế.
•	Tự động ưu tiên cho xe khẩn cấp (cứu thương, cứu hỏa). 
•	Sản phẩm cuối cùng không phải là một hệ thống chạy ngoài đời thực mà là một bản mô phỏng (PoC) hoạt động trên phần mềm SUMO cùng với một giao diện điều khiển đơn giản.
II. CÁC CHỨC NĂNG CHÍNH 
Hệ thống của chúng ta cần thực hiện được 6 chức năng chính sau:
1.	Giả lập giao thông: Chạy một kịch bản giao thông ảo trên SUMO với các luồng xe và sự xuất hiện của xe ưu tiên.
2.	Phát hiện và Đếm xe: Tự động xác định số lượng xe đang chờ trên mỗi làn đường tiến vào giao lộ.
3.	Phát hiện xe ưu tiên: Nhận diện chính xác khi có xe ưu tiên xuất hiện trong khu vực. 
4.	Thuật toán điều khiển thông thường: Tự động tính toán và điều chỉnh thời gian đèn xanh dựa trên số lượng xe đang chờ.
5.	Thuật toán xử lý ưu tiên: Khi có xe ưu tiên, hệ thống phải ngay lập tức ghi đè lên thuật toán thường, dọn dẹp giao lộ và mở đường cho làn có xe ưu tiên.
6.	Giao diện giám sát (Dashboard): Một màn hình đơn giản để trực quan hóa trạng thái đèn, mật độ xe và các sự kiện ưu tiên.
III. PHẠM VI NGHIÊN CỨU 
Việc xác định rõ phạm vi giúp chúng ta tập trung và không bị sa đà vào các tính năng không cần thiết.

Trong phạm vi (In-Scope):
Xây dựng mô hình giả lập cho một ngã tư phức tạp hoặc một cụm 2 ngã tư gần nhau.
•	Phát triển các module phát hiện (đếm xe, xe ưu tiên) hoàn toàn bằng phần mềm dựa trên API của SUMO.
•	Xây dựng và kiểm thử hai thuật toán cốt lõi đã nêu ở trên.
•	Xây dựng một giao diện giám sát cơ bản trên máy tính.
Ngoài phạm vi (Out-of-Scope):
•	KHÔNG triển khai trên phần cứng vật lý (camera, cảm biến thật).
•	KHÔNG phát triển ứng dụng di động cho người dùng.
•	KHÔNG tích hợp vào hệ thống quản lý giao thông của thành phố.
•	KHÔNG xử lý các yếu tố phức tạp như người đi bộ, tai nạn, hay điều kiện thời tiết.
IV. HƯỚNG GIẢI QUYẾT KỸ THUẬT CỤ THỂ 
Đây là cách chúng ta sẽ triển khai từng phần trong phạm vi dự án:
1.Môi trường giả lập: 
Sử dụng bộ công cụ của SUMO. Dùng netedit để thiết kế bản đồ (.net.xml), và viết file kịch bản luồng xe (.rou.xml) để định nghĩa các dòng xe, trong đó có vType riêng cho xe ưu tiên.
2.Module Đếm xe: 
Sử dụng cảm biến vòng lặp cảm ứng (Induction Loop Detectors - E1) của SUMO. Chúng ta sẽ đặt các cảm biến ảo này trên các làn đường và dùng API TraCI trong script Python để đọc số lượng xe đi qua trong thời gian thực.
3.Module Phát hiện xe ưu tiên: 
Trong script Python, chúng ta sẽ liên tục quét các xe trong một bán kính nhất định quanh giao lộ. Dùng API TraCI để kiểm tra typeID của từng xe. Nếu typeID là "xe ưu tiên" (đã được định nghĩa ở bước 1), module sẽ kích hoạt tín hiệu khẩn cấp.

4. Thuật toán điều khiển thông thường: 
Áp dụng thuật toán "Điều khiển thích ứng dựa trên trọng số hàng chờ".
Logic: Tính "điểm áp lực" cho mỗi hướng đi dựa trên số xe đang chờ. Hướng nào có điểm cao hơn sẽ được ưu tiên đèn xanh.
•	Thời gian xanh: Sẽ được tính linh hoạt dựa trên chính điểm áp lực đó (ví dụ: Thời gian xanh = 10s (tối thiểu) + 0.5s * số xe).
•	Đảm bảo chuyển màu phù hợp để không có một đường nào đợt quá lâu mà không được đii.
5. Thuật toán xử lý ưu tiên: 
Xây dựng một máy trạng thái (State Machine) ghi đè lên thuật toán thường.
•	Trạng thái 1 - Phát hiện: Kích hoạt khi có xe ưu tiên.
•	Trạng thái 2 - Chuyển tiếp an toàn: Bật đèn vàng cho các luồng đang xanh, sau đó bật "tất cả đỏ" trong 1-2 giây để dọn dẹp giao lộ.
•	Trạng thái 3 - Mở đường: Bật đèn xanh cho luồng có xe ưu tiên.
•	Trạng thái 4 - Trở lại bình thường: Khi xe đã đi qua, hệ thống quay về thuật toán điều khiển thông thường.
6. Giao diện giám sát: 
Sử dụng một thư viện GUI của Python như PyQt5 hoặc Tkinter để xây dựng một ứng dụng desktop đơn giản, hiển thị dữ liệu được cập nhật liên tục từ script điều khiển chính.
A. KPI CHO THUẬT TOÁN ĐIỀU KHIỂN THÔNG THƯỜNG (ADAPTIVE CONTROL)
Tất cả các chỉ số (KPI) đều đo bằng dữ liệu mô phỏng trong SUMO qua TraCI.
Mỗi kịch bản nên chạy nhiều lần (ít nhất 30 lần, với random seed khác nhau) để kết quả có độ tin cậy.
1.Thời gian trễ trung bình Average Delay (s/xe) 
	Định nghĩa: Thời gian một xe phải chờ thêm để đi qua nút giao so với trường hợp không phải dừng lại.
	Công thức: Delay = Thời gian thực tế qua giao lộ − Thời gian lý tưởng (free-flow).
	Hiểu đơn giản: Có thể coi đây chính là thời gian chờ đèn đỏ trung bình (kèm thêm chút thời gian do xe phải dừng rồi khởi động lại).
	Cách đo trong SUMO: dùng TraCI để lấy thời gian di chuyển (travelTime) của từng xe, rồi trừ đi freeFlowTime.
	Mục tiêu: giảm ít nhất 20% so với hệ thống đèn cố định, đặc biệt trong giờ cao điểm.
	Ý nghĩa với giao thông Việt Nam: giảm thời gian chờ giúp xe máy, xe con bớt ùn tắc và di chuyển mượt hơn. 
2. Chiều dài hàng chờ trung bình Average Queue Length (xe hoặc PCU)
	Định nghĩa: Số xe trung bình đang chờ tại mỗi làn trong khoảng thời gian.
	Cách đo: đọc detector/induction loop trả về queue length hoặc đếm xe đứng yên trong vùng chờ.
	Mục tiêu: giảm ít nhất 25% so với hệ thống đèn cố định.
	Lưu ý Việt Nam: nên quy đổi xe thành đơn vị PCU để phản ánh thực tế:
	1 ô tô = 1.0 PCU
	1 xe máy = 0.3 PCU
	1 xe bus/truck = 1.5 PCU
3.Lưu lượng thông qua Throughput (xe / giờ hoặc PCU/h)
	Định nghĩa: Số xe (hoặc PCU) qua giao lộ trong 1 giờ.
	Mục tiêu: tăng ít nhất 5% hoặc giữ ổn định trong khi vẫn giảm delay.
4. Số lần dừng trung bình mỗi xe Average Number of Stops per Vehicle
	Định nghĩa: Trung bình mỗi xe phải dừng bao nhiêu lần khi đi qua giao lộ.
	Mục tiêu: giảm ≥ 15%.
	Giải thích: Có những tình huống xe có thể phải dừng nhiều lần, ví dụ:
	Xe vừa được bật đèn xanh nhưng phía trước ùn tắc khiến xe không kịp qua giao lộ → xe phải dừng thêm 1 cái đèn đỏ nữa mới kịp đii tiếp rồi đi tiếp.
	Giao lộ có nhiều pha (rẽ trái, thẳng, phải) → nếu pha ngắn, một số xe bị “kẹt lại” và phải dừng thêm 1 lần nữa.
5.Thời gian chờ tối đa Maximum Waiting Time (s)
	Định nghĩa: Thời gian lâu nhất mà một xe bất kỳ phải chờ.
	Giới hạn an toàn (target): 
	Chấp nhận được < 120s (2 phút) trong điều kiện cực, 
	Tốt nhất < 60s. 
	Nếu vượt giới hạn này → thuật toán phải kích hoạt cơ chế tránh “bỏ đói” (starvation prevention).
6.Chu kì đèn và độ ổn định Cycle Length & Variability
	Định nghĩa: Độ dài trung bình của một chu kỳ đèn và mức độ biến động của nó.
	Mục tiêu: chu kỳ đèn ổn định, tránh biến động quá lớn (±30%).
7.Mức độ công bằng Fairness Index
	Định nghĩa: So sánh giữa thời gian chờ lớn nhất và trung bình. Chỉ số thấp nghĩa là công bằng hơn.
	Mục tiêu: không để một hướng nào phải chờ quá lâu so với các hướng khác..
8.Thời gian xử lý xe ưu tiên Emergency Vehicle Clearance Time (khi test ưu tiên)
	Định nghĩa: Thời gian từ khi phát hiện xe ưu tiên đến khi xe đầu tiên trong đoàn đi qua giao lộ.
	Mục tiêu: ≤ 15s (mục tiêu tốt), ≤ 25s chấp nhận được. (tùy kịch bản và khoảng cách phát hiện)

9.KPI TỔNG HỢP CHO BÁO CÁO
	Nếu KPI là cảng nhỏ càng tốt (delay, queue, stops, waiting time) dùng công thức sau:
% Cải thiện = ((Giá trị truyền thống- Giá trị thông minh)/Giá trị tuyền thống) x 100%
	Nếu KPI là cảng lớn càng tốt (throughput) dùng công thức sau:
% Cải thiện = ((Giá trị thông minh- Giá trị truyền thống)/Giá trị tuyền thống ) x 100%
	Ví dụ với 1 KPI cụ thể: Average Delay
	Kịch bản điều khiển truyền thống (fixed-time): trung bình delay = 60 giây/xe
	Kịch bản điều khiển thông minh (adaptive): trung bình delay = 42 giây/xe
	Áp công thức:
%"Cải thiện"=(60-42)/60×100%=30%

=> Nghĩa là hệ thống thông minh giúp giảm 30% thời gian chờ so với truyền thống.
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
TÓM LẠI CẦN TÍNH TOÁN VÀ NHẬN BIẾT NHỮNG ĐIỀU SAU
1. Cần tính toán gì?
8 KPI chính (Delay, Queue, Throughput, Stops, Max Waiting, Cycle Length, Fairness, Emergency Clearance Time).
% cải thiện KPI (so adaptive so với fixed-time).
ETA (Estimated Time of Arrival) cho xe ưu tiên:
ETA=("Khoảng c" "a"  ˊ"ch đ" "e"  ˆ  ˊ"n giao lộ" )/("Vận t" "o"  ˆ  ˊ"c hiện tại" )

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
Tóm gọn:
	Tính toán: KPI, % cải thiện, ETA, thời gian xanh động, All-Red.
	Nhận diện: mật độ xe, xe ưu tiên, báo giả, tình huống đặc biệt, trạng thái hệ thống.
	Thành công cần: mô phỏng chuẩn + thuật toán adaptive & preemption chi tiết + log/KPI đánh giá + cơ chế khôi phục.
