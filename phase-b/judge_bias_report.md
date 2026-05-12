# Báo Cáo Judge Bias

## Tóm Tắt Điều Hành

Kết quả calibration cho thấy có 2 loại `judge bias` lặp lại rõ nhất:

1. `position bias`
2. `length bias`

Sau `swap-and-average`, verdict cuối cùng cân bằng ở mức `A = 14`, `B = 14`, `tie = 2`, đây là tín hiệu tốt cho thấy ảnh hưởng của thứ tự đã được giảm đáng kể.

## Bảng Bias

| Bias | Evidence | Impact | Mitigation |
| --- | --- | --- | --- |
| `position bias` | `run1`: `A = 17`, `B = 12`, `tie = 1` so với `run2`: `A = 13`, `B = 15`, `tie = 2` | Câu trả lời được đặt trước vẫn có lợi thế nhẹ | Giữ `swap-and-average` và randomize thứ tự câu trả lời |
| `length bias` | Ở các mẫu chênh lệch vừa, câu dài hơn thắng `11/15` lần; ở các câu quá dài, win rate giảm còn `3/10` | Judge ưu tiên verbosity cho đến khi câu trả lời trở nên rối | Giới hạn độ dài câu trả lời và thêm ví dụ ngắn gọn vào `rubric` |

## Ý Nghĩa

- Judge chưa hỏng nặng.
- Judge vẫn nhạy với thứ tự và độ dài.
- Kế hoạch mitigation là đủ cho bài tập học phần, nhưng chưa thể xem là production-grade.
