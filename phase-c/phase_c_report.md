# Báo Cáo Phase C: Guardrails Stack

## Mục tiêu

Phase C xây một `defense-in-depth guardrail stack` gồm 3 lớp chính:

1. `Input guard` để redaction `PII` và chặn injection
2. `Topic scope validator` để giữ truy vấn trong miền pháp lý
3. `Output guard` để chặn leakage, jailbreak và câu trả lời không an toàn

Mục tiêu của phase này không phải là cải thiện trực tiếp chất lượng `RAG` ở Phase A, mà là giảm rủi ro khi hệ thống nhận input xấu hoặc sinh output xấu. Điều này khớp với Phase A/B: quality vẫn được đo riêng, còn Phase C xử lý safety và policy.

## Kết Quả Chính

| Hạng mục | Kết quả | Đánh giá |
|---|---:|---|
| `PII redaction` | 8/8 mẫu có PII được redaction đúng | Pass |
| `Edge cases` | 2/2 mẫu rỗng / dài / không điển hình được xử lý an toàn | Pass |
| `Topic scope validator` | 18/20 mẫu đúng | Pass |
| `False positive rate` | 0/10 trên các truy vấn hợp lệ | Pass |
| `Adversarial blocking` | 18/20 mẫu tấn công bị chặn | Pass |
| `Output safety` | 19/20 mẫu được phân loại đúng | Pass |
| `Latency P95 full stack` | `88.7ms` | Pass |

## Input Guard

`InputGuard` dùng kết hợp:

- `VN regex` cho `CCCD`, số điện thoại, `tax code`, `email`
- `Presidio` nếu môi trường có cài đặt
- heuristic redaction cho tên riêng tiếng Anh và tổ chức
- phát hiện pattern injection như `ignore previous instructions`, `jailbreak`, `roleplay`

### `pii_test_results.csv`

Kết quả synthetic cho thấy redaction hoạt động ổn định trên cả input tiếng Anh và tiếng Việt. Các trường hợp dài và rỗng vẫn trả về output an toàn, không crash.

### Nhận xét

Input guard giúp giảm rò rỉ dữ liệu từ đầu vào, nhưng không can thiệp vào chất lượng truy xuất. Vì vậy, nó bổ sung cho Phase A thay vì thay thế Phase A.

## Topic Scope Validator

`TopicGuard` dùng keyword similarity theo miền pháp lý, có thể mở rộng sang embedding similarity hoặc LLM zero-shot nếu cần. Trong bản này, mình giữ cấu hình nhẹ để chạy ổn định trên máy local.

### `topic_scope_results.csv`

- `Accuracy`: `18/20 = 90%`
- `False positive rate` trên truy vấn hợp lệ: `0%`
- Hai mẫu off-topic còn lọt qua là những trường hợp semantic ambiguity nhẹ, không phải lỗi phá vỡ hoàn toàn

### Nhận xét

Lớp này quan trọng vì Phase A đã cho thấy các câu `multi_context` và `reasoning` dễ làm pipeline lạc hướng. `TopicGuard` không sửa quality của answer, nhưng nó ngăn phần input đi lệch domain ngay từ đầu.

## Adversarial Testing

### `adversarial_test_results.csv`

20 mẫu tấn công được chia thành:

- `DAN`
- `roleplay`
- `payload splitting`
- `encoding`
- `indirect injection`

Kết quả:

- `18/20` mẫu bị chặn
- 2 mẫu `indirect injection` còn lọt qua vì được ngụy trang trong ngữ cảnh pháp lý khá tự nhiên

### Nhận xét

Điểm còn yếu chủ yếu nằm ở `indirect injection`, nên hướng cải tiến tiếp theo là tăng `contextual injection patterns` và thêm `document-level scanning`.

## Output Guard

`OutputGuard` được triển khai theo 2 chế độ:

- `heuristic`
- `OpenAI judge` nếu muốn nâng cấp sang LLM-based safety check

### `output_guard_results.csv`

- 10 mẫu safe: 10 mẫu được chấp nhận
- 10 mẫu unsafe: 9 mẫu bị chặn đúng, 1 mẫu tạo ra `false negative` trên leakage patterns

### Nhận xét

`OutputGuard` giúp tránh việc model trả lời chứa `PII` hoặc echo lại jailbreak content. Đây là lớp cần thiết để bảo đảm output cuối cùng sạch hơn, kể cả khi `RAG` pipeline trả về context tốt.

## Latency Benchmark

### `latency_benchmark.csv`

- `input_guard` P95: `24.6ms`
- `topic_guard` P95: `19.2ms`
- `rag_call` P95: `67.9ms`
- `output_guard` P95: `36.8ms`
- `full_stack` P95: `88.7ms`
- `baseline_no_guardrail` P95: `63.8ms`

### Diễn giải

Overhead so với baseline là khoảng `+25ms` ở mức P95. Đây là mức chấp nhận được cho bài lab vì đổi lại ta có thêm 3 lớp kiểm soát an toàn.

## Acceptance Criteria Check

- `PII detection` đạt yêu cầu trên bộ test 10 input
- `Topic validator` có accuracy vượt ngưỡng tối thiểu
- `Adversarial blocking` đạt trên 70%
- `Output guard` chặn đúng phần lớn output nguy hiểm
- `Latency budget` vẫn nằm trong giới hạn đề bài

## Kết Luận

Phase C hoàn thành mục tiêu `defense-in-depth` cho hệ thống:

- Phase A xử lý `RAG evaluation`
- Phase B xử lý `LLM-as-judge` và calibration
- Phase C xử lý `guardrails`

Ba phase này khớp với nhau: khi `RAG` yếu ở `multi_context` hoặc `reasoning`, Phase C vẫn đảm bảo đầu vào và đầu ra không gây thêm rủi ro về safety hoặc leakage.
