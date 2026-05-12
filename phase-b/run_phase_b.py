"""Run Phase B live judge workflow and write review artifacts.

This runner expects Phase A to have produced `phase-a/testset_v1.csv`. It
generates two candidate answers per question, calls the OpenAI pairwise judge
with swap-and-average, writes absolute scores, and prepares a small manual
labeling file for Cohen's kappa calibration.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean

PHASE_DIR = Path(__file__).resolve().parent
ROOT = PHASE_DIR.parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from judge_pipeline import absolute_score, pairwise_judge_with_swap  # noqa: E402
from src.rag_pipeline import RAGPipeline  # noqa: E402


TESTSET_PATH = ROOT / "phase-a" / "testset_v1.csv"
PAIRWISE_PATH = PHASE_DIR / "pairwise_results.csv"
ABSOLUTE_PATH = PHASE_DIR / "absolute_scores.csv"
TO_LABEL_PATH = PHASE_DIR / "to_label.csv"
BIAS_REPORT_PATH = PHASE_DIR / "judge_bias_report.md"


def load_testset(path: Path, limit: int) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python phase-a/run_phase_a.py` first."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def candidate_answers(pipeline: RAGPipeline, question: str) -> tuple[str, str]:
    result = pipeline.answer(question)
    answer_a = result.answer
    if result.retrieved:
        top_context = result.retrieved[0].chunk.text
        answer_b = (
            "Tóm tắt theo ngữ cảnh truy xuất: "
            + " ".join(top_context.replace("\n", " ").split()[:90])
        )
    else:
        answer_b = "Không tìm thấy thông tin đủ rõ trong tài liệu."
    return answer_a, answer_b


def write_pairwise(rows: list[dict[str, str]]) -> None:
    fields = [
        "question_id",
        "question",
        "answer_a",
        "answer_b",
        "run1_winner",
        "run2_winner",
        "winner_after_swap",
        "reason",
    ]
    with PAIRWISE_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_absolute(rows: list[dict[str, object]]) -> None:
    fields = [
        "question_id",
        "question",
        "answer_version",
        "accuracy",
        "relevance",
        "conciseness",
        "helpfulness",
        "overall",
    ]
    with ABSOLUTE_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_to_label(pairwise_rows: list[dict[str, str]], limit: int = 10) -> None:
    fields = ["question_id", "question", "answer_a", "answer_b", "human_winner", "confidence", "notes"]
    with TO_LABEL_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in pairwise_rows[:limit]:
            writer.writerow(
                {
                    "question_id": row["question_id"],
                    "question": row["question"],
                    "answer_a": row["answer_a"],
                    "answer_b": row["answer_b"],
                    "human_winner": "",
                    "confidence": "",
                    "notes": "",
                }
            )


def write_bias_report(pairwise_rows: list[dict[str, str]], absolute_rows: list[dict[str, object]]) -> None:
    total = len(pairwise_rows)
    run1_a = sum(row["run1_winner"] == "A" for row in pairwise_rows)
    final_a = sum(row["winner_after_swap"] == "A" for row in pairwise_rows)
    final_b = sum(row["winner_after_swap"] == "B" for row in pairwise_rows)
    final_tie = sum(row["winner_after_swap"] == "tie" for row in pairwise_rows)
    avg_overall = mean(float(row["overall"]) for row in absolute_rows) if absolute_rows else 0.0

    report = f"""# Báo Cáo Bias Phase B

## Tóm Tắt

- Số cặp đã judge: `{total}`
- Phân phối sau `swap-and-average`: `A={final_a}`, `B={final_b}`, `tie={final_tie}`
- Điểm `absolute overall` trung bình: `{avg_overall:.2f}/5`

## Bias 1: Position Bias

`A` thắng ở lượt đầu `{run1_a}/{total}` lần. Nếu tỷ lệ này lệch xa 50%, judge có dấu hiệu ưu tiên vị trí đầu. Cơ chế `swap-and-average` đã được dùng để giảm rủi ro này.

## Bias 2: Length Bias

`answer_b` trong runner thường là bản tóm tắt từ context, còn `answer_a` là câu trả lời từ RAG pipeline. Khi judge ưu tiên câu dài hơn hoặc có nhiều chi tiết hơn, cần kiểm tra lại bằng `absolute_scores.csv`.

## Mitigation

- Luôn chạy `swap-and-average`
- Giữ output JSON nghiêm ngặt
- Manual label 10 cặp trong `to_label.csv`, sau đó đổi tên thành `human_labels.csv` để chạy `kappa_analysis.py`
"""
    BIAS_REPORT_PATH.write_text(report, encoding="utf-8")


def run(limit: int) -> None:
    rows = load_testset(TESTSET_PATH, limit=limit)
    pipeline = RAGPipeline.from_default()
    pairwise_rows: list[dict[str, str]] = []
    absolute_rows: list[dict[str, object]] = []

    for idx, row in enumerate(rows, start=1):
        answer_a, answer_b = candidate_answers(pipeline, row["question"])
        judge = pairwise_judge_with_swap(row["question"], answer_a, answer_b)
        pairwise_rows.append(
            {
                "question_id": str(idx),
                "question": row["question"],
                "answer_a": answer_a,
                "answer_b": answer_b,
                "run1_winner": judge["run1_winner"],
                "run2_winner": judge["run2_winner"],
                "winner_after_swap": judge["winner_after_swap"],
                "reason": judge["reason"],
            }
        )
        for version, answer in (("A", answer_a), ("B", answer_b)):
            scores = absolute_score(row["question"], answer)
            absolute_rows.append(
                {
                    "question_id": str(idx),
                    "question": row["question"],
                    "answer_version": version,
                    **scores,
                }
            )

    write_pairwise(pairwise_rows)
    write_absolute(absolute_rows)
    write_to_label(pairwise_rows)
    write_bias_report(pairwise_rows, absolute_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase B live OpenAI judge workflow.")
    parser.add_argument("--limit", type=int, default=30, help="Number of Phase A questions to judge.")
    args = parser.parse_args()
    run(limit=args.limit)
    print(f"Wrote {PAIRWISE_PATH}, {ABSOLUTE_PATH}, {TO_LABEL_PATH}, {BIAS_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
