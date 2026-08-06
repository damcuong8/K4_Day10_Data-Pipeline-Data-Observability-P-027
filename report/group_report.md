# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | P-027 |
| Repository | https://github.com/damcuong8/K4_Day10_Data-Pipeline-Data-Observability-P-027 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

> Điền đúng người đã trực tiếp viết từng file. Bảng dưới phản ánh cách nhóm đã thực sự chia việc (khác với gợi ý mặc định trong `report/README.md`).

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đàm Việt Cường | 2A202601566 | Pipeline integrator | `pipelines/phase1.py`, `pipelines/corruption_flow.py`, cấu hình multi-provider embedding |
| 2 | Nguyễn Vũ Hà An | 2A20261692 | Data foundation & recovery | `ingestion/crossref.py`, `ingestion/cleaning.py`, `ingestion/corruption.py` |
| 3 | Nguyễn Văn Hiệp | 2A202601488 | RAG & agent owner | Tích hợp `retrieval/` (index, embeddings, agent), smoke test `script/test_role3_rag.py` |
| 4 | Lý Nhật Huy | 2A202601450 | Evaluation & observability | `evaluation/testset.py`, `observability/quality.py`, `observability/reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ vòng đời dữ liệu end-to-end: lấy 100 bài báo từ Crossref API, làm sạch và chuẩn hóa thành dataset có `text_for_embedding`, xây index ChromaDB, sinh evaluation set 20 câu hỏi, đánh giá baseline, chủ động tạo lỗi dữ liệu, đo lại tác động, phục hồi từ raw và so sánh ba trạng thái.

Baseline đạt kết quả tốt: `retrieval_hit_rate` 1.00, `mean_token_f1` 0.75, `judge_accuracy` 0.75, `mean_judge_score` 4.0/5. Data quality và freshness đều pass (0 duplicate, 0 stale row, dữ liệu mới nhất 2026-08-05).

Corruption gây sụp đổ gần như hoàn toàn: `retrieval_hit_rate` rơi từ 1.00 xuống **0.00**, `mean_token_f1` từ 0.75 xuống 0.046, `judge_accuracy` về 0.00, `mean_judge_score` từ 4.0 xuống 1.35. Loại corruption ảnh hưởng mạnh nhất là **`DROP_LATEST`** — xóa 10 bài mới nhất, trong đó có đúng cả 5 bài mà test set dùng làm ground truth, khiến agent không còn tài liệu nào để retrieve đúng. Quality check phát hiện được bất thường (`is_healthy=False`, 3 duplicate, 4 stale row) và freshness chuyển sang `is_fresh=false`.

Repair bằng cách chạy lại cleaning từ raw snapshot phục hồi **100% mọi chỉ số** về đúng mức baseline, quality trở lại `is_healthy=true`.

Giới hạn quan trọng nhất còn lại: trường `categories_joined` rỗng ở toàn bộ 100 record do Crossref không trả về `subject`, khiến 5/20 câu hỏi loại `categories` luôn bị 0 điểm ở cả ba trạng thái và kéo trần `mean_token_f1` xuống 0.75 thay vì gần 1.0.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (api.crossref.org/works)
    -> data/raw/crossref_response.json + crossref_records.json
    -> data/clean/papers_clean.csv|json  (100 rows, text_for_embedding, age_days)
    -> ChromaDB collection papers-baseline (768-dim, cosine)
    -> data/eval/test_set.json (20 câu, 4 loại)
    -> data/results/baseline_metrics.json + baseline_answers.json
    -> data/quality/baseline_quality.json + freshness_report.json
    -> corruption -> papers-corrupted -> corrupted_metrics.json
    -> repair từ raw -> papers-repaired -> repaired_metrics.json
    -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref REST API | Fetch + retry/backoff 429/502/503/504, parse JATS abstract, tạo `paper_id` từ DOI | `data/raw/` | Hà An |
| Cleaning | 100 `PaperRecord` | Drop field thiếu, dedupe `paper_id`, tính `age_days`, build `text_for_embedding` | `data/clean/` | Hà An |
| Embedding/index | Cleaned df | OpenAI `text-embedding-3-small` 768-dim, Chroma cosine, 3 collection tách biệt | `data/embeddings/`, `data/chroma/` | Văn Hiệp |
| Evaluation | Cleaned df | 20 câu hỏi × 4 loại, ground truth lấy trực tiếp từ cột dữ liệu | `data/eval/`, `data/results/` | Nhật Huy |
| Observability | Cleaned/corrupted df | Null, duplicate, stale, tỉ lệ cột rỗng, freshness | `data/quality/` | Nhật Huy |
| Corruption/repair | Baseline clean CSV | 6 loại lỗi có log, repair bằng re-run cleaning từ raw | `corruption_log.json` | Hà An + Việt Cường |
| Orchestration | Tất cả | Điều phối thứ tự, tách path/collection cho 3 trạng thái | `data/reports/` | Việt Cường |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | `openai` |
| Embedding model | `text-embedding-3-small` (768 chiều) |
| Số lượng Crossref records | `max_results=100` |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | 42 (trong `corruption.py`) |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<today-180d>,has-abstract:true` |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 17:00 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 17:14 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:<today-180d>,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được | 100 |
| Cơ chế retry/backoff | 5 lần thử, backoff mũ `2^attempt`, áp dụng cho 429/502/503/504 |

