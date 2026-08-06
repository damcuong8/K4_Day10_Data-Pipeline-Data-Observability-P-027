# Member Role Report — Day 10: Data Pipeline & Data Observability

> Bản này được viết cho vai trò **Pipeline integrator**. Nếu bạn giữ vai trò khác, hãy sửa lại mục 2-6 cho đúng phần việc mình trực tiếp làm — không nhận ownership cho file mình không viết.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | [Họ và tên] |
| MSSV | [MSSV] |
| Khóa/Lớp | K4 |
| Tên nhóm | [Tên hoặc mã nhóm] |
| Vai trò chính | Pipeline integrator (orchestration + reproducibility) |
| Repository | [Đường dẫn repository] |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `pipelines/phase1.py` — `main()`, `save_clean_dataframe()`, `load_clean_dataframe()`, `run_agent_demo()` | Hàm của ingestion/cleaning/testset/quality/reporting | `baseline_metrics.json`, `baseline_answers.json`, `agent_demo_answers.json`, `phase1_report.md` | Hoàn thành |
| Corruption orchestration | `pipelines/corruption_flow.py` — `main()`, `_evaluate_state()`, `_require_baseline()` | Baseline clean CSV + raw records | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| Multi-provider embedding | `retrieval/embeddings.py` — `GeminiEmbeddings`, `OpenAIEmbeddingsBackend`, `build_embeddings()`; `core/config.py` — `embedding_provider`/`embedding_model`/`embedding_dimensions` | Settings | Backend embedding chuyển đổi được qua `.env` | Hoàn thành |
| Tài liệu cấu hình | `.env.example` | — | File mẫu ghi rõ LLM và embedding là hai trục độc lập | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug `KeyError: 'categories_joined'` | `retrieval/qa.py` (code tham khảo) + `corruption_flow.py` | Xác định root cause là NaN sau `read_csv`, sửa bằng `load_clean_dataframe()` |
| Viết smoke test độc lập | `evaluation/testset.py`, `observability/*` | `script/test_role4.py` — cho phép kiểm thử Role 4 trên dữ liệu thật trước khi pipeline hoàn thiện |
| Bổ sung quality check | `observability/quality.py` | Thêm `empty_ratios`/`fully_empty_columns` và tự ghi artifact vào `data/quality/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Ghép baseline pipeline 8 bước | `pipelines/phase1.py` | 4 artifact mới + report | `python script/run_phase1.py` |
| Ghép corruption/repair/compare 7 bước | `pipelines/corruption_flow.py` | 5 artifact mới + comparison report | `python script/run_corruption_flow.py` |
| Tách path/collection cho 3 trạng thái | `_evaluate_state()` truyền `embeddings_output_path` riêng | 3 collection độc lập, baseline không bị ghi đè | `ls data/embeddings/`, kiểm tra `collection_name` trong từng manifest |
| Chặn chạy sai thứ tự | `_require_baseline()` | Báo lỗi rõ ràng nếu thiếu baseline artifact | Xóa `baseline_metrics.json` rồi chạy corruption flow |

Output cụ thể mà phần việc này tạo ra: **bảng so sánh ba trạng thái in trực tiếp ra terminal khi kết thúc corruption flow**, đối chiếu 4 metric + row count + trạng thái quality giữa baseline/corrupted/repaired. Đây là bằng chứng gọn nhất cho kết luận trung tâm của bài lab, và mọi số trong đó đều đọc từ file JSON thật chứ không tính lại trong bộ nhớ.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bốn module (ingestion, cleaning, evaluation, observability) được viết song song bởi các thành viên khác nhau, mỗi module đúng khi chạy riêng nhưng chưa từng chạy nối tiếp. Vai trò của tôi là biến chúng thành hai pipeline chạy một lệnh từ đầu đến cuối, đồng thời đảm bảo phép so sánh ba trạng thái là công bằng — tức không để trạng thái sau ghi đè hoặc làm nhiễu trạng thái trước.

### Cách triển khai

`phase1.py` chạy tuần tự 8 bước: fetch/load raw → clean → lưu artifact → build index → tạo hoặc nạp lại test set → evaluate → quality/freshness → sinh report và demo agent. Quyết định thiết kế quan trọng nhất là **nạp lại test set thay vì tạo mới** khi file đã tồn tại và `refresh_test_set=False`, để lần chạy corruption sau dùng đúng bộ câu hỏi cũ.

`corruption_flow.py` chạy 7 bước, trong đó khâu cốt lõi là hàm `_evaluate_state()` — nhận một DataFrame, build index vào một đường dẫn manifest riêng, rồi evaluate bằng test set cố định. Việc truyền `embeddings_output_path` khác nhau cho mỗi trạng thái là cách tách collection: `index.py` map đường dẫn manifest sang tên collection (`papers-baseline`/`papers-corrupted`/`papers-repaired`), nên chỉ cần đổi path là ba trạng thái nằm ở ba collection độc lập, không đè lên nhau.

Repair không sửa dữ liệu hỏng mà gọi lại `load_raw_records()` rồi `build_clean_dataframe()` — tái tạo dataset từ snapshot nguồn. Đây là điểm phân biệt giữa "che lỗi" và "phục hồi thật": nếu chỉ xóa duplicate và điền lại summary trên corrupted dataframe thì không chứng minh được raw snapshot còn dùng được.

Phần multi-provider embedding: tôi tách `build_embeddings()` thành factory chọn backend theo `EMBEDDING_PROVIDER`, thay cho việc hard-code MiniLM trong `index.py`. Với Gemini phải tách `task_type` thành `retrieval_document`/`retrieval_query` và chia batch 50 text/request; với OpenAI dùng tham số `dimensions` để rút gọn 1536 → 768 chiều cho đồng nhất. Cả hai đều chuẩn hóa vector về độ dài 1 vì model không tự normalize khi rút gọn số chiều.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings` từ `core/config.py`; raw records JSON; cleaned DataFrame với 9 cột metadata bắt buộc |
| Output | Metrics/answers JSON cho 3 trạng thái, quality/freshness JSON, 2 markdown report |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `ingestion.corruption`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting`, `retrieval.index`, `retrieval.agent` |
| Module sử dụng output | `script/run_phase1.py`, `script/run_corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Cleaned dataframe rỗng; thiếu baseline artifact khi chạy phase 2; agent lỗi do thiếu credential (bắt exception và ghi lý do thay vì làm hỏng cả pipeline) |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai lệnh chạy hết, sinh đủ artifact, và bảng so sánh cho thấy corrupted kém hơn baseline còn repaired quay về mức baseline.
- **Kết quả thực tế:** Đúng như mong đợi. `retrieval_hit_rate` 1.00 → 0.00 → 1.00; `mean_token_f1` 0.75 → 0.046 → 0.75; `judge_accuracy` 0.75 → 0.00 → 0.75; `mean_judge_score` 4.0 → 1.35 → 4.0; `is_healthy` true → false → true.
- **Artifact/log:** `data/results/*.json`, `data/quality/*.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corruption flow cần build lại index cho corrupted và repaired. Nếu dùng chung một collection ChromaDB thì lần build sau sẽ xóa lần trước, khiến không thể quay lại kiểm chứng baseline sau khi đã corrupt.
- **Các phương án đã cân nhắc:** (1) Dùng một collection duy nhất và build lại mỗi lần — đơn giản nhưng phá hủy trạng thái cũ. (2) Sao lưu thư mục `data/chroma` trước mỗi lần build rồi khôi phục — cồng kềnh, tốn dung lượng. (3) Tách ba collection riêng bằng cách truyền `embeddings_output_path` khác nhau, tận dụng cơ chế map path → tên collection có sẵn trong `index.py`.
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** Không tốn thêm dòng code hạ tầng nào vì `_derive_collection_name()` đã hỗ trợ sẵn; ba trạng thái cùng tồn tại nên có thể query lại bất kỳ lúc nào để đối chứng; và quan trọng nhất là loại bỏ hoàn toàn nguy cơ ghi đè baseline — thứ mà hướng dẫn nhấn mạnh là điều kiện để phép so sánh có giá trị.
- **Bằng chứng quyết định phù hợp:** Sau khi chạy xong cả hai pipeline, `data/embeddings/` chứa đủ 3 manifest với `collection_name` khác nhau, và `baseline_metrics.json` không thay đổi timestamp sau khi corruption flow chạy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  File "src/retrieval/qa.py", line 28, in _extract_answer
      return metadata["categories_joined"]
  KeyError: 'categories_joined'
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` (thành công) rồi `python script/run_corruption_flow.py` (lỗi ở bước evaluate corrupted).
- **Nguyên nhân gốc:** `categories_joined` rỗng ở toàn bộ 100 record vì Crossref không trả về trường `subject`. Khi ghi ra CSV, giá trị `""` trở thành ô trống; khi `pd.read_csv()` đọc lại, pandas chuyển ô trống thành `NaN`. ChromaDB loại bỏ các cặp metadata có giá trị `NaN` khi lưu, nên khi query trả về, key này không còn tồn tại trong dict. `phase1.py` không dính lỗi vì nó dùng DataFrame trực tiếp trong bộ nhớ, chưa đi qua vòng CSV.
- **Cách xử lý:** Viết `load_clean_dataframe()` thực hiện `fillna("").astype(str)` cho toàn bộ cột nằm trong Chroma metadata, và thay `pd.read_csv()` bằng hàm này trong `corruption_flow.py`.
- **Cách xác minh sau khi sửa:** Chạy lại corruption flow — hoàn tất đủ 7 bước, sinh ra `corrupted_metrics.json` và `repaired_metrics.json`.
- **Điều học được:** Contract dữ liệu giữa các module không chỉ là danh sách tên cột mà còn bao gồm kiểu dữ liệu **sau khi qua vòng serialize/deserialize**. CSV không phân biệt được chuỗi rỗng với giá trị thiếu, nên bất kỳ pipeline nào đọc lại từ CSV cũng phải chuẩn hóa kiểu trước khi đưa xuống tầng dưới. Đây cũng là lý do lỗi chỉ lộ ra ở pipeline thứ hai chứ không phải pipeline thứ nhất.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
`fetch_source_records()` gọi `api.crossref.org/works` với query và filter từ `Settings`, lưu nguyên payload vào `data/raw/crossref_response.json` trước khi xử lý gì. `parse_crossref_payload()` bóc từng item lấy DOI làm `paper_id`, strip tag JATS khỏi abstract, ghép tên tác giả, chuẩn hóa `date-parts` thành `YYYY-MM-DD`, rồi lưu tiếp vào `crossref_records.json`. `build_clean_dataframe()` loại record thiếu field bắt buộc, dedupe theo `paper_id`, tính `age_days` và ghép `text_for_embedding` từ title + authors + categories + summary. Cuối cùng `LocalEmbeddingIndex.build()` embed cột `text_for_embedding` và nạp vào ChromaDB kèm metadata để trả lời được cả câu hỏi về tác giả và ngày.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Mỗi câu hỏi mang theo `ground_truth` (đáp án text) và `ground_truth_doc_ids` (paper_id đúng). Hai thứ này đo hai tầng khác nhau: `retrieval_hit_rate` kiểm tra xem trong `top_k` tài liệu lấy về có tài liệu đúng không — đo tầng **tìm kiếm**; còn `token_f1` và LLM judge so đáp án sinh ra với `ground_truth` — đo tầng **trả lời**. Tách hai tầng cho phép chẩn đoán chính xác: retrieval sai thì lỗi ở index/embedding, retrieval đúng mà đáp án sai thì lỗi ở khâu sinh câu trả lời.

