# Nhóm thực hiện K4 Track 3A

Tên nhóm: 7kem10

Repo chung: https://github.com/quan05102k4/K4-L3-DAY24-7kem10-Eval-Guard

Trưởng nhóm/người nộp: Nguyễn Minh Quân - 2A202602490

Ngày lab/deadline áp dụng: 2026-10-12, 23:59 theo deadline mặc định (áp dụng điều chỉnh của key coach nếu có) — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: commit cuối trên `main` (commit cập nhật TEAM ngay sau `2b700cf`; SHA gửi kèm link nộp). Commit cuối trước deadline: `804c31c` (2026-10-12 23:58 +07:00)

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Nguyễn Minh Quân | 2A202602490 | Trưởng nhóm; tích hợp m1–m5 (adapter m2 qdrant 1.9, m4 RAGAS + evaluator_models, m5 OpenAI song song); môi trường; sinh answers; Phase C Tasks 9a–12 trong `src/phase_c_guard.py`, chỉnh prompt self-check input, `blueprint.md`; TEAM; nộp bài | Commit `4803143` (pipeline + answers_50q.json), `8ea2feb` (.gitattributes), commit Phase C + blueprint + TEAM |
| 2 | Ngô Văn Giáp | 2A202602644 | Phase A Tasks 1–4 trong `src/phase_a_ragas.py`; chạy RAGAS live; `failure_clusters.md` | Commit `edd007d` (phase A + ragas_50q.json + failure_clusters.md) |
| 3 | Bùi Phương Duy | 2A202602684 | Phase B Tasks 5–8 trong `src/phase_b_judge.py`; chạy judge live; `bias_report.md` | Commit `2b700cf` (phase_b_judge.py + judge_results.json + bias_report.md), push sau deadline, xem mục Cập nhật sau khi nộp |

Người tích hợp/chạy batch/nộp link: Nguyễn Minh Quân, chạy setup và ba runner live trên máy Windows của nhóm, kiểm tra `scripts/check_lab.py`, push và nộp link.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Home 10.0.26200; Python 3.11.17 (cài qua uv); MSVC 14.44 từ Visual Studio 2022 Build Tools (workload C++) để build `annoy==1.17.3`; GPU RTX 4050 với torch 2.6.0+cu124.
Virtualenv/dependencies/imports: `.venv` cài `requirements/requirements.txt -c requirements/constraints-core.txt`; `annoy` build thành công từ source; `pip check` báo "No broken requirements found". Phải hạ thêm `pyarrow<18` và `pandas<2.3` vì bản mới đòi NumPy 2 (xung đột pin numpy 1.26.4), và nâng torch lên 2.6.0 vì transformers 5.x cần `torch.accelerator`. `import ragas, nemoguardrails, presidio_analyzer, spacy` OK (ragas 0.1.22, nemoguardrails 0.10.0); `spacy download en_core_web_lg` OK. Unit tests: `python -m pytest tests/ -q` cho 86 passed, 3 deselected (integration).
Models/Qdrant/50 answers đã chuẩn bị: Qdrant `qdrant/qdrant:v1.9.7` qua docker compose; BGE-M3 và `BAAI/bge-reranker-v2-m3` tải từ HuggingFace; `python scripts/setup_answers.py --live` sinh 50 answers, cả 50 ở mode `llm` (`gpt-4o-mini-2024-07-18`), không fallback. Giới hạn: `BCTC.pdf` và Nghị định 13/2023 là PDF scan không có text layer nên m1 bỏ qua; 128 chunks được enrich bằng gpt-4o-mini.

## INDIVIDUAL

### NguyenMinhQuan-2A202602490

- Phần được giao và phần thực tế đã làm: tích hợp năm module m1–m5 từ bài RAG trước vào `src/`. Sửa adapter: m2 dùng `client.search` vì qdrant-client được pin <1.10; m4 chuyển sang OpenAI, trả `metadata.evaluator_models`, chấm lại câu NaN thay vì gán 0; m5 dùng `OPENAI_API_KEY`/`GENERATION_MODEL` và enrich song song nhưng giữ thứ tự chunk. Dựng môi trường Python 3.11/MSVC/Qdrant, sinh `artifacts/answers_50q.json`. Phase C trong `src/phase_c_guard.py`: Task 9a `pii_scan` (Presidio, lọc entity có cấu trúc để tránh NER tiếng Anh nhận nhầm từ tiếng Việt); Task 9b/11 `check_input_rail`/`check_output_rail` đọc quyết định từ `log.activated_rails[].stop`, không dùng từ khóa; Task 10 `run_adversarial_suite` một event loop, dừng sớm theo tầng; Task 12 `measure_p95_latency` warm-up 2 lượt thật, 20 mẫu. Sau lượt đầu (18/20 attacks, 7/8 clean, chặn nhầm câu 107), chỉnh prompt `self_check_input` trong `guardrails/config.yml`, thử 3 lần trên bản sao trước khi áp dụng; viết `blueprint.md`; điền TEAM, nộp link.
- Bằng chứng: commit `4803143` (m1–m5, answers_50q.json), `8ea2feb` (.gitattributes giữ CRLF cho file được băm hash), commit Phase C + blueprint + TEAM; `artifacts/answers_50q.json`, `artifacts/guard_results.json`, `guardrails/config.yml`, `doc/reports/blueprint.md`.
- Cách kiểm tra: live `python scripts/setup_answers.py --live` (50/50 llm); `python -m pytest tests/test_phase_c.py` (12 passed); live `python scripts/run_experiments.py --phase c --live --latency-samples 20` cho 20/20 attacks, 8/8 clean, 4/4 outputs; `python scripts/check_lab.py` báo PASS answers_50q.json và Phase C artifact.
- Điều đã học: pipeline RAG phụ thuộc nhiều vào phiên bản thư viện (qdrant-client, transformers/torch, pyarrow/numpy). Interface giữa các module (đúng số lượng, đúng thứ tự, metadata model) quan trọng để kết quả đánh giá truy vết được. Với guardrails, clean controls bắt buộc để phát hiện always-block và false positive; phạm vi đo latency phải ghi rõ (input layers ≠ full guard), NeMo input chiếm khoảng 97% thời gian.
- Giới hạn/cách xử lý: hai PDF scan chưa OCR nên không vào corpus, ghi rõ trong báo cáo Phase A. P95 input guard 763.5 ms vượt target 500 ms, ghi đúng số đo. Prompt guard được chỉnh trên chính 28 inputs nên cần bộ held-out.
- Nguồn/AI hỗ trợ nếu có: Claude Code hỗ trợ cài môi trường, sửa adapter, viết code Phase C, thử prompt và viết nháp tài liệu. Tự kiểm chứng bằng unit tests, lượt chạy live trước/sau và đối chiếu JSON với corpus.

