"""Topic scope validator for legal-domain inputs."""

from __future__ import annotations

import asyncio
import math
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from config import OPENAI_API_KEY

if TYPE_CHECKING:
    from openai import OpenAI as OpenAIClient
else:  # pragma: no cover - typing helper only
    OpenAIClient = Any

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


LEGAL_TOPICS = [
    "luat lao dong",
    "hop dong lao dong",
    "tien luong",
    "thoi gian lam viec",
    "nghi phep",
    "ky luat lao dong",
    "bao hiem xa hoi",
    "an toan lao dong",
]

OFFTOPIC_PATTERNS = (
    r"ignore previous instructions",
    r"jailbreak",
    r"dan mode",
    r"roleplay",
    r"how to hack",
    r"bypass",
    r"secret prompt",
    r"system prompt",
)


@dataclass
class TopicGuardResult:
    allowed: bool
    reason: str
    latency_ms: float
    closest_topic: str = ""
    score: float = 0.0
    evidence: list[str] = field(default_factory=list)


class TopicGuard:
    def __init__(self, allowed_topics: list[str] | None = None, threshold: float = 0.45) -> None:
        self.allowed_topics = allowed_topics or LEGAL_TOPICS
        self.threshold = threshold
        self._client: OpenAIClient | None = None
        self._topic_vectors: dict[str, set[str]] = {
            topic: self._tokenize(topic) for topic in self.allowed_topics
        }

    def _client_or_none(self) -> OpenAIClient | None:
        if not OPENAI_API_KEY or OpenAI is None:
            return None
        if self._client is None:
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client

    def _tokenize(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9à-ỹđ]+", text.lower())
        return {token for token in tokens if len(token) > 2}

    def _keyword_score(self, text: str, topic: str) -> float:
        q = self._tokenize(text)
        t = self._tokenize(topic)
        if not q or not t:
            return 0.0
        overlap = len(q & t)
        denom = math.sqrt(len(q) * len(t))
        return overlap / denom if denom else 0.0

    def _best_topic(self, text: str) -> tuple[str, float]:
        best_topic = ""
        best_score = 0.0
        for topic in self.allowed_topics:
            score = self._keyword_score(text, topic)
            if score > best_score:
                best_topic = topic
                best_score = score
        return best_topic, best_score

    def _detect_offtopic_injection(self, text: str) -> tuple[bool, str]:
        lowered = text.lower()
        for pattern in OFFTOPIC_PATTERNS:
            if re.search(pattern, lowered):
                return True, f"Injection/off-topic pattern matched: {pattern}"
        return False, ""

    def check(self, text: str) -> tuple[bool, str, float]:
        start = time.perf_counter()
        blocked, reason = self._detect_offtopic_injection(text)
        if blocked:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return False, reason, latency_ms

        best_topic, score = self._best_topic(text)
        if score >= self.threshold:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return True, f"On topic: {best_topic}", latency_ms

        latency_ms = (time.perf_counter() - start) * 1000.0
        return False, f"Off topic. Closest topic: {best_topic or 'legal-domain'}", latency_ms

    async def check_async(self, text: str) -> tuple[bool, str, float]:
        return await asyncio.to_thread(self.check, text)