**3. Quality checks khác freshness monitoring ở điểm nào?**
Quality check đo **tính đúng đắn nội tại** của dữ liệu tại một thời điểm: có null không, có trùng `paper_id` không, có cột nào rỗng hoàn toàn không. Freshness monitoring đo **quan hệ với thời gian**: dữ liệu mới nhất là bao giờ, bao nhiêu bản ghi vượt ngưỡng 180 ngày. Một dataset có thể sạch tuyệt đối về mặt cấu trúc nhưng đã cũ ba năm — quality pass mà freshness fail. Trong bài này corruption chạm cả hai: `DUPLICATE_ROW` bị quality bắt, `STALE_DATE` và `DROP_LATEST` bị freshness bắt.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Vì test set là biến kiểm soát. Chỉ khi câu hỏi và ground truth giữ nguyên thì mọi thay đổi trong metric mới quy được về nguyên nhân duy nhất là chất lượng dữ liệu. Nếu sinh lại test set sau khi corrupt, câu hỏi sẽ được tạo từ chính dữ liệu đã hỏng — ground truth cũng hỏng theo, và agent có thể vẫn "trả lời đúng" theo chuẩn hỏng đó, khiến metric không giảm mà kết luận thì vô nghĩa. `refresh_test_set` mặc định `False` chính là để bảo vệ điều này.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Ba tầng bằng chứng phải cùng khớp. Tầng dữ liệu: `repaired_quality.json` cho thấy 100 row, `duplicate_paper_ids=0`, `stale_rows_count=0`, `is_healthy=true`. Tầng freshness: `latest_published` quay lại 2026-08-05. Tầng agent: `repaired_metrics.json` trùng khít baseline ở cả 4 metric. Nếu chỉ quality pass mà metric agent không hồi, nghĩa là repair mới sửa được hình thức chứ chưa khôi phục nội dung.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.0000 | 1.0000 | Sụp tối đa — dấu hiệu corruption trùng đúng tập test, không phải suy giảm dần |
| `mean_token_f1` | 0.7500 | 0.0463 | 0.7500 | Còn 6%; phần sót lại là các từ chung tình cờ trùng |
| `judge_accuracy` | 0.7500 | 0.0000 | 0.7500 | Judge không chấm đúng câu nào — khắc nghiệt hơn cả token F1 |
| `mean_judge_score` | 4.0000 | 1.3500 | 4.0000 | 1.35/5 gần sát đáy thang điểm |
| Quality checks | Pass | Fail | Pass | Bắt được 3 duplicate + 4 stale |
| Freshness status | Fresh | Stale | Fresh | `latest_published` lùi 23 ngày |

