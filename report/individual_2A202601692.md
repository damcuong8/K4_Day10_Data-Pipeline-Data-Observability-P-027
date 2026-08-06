# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                  |
| ------------------ | -------------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Vũ Hà An                                                           |
| MSSV               | 2A202601692                                                                |
| Khóa/Lớp         | K4                                                                        |
| Tên nhóm         | T027 (K4_Day10_Data-Pipeline-Data-Observability-P-027)                     |
| Vai trò chính    | Vai trò 2: Data Foundation & Recovery Owner (Source Ingestion, Clean & Corruption) |
| Repository         | https://github.com/damcuong8/K4_Day10_Data-Pipeline-Data-Observability-P-027.git |
| Ngày hoàn thành | 2026-08-06                                                                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion Raw** | `src/ingestion/crossref.py`<br>- `fetch_crossref_payload()`<br>- `parse_crossref_payload()` | Query term, `max_results=100`, Crossref REST API response | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` (`list[PaperRecord]`) | Hoàn thành |
| **Data Cleaning** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe()` | `list[PaperRecord]` | `pd.DataFrame` sạch,<br>`data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Hoàn thành |
| **Data Corruption** | `src/ingestion/corruption.py`<br>- `corrupt_clean_dataframe()` | `pd.DataFrame` sạch | `pd.DataFrame` bị hỏng,<br>`data/results/corruption_log.json` | Hoàn thành |
| **Data Repair** | Nạp lại pipeline `cleaning.py` từ snapshot raw | `data/raw/crossref_records.json` | `data/clean/papers_clean_repaired.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Handoff Clean Schema | RAG Owner (Chroma Index) & Eval Owner | Cung cấp đúng định dạng `paper_id`, `text_for_embedding`, `age_days` chuẩn không bị null |
| Hỗ trợ Testset Verification | Eval Owner (`testset.py`) | Xác minh 100% `ground_truth_doc_ids` sử dụng DOI thật từ dữ liệu đã clean |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Fetch & cache raw Crossref payload | `src/ingestion/crossref.py` | Kéo thành công 100 bản ghi, retry/backoff cho 429/503 | `python scratch/test_crossref.py` |
| Normalize & Dedupe & Embedding Text | `src/ingestion/cleaning.py` | Lọc bớt bản ghi lỗi, gán stable DOI, tính `age_days`, dựng `text_for_embedding` | `python scratch/test_cleaning.py` |
| Mô phỏng 6 dạng Data Corruption | `src/ingestion/corruption.py` | 93 bản ghi hỏng (Drop latest, Blank summary, Noise title, Truncate, Stale date, Duplicate) | `python scratch/test_corruption.py` |

**Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:**
File `data/clean/papers_clean.json` chứa 100 bản ghi bài báo nghiên cứu khoa học thực tế từ Crossref API. Mỗi bản ghi đều có `paper_id` dựa trên DOI hợp lệ (vd: `10.1002/widm.70122`), tựa đề và tác giả đã qua chuẩn hóa khoảng trắng, cùng với chuỗi `text_for_embedding` hoàn chỉnh để RAG vector search sử dụng.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng lớp Ingestion dữ liệu thô từ nguồn Crossref API bên ngoài, chuyển đổi và làm sạch dữ liệu khoa học về đúng Data Contract của hệ thống, đồng thời viết cơ chế làm hỏng dữ liệu có chủ đích (Corruption) để kiểm thử sức chịu đựng và độ tin cậy của RAG Agent.

### Cách triển khai
1. **Crossref Fetcher & Parser (`crossref.py`)**: Sử dụng `urllib.request` kèm header `User-Agent` hợp lệ. Bổ sung vòng lặp retry tự động với exponential backoff khi gặp lỗi HTTP status 429 (Rate Limit) hoặc 503. Trích xuất DOI làm `paper_id` ổn định.
2. **Cleaning & Normalization (`cleaning.py`)**:
   - Loại bỏ các bản ghi thiếu `paper_id` hoặc `title`.
   - Chuẩn hóa khoảng trắng dư thừa (`normalize_whitespace`).
   - Xử lý ngày xuất bản, tính `age_days = (run_date - published_date).days` và gắn flag cho ngày tương lai.
   - Loại bỏ bản ghi lặp `paper_id` (deduplication).
   - Ghép `text_for_embedding = "Title: ... \nAuthors: ... \nCategories: ... \nSummary: ..."`.
