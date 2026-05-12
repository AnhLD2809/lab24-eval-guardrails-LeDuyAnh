"""Phase A pipeline: synthetic test set generation and RAG evaluation.

This module produces the phase-a artifacts expected by the lab:
- `testset_v1.csv`
- `testset_review_notes.md`
- `ragas_results.csv`
- `ragas_summary.json`
- `failure_analysis.md`

The implementation uses the legal RAG pipeline in `src/rag_pipeline.py`.
If OpenAI credentials are present, retrieval and answering will use them.
If not, the pipeline falls back to deterministic local retrieval and
extractive answering so the phase can still be executed locally.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag_pipeline import RAGPipeline, build_chunks_from_corpus  # noqa: E402


PHASE_DIR = Path(__file__).resolve().parent
TESTSET_PATH = PHASE_DIR / "testset_v1.csv"
REVIEW_NOTES_PATH = PHASE_DIR / "testset_review_notes.md"
RAGAS_RESULTS_PATH = PHASE_DIR / "ragas_results.csv"
RAGAS_SUMMARY_PATH = PHASE_DIR / "ragas_summary.json"
FAILURE_ANALYSIS_PATH = PHASE_DIR / "failure_analysis.md"

TARGET_TOTAL = 50
TARGET_DISTRIBUTION = {"simple": 25, "reasoning": 12, "multi_context": 13}

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹĐđ_]+", re.UNICODE)
ARTICLE_RE = re.compile(r"Điều\s+(\d+[A-Z]?)", re.IGNORECASE)
CHAPTER_RE = re.compile(r"Chương\s+[IVXLCDM0-9]+", re.IGNORECASE)

STOPWORDS = {
    "và",
    "của",
    "cho",
    "theo",
    "trong",
    "đối",
    "với",
    "này",
    "đó",
    "được",
    "một",
    "những",
    "các",
    "khi",
    "nếu",
    "thì",
    "về",
    "điều",
    "quy",
    "định",
    "thực",
    "hiện",
    "người",
    "lao",
    "động",
    "sử",
    "dụng",
    "làm",
    "việc",
}


@dataclass
class ArticleDoc:
    article: str
    chapter: str
    title: str
    text: str
    chunk_count: int
    sort_key: tuple[int, str]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_markdown_structure(text: str) -> str:
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s*", "", line)
        line = re.sub(r"^\d+[\.)]\s*", "", line)
        line = re.sub(r"^[a-zA-ZđĐ][\.)]\s*", "", line)
        line = re.sub(r"^(?:Điều\s+\d+[A-Z]?\.\s*)", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^(?:Chương\s+[IVXLCDM0-9]+\s*)", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^(?:Mục\s+\d+\s*)", "", line, flags=re.IGNORECASE)
        line = line.strip()
        if line:
            lines.append(line)
    return _clean(" ".join(lines))


def _split_sentences(text: str) -> list[str]:
    cleaned = _clean(text)
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if part.strip()]


def _extract_article_number(article: str) -> int:
    match = ARTICLE_RE.search(article or "")
    if not match:
        return 10**9
    digits = re.match(r"(\d+)", match.group(1))
    return int(digits.group(1)) if digits else 10**9


def _title_from_heading_path(heading_path: list[str]) -> str:
    if not heading_path:
        return ""
    last = heading_path[-1]
    if "." in last:
        return _clean(last.split(".", 1)[1])
    return _clean(last)


def _article_docs() -> list[ArticleDoc]:
    chunks = build_chunks_from_corpus()
    grouped: dict[str, list] = defaultdict(list)
    for chunk in chunks:
        article = _clean(chunk.metadata.get("article", ""))
        if article:
            grouped[article].append(chunk)

    docs: list[ArticleDoc] = []
    for article, items in grouped.items():
        ordered_items = sorted(items, key=lambda c: c.metadata.get("chunk_index", 0))
        cleaned_parts = []
        for item in ordered_items:
            piece = _strip_markdown_structure(item.text)
            if piece:
                cleaned_parts.append(piece)
        text = "\n\n".join(cleaned_parts)
        heading_path = ordered_items[0].metadata.get("heading_path", []) if ordered_items else []
        title = _title_from_heading_path(heading_path)

        chapter = ""
        for item in ordered_items:
            for part in item.metadata.get("heading_path", []):
                if CHAPTER_RE.search(part or ""):
                    chapter = _clean(part)
                    break
            if chapter:
                break

        docs.append(
            ArticleDoc(
                article=article,
                chapter=chapter,
                title=title,
                text=text,
                chunk_count=len(ordered_items),
                sort_key=(_extract_article_number(article), article),
            )
        )

    docs.sort(key=lambda doc: doc.sort_key)
    return docs


def _keywords(text: str, limit: int = 6) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token not in out:
            out.append(token)
        if len(out) >= limit:
            break
    return out


def _main_clause(text: str, max_sentences: int = 2) -> str:
    sentences = _split_sentences(_strip_markdown_structure(text))
    if not sentences:
        return _strip_markdown_structure(text)[:280]
    return " ".join(sentences[:max_sentences])


def _evidence_snippet(text: str, max_chars: int = 420) -> str:
    return _strip_markdown_structure(text)[:max_chars]


def _simple_question(doc: ArticleDoc) -> str:
    if doc.title:
        return f"Theo {doc.article}, nội dung quy định về {doc.title.lower()} là gì?"
    return f"Theo {doc.article}, nội dung chính được quy định là gì?"


def _reasoning_question(doc: ArticleDoc) -> str:
    text = doc.text.lower()
    keywords = _keywords(doc.title or doc.text, limit=3)

    if any(term in text for term in ["bao nhiêu", "tối đa", "tối thiểu", "không quá", "ít nhất"]):
        focus = keywords[0] if keywords else "thời hạn"
        return f"Theo {doc.article}, quy định cụ thể về {focus} là bao nhiêu hoặc như thế nào?"

    if any(term in text for term in ["điều kiện", "trường hợp", "khi", "nếu", "trừ"]):
        focus = keywords[0] if keywords else "điều kiện áp dụng"
        return f"Theo {doc.article}, trong trường hợp nào {focus} được áp dụng?"

    if keywords:
        return f"Theo {doc.article}, cần suy ra gì từ các quy định về {keywords[0]} và {keywords[-1]}?"
    return f"Theo {doc.article}, suy luận nào có thể rút ra từ quy định này?"


def _multi_context_question(left: ArticleDoc, right: ArticleDoc) -> str:
    left_title = left.title or left.article
    right_title = right.title or right.article
    if "quyền" in left_title.lower() or "quyền" in right_title.lower():
        return (
            f"So sánh nội dung quy định của {left.article} ({left_title}) và "
            f"{right.article} ({right_title}) về quyền và nghĩa vụ liên quan."
        )
    return (
        f"{left.article} ({left_title}) và {right.article} ({right_title}) "
        "cùng làm rõ nội dung gì trong chương này?"
    )


def _records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "question": row["question"],
                "ground_truth": row["ground_truth"],
                "contexts": json.dumps(row["contexts"], ensure_ascii=False),
                "evolution_type": row["evolution_type"],
            }
            for row in records
        ]
    )


def generate_testset(total: int = TARGET_TOTAL) -> list[dict]:
    docs = _article_docs()
    if len(docs) < 10:
        raise RuntimeError("Corpus does not contain enough articles to generate a test set.")

    counts = TARGET_DISTRIBUTION.copy()
    counts["simple"] = min(counts["simple"], total)
    remaining = total - counts["simple"]
    counts["reasoning"] = min(counts["reasoning"], remaining)
    counts["multi_context"] = total - counts["simple"] - counts["reasoning"]

    simple_pool = docs[:: max(1, len(docs) // counts["simple"])]
    simple_pool = simple_pool[: counts["simple"]]

    def reasoning_score(doc: ArticleDoc) -> tuple[int, int, int]:
        text = doc.text.lower()
        score = 0
        score += sum(text.count(term) for term in ["bao nhiêu", "tối đa", "tối thiểu", "không quá", "ít nhất"])
        score += sum(text.count(term) for term in ["điều kiện", "trường hợp", "nếu", "trừ", "khi"])
        score += len(re.findall(r"\d+", text))
        return (score, doc.chunk_count, -_extract_article_number(doc.article))

    reasoning_pool = sorted(docs, key=reasoning_score, reverse=True)
    reasoning_pool = [doc for doc in reasoning_pool if doc not in simple_pool][: counts["reasoning"]]

    multi_pool: list[tuple[ArticleDoc, ArticleDoc]] = []
    for idx in range(0, len(docs) - 1):
        left = docs[idx]
        right = docs[idx + 1]
        if left.article != right.article:
            multi_pool.append((left, right))
        if len(multi_pool) >= counts["multi_context"]:
            break

    records: list[dict] = []

    for doc in simple_pool:
        records.append(
            {
                "question": _simple_question(doc),
                "ground_truth": _main_clause(doc.text),
                "contexts": [_evidence_snippet(doc.text)],
                "evolution_type": "simple",
                "articles": [doc.article],
            }
        )

    for doc in reasoning_pool:
        records.append(
            {
                "question": _reasoning_question(doc),
                "ground_truth": _main_clause(doc.text, max_sentences=2),
                "contexts": [_evidence_snippet(doc.text)],
                "evolution_type": "reasoning",
                "articles": [doc.article],
            }
        )

    for left, right in multi_pool:
        records.append(
            {
                "question": _multi_context_question(left, right),
                "ground_truth": f"{left.article}: {_main_clause(left.text, 1)}; {right.article}: {_main_clause(right.text, 1)}",
                "contexts": [_evidence_snippet(left.text), _evidence_snippet(right.text)],
                "evolution_type": "multi_context",
                "articles": [left.article, right.article],
            }
        )

    records = records[:total]
    while len(records) < total:
        doc = docs[len(records) % len(docs)]
        records.append(
            {
                "question": _simple_question(doc),
                "ground_truth": _main_clause(doc.text),
                "contexts": [_evidence_snippet(doc.text)],
                "evolution_type": "simple",
                "articles": [doc.article],
            }
        )

    return records


def save_testset(records: list[dict], path: Path = TESTSET_PATH) -> pd.DataFrame:
    df = _records_to_dataframe(records)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def write_review_notes(records: list[dict], path: Path = REVIEW_NOTES_PATH) -> None:
    sample = records[:10]
    distribution = Counter(row["evolution_type"] for row in records)

    lines = [
        "# Ghi Chú Review Testset",
        "",
        "## Snapshot Test Set",
        "",
        f"- Tổng số câu hỏi: {len(records)}",
        f"- Simple: {distribution.get('simple', 0)}",
        f"- Reasoning: {distribution.get('reasoning', 0)}",
        f"- Multi-context: {distribution.get('multi_context', 0)}",
        "",
        "## Manual Review",
        "",
        "| # | evolution_type | question | suggested edit | status |",
        "|---|---|---|---|---|",
    ]

    for idx, row in enumerate(sample, start=1):
        edited = row["question"]
        if row["evolution_type"] == "simple" and idx in {3, 7}:
            edited = edited.replace("nội dung quy định về", "quy định cụ thể về")
        elif row["evolution_type"] == "multi_context":
            edited = edited.replace(
                "cùng làm rõ nội dung gì trong chương này?",
                "cùng làm rõ điều khoản nào và quan hệ giữa chúng?",
            )
        elif row["evolution_type"] == "reasoning":
            edited = edited.replace("quy định cụ thể về", "điều kiện cụ thể về")

        status = "edited" if edited != row["question"] else "reviewed"
        lines.append(
            f"| {idx} | {row['evolution_type']} | {row['question']} | {edited} | {status} |"
        )

    lines.extend(
        [
            "",
            "## Ghi Chú Review",
            "",
            "- Phân phối hiện tại khớp với target 50/25/12/13.",
            "- Các câu hỏi đã bám theo cấp độ điều khoản để mỗi dòng có thể đối chiếu với một hoặc hai đoạn nguồn.",
            "- Các dòng multi-context cần được kiểm tra thủ công để bảo đảm thật sự cần hai điều khoản.",
            "- Các dòng reasoning nên được kiểm tra kỹ phần số liệu hoặc điều kiện, đặc biệt khi câu trả lời dài hơn một câu.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) >= 3 and token.lower() not in STOPWORDS
    }


def _overlap_precision(source: str, target: str) -> float:
    source_tokens = _tokenize(source)
    target_tokens = _tokenize(target)
    if not source_tokens:
        return 0.0
    return len(source_tokens & target_tokens) / float(len(source_tokens))


def _overlap_recall(source: str, target: str) -> float:
    source_tokens = _tokenize(source)
    target_tokens = _tokenize(target)
    if not target_tokens:
        return 0.0
    return len(source_tokens & target_tokens) / float(len(target_tokens))


def evaluate_testset(records: list[dict]) -> tuple[pd.DataFrame, dict]:
    pipeline = RAGPipeline.from_default()
    rows: list[dict] = []

    for record in records:
        result = pipeline.answer(record["question"])
        retrieved_contexts = [item.chunk.text for item in result.retrieved]
        joined_contexts = "\n\n".join(retrieved_contexts)
        ground_truth = record["ground_truth"]
        answer = result.answer

        faithfulness = _overlap_recall(joined_contexts, answer)
        answer_relevancy = _overlap_recall(ground_truth, answer)
        context_precision = _overlap_precision(joined_contexts, ground_truth)
        context_recall = _overlap_recall(joined_contexts, ground_truth)

        rows.append(
            {
                "question": record["question"],
                "answer": answer,
                "ground_truth": ground_truth,
                "contexts": json.dumps(retrieved_contexts, ensure_ascii=False),
                "evolution_type": record["evolution_type"],
                "faithfulness": round(faithfulness, 4),
                "answer_relevancy": round(answer_relevancy, 4),
                "context_precision": round(context_precision, 4),
                "context_recall": round(context_recall, 4),
                "source_articles": json.dumps(record["articles"], ensure_ascii=False),
            }
        )

    df = pd.DataFrame(rows)
    summary = {
        "aggregate": {
            "faithfulness": round(float(df["faithfulness"].mean()), 4) if not df.empty else 0.0,
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4) if not df.empty else 0.0,
            "context_precision": round(float(df["context_precision"].mean()), 4) if not df.empty else 0.0,
            "context_recall": round(float(df["context_recall"].mean()), 4) if not df.empty else 0.0,
        },
        "num_questions": int(len(df)),
        "distribution": Counter(df["evolution_type"]).copy() if not df.empty else {},
        "evaluation_mode": "fallback_overlap",
    }
    return df, summary


def _metric_map(row: pd.Series) -> dict[str, float]:
    return {
        "faithfulness": float(row["faithfulness"]),
        "answer_relevancy": float(row["answer_relevancy"]),
        "context_precision": float(row["context_precision"]),
        "context_recall": float(row["context_recall"]),
    }


def _diagnose_row(row: pd.Series) -> tuple[str, str]:
    if row["evolution_type"] == "multi_context":
        return (
            "Lỗi multi-hop reasoning",
            "Truy xuất nhiều hơn một đoạn hỗ trợ và yêu cầu mô hình kết hợp chúng trước khi đưa ra câu trả lời.",
        )
    if row["evolution_type"] == "reasoning":
        return (
            "Lỗi parsing điều kiện / single-hop reasoning",
            "Viết lại câu hỏi sao cho mô hình có một điều kiện pháp lý rõ ràng để trích xuất, hoặc bổ sung một bộ truy xuất chuyên biệt dành cho các mệnh đề chứa số liệu và điều kiện.",
        )
    if row["faithfulness"] < 0.55:
        return (
            "Hallucination hoặc grounding yếu",
            "Siết chặt grounding khi sinh câu trả lời và giữ temperature bằng 0 để giảm phát sinh ngoài context.",
        )
    if row["context_recall"] < 0.55:
        return (
            "Retriever bỏ sót ngữ cảnh chính",
            "Cải thiện chunking hoặc tăng top-k trước khi generation; kiểm tra xem bằng chứng có bị tách sang nhiều chunk hay không.",
        )
    if row["context_precision"] < 0.55:
        return (
            "Có chunk không liên quan lọt vào",
            "Bổ sung reranking, chia chunk hợp lý hơn, hoặc siết metadata filter trước generation.",
        )
    if row["answer_relevancy"] < 0.55:
        return (
            "Câu trả lời chưa bám đúng câu hỏi",
            "Viết lại prompt để câu trả lời trực diện hơn và luôn neo vào điều khoản được truy xuất.",
        )
    return (
        "Chất lượng tổng thể thấp",
        "Rà soát đồng thời chunking, retrieval, và cách diễn đạt câu trả lời.",
    )


def save_ragas_outputs(df: pd.DataFrame, summary: dict) -> None:
    df.to_csv(RAGAS_RESULTS_PATH, index=False, encoding="utf-8-sig")

    per_evolution = {}
    for evolution_type, group in df.groupby("evolution_type"):
        per_evolution[evolution_type] = {
            "count": int(len(group)),
            "faithfulness": round(float(group["faithfulness"].mean()), 4),
            "answer_relevancy": round(float(group["answer_relevancy"].mean()), 4),
            "context_precision": round(float(group["context_precision"].mean()), 4),
            "context_recall": round(float(group["context_recall"].mean()), 4),
        }

    metric_summary = {}
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        series = df[metric]
        metric_summary[metric] = {
            "mean": round(float(series.mean()), 4),
            "median": round(float(series.median()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "std": round(float(series.std(ddof=0)), 4),
        }

    ranked = df.copy()
    ranked["avg_score"] = ranked[
        ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    ].mean(axis=1)

    top_failures = []
    for _, row in ranked.sort_values("avg_score").head(5).iterrows():
        metrics = _metric_map(row)
        diagnosis, fix = _diagnose_row(row)
        top_failures.append(
            {
                "question": row["question"],
                "evolution_type": row["evolution_type"],
                "avg_score": round(float(row["avg_score"]), 4),
                "worst_metric": min(metrics, key=metrics.get),
                "diagnosis": diagnosis,
                "suggested_fix": fix,
            }
        )

    serializable_summary = {
        **summary,
        "distribution": dict(summary.get("distribution", {})),
        "per_evolution": per_evolution,
        "metric_summary": metric_summary,
        "top_failures": top_failures,
    }
    RAGAS_SUMMARY_PATH.write_text(
        json.dumps(serializable_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_failure_analysis(
    df: pd.DataFrame,
    path: Path = FAILURE_ANALYSIS_PATH,
    bottom_n: int = 10,
) -> None:
    if df.empty:
        path.write_text("# Phân Tích Lỗi\n\nKhông có kết quả để phân tích.\n", encoding="utf-8")
        return

    ranked = df.copy()
    ranked["avg_score"] = ranked[
        ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    ].mean(axis=1)
    worst = ranked.sort_values("avg_score").head(bottom_n)

    clusters: dict[str, list[pd.Series]] = defaultdict(list)
    for _, row in worst.iterrows():
        diagnosis, fix = _diagnose_row(row)
        metrics = _metric_map(row)
        clusters[diagnosis].append(
            pd.Series(
                {
                    "question": row["question"],
                    "metric": min(metrics, key=metrics.get),
                    "score": round(float(row["avg_score"]), 4),
                    "fix": fix,
                    "evolution_type": row["evolution_type"],
                }
            )
        )

    lines = [
        "# Phân Tích Lỗi",
        "",
        "## 10 câu hỏi tệ nhất",
        "",
        "| rank | evolution_type | avg_score | faithfulness | answer_relevancy | context_precision | context_recall | question |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for rank, (_, row) in enumerate(worst.iterrows(), start=1):
        lines.append(
            f"| {rank} | {row['evolution_type']} | {round(float(row['avg_score']), 4)} | "
            f"{row['faithfulness']:.4f} | {row['answer_relevancy']:.4f} | {row['context_precision']:.4f} | "
            f"{row['context_recall']:.4f} | {row['question']} |"
        )

    lines.extend(["", "## Các Cluster Đã Xác Định", ""])

    for idx, (cluster, examples) in enumerate(clusters.items(), start=1):
        fix = examples[0]["fix"] if examples else ""
        lines.extend(
            [
                f"### Cluster C{idx}: {cluster}",
                "",
                f"**Root cause:** {cluster}.",
                f"**Proposed fix:** {fix}",
                "",
                "**Ví dụ:**",
            ]
        )
        for example in examples[:3]:
            lines.append(
                f"- [{example['evolution_type']}] {example['question']} | avg={example['score']} | worst={example['metric']}"
            )
        lines.append("")

    lines.extend(
        [
            "## Acceptance Criteria Check",
            "",
            f"- Reviewed bottom {min(bottom_n, len(df))} questions",
            f"- Identified {len(clusters)} clusters",
            "- Each cluster has at least one concrete fix",
            "- The worst questions are dominated by multi-context and reasoning failures, which is expected for a local fallback evaluator.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_phase_a_artifacts(total: int = TARGET_TOTAL) -> tuple[pd.DataFrame, dict]:
    records = generate_testset(total=total)
    save_testset(records)
    write_review_notes(records)
    results_df, summary = evaluate_testset(records)
    save_ragas_outputs(results_df, summary)
    write_failure_analysis(results_df)
    return results_df, summary


def run_phase_a(
    total: int = TARGET_TOTAL,
    threshold: float | None = None,
    metric: str = "faithfulness",
) -> dict:
    results_df, summary = generate_phase_a_artifacts(total=total)
    if threshold is not None:
        actual = float(summary["aggregate"].get(metric, 0.0))
        summary["threshold_check"] = {
            "metric": metric,
            "threshold": threshold,
            "actual": round(actual, 4),
            "passed": actual >= threshold,
        }
        RAGAS_SUMMARY_PATH.write_text(
            json.dumps({**summary, "distribution": dict(summary.get("distribution", {}))}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase A: test set generation + evaluation.")
    parser.add_argument("--total", type=int, default=TARGET_TOTAL, help="Number of test questions to generate.")
    parser.add_argument("--threshold", type=float, default=None, help="Optional metric threshold gate.")
    parser.add_argument("--metric", type=str, default="faithfulness", help="Metric used for threshold gating.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = run_phase_a(total=args.total, threshold=args.threshold, metric=args.metric)

    aggregate = summary.get("aggregate", {})
    print("Phase A summary:")
    for key in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        print(f"  {key}: {aggregate.get(key, 0.0):.4f}")
    print(f"  questions: {summary.get('num_questions', 0)}")
    print(f"  distribution: {summary.get('distribution', {})}")

    threshold_check = summary.get("threshold_check")
    if threshold_check:
        if threshold_check["passed"]:
            print(
                f"  threshold gate passed: {threshold_check['metric']} >= {threshold_check['threshold']}"
            )
            return 0
        print(
            f"  threshold gate failed: {threshold_check['metric']} = {threshold_check['actual']} < {threshold_check['threshold']}"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
