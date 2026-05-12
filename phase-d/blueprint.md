# Blueprint Document: Guarded Legal RAG Platform

## 1. SLO Definition

| Metric | Target | Alert Threshold | Severity |
|---|---:|---:|---|
| `Faithfulness` | `>= 0.85` | `< 0.80` trong `30 min` | `P2` |
| `Answer relevancy` | `>= 0.80` | `< 0.75` trong `30 min` | `P2` |
| `Context precision` | `>= 0.70` | `< 0.65` trong `1h` | `P3` |
| `Context recall` | `>= 0.75` | `< 0.70` trong `1h` | `P3` |
| `P95 latency` vá»›i guardrails | `< 2.5s` | `> 3s` trong `5 min` | `P1` |
| `Guardrail detection rate` | `>= 90%` | `< 85%` trong `1h` | `P2` |
| `False positive rate` | `< 5%` | `> 10%` trong `1h` | `P2` |

## 2. Baseline Metrics

| Háº¡ng má»¥c | GiÃ¡ trá»‹ má»›i nháº¥t |
|---|---:|
| `faithfulness` | `1.0` |
| `answer_relevancy` | `0.6912` |
| `context_precision` | `0.1897` |
| `context_recall` | `0.784` |
| `pairwise judge rows` | `30` |
| `full stack P95` | `0.52ms` |

## 3. Architecture Diagram

```mermaid
graph TD
    A[User Input] --> B[L1 Input Guard]
    B --> C{Topic OK?}
    C -->|No| Z[Refuse + Audit Log]
    C -->|Yes| D[L2 RAG Pipeline]
    D --> E[Retriever]
    E --> F[OpenAI Generator]
    F --> G[L3 Output Guard]
    G --> H{Safe?}
    H -->|No| Z
    H -->|Yes| I[Response to User]
    I --> J[L4 Async Audit Log]
    Z --> J
```

## 4. Alert Playbook

### Incident 1: `Faithfulness` hoáº·c `Answer relevancy` giáº£m

**Severity:** `P2`

**Likely causes:** corpus Ä‘á»•i nhÆ°ng index chÆ°a rebuild, retriever láº¥y sai chunk, prompt generator drift.

**Investigation:** kiá»ƒm tra `ragas_results.csv`, nhÃ³m theo `evolution_type`, xem 10 cÃ¢u tháº¥p nháº¥t trong `failure_analysis.md`.

**Resolution:** rebuild index, tÄƒng `top_k`, thÃªm reranker, hoáº·c chá»‰nh prompt generation.

### Incident 2: `P95 latency` vÆ°á»£t `3s`

**Severity:** `P1`

**Likely causes:** OpenAI API cháº­m, output judge dÃ¹ng LLM quÃ¡ náº·ng, cache index lá»—i.

**Resolution:** chuyá»ƒn guard sang heuristic, giáº£m `top_k`, báº­t cache, tÃ¡ch audit log khá»i critical path.

### Incident 3: `False positive rate` vÆ°á»£t `10%`

**Severity:** `P2`

**Likely causes:** topic threshold quÃ¡ cháº·t, regex PII over-redaction, output guard nháº§m chuá»—i an toÃ n.

**Resolution:** ná»›i threshold, thÃªm allowlist, review manual cÃ¡c máº«u bá»‹ cháº·n nháº§m.

## 5. Cost Analysis

Giáº£ Ä‘á»‹nh `100k queries/month`:

| Component | Unit Cost | Volume | Monthly Cost |
|---|---:|---:|---:|
| `RAG generation` (`gpt-4o-mini`) | `$0.01 / query` | `100k` | `$100` |
| `RAGAS-style eval` (`1% sample`) | `$0.01 / query` | `1k` | `$10` |
| `LLM judge` | `$0.01 / query` | `1k` | `$10` |
| `Output guard heuristic` | `$0` | `100k` | `$0` |
| `Optional LLM output guard` | `$0.01 / query` | `10k` | `$100` |
| **Total estimate** |  |  | **`$220`** |

## 6. Conclusion

Blueprint nÃ y ná»‘i Phase A, B, C thÃ nh má»™t quy trÃ¬nh váº­n hÃ nh cÃ³ `SLO`, alert, playbook vÃ  cost estimate. CÃ¡c sá»‘ liá»‡u baseline Ä‘Æ°á»£c Ä‘á»c tá»« artefact má»›i nháº¥t sau khi cháº¡y code, nÃªn tÃ i liá»‡u khÃ´ng phá»¥ thuá»™c vÃ o káº¿t quáº£ máº«u cÅ©.