3. **Controlled Corruption (`corruption.py`)**:
   - `DROP_LATEST`: Loại bỏ 10% các bài báo mới nhất dựa trên `age_days`.
   - `BLANK_SUMMARY`: Xóa rỗng trường `summary` của 10% bài báo.
   - `INJECT_NOISE`: Chèn chuỗi `[IRRELEVANT NOISE DATA CORRUPTION]` vào 5% tựa đề.
   - `TRUNCATE_TITLE`: Cắt cụt tựa đề xuống còn 10 ký tự cho 5% bài báo.
   - `STALE_DATE`: Cộng 1000 ngày vào `age_days` làm dữ liệu bị quá hạn.
   - `DUPLICATE_ROW`: Tạo bản sao trùng lặp cho 3 bài báo.
   - Xuất log chi tiết từng hành vi vào `data/results/corruption_log.json`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | Crossref REST API JSON Response (`https://api.crossref.org/works`) |
| Output | `pd.DataFrame` đã clean với đầy đủ các cột: `paper_id`, `title`, `summary`, `authors`, `published`, `age_days`, `text_for_embedding` |
| Module phụ thuộc | `src/core/config.py`, `src/core/models.py`, `src/core/utils.py` |
| Module sử dụng output | `src/retrieval/index.py` (Vector Embedding Index), `src/evaluation/testset.py` |
| Điều kiện lỗi cần xử lý | Lỗi mạng, HTTP 429/503, ngày tháng sai định dạng, tiêu đề rỗng, tác giả thiếu |

### Cách xác minh

```bash
python scratch/test_cleaning.py
```

- **Kết quả mong đợi:** Tải 100 raw record, làm sạch thành công 100 record, xuất ra file `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`.
- **Kết quả thực tế:** Cleaned DataFrame có đúng 100 bản ghi hợp lệ, không còn ô rỗng ở `title` và `paper_id`, xuất file thành công.
- **Artifact/log:** `data/clean/papers_clean.json`, `data/raw/crossref_records.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn identifier làm `paper_id` duy nhất (stable unique key) cho bài báo. Crossref trả về nhiều thông tin như URL, DOI, title.
- **Các phương án đã cân nhắc:**
  1. Dùng URL (VD: `https://doi.org/10.1002/widm.70122`).
  2. Dùng hash (MD5/SHA256) của tựa đề bài báo.
  3. Dùng nguyên bản DOI chuẩn hóa (VD: `10.1002/widm.70122`).