### Raw và clean schema

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | str | Có | DOI, dùng làm document ID xuyên suốt | Fallback sang item id, cuối cùng hash MD5 của title |
| `title` | str | Có | Tiêu đề đã strip tag JATS | Bỏ record nếu rỗng |
| `summary` | str | Có | Abstract đã unescape HTML entity | Bỏ record nếu rỗng |
| `published` | str `YYYY-MM-DD` | Có | Ưu tiên `published-online` → `published-print` → `issued` → `created` | Bỏ record nếu parse lỗi |
| `authors`/`authors_joined` | list/str | Không | Tác giả ghép `given family` | Để rỗng |
| `categories`/`categories_joined` | list/str | Không | Từ trường `subject` | Để rỗng — thực tế rỗng 100% |
| `age_days` | int | Có | `run_date - published` | Loại record có `age_days < 0` |
| `text_for_embedding` | str | Có | Title + Authors + Categories + Summary | Rebuild sau mọi thao tác sửa dữ liệu |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại record thiếu `paper_id`/`title`/`summary`/`published` | Completeness | 0 | Log `ingestion.cleaning` |
| Dedupe theo `paper_id` | Uniqueness | 0 | `duplicate_paper_ids=0` trong `baseline_quality.json` |
| Loại record `published` không parse được | Validity | 0 | Log `ingestion.cleaning` |
| Loại record `age_days < 0` (ngày tương lai) | Validity | 0 | Log `ingestion.cleaning` |

