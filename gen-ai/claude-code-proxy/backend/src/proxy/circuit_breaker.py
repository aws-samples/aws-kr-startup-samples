from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from ..config import get_settings
from ..domain import CIRCUIT_TRIGGERS, ErrorType


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class KeyCircuitState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_at: datetime | None = None
    opened_at: datetime | None = None


@dataclass
class CircuitBreaker:
    """Per-access-key circuit breaker."""

    failure_threshold: int = field(default_factory=lambda: get_settings().circuit_failure_threshold)
    failure_window: int = field(default_factory=lambda: get_settings().circuit_failure_window)
    reset_timeout: int = field(default_factory=lambda: get_settings().circuit_reset_timeout)
    _states: dict[str, KeyCircuitState] = field(default_factory=dict)

    def is_open(self, key_id: str) -> bool:
        state = self._states.get(key_id)
        if not state:
            return False

        if state.state == CircuitState.OPEN:
            # Check if should transition to half-open
            if state.opened_at and datetime.now(timezone.utc) > state.opened_at + timedelta(
                seconds=self.reset_timeout
            ):
                state.state = CircuitState.HALF_OPEN
                return False
            return True

        return False

    def record_success(self, key_id: str) -> None:
        state = self._states.get(key_id)
        if state and state.state == CircuitState.HALF_OPEN:
            # Reset to closed on success in half-open
            state.state = CircuitState.CLOSED
            state.failure_count = 0
            state.opened_at = None

    def record_failure(self, key_id: str, error_type: ErrorType) -> None:
        # Only circuit-triggering errors count
        if error_type not in CIRCUIT_TRIGGERS:
            return

        now = datetime.now(timezone.utc)
        state = self._states.get(key_id)

        if not state:
            state = KeyCircuitState()
            self._states[key_id] = state

        # Reset count if outside failure window
        if state.last_failure_at and now > state.last_failure_at + timedelta(
            seconds=self.failure_window
        ):
            state.failure_count = 0

        state.failure_count += 1
        state.last_failure_at = now

        # Open circuit if threshold reached
        if state.failure_count >= self.failure_threshold:
            state.state = CircuitState.OPEN
            state.opened_at = now
