"""
Persistent request counters for LLM Katan.

Tracks total and per-provider request counts across server restarts.

Signed-off-by: Yossi Ovadia <yovadia@redhat.com>
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


DEFAULT_PRICING = {
    "openai": {"input": 2.50, "output": 10.00},
    "anthropic": {"input": 3.00, "output": 15.00},
    "vertexai": {"input": 1.25, "output": 5.00},
    "bedrock": {"input": 3.00, "output": 15.00},
    "azure_openai": {"input": 2.50, "output": 10.00},
}


class PersistentStats:
    """Global request counters that persist to a JSON file."""

    def __init__(self, path: str | None = None):
        self._path = Path(path) if path else None
        self._total: int = 0
        self._providers: dict[str, int] = {}
        self._tokens: dict[str, dict[str, int]] = {}
        self._pricing: dict[str, dict[str, float]] = {}
        if self._path:
            self._load()

    def _load(self):
        if self._path and self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._total = data.get("total", 0)
                self._providers = data.get("providers", {})
                self._tokens = data.get("tokens", {})
                self._pricing = data.get("pricing", {})
                logger.info("Loaded persistent stats: %d total requests", self._total)
            except Exception:
                logger.warning("Could not load stats from %s, starting fresh", self._path)

    def _save(self):
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._serialize(), indent=2) + "\n")

    def _serialize(self) -> dict:
        data = {
            "total": self._total,
            "providers": dict(self._providers),
            "tokens": {k: dict(v) for k, v in self._tokens.items()},
        }
        if self._pricing:
            data["pricing"] = {k: dict(v) for k, v in self._pricing.items()}
        return data

    def record(self, provider: str):
        self._total += 1
        self._providers[provider] = self._providers.get(provider, 0) + 1
        self._save()

    def record_tokens(self, provider: str, prompt_tokens: int, completion_tokens: int):
        if provider not in self._tokens:
            self._tokens[provider] = {"prompt": 0, "completion": 0}
        self._tokens[provider]["prompt"] += prompt_tokens
        self._tokens[provider]["completion"] += completion_tokens
        self._save()

    @property
    def pricing(self) -> dict[str, dict[str, float]]:
        merged = dict(DEFAULT_PRICING)
        merged.update(self._pricing)
        return merged

    @pricing.setter
    def pricing(self, overrides: dict[str, dict[str, float]]):
        self._pricing.update(overrides)
        self._save()

    def estimated_savings(self) -> float:
        total = 0.0
        prices = self.pricing
        for provider, counts in self._tokens.items():
            p = prices.get(provider, prices.get("openai", {"input": 2.50, "output": 10.00}))
            total += counts["prompt"] / 1_000_000 * p["input"]
            total += counts["completion"] / 1_000_000 * p["output"]
        return round(total, 2)

    def get(self) -> dict:
        return {
            "total": self._total,
            "providers": dict(self._providers),
            "tokens": {k: dict(v) for k, v in self._tokens.items()},
            "pricing": self.pricing,
            "estimated_savings": self.estimated_savings(),
        }

    @property
    def total(self) -> int:
        return self._total

    @property
    def providers(self) -> dict[str, int]:
        return dict(self._providers)
