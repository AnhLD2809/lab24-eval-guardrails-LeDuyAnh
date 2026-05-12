# Lab 24 - Full Evaluation & Guardrail System

## Overview

Repo này xây một hệ thống `Legal RAG` cho corpus `data/luat_lao_dong.md`, gồm retrieval/generation, đánh giá `RAGAS-style`, `LLM-as-judge`, calibration với `Cohen's kappa`, guardrails nhiều lớp và blueprint vận hành. Phase A tạo test set 50 câu hỏi cho ba nhóm `simple`, `reasoning`, `multi_context`; Phase B so sánh hai phiên bản trả lời bằng `swap-and-average`; Phase C kiểm tra `PII`, `topic scope`, adversarial input, output safety và latency; Phase D tổng hợp thành tài liệu vận hành có `SLO`, incident playbook và cost analysis.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...
```

## Results Summary

### Phase A (RAGAS)

- Test set: `50` questions (`50% simple`, `24% reasoning`, `26% multi-context`)
- Faithfulness: `1.00` | AR: `0.69` | CP: `0.19` | CR: `0.78`
- Total eval cost: local run for submitted artifacts; OpenAI judge runner is available in `phase-a/openai_eval.py`
- Identified `3` failure clusters (see `phase-a/failure_analysis.md`)

### Phase B (LLM-Judge)

- Cohen's kappa vs human: `0.68` (`substantial agreement`)
- Position bias mitigated via `swap-and-average`
- Final pairwise distribution: `A=15`, `B=11`, `tie=4`
- Absolute scoring saved in `phase-b/absolute_scores.csv`
- Bias analysis saved in `phase-b/judge_bias_report.md`

### Phase C (Guardrails)

- PII detection handled across English/Vietnamese and mixed-format inputs
- Topic validator accuracy: `15/20`
- Adversarial defense: `18/20`
- Output safety: `10/10`
- Full-stack latency P95: `0.52ms`

### Phase D (Blueprint)

- Production blueprint: `phase-d/blueprint.md`
- Includes SLO table, Mermaid architecture diagram, alert playbook, release notes and monthly cost estimate.

## Lessons Learned

Nút thắt chính về chất lượng không nằm ở khả năng bám sát dữ kiện cơ bản (factual grounding), mà nằm ở trọng tâm truy xuất (retrieval) đối với các câu hỏi yêu cầu suy luận (reasoning) và đa ngữ cảnh (multi_context). Luồng RAG hiện tại xử lý rất tốt việc tra cứu điều khoản trực tiếp, nhưng với các câu hỏi pháp lý suy luận đa bước (multi-hop), hệ thống cần khả năng xếp hạng lại (reranking) tốt hơn, chỉ số top_k cao hơn và việc tổng hợp câu trả lời một cách rõ ràng hơn.

Phương pháp LLM-as-judge (dùng LLM làm giám khảo) rất hữu ích cho việc đánh giá trên quy mô lớn, nhưng cần có các biện pháp kiểm soát thiên kiến. Kỹ thuật hoán đổi và lấy trung bình (swap-and-average), chấm điểm tuyệt đối (absolute scoring) và hiệu chuẩn từ con người (human calibration) sẽ giúp bộ đánh giá trở nên đáng tin cậy hơn so với việc chỉ đưa ra quyết định ưu tiên một chiều duy nhất (one-pass preference decision).

Các cơ chế bảo vệ (Guardrails) nên được xem là một lớp an toàn độc lập chứ không phải để thay thế cho quá trình đánh giá (eval). Các lớp InputGuard, TopicGuard và OutputGuard giúp giảm thiểu rủi ro về quyền riêng tư, vi phạm phạm vi (scope) và các cuộc tấn công đánh lừa (adversarial), trong khi đó Giai đoạn A/B vẫn tiếp tục nhiệm vụ đo lường chất lượng của câu trả lời.