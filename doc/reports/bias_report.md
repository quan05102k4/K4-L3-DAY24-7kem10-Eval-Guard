# Đánh giá LLM Judge Phase B

Nhóm: 7kem10

Người phụ trách: Bùi Phương Duy - 2A202602684

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T16:31:04.542458+00:00.
Models generation/judge: generation `gpt-4o-mini-2024-07-18` (answer A từ pipeline);
judge `gpt-4o-mini` cho cả pairwise (`phase_b_judge.JUDGE_MODEL`) và binary
(`experiment_support.judge_binary`), temperature=0, `response_format=json_object`.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Pass 1 đưa (A, B), pass 2 đưa (B, A) với cùng question/reference; winner và scores pass 2
đã được quy về A/B gốc. Final = winner nếu hai lượt đồng ý, ngược lại là tie.

| ID | Candidate A (pipeline) | Candidate B (model_answer) | Pass 1 | Pass 2 (quy về gốc) | Final | Nhất quán | Scores pass 1 (A/B) | Scores pass 2 (A/B) | Reasoning tóm tắt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc khi kết hôn | Nghỉ 3 ngày làm việc có lương khi kết hôn | B | B | B | True | 0.8 / 1.0 | 0.5 / 1.0 | B nêu thêm "có lương", khớp reference hơn |
| 5 | "Tổn." | Cần Giám đốc phòng ban phê duyệt | B | A | tie | False | 0.0 / 0.5 | 0.5 / 0.0 | Cả hai sai (reference: CEO); judge thiên về answer đứng sau ở cả hai lượt |
| 12 | Thưởng Tết tối thiểu 1 tháng lương cho NV có từ 6 tháng | Thưởng Tết tối thiểu 1 tháng lương | A | tie | tie | False | 1.0 / 0.5 | 1.0 / 1.0 | Pass 1: A nêu điều kiện 6 tháng; pass 2: coi hai câu tương đương |
| 21 | Không tìm thấy | 18 ngày phép (15+3), lương Senior 20–35 triệu | B | B | B | True | 0.0 / 1.0 | 0.0 / 1.0 | B đúng cả hai vế; A không trả lời |
| 41 | 15 ngày phép năm có lương | 12 ngày phép năm | A | A | A | True | 1.0 / 0.0 | 1.0 / 0.0 | A đúng v2024; B dùng chính sách cũ v2023 |

Position bias count/rate: 2/5 = 0.40.
Verbosity win rate: 1.00 (3/3); decisive cases: 3 (A thắng 1: id 41; B thắng 2: id 1, 21).

Hai cặp không nhất quán có bản chất khác nhau:

- **ID 5**: pass 1 chọn B (đứng sau), pass 2 chọn ô B của lượt đảo, tức "Tổn." (A gốc,
  lúc này đứng sau). Cả hai lượt chọn **answer đứng sau** dù cả hai candidate đều sai
  (reference: >50 triệu cần CEO). Reasoning pass 2 còn tự mâu thuẫn ("B ít sai hơn" nhưng
  gán điểm cao cho answer vô nghĩa). Đây là dấu hiệu position/recency bias khi không
  candidate nào đúng, judge phải chọn giữa hai câu sai.
- **ID 12**: một lượt chọn A, lượt kia tie. Hai answer cùng đúng mức thưởng, A thêm điều
  kiện "từ 6 tháng" có trong reference. Bất đồng ở đây là ranh giới "đầy đủ hơn" so với
  "tương đương", thuộc dao động khi chấm cặp gần bằng nhau, không nhất thiết do vị trí.

Swap-and-average quy cả hai cặp về tie nên kết quả cuối không bị ảnh hưởng bởi thứ tự.

Verbosity rate 1.00 là **dấu hiệu thống kê**, không phải kết luận nguyên nhân. Đọc nội
dung thì cả 3 winner dài hơn đều đúng hoặc đầy đủ hơn theo reference: id 1 thêm "có lương"
(có trong reference), id 21 B trả lời đủ còn A từ chối, id 41 A đúng phiên bản v2024 còn B
dùng v2023. Không có case nào answer dài hơn thắng dù sai. Vì vậy mẫu này không đủ bằng
chứng về verbosity bias: độ dài và độ chính xác đang trùng nhau.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| question_id | model_answer gốc | Judge | Reasoning của judge (tóm tắt) | Human | Agree |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Chính xác theo reference | 1 | Có |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Sai: cần Tổng Giám đốc, không phải Giám đốc phòng ban | 0 | Có |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Chính xác, đủ ý theo reference | 1 | Có |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Đúng số ngày phép và khoảng lương | 1 | Có |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng lý do và số tiền hoàn trả | 1 | Có |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu phê duyệt Kế toán trưởng; cách tính phạt sai | 0 | Có |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Đúng số ngày phép và tổng phụ cấp | 1 | Có |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dùng chính sách cũ v2023 thay vì v2024 (15 ngày) | 0 | Có |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Đúng phủ định và điều kiện | 1 | Có |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Sai: chính sách cấm VPN cá nhân | 0 | Có |

Cohen’s κ: 1.000.
Observed/chance agreement và diễn giải: p_o = 10/10 = 1.00. Judge và human đều có
6 nhãn 1 và 4 nhãn 0, nên p_e = 0.6 × 0.6 + 0.4 × 0.4 = 0.52. κ = (1.00 − 0.52) / (1 − 0.52)
= 1.00, mức "almost perfect" theo Landis–Koch và vượt ngưỡng 0.6.

## Giới hạn và cách dùng judge

- Model/prompt: một model `gpt-4o-mini` chấm cả pairwise và binary, nên chưa kiểm tra
  được self-preference (answer A cũng do gpt-4o-mini sinh). Nên chạy thêm một judge khác
  họ model để so sánh.
- Kích thước mẫu: 5 cặp pairwise và 10 nhãn binary là quá nhỏ. κ = 1.0 trên 10 câu có
  khoảng tin cậy rộng, một nhãn lệch sẽ kéo κ xuống khoảng 0.78. Các câu trong bộ nhãn
  khá rõ ràng (sai phiên bản, sai người phê duyệt, cấm VPN cá nhân), chưa có ca mơ hồ.
- Không có case nào judge lệch với human trong lượt này. Case cần theo dõi là pairwise
  id 5, nơi judge phải chọn giữa hai answer sai và cho kết quả đổi theo vị trí, cùng
  reasoning pass 2 mâu thuẫn với winner.
- Cách kiểm chứng: giữ swap-and-average, coi bất đồng là tie; định kỳ lấy mẫu thêm nhãn
  người (≥30 câu có ca mơ hồ) để đo lại κ; đọc reasoning của các case tie và case score
  hai lượt chênh ≥0.5 (id 1: A 0.8 rồi 0.5; id 12: B 0.5 rồi 1.0).
- Judge chỉ là công cụ sàng lọc có hiệu chỉnh, **không phải đáp án tuyệt đối**. Quyết
  định release cần đối chiếu với nhãn người trên mẫu đủ lớn.
