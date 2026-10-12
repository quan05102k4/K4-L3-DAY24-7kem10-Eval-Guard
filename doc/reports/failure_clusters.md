# Phân tích lỗi Phase A

Nhóm: 7kem10

Người phụ trách: Ngô Văn Giáp - 2A202602644

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T16:41:00.816481+00:00.
Generation mode/fallback và điều kiện chạy: cả 50 answers ở mode `llm`, không có
extractive fallback. Pipeline gồm m1 hierarchical chunking (128 child chunks từ 25 file
Markdown và `so_tay_an_toan.pdf`; `BCTC.pdf` và Nghị định 13/2023 là PDF scan không có
text layer nên bị bỏ qua), m5 enrichment (contextual prepend bằng gpt-4o-mini), m2 hybrid
BM25 + BGE-M3 trên Qdrant v1.9.7 với RRF, m3 rerank `BAAI/bge-reranker-v2-m3` lấy top-3.
Models generation/evaluator: generation `gpt-4o-mini-2024-07-18`; evaluator do m4 trả về
`gpt-4o-mini` (LLM) và `text-embedding-3-small` (embedding cho answer_relevancy).

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.883 | 0.458 | 0.600 |
| answer_relevancy | 0.490 | 0.392 | 0.347 |
| context_precision | 0.967 | 0.921 | 0.983 |
| context_recall | 0.900 | 0.846 | 0.683 |
| avg_score | 0.810 | 0.654 | 0.653 |

Mean toàn bộ 50 câu: avg_score 0.716, faithfulness 0.656, answer_relevancy 0.422,
context_precision 0.952, context_recall 0.835. Retrieval (precision/recall) tốt hơn hẳn
generation (faithfulness/relevancy): vấn đề chính nằm ở bước sinh câu trả lời.

## Bottom 10 và nguyên nhân

Diagnosis/suggested_fix dưới đây là output Task 3 (`bottom_10`) được exporter giữ nguyên,
rút gọn cho bảng; bản đầy đủ có trong JSON. F/AR/CP/CR = faithfulness / answer_relevancy /
context_precision / context_recall.

| Rank | ID | Question | Distribution | avg_score | worst_metric | Diagnosis | Suggested fix |
|---|---|---|---|---|---|---|---|
| 1 | 39 | So sánh mật khẩu v1.0 và v2.0 (độ dài, thời hạn đổi, MFA) | multi_hop | 0.125 | faithfulness | Generation từ chối "Không tìm thấy" dù contexts chứa phần v1 và MFA v2 (F=0, AR=0, CP=0, CR=0.50) | Cho phép tổng hợp từ nhiều context; trả parent chunk/tăng top_k để có đủ hai phiên bản |
| 2 | 5 | Mua thiết bị 55 triệu cần ai phê duyệt | factual | 0.340 | faithfulness | Answer bị cụt thành "Tổn." dù context có bảng thẩm quyền (F=0, AR=0.36, CP=1.00, CR=0) | Kiểm tra finish_reason, retry khi answer quá ngắn, đặt temperature=0 |
| 3 | 21 | Senior 9 năm thâm niên: số ngày phép và khung lương | multi_hop | 0.375 | faithfulness | Từ chối dù có context thâm niên v2024 (F=0, AR=0, CP=1.00, CR=0.50) | Cho phép tính 15 + 9÷3; tăng top_k để lấy thêm bảng lương |
| 4 | 33 | Manager 12 năm: tổng phụ cấp và phép năm v2024 | multi_hop | 0.375 | faithfulness | Từ chối dù có phép năm v2024 và khung lương (F=0, AR=0, CP=1.00, CR=0.50) | Cho phép tổng hợp/tính; thiếu chunk phụ cấp nên cần tăng top_k |
| 5 | 43 | Mật khẩu tối thiểu bao nhiêu ký tự | adversarial | 0.417 | faithfulness | Từ chối khi gặp cả 12 ký tự (v2.0) và 8 ký tự (v1.0) (F=0, AR=0, CP=1.00, CR=0.67) | Gắn version/effective date; prompt chọn bản đang hiệu lực |
| 6 | 42 | Thâm niên bao nhiêu năm thì cộng ngày phép | adversarial | 0.417 | faithfulness | Từ chối khi gặp 3 năm (v2024) và 5 năm (v2023) (F=0, AR=0, CP=1.00, CR=0.67) | Như trên: ưu tiên bản v2024 qua metadata |
| 7 | 50 | Manager dùng NordVPN khi WFH được không | adversarial | 0.417 | faithfulness | Từ chối dù context top-1 ghi "Không sử dụng VPN cá nhân (NordVPN, ExpressVPN)" (F=0, AR=0, CP=1.00, CR=0.67) | Prompt phải trả lời phủ định khi policy cấm, không im lặng |
| 8 | 44 | Bao lâu phải đổi mật khẩu | adversarial | 0.458 | faithfulness | Từ chối khi gặp 120 ngày (v2.0) và 90 ngày (v1.0) (F=0, AR=0, CP=0.83, CR=1.00) | Ưu tiên bản hiện hành qua metadata |
| 9 | 9 | Nam nhân viên nghỉ mấy ngày khi vợ sinh con | factual | 0.500 | faithfulness | Từ chối dù context chứa đáp án (F=0, AR=0, CP=1.00, CR=1.00) | Nới điều kiện "Không tìm thấy" trong prompt generation |
| 10 | 25 | Lương thử việc Junior mức cao nhất | multi_hop | 0.500 | faithfulness | Từ chối dù có 85% và khung lương (F=0, AR=0, CP=1.00, CR=1.00) | Cho phép tính 85% × 20 triệu từ hai context |

