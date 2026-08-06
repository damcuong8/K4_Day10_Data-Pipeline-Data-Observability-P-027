# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                  |
| ------------------ | -------------------------------------------------------------------------- |
| Họ và tên       | Lý Nhật Huy                                                               |
| MSSV               | 2A202601450                                                                |
| Khóa/Lớp         | K4                                                                        |
| Tên nhóm         | T027 (K4_Day10_Data-Pipeline-Data-Observability-P-027)                     |
| Vai trò chính    | Vai trò 4: Evaluation & Observability Owner (Test Set, Metrics & Reporting) |
| Repository         | https://github.com/damcuong8/K4_Day10_Data-Pipeline-Data-Observability-P-027.git |
| Ngày hoàn thành | 2026-08-06                                                                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Evaluation Testset** | `src/evaluation/testset.py`<br>- `build_test_set()` | `pd.DataFrame` sạch | `data/eval/test_set.json` (Bộ 20 câu hỏi kiểm thử) | Hoàn thành |
| **Metrics Evaluator** | `src/evaluation/metrics.py`<br>- `evaluate_pipeline()`<br>- `_judge_answer()` | `test_set.json`, `LocalEmbeddingIndex` | `baseline_metrics.json`, `corrupted_metrics.json`, `answers.json` | Hoàn thành |
| **Data Quality & Freshness** | `src/observability/quality.py`<br>- `run_data_quality_checks()`<br>- `build_freshness_report()` | `pd.DataFrame` sạch / hỏng | `freshness_report.json`, Quality signals payload | Hoàn thành |
| **Observability Reporting** | `src/observability/reporting.py`<br>- `generate_phase1_report()`<br>- `generate_corruption_report()` | Metrics JSON, Quality JSON | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Kiểm tra schema Data Clean | Ingest/Clean Owner (`cleaning.py`) | Đảm bảo các trường `summary`, `authors_joined`, `published`, `categories_joined` không bị trống trước khi sinh testset |
| Phối hợp tích hợp Pipeline | Lead / Integrator (`run_phase1.py`, `run_corruption_flow.py`) | Tích hợp thành công hàm sinh báo cáo tự động vào luồng chạy chính |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng bộ Test Set mẫu | `src/evaluation/testset.py` | 20 câu hỏi chuẩn hóa (4 loại: summary, authors, date, categories) | `cat data/eval/test_set.json` |
| Đo lường hiệu năng RAG | `src/evaluation/metrics.py` | Tính toán `retrieval_hit_rate`, `mean_token_f1`, và `judge_score` | `cat data/results/baseline_metrics.json` |
| Đo lường sức khỏe dữ liệu | `src/observability/quality.py` | Kiểm tra Null, Duplicate ID, Row count drop, Stale rows count (`age_days > 180`) | Kiểm tra `freshness_report.json` |
| Sinh báo cáo tác động | `src/observability/reporting.py` | Xuất bảng so sánh hiệu năng Delta giữa Baseline, Corrupted và Repaired | `cat data/reports/corruption_report.md` |

**Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:**
Báo cáo markdown [corruption_report.md](file:///e:/VinAI/LABS/K4_Day10_Data-Pipeline-Data-Observability-P-027/data/reports/corruption_report.md) thể hiện trực quan bảng so sánh 3 trạng thái. Báo cáo chứng minh rõ ràng khi dữ liệu bị hỏng (Blank summary & Title noise), chỉ số `retrieval_hit_rate` giảm từ 95.0% xuống 60.0% và `mean_judge_score` rớt từ 4.6/5.0 xuống 1.8/5.0.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Thiết lập bộ khung đánh giá tự động (Evaluation Framework) để định lượng độ chính xác của RAG Agent, đồng thời xây dựng hệ thống giám sát chất lượng dữ liệu (Data Observability) nhằm phát hiện kịp thời suy biến dữ liệu (Data Drift / Data Degradation).

### Cách triển khai
1. **Testset Generator (`testset.py`)**:
   - Lọc lấy danh sách bài báo đại diện từ tập dataframe sạch.
   - Tạo 4 loại câu hỏi dựa trên cấu trúc trích xuất của `qa.py`:
     - Summary: `What is the summary of the paper '{title}'?` -> `ground_truth` = câu đầu tóm tắt.
     - Authors: `Who authored the paper '{title}'?` -> `ground_truth` = danh sách tác giả.
     - Date: `When was the paper '{title}' published?` -> `ground_truth` = ngày xuất bản.
     - Categories: `What categories does the paper '{title}' belong to?` -> `ground_truth` = thể loại.
   - Gán `ground_truth_doc_ids` chính xác bằng `paper_id` của bài báo đó.
2. **Evaluator Core (`metrics.py`)**:
   - Duyệt qua từng câu hỏi trong test set, gọi `answer_question()`.
   - Kiểm tra `retrieval_hit = any(doc_id in ground_truth_doc_ids for doc_id in retrieved_doc_ids)`.
   - Tính toán `token_f1` giữa câu trả lời và ground truth.
   - Gọi `_judge_answer()` dùng LLM Structured Output để chấm điểm từ 1-5 và giải thích lý do.
3. **Data Quality & Freshness (`quality.py`)**:
   - Đếm số dòng null ở các cột bắt buộc.
   - Phát hiện trùng lặp `paper_id`.
   - Tính toán `stale_rows_count` dựa trên điều kiện `age_days > freshness_threshold_days` (180 ngày).
4. **Automated Reporting (`reporting.py`)**:
   - Tổng hợp các dict kết quả và định dạng thành file Markdown báo cáo có bảng biểu so sánh chi tiết.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | `pd.DataFrame` sạch / hỏng, `test_set.json`, `LocalEmbeddingIndex` |
| Output | `test_set.json`, `metrics.json`, `answers.json`, `freshness_report.json`, `corruption_report.md` |
| Module phụ thuộc | `src/core/config.py`, `src/retrieval/qa.py`, `src/retrieval/index.py` |
| Module sử dụng output | Giảng viên / Người đánh giá đồ án, Báo cáo chung của nhóm (`group_report.md`) |
| Điều kiện lỗi cần xử lý | LLM Evaluator bị hết quota/timeout -> Chuyển sang dùng Fallback Heuristic Judge (dựa trên Token F1) |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Sinh ra file `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.
- **Kết quả thực tế:** Tất cả các file JSON và báo cáo Markdown được tạo đầy đủ, `retrieval_hit_rate` đạt 95.0%, `mean_judge_score` đạt 4.6/5.0.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi gọi LLM Judge (`_judge_answer`) để chấm điểm câu trả lời RAG, dịch vụ LLM có thể bị Rate Limit (HTTP 429), lỗi mạng, hoặc cạn quota API.
- **Các phương án đã cân nhắc:**
  1. Cho phép chương trình ném Exception và dừng (crash) toàn bộ luồng evaluation.
  2. Bỏ qua câu hỏi bị lỗi và gán điểm 0.
  3. Xây dựng **Fallback Heuristic Judge**: Sử dụng chỉ số `_token_f1(reference, prediction)` để quy đổi ra điểm 1, 3, hoặc 5 khi LLM không phản hồi.
- **Phương án đã chọn:** Phương án 3 - Xây dựng Fallback Heuristic Judge dựa trên Token F1.
- **Lý do:** Đảm bảo tính chống chịu (Fault Tolerance) của pipeline đánh giá, giúp quá trình benchmark không bị đứt gãy giữa chừng mà vẫn đưa ra được điểm số ước lượng hợp lý.
- **Bằng chứng quyết định phù hợp:** Đoạn code `try-except` trong `_judge_answer()` của `metrics.py` giúp quá trình test 100% hoàn tất ngay cả khi mất kết nối internet tới dịch vụ LLM.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'ground_truth_doc_ids'` khi chạy hàm `evaluate_pipeline()`.
- **Lệnh hoặc bước tái hiện:** Chạy thử nghiệm script evaluation trên file `test_set.json` khởi tạo ban đầu.
- **Nguyên nhân gốc:** Cấu trúc dict trong file `test_set.json` bản cũ sử dụng tên key `doc_ids` thay vì `ground_truth_doc_ids`, dẫn đến việc truy cập key trong `metrics.py` bị lỗi.
- **Cách xử lý:** Cập nhật hàm `build_test_set()` trong `testset.py` để ghi đúng chuẩn key name `ground_truth_doc_ids` dạng `list[str]`.
- **Cách xác minh sau khi sửa:** Chạy lại `evaluate_pipeline()`, hàm thực thi mượt mà và đo chính xác tỷ lệ `retrieval_hit_rate`.
- **Điều học được:** Phải thống nhất Data Contract chặt chẽ giữa module tạo dữ liệu test (`testset.py`) và module chấm điểm (`metrics.py`).

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   `crossref.py` fetch JSON thô từ Crossref API -> `cleaning.py` làm sạch, tính `age_days`, ghép `text_for_embedding` -> ghi file `papers_clean.json` -> `index.py` tạo vector embeddings bằng `MiniLMEmbeddings` và lưu vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Evaluation set cung cấp danh sách câu hỏi kiểm thử và `ground_truth_doc_ids` (ID chuẩn chứa đáp án). Khi RAG trả lời, `evaluate_pipeline()` so sánh `retrieved_doc_ids` với `ground_truth_doc_ids` để tính Hit Rate, đồng thời so sánh câu trả lời tạo ra với `ground_truth` bằng Token F1 & LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks**: Đánh giá độ toàn vẹn của cấu trúc dữ liệu (kiểm tra ô rỗng null ở title/summary, phát hiện duplicate ID, đếm dòng).
   - **Freshness monitoring**: Đánh giá tính thời sự của dữ liệu dựa trên tuổi đời (`age_days` tính từ ngày xuất bản đến ngày chạy pipeline), phát hiện dữ liệu bị quá hạn (>180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính nhất quán và công bằng của bài benchmark. Giữ nguyên 1 bộ test set giúp cô lập tác động của Data Corruption, đảm bảo sự sụt giảm hay phục hồi của các chỉ số metric phản ánh đúng chất lượng dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi:
   - Artifact `repaired_metrics.json` cho thấy `retrieval_hit_rate` và `mean_judge_score` phục hồi về mức Baseline.
   - Báo cáo `corruption_report.md` thể hiện các chỉ số Quality & Freshness trở lại trạng thái PASS & FRESH.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   95.0%  |   60.0%   |   95.0%  | Giảm 35% do các bài báo bị xóa tóm tắt và lỗi tựa đề. |
| `mean_token_f1`        |    0.85  |    0.35   |    0.84  | Giảm sâu do RAG trả về câu trả lời rác hoặc báo "I don't know". |
| `judge_accuracy`       |   90.0%  |   25.0%   |   90.0%  | Độ chính xác đánh giá của LLM rớt thảm hại khi data rác. |
| `mean_judge_score`     |  4.6/5.0 |  1.8/5.0  | 4.5/5.0  | Điểm số rớt từ 4.6 xuống 1.8 thể hiện rõ tác động tiêu cực của data xấu. |
| Quality checks         |   PASS   |   FAIL    |   PASS   | Thất bại do xuất hiện ô null và trùng lặp ID. |
| Freshness status       |   FRESH  |   STALE   |   FRESH  | Bị cảnh báo stale do dữ liệu bị ép cộng tuổi. |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**
   Hành vi làm rỗng summary và chèn noise tựa đề → Quality checks phát hiện lỗi Null Summary & Stale Rows → Vector Search tìm sai bài báo → `retrieval_hit_rate` giảm từ 95% xuống 60%, `mean_judge_score` giảm từ 4.6 xuống 1.8.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**
   Hành động chạy lại pipeline cleaning từ snapshot thô → Quality checks đạt PASS & FRESH → Retrieval khôi phục độ chính xác -> `mean_judge_score` tăng lại mức 4.5/5.0.

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**
  Lỗi **Blank Summary** ảnh hưởng nặng nhất vì vector embeddings mất hoàn toàn ngữ cảnh tri thức, làm suy giảm trực tiếp khả năng Semantic Search của RAG.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **RAG phụ thuộc tuyệt đối vào Data Quality**: Dữ liệu đầu vào sai hỏng sẽ khiến LLM bị hallucinate hoặc trả lời "không biết".
2. **Cần đo lường đa chiều**: Không chỉ đo độ chính xác của câu trả lời (LLM Judge) mà phải đo cả khả năng tìm kiếm thông tin (Retrieval Hit Rate) và sức khỏe dữ liệu (Data Quality Signals).
3. **Báo cáo tự động (Automated Reporting)** giúp team liên tục nắm bắt được sự sụt giảm hiệu năng qua từng lần chạy pipeline.

### Nếu có thêm thời gian
Tôi sẽ phát triển thêm dashboard hiển thị thời gian thực (Real-time Observability Dashboard) để trực quan hóa biến động của Hit Rate và Token F1 qua từng phiên build dữ liệu.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lý Nhật Huy  
**Ngày xác nhận:** 2026-08-06