`text_for_embedding` được ghép theo định dạng `Title / Authors / Categories / Summary` để vector chứa cả metadata lẫn nội dung, giúp câu hỏi về tác giả và ngày cũng có tín hiệu ngữ nghĩa. `paper_id` dùng thẳng DOI nên ổn định tuyệt đối qua raw → clean → corrupt → repair. `age_days` tính từ `run_date` truyền vào chứ không phải `datetime.now()` bên trong hàm, để pipeline có thể tái lập.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 20 (5 paper × 4 loại) |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | `[paper_id]` lấy trực tiếp từ cleaned dataframe |
| Embedding model | `text-embedding-3-small`, 768 chiều, `task_type` tách document/query |
| Vector store/collection | ChromaDB cosine — `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI `gpt-4o-mini`, `temperature=0` |
| Test set dùng chung | `data/eval/test_set.json`, giữ nguyên cho cả ba trạng thái |

Test set được sinh **tự động từ cleaned dataset** chứ không viết tay, để `ground_truth` luôn khớp tuyệt đối với nội dung trong corpus. Câu hỏi bọc tiêu đề trong dấu nháy đơn (`'...'`) vì `qa.py` dùng regex bắt chuỗi trong nháy để thực hiện exact lookup trước khi semantic search.

Test set được giữ nguyên khi đánh giá cả ba trạng thái vì đó là biến kiểm soát duy nhất cho phép quy kết thay đổi metric về nguyên nhân dữ liệu. Nếu sinh lại test set sau khi corrupt, câu hỏi sẽ được tạo từ chính dữ liệu đã hỏng và ground truth cũng hỏng theo, khiến metric có thể không giảm mà vẫn không chứng minh được gì. `settings.refresh_test_set` mặc định `False` chính là để bảo vệ điều này.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | `crossref_response.json`, `crossref_records.json` (100 record) |
| Cleaned dataset | `data/clean/` | Có | `papers_clean.csv`, `papers_clean.json` |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | 3 manifest + 3 collection |
| Evaluation set | `data/eval/test_set.json` | Có | 20 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness | `data/quality/` | Có | 3 quality + 3 freshness report |
| Baseline report | `data/reports/phase1_report.md` | Có | |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | Cả 20/20 câu đều retrieve đúng paper chứa ground truth — exact lookup theo tiêu đề hoạt động chính xác |
| `mean_token_f1` | 0.7500 | Đúng bằng 15/20: 15 câu (summary/authors/date) đạt gần 1.0, 5 câu `categories` bị 0 vì ground truth rỗng |
| `judge_accuracy` | 0.7500 | Cùng nguyên nhân — LLM judge chấm sai 5 câu categories |
| `mean_judge_score` | 4.0000 | Trung bình 4/5 |
| Ragas | Skipped | Không bật `RUN_RAGAS=1` để tiết kiệm thời gian và chi phí API |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Completeness | > 0 | Pass — 100 rows | `baseline_quality.json` |
| Null ở cột bắt buộc | Completeness | = 0 | Pass — cả 4 cột đều 0 | `baseline_quality.json` |
| `paper_id` duplicate | Uniqueness | = 0 | Pass — 0 | `baseline_quality.json` |
| Stale rows (`age_days > 180`) | Timeliness | = 0 | Pass — 0, max 175 ngày | `baseline_quality.json` |
| Cột rỗng hoàn toàn | Completeness | Không có | **Fail — `categories_joined` rỗng 100%** | `empty_ratios` trong `baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Cleaned dataset (cột `published` và `age_days`) |
| Timestamp mới nhất | 2026-08-05 |
| Timestamp cũ nhất | 2026-02-12 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | Fresh (`is_fresh=true`, 0 stale row) |
| Lý do | Filter `from-pub-date` của Crossref đã chặn sẵn bài cũ hơn 180 ngày ngay từ khâu ingest |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `DROP_LATEST` | Xóa 10% record có `age_days` nhỏ nhất | 10 | Row count giảm, freshness kém đi | **Nghiêm trọng nhất** — xóa cả 5 paper của test set → `retrieval_hit_rate` = 0 | Re-run cleaning từ raw |
| `BLANK_SUMMARY` | Set `summary = ""` | 9 | Tăng tỉ lệ rỗng | Vector mất nội dung, câu hỏi summary sai | Re-run cleaning từ raw |
| `INJECT_NOISE` | Nối `[IRRELEVANT NOISE DATA CORRUPTION]` vào title | 4 | Không có signal trực tiếp | Nhiễu embedding, hỏng exact lookup theo tiêu đề | Re-run cleaning từ raw |
| `TRUNCATE_TITLE` | Cắt title còn 10 ký tự | 4 | Không có signal trực tiếp | Exact lookup thất bại hoàn toàn | Re-run cleaning từ raw |
| `STALE_DATE` | Cộng 1000 vào `age_days` | 4 | `stale_rows > 0`, `is_fresh=false` | Phát hiện đúng: 4 stale row, max_age 1128 ngày | Re-run cleaning từ raw |
| `DUPLICATE_ROW` | Nhân bản 3 record ngẫu nhiên | 3 | `duplicate_paper_ids > 0` | Phát hiện đúng: 3 duplicate | Re-run cleaning từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có — 34 bản ghi
- Nhận xét: Log ghi đủ `action`, `paper_id`, giá trị `before` và `after` cho từng thao tác, cho phép truy vết chính xác record nào bị lỗi gì. Random seed cố định 42 nên tái lập được.