### Kết luận từ số liệu

1. **`DROP_LATEST` xóa 10 bài mới nhất** → freshness đổi trạng thái (`is_fresh` true→false, `latest_published` 2026-08-05 → 2026-07-13) và row count 100→93 → **`retrieval_hit_rate` 1.00 → 0.00**, vì đối chiếu `corruption_log.json` với `test_set.json` cho thấy cả 5/5 paper ground truth đều nằm trong nhóm bị xóa.

2. **Repair bằng re-run cleaning từ raw snapshot** → quality phục hồi (`is_healthy` false→true, duplicate 3→0, stale 4→0) và freshness về `is_fresh=true` → **cả 4 metric agent quay về đúng giá trị baseline không sai số**, chứng minh raw snapshot đủ để tái tạo trạng thái sạch.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
`DROP_LATEST`, áp đảo hoàn toàn. Nó không làm giảm chất lượng tài liệu mà **xóa hẳn tài liệu khỏi corpus**, nên agent không có gì để tìm — khác về bản chất với các lỗi làm nhiễu (blank summary, noise, truncate) vốn chỉ khiến tài liệu khó tìm hơn. Trong thí nghiệm này tác động của nó lớn đến mức che lấp năm loại còn lại: khi cả 5 paper ground truth đã biến mất thì dù các paper khác có sạch hay bẩn cũng không ảnh hưởng tới `retrieval_hit_rate`.

