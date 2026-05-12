# Kết Quả Phân Tích Kappa

Sample size: 10 human-labeled comparisons.

## Tóm Tắt

- Phân phối nhãn human: `A = 7`, `B = 2`, `tie = 1`
- Phân phối nhãn judge: `A = 7`, `B = 2`, `tie = 1`
- Cohen's kappa: `0.57`
- Diễn giải: `Moderate agreement`

## Nhận Định

Judge hiện đủ ổn để dùng cho calibration, nhưng chưa đủ ổn định để xem như proxy production cho human preference.

## Phân Tích Root Cause

- `rubric` vẫn còn khoảng trống cho bất đồng giữa `tie` và `A` khi hai câu trả lời đều đúng nhưng khác độ concise.
- `position bias` vẫn xuất hiện ở một vài mẫu borderline dù đã dùng `swap-and-average`.
- Bộ calibration khá nhỏ, nên chỉ cần một vài disagreement là score dao động rõ.

## Bước Tiếp Theo

- Thêm 10 đến 20 nhãn calibration nữa trước khi siết decision threshold.
- Bổ sung 2 ví dụ neo cho lớp `tie`.
- Giữ `swap-and-average`, nhưng bổ sung tie policy chặt hơn cho các câu gần như tương đương.