Repair được thực hiện bằng cách gọi lại `load_raw_records()` trên `data/raw/crossref_records.json` rồi chạy lại `build_clean_dataframe()` — tức tái tạo dataset từ snapshot nguồn đáng tin cậy, **không** sửa tay dữ liệu hỏng và **không** chỉnh file metrics. Raw snapshot không bị đụng tới trong suốt corruption flow, và `refresh_source=False` đảm bảo không fetch lại từ Crossref (nếu fetch lại, dữ liệu có thể đã đổi và phép so sánh mất công bằng). Bằng chứng repair đúng: repaired dataset trở lại đúng 100 row, `duplicate_paper_ids=0`, `stale_rows=0`, `latest_published` quay lại 2026-08-05.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.0000 | 1.0000 | −1.0000 | 100% | Sụp hoàn toàn rồi phục hồi tuyệt đối |
| `mean_token_f1` | 0.7500 | 0.0463 | 0.7500 | −0.7037 | 100% | Còn 6% giá trị ban đầu |
| `judge_accuracy` | 0.7500 | 0.0000 | 0.7500 | −0.7500 | 100% | Không câu nào được chấm đúng |
| `mean_judge_score` | 4.0000 | 1.3500 | 4.0000 | −2.6500 | 100% | Rơi về gần mức thấp nhất (1/5) |
| Quality checks | Pass | **Fail** | Pass | `is_healthy` true→false | 100% | 3 duplicate + 4 stale bị bắt |
| Freshness status | Fresh | **Stale** | Fresh | `is_fresh` true→false | 100% | `latest_published` lùi từ 08-05 về 07-13 |
| Row count | 100 | 93 | 100 | −7 | 100% | −10 drop +3 duplicate |

Hai chuỗi nhân quả có bằng chứng:

1. **`DROP_LATEST` xóa 10 bài mới nhất** → freshness signal đổi (`latest_published` lùi từ 2026-08-05 về 2026-07-13, `is_fresh=false`) và row count giảm 100→93 → **`retrieval_hit_rate` rơi từ 1.00 xuống 0.00** vì cả 5 paper ground truth của test set đều nằm trong nhóm bị xóa, không còn tài liệu nào để retrieve đúng. Kiểm chứng: đối chiếu `ground_truth_doc_ids` trong `test_set.json` với các bản ghi `action=DROP_LATEST` trong `corruption_log.json` — trùng 5/5.

2. **Repair bằng re-run cleaning từ raw snapshot** → quality signal phục hồi (`is_healthy` false→true, duplicate 3→0, stale 4→0) và freshness trở lại `is_fresh=true` → **toàn bộ 4 metric của agent quay về đúng giá trị baseline** (1.00 / 0.75 / 0.75 / 4.0, trùng khít không sai số). Điều này chứng minh raw snapshot đủ để tái tạo trạng thái sạch và lỗi nằm hoàn toàn ở tầng dữ liệu đã xử lý, không phải ở tầng nguồn.

