"""CLI entry point for the legal RAG pipeline."""

from __future__ import annotations

import sys

from src.rag_pipeline import RAGPipeline, pretty_print_result


def main() -> None:
    try:
        pipeline = RAGPipeline.from_default()
        pipeline.build()

        if len(sys.argv) > 1:
            question = " ".join(sys.argv[1:]).strip()
        else:
            question = input("Nhập câu hỏi về Bộ luật Lao động: ").strip()

        if not question:
            print("Chưa có câu hỏi.")
            return

        result = pipeline.answer(question)
        print(pretty_print_result(result))
    except RuntimeError as exc:
        print(f"Lỗi cấu hình: {exc}")


if __name__ == "__main__":
    main()
