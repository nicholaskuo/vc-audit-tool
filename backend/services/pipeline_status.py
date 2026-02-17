import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StepEvent:
    step_name: str
    status: str  # "started", "completed", "failed"
    timestamp: str
    duration_ms: float | None = None
    error: str | None = None


@dataclass
class PipelineStatus:
    report_id: str
    events: list[StepEvent] = field(default_factory=list)
    complete: bool = False
    _event: asyncio.Event = field(default_factory=asyncio.Event)
    _event_index: int = 0

    def emit(self, step_name: str, status: str, duration_ms: float | None = None, error: str | None = None):
        self.events.append(StepEvent(
            step_name=step_name,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            error=error,
        ))
        self._event.set()
        self._event = asyncio.Event()

    def mark_complete(self):
        self.complete = True
        self._event.set()

    async def wait_for_event(self, timeout: float = 30.0) -> list[StepEvent]:
        """Wait for new events since last call. Returns new events."""
        if self._event_index < len(self.events):
            new = self.events[self._event_index:]
            self._event_index = len(self.events)
            return new

        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        new = self.events[self._event_index:]
        self._event_index = len(self.events)
        return new


# Module-level registry
_statuses: dict[str, PipelineStatus] = {}


def create_status(report_id: str) -> PipelineStatus:
    status = PipelineStatus(report_id=report_id)
    _statuses[report_id] = status
    return status


def get_status(report_id: str) -> PipelineStatus | None:
    return _statuses.get(report_id)


def cleanup_status(report_id: str):
    _statuses.pop(report_id, None)
