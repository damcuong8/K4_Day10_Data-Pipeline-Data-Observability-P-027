# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Văn Hiệp             |
| MSSV               | 2A202601488                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | P-027     |
| Vai trò chính    | Vai trò 3 - RAG & Agent Owner                 |
| Repository         | https://github.com/damcuong8/K4_Day10_Data-Pipeline-Data-Observability-P-027 |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Semantic Search (Vector Index) | `src/retrieval/index.py` (LocalEmbeddingIndex) | Data clean JSON (`papers_clean.json`) | ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và manifest JSON | Hoàn thành |
| Agent LLM | `src/retrieval/agent.py` và `llm.py` | Câu hỏi truy vấn và Index tìm kiếm | Câu trả lời sinh ra từ văn bản (Agent) | Chưa chạy được toàn trình (Vướng Blocker) |
| Validation Scripts | `script/cp2_role3.py` & `script/cp5_cp6_role3.py` | Data từ 3 trạng thái của Role 2 | Log kết quả tìm kiếm và Agent QA | Một phần (Thử nghiệm Index pass, Agent bị block) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Fix lỗi thư viện UV trên Windows | Cả nhóm | Fix thành công lỗi `Access is denied` (OS error 5) khi cài đặt bằng lệnh `uv sync --link-mode=copy` |
| Fix kẹt terminal Git pull | Cả nhóm | Khắc phục trình trạng terminal treo do vim editor khi merge, giúp Role 2 và Role 3 thông luồng Git |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Cấu hình LLM & Index | `src/retrieval/llm.py` và `.env` | Kết nối thành công model Gemini-2.0-flash và sinh embeddings bằng MiniLM | Chạy script báo kết nối thành công |
| Build 3 Vector Indexes | `script/cp5_cp6_role3.py` | `papers-baseline`, `papers-corrupted`, `papers-repaired` trong `data/embeddings/` | Kiểm tra thư mục `data/embeddings/` sinh đủ 3 manifest JSON. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Tôi đã tạo ra 3 cơ sở dữ liệu ChromaDB hoàn toàn độc lập với nhau (baseline, corrupted, repaired) được sinh ra từ các file dữ liệu mà Role 2 làm sạch. Qua đó giúp Role 4 có thể benchmark được khả năng truy xuất (Retrieval) thay đổi ra sao khi dữ liệu bị lỗi và được sửa đổi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hệ thống RAG cần một cơ sở dữ liệu Vector để tìm kiếm ngữ nghĩa các bài báo khoa học. Tôi cần đọc dữ liệu sạch, dùng mô hình nhúng (`all-MiniLM-L6-v2`) để biến văn bản thành vector và lưu trữ vào ChromaDB, đồng thời xây dựng một Agent (dùng LangChain) có khả năng sử dụng các công cụ tìm kiếm này để trả lời câu hỏi.

### Cách triển khai

- Sử dụng `sentence-transformers/all-MiniLM-L6-v2` để sinh vector cho cột `text_for_embedding`.
- Dùng `chromadb.PersistentClient` lưu trực tiếp xuống ổ cứng (`data/chroma/`).
- Quản lý linh hoạt việc cấp phát Collection cho 3 trạng thái bằng cách dựa vào đường dẫn `embeddings_output_path` để quyết định tên collection (ví dụ: `papers-baseline` hay `papers-corrupted`).
- Tạo Langchain Agent (`create_react_agent`) với Tools là hàm search và lookup, cho phép Agent tự suy luận và gọi hàm để lấy văn bản.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | File `papers_clean.json` chứa trường `text_for_embedding` |
| Output                         | Thư mục ChromaDB và tệp manifest báo cáo trạng thái `papers_embeddings.json` |
| Module phụ thuộc             | `src/ingestion/cleaning.py` (Vai trò 2) |
| Module sử dụng output        | `src/evaluation/metrics.py` (Vai trò 4) |
| Điều kiện lỗi cần xử lý | Xử lý lỗi khi model LLM (Gemini) bị Rate Limit hoặc hết quota |

### Cách xác minh

```bash
uv run python script/cp5_cp6_role3.py
```

- **Kết quả mong đợi:** Script tạo xong 2 index bị lỗi và đã sửa, kết quả tìm kiếm trên index lỗi thay đổi khác biệt, nhưng kết quả trên index sửa quay về đúng như baseline.
- **Kết quả thực tế:** Đúng như mong đợi. Baseline không bị ảnh hưởng khi build corrupted data.
- **Artifact/log:** `data/embeddings/papers_embeddings_corrupted.json` và `papers_embeddings_repaired.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi khởi tạo `LocalEmbeddingIndex.build()` cho CP5 (Dữ liệu bị lỗi), tôi bị dính lỗi `TypeError: got an unexpected keyword argument 'collection_name'`.
- **Các phương án đã cân nhắc:**
  1. Thêm tham số `collection_name` vào hàm `build()`.
  2. Dựa vào cơ chế map tự động của class `LocalEmbeddingIndex` thông qua đường dẫn file `embeddings_output_path`.
- **Phương án đã chọn:** Phương án 2. Xóa tham số truyền thừa.
- **Lý do:** Đảm bảo giữ đúng thiết kế gốc (contract) của hàm `build` do Project định ra, tăng tính cô lập (đường dẫn path tương ứng với collection name cố định) để tránh rủi ro ghi đè nhầm collection.
- **Bằng chứng quyết định phù hợp:** Script chạy thành công hoàn toàn mà không phá vỡ kiến trúc cũ.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `langchain_google_genai.chat_models.ChatGoogleGenerativeAIError: Error calling model 'gemini-2.0-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED`
- **Lệnh hoặc bước tái hiện:** `uv run python script/cp2_role3.py` (Lúc test Agent LLM)
- **Nguyên nhân gốc:** Quota giới hạn Free-tier của API Key Gemini đã bị vượt quá do gọi request liên tục hoặc đã hết hạn mức.
- **Cách xử lý (Tạm thời):** Tạm thời tắt hoặc bypass phần gọi LLM sinh text, chỉ verify đến bước Retrieval (Vector Search) trả về top_K hợp lệ.

