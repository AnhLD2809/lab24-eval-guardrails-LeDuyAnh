"""OpenAI-backed judge pipeline for Phase B.

The checked-in Phase B CSV files are precomputed calibration artifacts. This
module provides the live implementation path: pairwise judging with
swap-and-average plus absolute scoring with a four-dimension rubric.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import OPENAI_API_KEY, OPENAI_CHAT_MODEL  # noqa: E402
from openai import OpenAI  # noqa: E402


PAIRWISE_SYSTEM = (
    "You are an impartial evaluator. Compare two answers to the same question. "
    "Judge factual accuracy first, then relevance, then conciseness. "
    "Return JSON only with keys winner and reason. Winner must be A, B, or tie."
)

ABSOLUTE_SYSTEM = (
    "You are a strict grading judge for a Vietnamese legal QA system. "
    "Score accuracy, relevance, conciseness, and helpfulness from 1 to 5. "
    "Return JSON only."
)


def require_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI-backed judge runs.")
    return OpenAI(api_key=OPENAI_API_KEY)


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


def normalize_winner(value: Any) -> str:
    winner = str(value or "tie").strip().lower()
    if winner in {"a", "answer_a", "answer a"}:
        return "A"
    if winner in {"b", "answer_b", "answer b"}:
        return "B"
    return "tie"


def pairwise_once(
    client: OpenAI,
    model: str,
    question: str,
    answer_a: str,
    answer_b: str,
) -> dict[str, str]:
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=200,
        messages=[
            {"role": "system", "content": PAIRWISE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Answer A:\n{answer_a}\n\n"
                    f"Answer B:\n{answer_b}\n\n"
                    'Return {"winner": "A" | "B" | "tie", "reason": "..."}'
                ),
            },
        ],
    )
    parsed = parse_json_object(response.choices[0].message.content or "{}")
    return {
        "winner": normalize_winner(parsed.get("winner")),
        "reason": str(parsed.get("reason", "")).strip(),
    }


def flip_winner(winner: str) -> str:
    return {"A": "B", "B": "A", "tie": "tie"}.get(winner, "tie")


def pairwise_judge_with_swap(
    question: str,
    answer_a: str,
    answer_b: str,
    model: str = OPENAI_CHAT_MODEL,
) -> dict[str, str]:
    client = require_client()
    run1 = pairwise_once(client, model, question, answer_a, answer_b)
    run2_raw = pairwise_once(client, model, question, answer_b, answer_a)
    run2_winner = flip_winner(run2_raw["winner"])
    winner_after_swap = run1["winner"] if run1["winner"] == run2_winner else "tie"
    reason = run1["reason"] if winner_after_swap != "tie" else "Swap disagreement; final tie."
    return {
        "run1_winner": run1["winner"],
        "run2_winner": run2_winner,
        "winner_after_swap": winner_after_swap,
        "run1_reason": run1["reason"],
        "run2_reason": run2_raw["reason"],
        "reason": reason,
    }


def clamp_int_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 3
    return max(1, min(5, score))


def absolute_score(
    question: str,
    answer: str,
    model: str = OPENAI_CHAT_MODEL,
) -> dict[str, float]:
    client = require_client()
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=180,
        messages=[
            {"role": "system", "content": ABSOLUTE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\nAnswer:\n{answer}\n\n"
                    "Return JSON with integer keys accuracy, relevance, conciseness, "
                    "helpfulness, and numeric overall."
                ),
            },
        ],
    )
    parsed = parse_json_object(response.choices[0].message.content or "{}")
    dims = ("accuracy", "relevance", "conciseness", "helpfulness")
    scores: dict[str, float] = {dim: clamp_int_score(parsed.get(dim)) for dim in dims}
    try:
        overall = float(parsed.get("overall"))
    except (TypeError, ValueError):
        overall = sum(scores[dim] for dim in dims) / len(dims)
    scores["overall"] = round(max(1.0, min(5.0, overall)), 2)
    return scores


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live Phase B OpenAI judge calls.")
    parser.add_argument("--model", default=OPENAI_CHAT_MODEL, help="OpenAI judge model.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pairwise = subparsers.add_parser("pairwise", help="Compare two candidate answers.")
    pairwise.add_argument("--question", required=True)
    pairwise.add_argument("--answer-a", required=True)
    pairwise.add_argument("--answer-b", required=True)

    absolute = subparsers.add_parser("absolute", help="Score one answer with the rubric.")
    absolute.add_argument("--question", required=True)
    absolute.add_argument("--answer", required=True)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "pairwise":
        result = pairwise_judge_with_swap(
            question=args.question,
            answer_a=args.answer_a,
            answer_b=args.answer_b,
            model=args.model,
        )
    elif args.command == "absolute":
        result = absolute_score(
            question=args.question,
            answer=args.answer,
            model=args.model,
        )
    else:  # pragma: no cover - argparse prevents this path.
        raise ValueError(f"Unsupported command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
