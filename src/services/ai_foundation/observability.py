import logging
import time

from src.llm.providers.base import LLMProvider
from src.services.ai_foundation.types import SessionContext

logger = logging.getLogger(__name__)


class ObservabilityRecorder:
    """Wraps every Analyst's call to an LLMProvider with latency and token
    logging -- one implementation instead of each Analyst timing its own
    call (Domain Blueprint §4.8). Closes the real gap D-041 flagged
    (ProductionLLMProvider discarding message.usage) now that this Epic is
    the concrete trigger for it. Uses the project's existing structured
    `logging`, not a new metrics store -- no consumer asked for a dashboard."""

    @staticmethod
    def record_call(analyst_name: str, session: SessionContext, provider: LLMProvider, prompt: str) -> str:
        started = time.monotonic()
        result = provider.generate(prompt)
        elapsed_ms = round((time.monotonic() - started) * 1000, 1)

        # last_usage is an optional, duck-typed attribute -- only
        # ProductionLLMProvider sets it; its absence (e.g. MockLLMProvider)
        # means "no cost data available", never an error.
        usage = getattr(provider, "last_usage", None)
        logger.info(
            "AI Foundation call analyst=%s organization_id=%s latency_ms=%s input_tokens=%s output_tokens=%s",
            analyst_name,
            session.organization_id,
            elapsed_ms,
            usage.input_tokens if usage else None,
            usage.output_tokens if usage else None,
        )
        return result
