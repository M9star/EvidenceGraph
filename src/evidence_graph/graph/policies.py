from dataclasses import dataclass

from evidence_graph.config import Settings


@dataclass(frozen=True)
class ReliabilityPolicy:
    """Deadlines and budgets that keep one run from hanging or looping."""

    tool_timeout_s: float = 30.0
    country_timeout_s: float = 90.0
    run_timeout_s: float = 180.0
    max_tool_calls: int = 20
    max_retries: int = 2
    retry_backoff_s: float = 0.05
    excerpt_chars: int = 12_000
    history_keep_recent: int = 2

    @classmethod
    def from_settings(cls, settings: Settings) -> "ReliabilityPolicy":
        return cls(
            tool_timeout_s=settings.tool_timeout_s,
            country_timeout_s=settings.country_timeout_s,
            run_timeout_s=settings.run_timeout_s,
            max_tool_calls=settings.max_tool_calls_per_researcher,
            max_retries=settings.tool_retries,
            retry_backoff_s=settings.retry_backoff_s,
            excerpt_chars=settings.page_excerpt_chars,
            history_keep_recent=settings.history_keep_recent,
        )