Đối chiếu answer/contexts/reference của từng câu cho thấy **9/10 câu bottom có answer
"Không tìm thấy."** trong khi context_recall từ 0.50 đến 1.00. Ví dụ câu 9: context top-1
là mục "Các trường hợp được nghỉ phép đặc biệt" chứa dòng "Sinh con (nam giới): 5 ngày làm việc" (CR=1.00,
CP=1.00) nhưng answer vẫn từ chối. Câu 25: hai context nói "85% lương" và bảng khung lương
Junior 12–20 triệu đều đã được lấy (CR=1.00), chỉ thiếu bước tính 85% × 20 triệu. Như vậy
nguyên nhân là **generation từ chối nhầm** do system prompt của `setup_answers.py`
("Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'") khiến model không
dám suy luận/tính toán, chứ không phải hallucination như cây chẩn đoán mặc định gợi ý.
RAGAS chấm faithfulness = 0 vì answer từ chối không có khẳng định nào được hỗ trợ, và
answer_relevancy = 0 vì câu từ chối bị coi là noncommittal.

Câu 5 là lỗi generation khác: answer chỉ còn "Tổn." (có thể là "Tổng Giám đốc" bị cắt).
Context top-1 là bảng thẩm quyền phê duyệt của `mua_sam.md`, nên retrieval không phải
nguyên nhân. RAGAS chấm CR=0 cho câu này dù CP=1.00. Đây là dấu hiệu evaluator không
nhận ra hàng ">50 triệu → CEO" trong bảng Markdown, cần kiểm tra tay.

Có thêm một lỗi đo nằm ngoài bottom 10: câu 24, 31 và 38 (multi_hop) trả lời **đúng**
theo reference (phạt 50.000 VNĐ; 2.400.000 VNĐ; 600 USD) nhưng faithfulness = 0. Các
khẳng định là kết quả tính toán (2% × 15 triệu × 5/30) nên NLI của RAGAS không thấy
nguyên văn trong context. Faithfulness vì vậy đánh giá thấp các câu suy luận số học.

## Matrix và nhóm yếu nhất

Matrix đếm worst_metric của **mọi** câu (tổng cột = 20/20/10 là kích thước nhóm, không
phải số câu lỗi):

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---|---|---|---|
| faithfulness | 2 | 10 | 4 | 16 |
| answer_relevancy | 17 | 10 | 4 | 31 |
| context_precision | 0 | 0 | 0 | 0 |
| context_recall | 1 | 0 | 2 | 3 |

Nhóm yếu theo mean thấp nhất: adversarial; mean: 0.6533 (multi_hop 0.6539, factual 0.8100).
Worst metric xuất hiện nhiều nhất: answer_relevancy; số câu: 31.