**Kết quả khác kỳ vọng cần nêu rõ:** nhóm dự kiến metric sẽ giảm dần theo mức độ corruption, nhưng thực tế `retrieval_hit_rate` rơi thẳng về 0.00 — mức sụp tối đa. Giả thuyết ban đầu là do tổng hợp nhiều loại lỗi; kiểm tra bằng cách đối chiếu `corruption_log.json` với `test_set.json` cho thấy nguyên nhân thực tế hẹp hơn nhiều: test set lấy `df.head(5)` mà dataframe được sort theo `published` giảm dần, tức 5 bài **mới nhất**; còn `DROP_LATEST` xóa đúng 10 bài **mới nhất**. Hai tập trùng nhau hoàn toàn. Vì vậy con số 0.00 phản ánh sự trùng lặp trong thiết kế test set chứ không chứng minh được rằng năm loại corruption còn lại (blank summary, noise, truncate, stale, duplicate) gây hại ở mức nào. Đây là giới hạn về tính hợp lệ nội tại của thí nghiệm, được ghi ở mục 12.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `corruption_flow.py` crash với `KeyError: 'categories_joined'` tại `qa.py:28`, trong khi `phase1.py` chạy hoàn toàn bình thường với cùng bộ dữ liệu.
- **Nguyên nhân:** `phase1.py` truyền thẳng DataFrame từ `build_clean_dataframe()` nên `categories_joined` là chuỗi rỗng `""` — giá trị hợp lệ với ChromaDB. Còn `corruption_flow.py` đọc lại qua `pd.read_csv()`, và pandas tự chuyển ô trống trong CSV thành `NaN`. ChromaDB loại bỏ metadata có giá trị `NaN`, khiến key biến mất khỏi dict metadata trả về khi query. Vì `categories_joined` rỗng ở toàn bộ 100 record nên lỗi xảy ra chắc chắn ở mọi lần chạy.
- **Cách xử lý:** Thêm hàm `load_clean_dataframe()` trong `pipelines/phase1.py`, thực hiện `fillna("").astype(str)` cho toàn bộ cột được đưa vào Chroma metadata, và dùng hàm này thay cho `pd.read_csv()` trực tiếp trong `corruption_flow.py`.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` — hoàn tất đủ 7 bước và sinh ra `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md`.

Bài học rút ra: contract dữ liệu không chỉ nằm ở tên cột mà còn ở **kiểu dữ liệu sau khi đi qua vòng serialize/deserialize**. CSV không phân biệt được chuỗi rỗng với giá trị thiếu, nên mọi pipeline đọc lại từ CSV đều phải chuẩn hóa kiểu trước khi dùng.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| `categories_joined` rỗng 100% do Crossref không trả `subject` | 5/20 câu hỏi luôn 0 điểm, trần `mean_token_f1` bị kẹt ở 0.75 | Bỏ loại câu hỏi `categories`, thay bằng câu hỏi về tạp chí (`comment`); kỳ vọng `mean_token_f1` baseline lên gần 1.0 |
| Test set trùng hoàn toàn với nhóm record bị `DROP_LATEST` | `retrieval_hit_rate` = 0 bị chi phối bởi một loại corruption, không tách được đóng góp của 5 loại còn lại | Chọn 5 paper cho test set bằng lấy mẫu rải đều theo `published` thay vì `head(5)`; hoặc chạy ablation từng loại corruption riêng lẻ và ghi lại delta của mỗi loại |
| Chỉ 20 câu hỏi trên 100 paper | Metric nhạy cảm với vài câu, mỗi câu chiếm 5% | Tăng lên 15-20 paper (60-80 câu); kiểm chứng bằng độ lệch chuẩn giữa các lần chạy |
| Chưa bật Ragas | Thiếu các metric ngữ nghĩa như faithfulness, context precision | Chạy lại với `RUN_RAGAS=1` và so sánh với `token_f1` |
| Corruption dùng seed cố định 42 | Chỉ quan sát được một kịch bản ngẫu nhiên duy nhất | Chạy nhiều seed và báo cáo khoảng dao động của từng metric |
| Embedding dùng OpenAI thay vì MiniLM như đề bài | Lệch khỏi cấu hình chuẩn của lab | Đã cài đặt sẵn `EMBEDDING_PROVIDER=minilm` để chạy đối chứng, có thể so sánh trực tiếp hai backend |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, `refresh_test_set=False`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
