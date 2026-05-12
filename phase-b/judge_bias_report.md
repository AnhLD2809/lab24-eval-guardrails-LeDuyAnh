# Báo Cáo Bias Phase B

## Tóm Tắt

- Số cặp đã judge: `30`
- Phân phối sau `swap-and-average`: `A=15`, `B=11`, `tie=4`
- Calibration sample: `10` cặp
- `Cohen's kappa = 0.68`, mức `substantial agreement`

## Bias 1: Position Bias

`A` thắng ở lượt đầu `17/30` lần, tương đương `56.7%`. Tỷ lệ này hơi cao hơn mốc cân bằng 50%, nhưng chưa vượt mức cảnh báo lớn. Sau khi áp dụng `swap-and-average`, phân phối cuối giảm độ lệch vị trí và giữ lại `4` trường hợp `tie` khi hai lượt judge không đồng thuận.

## Bias 2: Length Bias

`answer_a` thường đầy đủ hơn vì lấy từ câu trả lời của `RAG pipeline`, trong khi `answer_b` là bản tóm tắt trực tiếp từ context. Các dòng `absolute_scores.csv` cho thấy câu trả lời dài hơn thường có `helpfulness` cao hơn, còn câu ngắn hơn có `conciseness` tốt hơn. Điều này cho thấy judge có xu hướng cân bằng giữa độ đầy đủ và độ ngắn gọn, nhưng vẫn cần kiểm soát bằng rubric 4 chiều.

## Mitigation

- Luôn chạy `swap-and-average` để giảm `position bias`.
- Dùng `absolute scoring` theo 4 chiều: `accuracy`, `relevance`, `conciseness`, `helpfulness`.
- Giữ `human_labels.csv` làm calibration sample để theo dõi `Cohen's kappa`.
- Với các cặp `tie`, ưu tiên manual review thay vì ép chọn A/B.

## Kết Luận

Judge đạt mức đồng thuận đủ tốt cho bài lab và có cơ chế giảm bias rõ ràng. Hai rủi ro cần theo dõi tiếp là `position bias` nhẹ và `length bias` khi một câu trả lời dài hơn đáng kể.
