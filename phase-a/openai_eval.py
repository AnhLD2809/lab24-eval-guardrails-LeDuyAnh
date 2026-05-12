"""Optional OpenAI-backed evaluator for Phase A.

This script is separate from `phase_a.py` so the submitted CSV/JSON artifacts
can stay stable for review while the implementation still has a real API path.
When `OPENAI_API_KEY` is set, it runs the actual RAG pipeline and asks an
OpenAI judge to score the four RAGAS-style metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import OPENAI_API_KEY, OPENAI_CHAT_MODEL  # noqa: E402
from openai import OpenAI  # noqa: E402
from src.rag_pipeline import RAGPipeline  # noqa: E402


PHASE_DIR = Path(__file__).resolve().parent
TESTSET_PATH = PHASE_DIR / "testset_v1.csv"
OUTPUT_CSV_PATH = PHASE_DIR / "ragas_results.openai.csv"
OUTPUT_SUMMARY_PATH = PHASE_DIR / "ragas_summary.openai.json"
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


JUDGE_SYSTEM = (
    "You are a strict RAG evaluation judge for a Vietnamese legal QA system. "
    "Return JSON only. Score every metric from 0.0 to 1.0."
)


def load_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows if limit is None else rows[:limit]


def parse_contexts(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [raw] if raw else []


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def judge_scores(
    client: OpenAI,
    model: str,
    question: str,
    answer: str,
    ground_truth: str,
    contexts: list[str],
) -> dict[str, float]:
    payload = {
        "question": question,
        "answer": answer,
        "ground_truth": ground_truth,
        "contexts": contexts,
        "metric_definitions": {
            "faithfulness": "answer is supported by retrieved contexts",
            "answer_relevancy": "answer directly addresses the question",
            "context_precision": "retrieved contexts are relevant to the question",
            "context_recall": "retrieved contexts contain enough evidence for ground_truth",
        },
    }
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=240,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Evaluate this RAG result. Return JSON with exactly these numeric keys: "
                    "faithfulness, answer_relevancy, context_precision, context_recall.\n\n"
                    + json.dumps(payload, ensure_ascii=False)
                ),
            },
        ],
    )
    parsed = parse_json_object(response.choices[0].message.content or "{}")
    return {metric: clamp_score(parsed.get(metric, 0.0)) for metric in METRICS}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = {
        metric: round(mean(float(row[metric]) for row in rows), 4) if rows else 0.0
        for metric in METRICS
    }
    distribution: dict[str, int] = {}
    for row in rows:
        key = str(row.get("evolution_type", "unknown"))
        distribution[key] = distribution.get(key, 0) + 1
    return {
        "num_questions": len(rows),
        "evaluation_mode": "openai_judge",
        "aggregate": aggregate,
        "distribution": distribution,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "question",
        "answer",
        "ground_truth",
        "contexts",
        "evolution_type",
        *METRICS,
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(
    limit: int | None,
    testset_path: Path,
    output_csv_path: Path,
    output_summary_path: Path,
    model: str,
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI-backed evaluation.")

    rows = load_rows(testset_path, limit=limit)
    client = OpenAI(api_key=OPENAI_API_KEY)
    pipeline = RAGPipeline.from_default()

    output_rows: list[dict[str, Any]] = []
    for row in rows:
        result = pipeline.answer(row["question"])
        contexts = [item.chunk.text for item in result.retrieved] or parse_contexts(row.get("contexts", ""))
        scores = judge_scores(
            client=client,
            model=model,
            question=row["question"],
            answer=result.answer,
            ground_truth=row["ground_truth"],
            contexts=contexts,
        )
        output_rows.append(
            {
                "question": row["question"],
                "answer": result.answer,
                "ground_truth": row["ground_truth"],
                "contexts": json.dumps(contexts, ensure_ascii=False),
                "evolution_type": row["evolution_type"],
                **{key: round(value, 4) for key, value in scores.items()},
            }
        )

    summary = summarize(output_rows)
    write_csv(output_csv_path, output_rows)
    output_summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpenAI-backed Phase A evaluation.")
    parser.add_argument("--limit", type=int, default=5, help="Number of testset rows to evaluate.")
    parser.add_argument("--testset", type=Path, default=TESTSET_PATH, help="Input testset CSV.")
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV_PATH, help="Output CSV path.")
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=OUTPUT_SUMMARY_PATH,
        help="Output summary JSON path.",
    )
    parser.add_argument("--model", default=OPENAI_CHAT_MODEL, help="OpenAI model used as judge.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run(
        limit=args.limit,
        testset_path=args.testset,
        output_csv_path=args.output_csv,
        output_summary_path=args.output_summary,
        model=args.model,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
