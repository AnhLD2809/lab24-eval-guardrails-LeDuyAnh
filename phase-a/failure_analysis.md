# Phân Tích Lỗi

## 10 câu hỏi tệ nhất

| rank | evolution_type | avg_score | faithfulness | answer_relevancy | context_precision | context_recall | question |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | reasoning | 0.3703 | 1.0000 | 0.0000 | 0.0720 | 0.4091 | Theo Điều 112, trong trường hợp nào nghỉ được áp dụng? |
| 2 | simple | 0.3988 | 1.0000 | 0.0000 | 0.1408 | 0.4545 | Theo Điều 1, nội dung quy định về phạm vi điều chỉnh là gì? |
| 3 | reasoning | 0.4009 | 1.0000 | 0.1064 | 0.0526 | 0.4444 | Theo Điều 185, quy định cụ thể về hội là bao nhiêu hoặc như thế nào? |
| 4 | multi_context | 0.404 | 1.0000 | 0.0000 | 0.1714 | 0.4444 | Điều 1 (Phạm vi điều chỉnh) và Điều 2 (Đối tượng áp dụng) cùng làm rõ nội dung gì trong chương này? |
| 5 | reasoning | 0.4045 | 1.0000 | 0.1818 | 0.0364 | 0.4000 | Theo Điều 54, quy định cụ thể về doanh là bao nhiêu hoặc như thế nào? |
| 6 | multi_context | 0.4077 | 1.0000 | 0.0000 | 0.0890 | 0.5417 | Điều 2 (Đối tượng áp dụng) và Điều 3 (Giải thích từ ngữ) cùng làm rõ nội dung gì trong chương này? |
| 7 | reasoning | 0.4365 | 1.0000 | 0.1429 | 0.0696 | 0.5333 | Theo Điều 55, quy định cụ thể về hợp là bao nhiêu hoặc như thế nào? |
| 8 | reasoning | 0.505 | 1.0000 | 0.2857 | 0.1343 | 0.6000 | Theo Điều 35, quy định cụ thể về quyền là bao nhiêu hoặc như thế nào? |
| 9 | reasoning | 0.5064 | 1.0000 | 0.0000 | 0.0921 | 0.9333 | Theo Điều 169, quy định cụ thể về tuổi là bao nhiêu hoặc như thế nào? |
| 10 | reasoning | 0.5124 | 1.0000 | 0.7500 | 0.0737 | 0.2258 | Theo Điều 113, quy định cụ thể về nghỉ là bao nhiêu hoặc như thế nào? |

## Các Cluster Đã Xác Định

### Cluster C1: Lỗi parsing điều kiện / single-hop reasoning

**Root cause:** Lỗi parsing điều kiện / single-hop reasoning.
**Proposed fix:** Viết lại câu hỏi sao cho mô hình có một điều kiện pháp lý rõ ràng để trích xuất, hoặc bổ sung một bộ truy xuất chuyên biệt dành cho các mệnh đề chứa số liệu và điều kiện.

**Ví dụ:**
- [reasoning] Theo Điều 112, trong trường hợp nào nghỉ được áp dụng? | avg=0.3703 | worst=answer_relevancy
- [reasoning] Theo Điều 185, quy định cụ thể về hội là bao nhiêu hoặc như thế nào? | avg=0.4009 | worst=context_precision
- [reasoning] Theo Điều 54, quy định cụ thể về doanh là bao nhiêu hoặc như thế nào? | avg=0.4045 | worst=context_precision

### Cluster C2: Retriever bỏ sót ngữ cảnh chính

**Root cause:** Retriever bỏ sót ngữ cảnh chính.
**Proposed fix:** Cải thiện chunking hoặc tăng top-k trước khi generation; kiểm tra xem bằng chứng có bị tách sang nhiều chunk hay không.

**Ví dụ:**
- [simple] Theo Điều 1, nội dung quy định về phạm vi điều chỉnh là gì? | avg=0.3988 | worst=answer_relevancy

### Cluster C3: Lỗi multi-hop reasoning

**Root cause:** Lỗi multi-hop reasoning.
**Proposed fix:** Truy xuất nhiều hơn một đoạn hỗ trợ và yêu cầu mô hình kết hợp chúng trước khi đưa ra câu trả lời.

**Ví dụ:**
- [multi_context] Điều 1 (Phạm vi điều chỉnh) và Điều 2 (Đối tượng áp dụng) cùng làm rõ nội dung gì trong chương này? | avg=0.404 | worst=answer_relevancy
- [multi_context] Điều 2 (Đối tượng áp dụng) và Điều 3 (Giải thích từ ngữ) cùng làm rõ nội dung gì trong chương này? | avg=0.4077 | worst=answer_relevancy