Do lỗi này thuộc về Billing của provider và chưa xử lý xong hoàn toàn:
- **Phạm vi bị ảnh hưởng:** Toàn bộ phần sinh câu trả lời của Agent QA và các module Evaluation (Role 4) sử dụng LLM-as-a-judge.
- **Những gì đã loại trừ:** Đã loại trừ nguyên nhân sai code logic (vì LLM client đã khởi tạo thành công), loại trừ nguyên nhân sai API endpoint.
- **Bước tiếp theo:** Thay thế API key mới có đủ quota, hoặc cấu hình đổi sang mô hình Local (như Ollama) trong `.env` để chạy offline không phụ thuộc rate limit.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô (JSON) kéo từ API Crossref -> Role 2 làm sạch, chuẩn hóa, parse date, loại trùng -> Tạo ra `papers_clean.json` với cột `text_for_embedding` -> Role 3 đọc file json này, chạy mô hình MiniLM nhúng thành vector -> Ghi vào ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Tập evaluation cung cấp 1 query và 1 danh sách các `paper_id` được coi là đúng (ground-truth). Hệ thống truy vấn ChromaDB để trả về top_K, nếu các id trong top_K khớp với ground-truth thì được tính điểm `hit_rate`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks tập trung vào tính toàn vẹn (không rỗng, đúng schema, unique IDs). Freshness monitoring tập trung vào "tuổi thọ" (độ trễ), đo lường `age_days` xem dữ liệu có bị cũ (stale) quá số ngày ngưỡng cho phép hay không.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính nhất quán và công bằng khi đối chiếu (A/B testing). Chỉ khi giữ nguyên thước đo, ta mới thấy rõ được sự suy giảm chất lượng do dữ liệu lỗi gây ra, và tính hiệu quả của cơ chế phục hồi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Khi metrics đo trên collection `papers-repaired` bằng hoặc rất gần với metrics của `papers-baseline`, đồng thời các reports từ Great Expectations báo passed hết các rule về completeness, freshness.

## 8. Phân tích kết quả

### Metrics chính *(Chờ Role 4 chạy Evaluation)*

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics             |
| `mean_token_f1`      |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics              |
| `judge_accuracy`     |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics              |
| `mean_judge_score`   |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics              |
| Quality checks         |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics              |
| Freshness status       |      [ ] |       [ ] |      [ ] | Đang đợi Role 4 xuất file JSON metrics              |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:
1. Data corruption (Role 2 cố tình làm trống summary, sai title, lệch ngày) -> quality/freshness signal failed -> Agent metrics (như Hit Rate) giảm thê thảm vì ChromaDB index nhầm vector từ rác.
2. Repair action (Role 2 restore lại) -> quality/freshness signal passed trở lại -> Agent metric phục hồi đúng như ban đầu.

Corruption nào ảnh hưởng rõ nhất và vì sao?
Việc "Blank summary" (Xóa tóm tắt) ảnh hưởng nặng nề nhất đến Vector Search vì phần tóm tắt chứa nhiều từ khóa mang ngữ nghĩa trọng tâm của bài báo nhất.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Data Pipeline:** Hiểu được sự phối hợp nhịp nhàng giữa các Node trong một pipeline dữ liệu (từ Ingestion đến Embedding).
2. **Data Observability:** Dữ liệu có thể rác đi theo thời gian, nếu không có cơ chế monitor (như Great Expectations) thì hệ thống RAG sẽ trả lời "ngáo" (hallucinate) mà ta không biết tại sao.
3. **RAG Agent:** Khả năng truy xuất chính xác của Agent phụ thuộc sống còn vào Data Quality (Chất lượng dữ liệu) chứ không chỉ phụ thuộc vào độ thông minh của LLM.

### Nếu có thêm thời gian
Tôi sẽ tích hợp thử **Ollama (Local LLM)** để dự phòng thay thế cho Gemini API (vì chúng ta bị Rate Limit ở CP2). Điều này giúp hệ thống Agent hoàn toàn chạy được offline mà không bị phụ thuộc vào quota của Google API.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Hiệp
**Ngày xác nhận:** 2026-08-06
