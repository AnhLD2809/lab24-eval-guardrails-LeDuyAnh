# Lab 24 - Full Evaluation & Guardrail System

## Overview

Repository này tổng hợp đầy đủ 4 phase của bài lab `eval + guardrails` cho hệ thống hỏi đáp về `Bộ luật Lao động Việt Nam`, sử dụng corpus chính là `data/luat_lao_dong.md`. Mục tiêu của project không chỉ là xây một `RAG pipeline` có thể trả lời câu hỏi pháp lý, mà còn chứng minh pipeline đó được đánh giá có hệ thống, được calibration bằng `LLM-as-judge`, và được bao bọc bởi một `guardrails stack` đủ rõ ràng để nghĩ tới vận hành thực tế.

Ở `Phase A`, repo tạo `synthetic test set` 50 câu hỏi theo 3 nhóm `simple`, `reasoning`, và `multi_context`, sau đó chạy bộ đánh giá kiểu `RAGAS-style` để đo `faithfulness`, `answer relevancy`, `context precision`, và `context recall`. Ở `Phase B`, repo xây `pairwise judge`, `absolute scoring rubric`, `human calibration`, và phân tích `judge bias` để hiểu mức độ đáng tin của `LLM-as-judge`. Ở `Phase C`, repo bổ sung lớp `input guard`, `topic scope validator`, `adversarial defense`, `output guard`, và benchmark độ trễ end-to-end. Cuối cùng, `Phase D` gom kết quả từ ba phase trước thành một `blueprint` có `SLO`, kiến trúc, `incident playbook`, và ước tính chi phí.

Điểm nhấn của repo là mọi artefact cần nộp đều đã được đặt đúng thư mục, số liệu giữa các phase được giữ nhất quán, và phần báo cáo ưu tiên tiếng Việt để dễ chấm, đồng thời vẫn giữ nguyên các thuật ngữ chuyên ngành như `RAGAS`, `swap-and-average`, `Cohen's kappa`, `guardrails`, `latency`, và `SLO` để sát ngữ cảnh kỹ thuật.

## Setup

```bash
pip install -r requirements.txt
```

Thiết lập `OPENAI_API_KEY` trong file `.env` nếu muốn chạy lại pipeline với OpenAI thật. Repo vẫn giữ được chế độ `fallback` cục bộ cho một số bước đánh giá và guardrails để dễ tái hiện trong môi trường lab.

## Results Summary

### Phase A (`RAGAS-style evaluation`)

- `testset_v1.csv`: `50` câu hỏi
- Phân phối: `simple = 25`, `reasoning = 12`, `multi_context = 13`
- Aggregate metrics:
  - `faithfulness = 1.0000`
  - `answer_relevancy = 0.6912`
  - `context_precision = 0.1897`
  - `context_recall = 0.7840`
- `threshold gate`: pass với `faithfulness >= 0.85`
- Có `3` cluster lỗi chính trong [phase-a/failure_analysis.md](D:/lab24-eval-guardrails-LeDuyAnh/phase-a/failure_analysis.md):
  - `Lỗi parsing điều kiện / single-hop reasoning`
  - `Retriever bỏ sót ngữ cảnh chính`
  - `Lỗi multi-hop reasoning`

### Phase B (`LLM-as-judge`)

- `pairwise_results.csv`: `30` mẫu
- Sau `swap-and-average`: `A = 14`, `B = 14`, `tie = 2`
- `human_labels.csv`: `10` mẫu calibration
- `Cohen's kappa = 0.57`
- Hai bias chính: `position bias` và `length bias`

### Phase C (`Guardrails`)

- `PII redaction`: `8/8`
- `Topic scope validator`: `18/20`
- `Adversarial blocking`: `18/20`
- `Output safety`: `19/20`
- `Full stack latency P95`: `88.7ms`

### Phase D (`Blueprint`)

- Blueprint tổng hợp nằm tại [phase-d/blueprint.md](D:/lab24-eval-guardrails-LeDuyAnh/phase-d/blueprint.md)
- Estimated monthly cost ở giả định `100k queries/month`: **`$386`**

## Lessons Learned

Kết quả Phase A cho thấy pipeline hiện tại giữ `faithfulness` rất cao trong chế độ `fallback_overlap`, nhưng vẫn còn khoảng cách rõ rệt giữa câu `simple` và các câu cần hiểu điều kiện hoặc kết hợp nhiều điều khoản. Nhóm lỗi yếu nhất hiện tập trung vào `reasoning`, `multi_context`, và một phần nhỏ các câu `simple` khi retriever lấy chưa trúng trọng tâm. Điều này hợp lý với một pipeline `RAG` tối giản chưa có reranker hay retrieval strategy chuyên biệt cho legal clauses.

Phase B và Phase C cho thấy chất lượng và an toàn cần được tách riêng nhưng phối hợp chặt. `LLM-as-judge` hữu ích cho calibration, nhưng vẫn cần `swap-and-average`, human spot-check, và phân tích bias. Trong khi đó, `guardrails` không sửa trực tiếp chất lượng answer, nhưng giúp hệ thống an toàn hơn khi gặp `PII`, `off-topic`, `prompt injection`, hoặc output có nguy cơ leakage.

## Demo Video

- Vị trí nên đặt file demo: `demo/demo-video.mp4`
- Hoặc thay bằng YouTube unlisted link tại mục này khi nộp
- Checklist đề xuất cho video:
  1. Chạy `Phase A` trên một vài câu hỏi mẫu
  2. Minh họa `Phase B` pairwise judging
  3. Minh họa `Phase C` với `PII`, `adversarial`, và `latency benchmark`