- **Phương án đã chọn:** Phương án 3 - Dùng mã DOI đã chuẩn hóa chữ thường.
- **Lý do:** DOI là mã định danh toàn cầu duy nhất cho các bài báo khoa học, tuyệt đối không bị đổi khi domain/URL thay đổi, đảm bảo tính nhất quán giữa Raw -> Clean -> Index -> Evaluation Test Set.
- **Bằng chứng quyết định phù hợp:** `ground_truth_doc_ids` trong bộ test set map khớp 100% với `paper_id` trong Chroma index mà không xảy ra tình trạng mismatch key.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2010' in position...` khi chạy script python trên môi trường Windows PowerShell.
- **Lệnh hoặc bước tái hiện:** Chạy `python scratch/test_cleaning.py` trên môi trường Windows mặc định.
- **Nguyên nhân gốc:** Console của Windows xài bảng mã `cp1252` hoặc `cp936`, trong khi dữ liệu bài báo từ Crossref chứa các ký tự Unicode đặc biệt (dấu gạch nối Unicode `\u2010`, tên tác giả quốc tế).
- **Cách xử lý:** Thêm đoạn mã ép kiểu UTF-8 cho `sys.stdout` và `sys.stderr` ở đầu các script entrypoint và chỉ định `encoding='utf-8'` khi lưu/đọc file JSON/CSV.
- **Cách xác minh sau khi sửa:** Chạy lại `python scratch/test_cleaning.py` - console in mượt mà không còn bị văng crash error.
- **Điều học được:** Luôn chủ động kiểm soát file/stream encoding là UTF-8 khi xử lý dữ liệu NLP/văn bản đa ngôn ngữ trên Windows.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được `crossref.py` fetch qua API dưới dạng JSON thô -> lưu vào `data/raw/` -> `cleaning.py` parse thành `PaperRecord`, lọc bớt ô rỗng/trùng, tính `age_days` và ghép thành `text_for_embedding` -> ghi ra `data/clean/papers_clean.json` -> `index.py` đọc file clean, chạy model `MiniLMEmbeddings` tạo vector 384 chiều -> đẩy vào Vector DB (ChromaDB).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Evaluation set bao gồm danh sách các câu hỏi test kèm `ground_truth` (câu trả lời chuẩn) và `ground_truth_doc_ids` (mã bài báo chứa câu trả lời đó). Khi RAG Agent chạy, hệ thống kiểm tra xem `retrieved_doc_ids` (bài báo do Vector search tìm ra) có chứa `ground_truth_doc_ids` không để tính `retrieval_hit_rate`. Sau đó dùng LLM Judge và Token F1 để so sánh câu trả lời tạo ra với `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks**: Đo lường tính toàn vẹn tĩnh của bản ghi dữ liệu (như missing value, null title/summary, duplicate paper_id, đếm số lượng dòng).
   - **Freshness monitoring**: Đo lường tính thời sự và độ tươi của dữ liệu theo thời gian (tính `age_days` dựa trên khoảng cách giữa `published_date` và ngày chạy pipeline `run_date`, cảnh báo khi dữ liệu quá 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính công bằng (Fair Benchmark) và kiểm soát biến số. Việc giữ nguyên duy nhất 1 test set cố định giúp đo lường chính xác mức độ sụt giảm hiệu năng (Delta) khi dữ liệu bị hỏng và mức độ phục hồi khi dữ liệu được sửa.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi:
   - Artifact `data/clean/papers_clean_repaired.json` phục hồi đủ 100 bản ghi gốc từ snapshot thô.
   - Metric `retrieval_hit_rate`, `mean_token_f1`, và `mean_judge_score` phục hồi quay lại tiệm cận mức Baseline ban đầu.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   95.0%  |   60.0%   |   95.0%  | Sụt giảm 35% do bài báo bị xóa summary và title bị chèn noise. |
| `mean_token_f1`        |    0.85  |    0.35   |    0.84  | Giảm mạnh do RAG trả về câu trả lời "I don't know" hoặc bị sai ngữ cảnh. |
| `judge_accuracy`       |   90.0%  |   25.0%   |   90.0%  | Tỷ lệ LLM đánh giá đúng rớt thảm hại trên data bị corrupted. |
| `mean_judge_score`     |  4.6/5.0 |  1.8/5.0  | 4.5/5.0  | Điểm trung bình giảm 2.8 điểm khi data bị làm hỏng. |
| Quality checks         |   PASS   |   FAIL    |   PASS   | Thất bại do xuất hiện duplicate rows và rỗng summary. |
| Freshness status       |   FRESH  |   STALE   |   FRESH  | Bị cảnh báo stale do hành vi cộng thêm 1000 ngày tuổi. |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**
   Khi thực hiện corrupt xóa `summary` và làm `stale date` → Quality check báo lỗi Null Summary & Stale Rows → Vector search không tìm ra tài liệu trúng → `retrieval_hit_rate` rớt từ 95% xuống 60%, `mean_judge_score` rớt từ 4.6 xuống 1.8.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**
   Thực hiện nạp lại dữ liệu sạch từ snapshot thô → Quality check khôi phục trạng thái PASS & FRESH → Vector search tìm lại đúng bài báo -> Điểm LLM Judge phục hồi lại mức 4.5/5.0.

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**
  Lỗi **Blank Summary** và **Drop Latest Records** ảnh hưởng nặng nhất. Vì RAG hoạt động dựa trên ngữ cảnh (context), khi summary bị xóa rỗng, vector embedding không còn ngữ cảnh tri thức để so khớp semantic search, khiến Agent hoàn toàn mất khả năng trả lời chính xác.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Garbage In, Garbage Out**: Chất lượng của RAG Agent phụ thuộc trực tiếp vào độ sạch và độ toàn vẹn của Data Pipeline bên dưới.
2. **Data Observability là bắt buộc**: Cần có các chốt kiểm soát tự động (Quality & Freshness signals) để phát hiện sớm lỗi dữ liệu trước khi đút vào Vector Index.
3. **Reproducibility & Lineage**: Việc lưu trữ Snapshot dữ liệu thô (Raw Cache) giúp phục hồi hệ thống nhanh chóng (Data Recovery) mà không bị phụ thuộc vào dịch vụ bên ngoài.

### Nếu có thêm thời gian
Tôi sẽ tích hợp công cụ Great Expectations (GX) để tự động hóa các bộ quy tắc kiểm tra Data Contract nâng cao, đồng thời thêm cơ chế cảnh báo qua Slack/Telegram khi phát hiện chỉ số Freshness bị giảm sút.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Vũ Hà An  
**Ngày xác nhận:** 2026-08-06
