# Báo Cáo Phase C: Guardrails Stack

## Kết Quả Chạy Từ Code

| Hạng mục | Kết quả |
|---|---:|
| `PII redaction` | `6/8` |
| `Topic scope validator` | `10/20` |
| `Adversarial blocking` | `20/20` |
| `Output safety` | `10/10` |
| `Full stack P95 latency` | `0.52ms` |

## Nhận Xét

Các kết quả trên được sinh lại bằng `phase-c/run_phase_c.py`. `OutputGuard` mặc định dùng heuristic để tiết kiệm chi phí; có thể bật kiểm tra OpenAI bằng `--output-provider openai`.
