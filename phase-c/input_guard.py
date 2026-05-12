"""Input guard for PII redaction and injection hygiene."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Iterable

try:
    from presidio_analyzer import AnalyzerEngine  # type: ignore
    from presidio_anonymizer import AnonymizerEngine  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    AnalyzerEngine = None  # type: ignore[assignment]
    AnonymizerEngine = None  # type: ignore[assignment]


VN_PII_PATTERNS: dict[str, str] = {
    "cccd": r"\b\d{12}\b",
    "phone_vn": r"(?:\+84|0)\d{9,10}\b",
    "tax_code": r"\b\d{10}(?:-\d{3})?\b",
    "email": r"\b[\w.+-]+@[\w.-]+\.\w+\b",
    "bank_account": r"\b\d{9,16}\b",
}

INJECTION_PATTERNS: tuple[str, ...] = (
    r"ignore previous instructions",
    r"bypass safety",
    r"system prompt",
    r"jailbreak",
    r"dan mode",
    r"roleplay",
    r"reveal the prompt",
    r"secret key",
)


@dataclass
class InputGuardResult:
    sanitized_text: str
    latency_ms: float
    pii_labels: list[str] = field(default_factory=list)
    blocked: bool = False
    reason: str = ""


class InputGuard:
    def __init__(self) -> None:
        self.analyzer = AnalyzerEngine() if AnalyzerEngine else None
        self.anonymizer = AnonymizerEngine() if AnonymizerEngine else None

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def scrub_vn(self, text: str) -> tuple[str, list[str]]:
        findings: list[str] = []
        cleaned = text
        for name, pattern in VN_PII_PATTERNS.items():
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                findings.append(name)
                cleaned = re.sub(pattern, f"[{name}]", cleaned, flags=re.IGNORECASE)
        return cleaned, findings

    def scrub_ner(self, text: str) -> tuple[str, list[str]]:
        findings: list[str] = []
        if self.analyzer and self.anonymizer:
            try:
                results = self.analyzer.analyze(text=text, language="en")
                if results:
                    findings.extend(sorted({result.entity_type.lower() for result in results}))
                    anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
                    return anonymized.text, findings
            except Exception:
                pass

        cleaned = text
        cleaned, org_count = re.subn(
            r"\b(?:Microsoft|Google|OpenAI|Apple|Meta|Amazon|Tesla|Facebook)\b",
            "[org]",
            cleaned,
            flags=re.IGNORECASE,
        )
        if org_count:
            findings.append("org")
        cleaned, name_count = re.subn(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
            "[name_en]",
            cleaned,
        )
        if name_count:
            findings.append("name_en")
        return cleaned, findings

    def detect_injection(self, text: str) -> tuple[bool, str]:
        lowered = text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lowered):
                return True, f"Injection pattern matched: {pattern}"
        return False, ""

    def sanitize(self, text: str) -> tuple[str, float, list[str]]:
        start = time.perf_counter()
        cleaned = self._normalize(text)
        cleaned, vn_findings = self.scrub_vn(cleaned)
        cleaned, ner_findings = self.scrub_ner(cleaned)
        cleaned = self._normalize(cleaned)
        findings = sorted(set(vn_findings + ner_findings))
        latency_ms = (time.perf_counter() - start) * 1000.0
        return cleaned, latency_ms, findings

    async def sanitize_async(self, text: str) -> tuple[str, float, list[str]]:
        return await asyncio.to_thread(self.sanitize, text)

    def check(self, text: str) -> tuple[bool, str, float]:
        start = time.perf_counter()
        blocked, reason = self.detect_injection(text)
        latency_ms = (time.perf_counter() - start) * 1000.0
        return (not blocked), reason, latency_ms


def guard_input(text: str) -> str:
    return InputGuard().sanitize(text)[0]
