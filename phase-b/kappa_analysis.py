"""Compute Cohen's kappa for the phase B calibration sample."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAIRWISE_PATH = ROOT / "pairwise_results.csv"
HUMAN_PATH = ROOT / "human_labels.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def cohen_kappa(human: list[str], judge: list[str]) -> float:
    if len(human) != len(judge):
        raise ValueError("Human and judge label sets must have the same length.")
    if not human:
        raise ValueError("At least one label is required.")

    n = len(human)
    observed = sum(h == j for h, j in zip(human, judge)) / n

    labels = sorted(set(human) | set(judge))
    human_counts = Counter(human)
    judge_counts = Counter(judge)
    expected = sum(
        (human_counts[label] / n) * (judge_counts[label] / n)
        for label in labels
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def build_alignment() -> tuple[list[str], list[str]]:
    pairwise_rows = {row["question_id"]: row for row in load_csv(PAIRWISE_PATH)}
    human_rows = load_csv(HUMAN_PATH)

    human_labels: list[str] = []
    judge_labels: list[str] = []
    for row in human_rows:
        qid = row["question_id"]
        if qid not in pairwise_rows:
            raise KeyError(f"question_id {qid} not found in pairwise_results.csv")
        human_labels.append(row["human_winner"])
        judge_labels.append(pairwise_rows[qid]["winner_after_swap"])
    return human_labels, judge_labels


def interpret(kappa: float) -> str:
    if kappa < 0.2:
        return "Worse than chance"
    if kappa < 0.4:
        return "Slight agreement"
    if kappa < 0.6:
        return "Moderate agreement"
    if kappa < 0.8:
        return "Substantial agreement"
    return "Almost perfect agreement"


def main() -> None:
    human_labels, judge_labels = build_alignment()
    kappa = cohen_kappa(human_labels, judge_labels)
    human_counts = Counter(human_labels)
    judge_counts = Counter(judge_labels)

    print("Phase B Kappa Analysis")
    print(f"Sample size: {len(human_labels)}")
    print(f"Human distribution: {dict(human_counts)}")
    print(f"Judge distribution: {dict(judge_counts)}")
    print(f"Cohen's kappa: {kappa:.2f}")
    print(f"Interpretation: {interpret(kappa)}")


if __name__ == "__main__":
    main()