### NgoVanGiap-2A202602644

- Phần được giao và phần thực tế đã làm: Phase A trong `src/phase_a_ragas.py`. Task 1 `group_by_distribution` (20/20/10); Task 2 `run_ragas_50q` gọi m4 một lần, kiểm tra số dòng, metric hữu hạn trong [0,1], lấy evaluator_models; Task 3 `bottom_10` có chẩn đoán dựa trên nội dung (phân biệt từ chối nhầm, answer cụt, lỗi retrieval); Task 4 `cluster_analysis` chọn nhóm yếu theo mean thấp nhất, bỏ nhóm rỗng, insight có tỷ lệ refusal.
- Bằng chứng: commit 2; `artifacts/ragas_50q.json`; `doc/reports/failure_clusters.md`.
- Cách kiểm tra: `python -m pytest tests/test_phase_a.py` (6 passed); live `python scripts/run_experiments.py --phase a --live`; checker PASS "Phase A artifact".
- Điều đã học: worst_metric matrix chỉ mô tả, nhóm yếu phải chọn bằng mean. faithfulness = 0 có thể là answer từ chối hoặc khẳng định do tính toán, không nhất thiết là hallucination, nên phải đọc answer/contexts trước khi kết luận.
- Giới hạn/cách xử lý: adversarial (0.6533) và multi_hop (0.6539) gần bằng nhau và RAGAS dao động giữa các lượt; answer_relevancy kém tin cậy với tiếng Việt. Cả hai điểm đều ghi trong báo cáo.
- Nguồn/AI hỗ trợ nếu có: Claude Code hỗ trợ viết code và nháp báo cáo. Tự kiểm chứng bằng tests mock và đối chiếu từng câu bottom 10 với contexts/corpus.

### BuiPhuongDuy-2A202602684

- Phần được giao và phần thực tế đã làm: Phase B trong `src/phase_b_judge.py`. Task 5 `pairwise_judge` có prompt 3 tiêu chí kèm reference, JSON mode, temperature 0, kiểm tra winner/scores; Task 6 `swap_and_average` quy winner/scores lượt đảo về A/B gốc; Task 7 `cohen_kappa` tính tay p_o/p_e; Task 8 `bias_report` đếm position inconsistency (tách chọn ô trước/ô sau/tie) và verbosity.
- Bằng chứng: commit 3; `artifacts/judge_results.json`; `doc/reports/bias_report.md`.
- Cách kiểm tra: `python -m pytest tests/test_phase_b.py` (8 passed); live `python scripts/run_experiments.py --phase b --live`; checker PASS "Phase B artifact"; κ = 1.0.
- Điều đã học: winner A/B khác nhãn 0/1. Swap-and-average phát hiện position bias (id 5 judge chọn answer đứng sau ở cả hai lượt). Verbosity rate cao chưa chứng minh bias khi answer dài hơn cũng đúng hơn.
- Giới hạn/cách xử lý: chỉ 5 cặp và 10 nhãn; judge cùng họ model với generator. Đề xuất thêm judge khác và mẫu nhãn lớn hơn.
- Nguồn/AI hỗ trợ nếu có: Claude Code hỗ trợ viết code và nháp báo cáo. Tự kiểm chứng κ bằng tính tay và đọc reasoning từng cặp.

## Cập nhật sau khi nộp

- Trước deadline 23:59 ngày 2026-10-12 (Asia/Ho_Chi_Minh), `main` có các commit `4803143`, `8ea2feb` (Nguyễn Minh Quân), `edd007d` (Ngô Văn Giáp) và `804c31c` (Nguyễn Minh Quân, 23:58). Ở thời điểm đó Phase B chưa được push.
- Commit `2b700cf` (Phase B: `src/phase_b_judge.py`, `artifacts/judge_results.json`, `doc/reports/bias_report.md`) do Bùi Phương Duy push lúc 00:57:37 ngày 2026-10-13 (+07:00), **sau deadline**. Lý do: card mạng của máy Lenovo của Duy bị hỏng nên không kết nối được để push đúng hạn. Trước đó lúc 00:43 Duy push nhầm nguyên file zip, sau đó đã thay bằng commit `2b700cf` chứa đúng 3 file.
- Nội dung 3 file giống hệt kết quả đã chạy live trước hạn: `artifacts/judge_results.json` có `metadata.created_at` = 2026-10-12T16:31:04Z (23:31 giờ Việt Nam). Không có thay đổi nào khác về code hay số liệu sau deadline ngoài commit này và commit cập nhật TEAM này.
- Sau khi đồng bộ, `python scripts/check_lab.py --with-tests` cho 0 failed checks, 86 tests pass.
- Việc dùng bản cập nhật để chấm theo quyết định của key coach.
