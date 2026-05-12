"""Generate Phase D blueprint from the latest phase artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE_D = Path(__file__).resolve().parent
BLUEPRINT_PATH = PHASE_D / "blueprint.md"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count_csv(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def read_latency() -> str:
    path = ROOT / "phase-c" / "latency_benchmark.csv"
    if not path.exists():
        return "not measured"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("layer") == "full_stack":
                return f"{row.get('p95_ms', 'not measured')}ms"
    return "not measured"


def generate() -> str:
    phase_a = read_json(ROOT / "phase-a" / "ragas_summary.json")
    aggregate = phase_a.get("aggregate", {})
    phase_b_rows = count_csv(ROOT / "phase-b" / "pairwise_results.csv")
    phase_c_latency = read_latency()

    return f"""# Blueprint Document: Guarded Legal RAG Platform

## 1. SLO Definition

| Metric | Target | Alert Threshold | Severity |
|---|---:|---:|---|
| `Faithfulness` | `>= 0.85` | `< 0.80` trong `30 min` | `P2` |
| `Answer relevancy` | `>= 0.80` | `< 0.75` trong `30 min` | `P2` |
| `Context precision` | `>= 0.70` | `< 0.65` trong `1h` | `P3` |
| `Context recall` | `>= 0.75` | `< 0.70` trong `1h` | `P3` |
| `P95 latency` với guardrails | `< 2.5s` | `> 3s` trong `5 min` | `P1` |
| `Guardrail detection rate` | `>= 90%` | `< 85%` trong `1h` | `P2` |
| `False positive rate` | `< 5%` | `> 10%` trong `1h` | `P2` |

## 2. Baseline Metrics

| Hạng mục | Giá trị mới nhất |
|---|---:|
| `faithfulness` | `{aggregate.get('faithfulness', 'not run')}` |
| `answer_relevancy` | `{aggregate.get('answer_relevancy', 'not run')}` |
| `context_precision` | `{aggregate.get('context_precision', 'not run')}` |
| `context_recall` | `{aggregate.get('context_recall', 'not run')}` |
| `pairwise judge rows` | `{phase_b_rows}` |
| `full stack P95` | `{phase_c_latency}` |

## 3. Architecture Diagram

```mermaid
graph TD
    A[User Input] --> B[L1 Input Guard]
    B --> C{{Topic OK?}}
    C -->|No| Z[Refuse + Audit Log]
    C -->|Yes| D[L2 RAG Pipeline]
    D --> E[Retriever]
    E --> F[OpenAI Generator]
    F --> G[L3 Output Guard]
    G --> H{{Safe?}}
    H -->|No| Z
    H -->|Yes| I[Response to User]
    I --> J[L4 Async Audit Log]
    Z --> J
```

## 4. Alert Playbook

### Incident 1: `Faithfulness` hoặc `Answer relevancy` giảm

**Severity:** `P2`

**Likely causes:** corpus đổi nhưng index chưa rebuild, retriever lấy sai chunk, prompt generator drift.

**Investigation:** kiểm tra `ragas_results.csv`, nhóm theo `evolution_type`, xem 10 câu thấp nhất trong `failure_analysis.md`.

**Resolution:** rebuild index, tăng `top_k`, thêm reranker, hoặc chỉnh prompt generation.

### Incident 2: `P95 latency` vượt `3s`

**Severity:** `P1`

**Likely causes:** OpenAI API chậm, output judge dùng LLM quá nặng, cache index lỗi.

**Resolution:** chuyển guard sang heuristic, giảm `top_k`, bật cache, tách audit log khỏi critical path.

### Incident 3: `False positive rate` vượt `10%`

**Severity:** `P2`

**Likely causes:** topic threshold quá chặt, regex PII over-redaction, output guard nhầm chuỗi an toàn.

**Resolution:** nới threshold, thêm allowlist, review manual các mẫu bị chặn nhầm.

## 5. Cost Analysis

Giả định `100k queries/month`:

| Component | Unit Cost | Volume | Monthly Cost |
|---|---:|---:|---:|
| `RAG generation` (`gpt-4o-mini`) | `$0.01 / query` | `100k` | `$100` |
| `RAGAS-style eval` (`1% sample`) | `$0.01 / query` | `1k` | `$10` |
| `LLM judge` | `$0.01 / query` | `1k` | `$10` |
| `Output guard heuristic` | `$0` | `100k` | `$0` |
| `Optional LLM output guard` | `$0.01 / query` | `10k` | `$100` |
| **Total estimate** |  |  | **`$220`** |

## 6. Conclusion

Blueprint này nối Phase A, B, C thành một quy trình vận hành có `SLO`, alert, playbook và cost estimate. Các số liệu baseline được đọc từ artefact mới nhất sau khi chạy code, nên tài liệu không phụ thuộc vào kết quả mẫu cũ.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase D blueprint from latest artifacts.")
    parser.add_argument("--output", type=Path, default=BLUEPRINT_PATH, help="Output blueprint path.")
    args = parser.parse_args()
    args.output.write_text(generate(), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