Adversarial và multi_hop gần như bằng nhau (chênh 0.0006). Với 10 câu adversarial và
evaluator LLM có dao động giữa các lượt chạy (lượt chạy trước của nhóm cho multi_hop
0.647 < adversarial 0.653), không nên kết luận chắc chắn nhóm nào yếu hơn. Điều chắc
chắn là cả hai đều thấp hơn factual khoảng 0.16. Lý do khác nhau:

- multi_hop: 4/20 câu từ chối nhầm và 10/20 câu có worst_metric là faithfulness. Câu cần
  ghép 2–3 điều khoản hoặc tính toán, prompt "CHỈ dựa trên context" làm model từ chối,
  còn câu có tính toán đúng lại bị RAGAS chấm faithfulness thấp.
- adversarial: 4/10 câu từ chối khi context chứa **cả hai phiên bản** chính sách
  (42, 43, 44) hoặc khi cần trả lời phủ định (50). context_recall thấp nhất (0.683) vì
  reference yêu cầu nêu cả bản cũ lẫn bản mới.

answer_relevancy là worst_metric của 31 câu, kể cả 17/20 câu factual đã trả lời đúng.
Trên 41 câu không từ chối, mean answer_relevancy chỉ 0.514 trong khi faithfulness 0.80.
RAGAS sinh câu hỏi ngược từ answer rồi so embedding với câu hỏi gốc. Với answer tiếng
Việt ngắn có định dạng Markdown (`**200.000.000 VNĐ/năm**`) và `text-embedding-3-small`,
độ tương đồng thấp dù answer đúng. Metric này cần được hiệu chỉnh với nhãn người trước
khi dùng làm gate.

Đề xuất sửa và cách kiểm chứng:

1. Sửa system prompt generation: "Trả lời dựa trên context; được phép tổng hợp và tính
   toán từ nhiều đoạn; nếu có nhiều phiên bản, dùng phiên bản đang hiệu lực và nêu rõ;
   chỉ trả 'Không tìm thấy' khi không đoạn nào liên quan". Chạy lại
   `python scripts/setup_answers.py --live` rồi Phase A. Thành công khi tỷ lệ answer
   "Không tìm thấy" giảm từ 9/50 về ≤2/50 và faithfulness multi_hop/adversarial tăng mà
   factual không giảm.
2. Thêm metadata `version`/`effective_date`/`status` (lấy từ header "Phiên bản: … | Ngày
   hiệu lực: …" của từng file) trong m1 và lọc/ưu tiên `status=hiện hành` khi rerank. Đo
   lại câu 41–44 và 49.
3. Retry khi `finish_reason != "stop"` hoặc answer < 12 ký tự (câu 5).
4. Với câu tính toán, chấm thêm bằng nhãn người hoặc judge có reference (Phase B) thay vì
   chỉ dựa vào faithfulness.

## Bẫy adversarial và giới hạn

Adversarial mean (0.653) thấp hơn factual (0.810) 0.157 điểm. Bottom 10 có 4 câu
adversarial: 42, 43, 44 là version conflict (v2023/v2024, mật khẩu v1.0/v2.0) và 50 là
bẫy phủ định ("dùng VPN cá nhân để tăng bảo mật" thực tế bị cấm). Ở cả bốn câu, context
đã chứa bản hiện hành (3 năm, 12 ký tự, 120 ngày, quy định VPN), nhưng pipeline **không
xử lý được xung đột** mà chọn từ chối. Điểm thấp vì thế phản ánh pipeline không giải
quyết được bẫy, không chứng minh pipeline nhận ra bẫy.

Ngược lại, câu 41 (15 ngày theo v2024), 46 (thử việc KHÔNG được nghỉ phép) và 49 (nêu cả
12 ngày v2023 lẫn 15 ngày v2024 hiện hành) được trả lời đúng phiên bản và giữ phủ định.
Dù vậy, cả ba câu có context_recall chỉ 0.67 vì không lấy đủ các vế của reference.

Giới hạn: chỉ 50 câu (10 adversarial), mỗi câu chấm một lượt RAGAS với gpt-4o-mini nên
mean dao động khoảng ±0.01 giữa các lượt. answer_relevancy kém tin cậy với tiếng Việt.
Hai PDF scan không vào corpus (cần OCR). Không có fallback extractive trong lượt này.