**Kết quả nào khác với kỳ vọng ban đầu?**
Tôi kỳ vọng metric giảm dần theo tỉ lệ record bị hỏng, khoảng 30-50%. Thực tế rơi thẳng về 0.00. Giả thuyết đầu tiên là do cộng dồn nhiều loại lỗi; tôi kiểm tra bằng cách trích tập `paper_id` có `action=DROP_LATEST` từ corruption log rồi đối chiếu với `ground_truth_doc_ids` trong test set — trùng 5/5. Nguyên nhân thật là lỗi thiết kế thí nghiệm chứ không phải mức độ nghiêm trọng của corruption: `build_test_set()` lấy `df.head(5)` trên dataframe đã sort theo `published` giảm dần, tức chọn đúng 5 bài mới nhất, trong khi `corrupt_clean_dataframe()` lại xóa 10 bài mới nhất. Hai tập giao nhau hoàn toàn theo thiết kế chứ không phải ngẫu nhiên. Kết luận đúng phải là: *đã chứng minh được data corruption làm sụp chất lượng agent và repair khôi phục được*, nhưng **chưa** tách được đóng góp riêng của từng loại corruption.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Contract giữa các module phải bao gồm cả kiểu dữ liệu sau vòng serialize, không chỉ tên cột. Lỗi `KeyError: 'categories_joined'` chỉ xuất hiện ở pipeline thứ hai vì đó là pipeline đầu tiên đọc lại từ CSV — cùng một dữ liệu, khác đường đi, khác kiểu.

2. **Về data quality/observability:** Giá trị của observability nằm ở chỗ tín hiệu phải **dẫn tới nguyên nhân**. `is_healthy=false` mới chỉ nói có vấn đề; phải nối được với `corruption_log.json` mới biết vấn đề gì và ở record nào. Việc bổ sung `fully_empty_columns` giúp phát hiện `categories_joined` rỗng 100% — một lỗi im lặng đã âm thầm giới hạn trần điểm ngay từ baseline mà không ai nhận ra cho tới khi có check này.

3. **Về ảnh hưởng của data đến RAG agent:** Chất lượng agent bị chặn trên bởi chất lượng dữ liệu. Không có prompt hay model nào cứu được câu hỏi mà tài liệu nguồn đã bị xóa khỏi corpus. Đây là lý do observability phải đặt ở tầng dữ liệu chứ không phải chỉ theo dõi output của model.

### Nếu có thêm thời gian

Chạy **ablation từng loại corruption riêng lẻ**: mỗi lần chỉ bật một trong sáu loại, giữ nguyên test set, ghi lại delta của cả 4 metric. Kết hợp với việc chọn test set bằng lấy mẫu rải đều theo `published` thay vì `head(5)` để loại bỏ sự trùng lặp với `DROP_LATEST`. Cách đo cải thiện: thay vì một con số 0.00 không phân giải được, sẽ có bảng sáu dòng cho thấy chính xác mỗi loại lỗi dữ liệu gây thiệt hại bao nhiêu — đó mới là thứ dùng được để quyết định nên ưu tiên monitor tín hiệu nào trong hệ thống thật.

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** 2026-08-06
