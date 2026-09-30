"""
scheduler/circuit_breaker.py
Circuit breaker protection for price source adapters.
Prevents hammering failing retailers and alerts when failure thresholds are breached.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class SourceBreakerState:
    failures: list[datetime] = field(default_factory=list)
    state: str = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
    tripped_at: datetime | None = None
    last_error: str | None = None


class CircuitBreaker:
    """Monitors and trips sources experiencing consecutive scraping/API errors."""

    def __init__(
        self,
        failure_threshold: int = 4,
        window_minutes: int = 10,
        cooldown_minutes: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.window_minutes = window_minutes
        self.cooldown_minutes = cooldown_minutes
        self._states: dict[str, SourceBreakerState] = {}

    def _get_state(self, source_name: str) -> SourceBreakerState:
        if source_name not in self._states:
            self._states[source_name] = SourceBreakerState()
        return self._states[source_name]

    def is_available(self, source_name: str, now: datetime | None = None) -> bool:
        """Check if source is healthy to query."""
        now = now or datetime.now(timezone.utc)
        state = self._get_state(source_name)

        if state.state == "CLOSED":
            return True

        if state.state == "OPEN":
            # Check if cooldown elapsed to allow half-open trial
            if state.tripped_at and (now - state.tripped_at) >= timedelta(minutes=self.cooldown_minutes):
                state.state = "HALF_OPEN"
                logger.info("[%s] Circuit breaker entering HALF_OPEN trial state", source_name)
                return True
            return False

        # HALF_OPEN allows single probe
        return True

    def record_success(self, source_name: str) -> None:
        """Record a successful check, resetting breaker state."""
        state = self._get_state(source_name)
        if state.state != "CLOSED":
            logger.info("[%s] Circuit breaker recovered to CLOSED", source_name)
        state.state = "CLOSED"
        state.failures.clear()
        state.tripped_at = None

    def record_failure(
        self,
        source_name: str,
        error_msg: str,
        now: datetime | None = None,
    ) -> bool:
        """
        Record a source failure. Returns True if this failure caused the breaker to trip.
        """
        now = now or datetime.now(timezone.utc)
        state = self._get_state(source_name)
        state.last_error = error_msg

        # Filter failures outside the rolling window
        cutoff = now - timedelta(minutes=self.window_minutes)
        state.failures = [t for t in state.failures if t >= cutoff]
        state.failures.append(now)

        if len(state.failures) >= self.failure_threshold:
            state.state = "OPEN"
            state.tripped_at = now
            logger.error(
                "🚨 [%s] Circuit breaker TRIPPED! Pausing source for %d minutes. Last error: %s",
                source_name,
                self.cooldown_minutes,
                error_msg,
            )
            return True
        return False

    def get_status(self, source_name: str) -> dict:
        """Return diagnostic metrics for this source breaker."""
        state = self._get_state(source_name)
        return {
            "source": source_name,
            "state": state.state,
            "recent_failures": len(state.failures),
            "tripped_at": state.tripped_at.isoformat() if state.tripped_at else None,
            "last_error": state.last_error,
        }
