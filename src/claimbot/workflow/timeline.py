"""Claim timeline - tracks claim status through its lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from claimbot.models import Claim, ClaimStatus, TimelineEvent


class ClaimTimeline:
    """Tracks and manages claim lifecycle events.

    A claim progresses through statuses:
    submitted -> under_review -> [additional_info_requested] -> approved/denied/investigating
    -> [partially_approved] -> paid -> closed

    Or: submitted -> under_review -> investigating -> approved/denied -> paid -> closed
    """

    VALID_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
        ClaimStatus.SUBMITTED: [ClaimStatus.UNDER_REVIEW, ClaimStatus.DENIED],
        ClaimStatus.UNDER_REVIEW: [
            ClaimStatus.APPROVED,
            ClaimStatus.PARTIALLY_APPROVED,
            ClaimStatus.DENIED,
            ClaimStatus.INVESTIGATING,
            ClaimStatus.ADDITIONAL_INFO_REQUESTED,
        ],
        ClaimStatus.ADDITIONAL_INFO_REQUESTED: [
            ClaimStatus.UNDER_REVIEW,
            ClaimStatus.DENIED,
            ClaimStatus.CLOSED,
        ],
        ClaimStatus.APPROVED: [ClaimStatus.PAID, ClaimStatus.CLOSED],
        ClaimStatus.PARTIALLY_APPROVED: [ClaimStatus.PAID, ClaimStatus.APPEALED, ClaimStatus.CLOSED],
        ClaimStatus.DENIED: [ClaimStatus.APPEALED, ClaimStatus.CLOSED],
        ClaimStatus.INVESTIGATING: [
            ClaimStatus.APPROVED,
            ClaimStatus.PARTIALLY_APPROVED,
            ClaimStatus.DENIED,
        ],
        ClaimStatus.PAID: [ClaimStatus.CLOSED],
        ClaimStatus.APPEALED: [ClaimStatus.UNDER_REVIEW, ClaimStatus.CLOSED],
        ClaimStatus.CLOSED: [],
    }

    def __init__(self) -> None:
        self._events: dict[str, list[TimelineEvent]] = {}

    def record_event(
        self,
        claim: Claim,
        new_status: ClaimStatus,
        actor: str = "system",
        description: str = "",
        metadata: dict[str, str] | None = None,
    ) -> TimelineEvent:
        """Record a status change event for a claim.

        Args:
            claim: The claim being updated.
            new_status: The new status to transition to.
            actor: Who/what triggered the change.
            description: Human-readable description of the event.
            metadata: Additional key-value data.

        Returns:
            The created TimelineEvent.

        Raises:
            ValueError: If the transition is not valid.
        """
        current_status = claim.status

        if not self.is_valid_transition(current_status, new_status):
            raise ValueError(
                f"Invalid transition from {current_status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in self.VALID_TRANSITIONS.get(current_status, [])]}"
            )

        event = TimelineEvent(
            status=new_status,
            actor=actor,
            description=description or f"Status changed from {current_status.value} to {new_status.value}",
            metadata=metadata or {},
        )

        if claim.claim_id not in self._events:
            self._events[claim.claim_id] = []
        self._events[claim.claim_id].append(event)

        claim.status = new_status

        return event

    def is_valid_transition(self, from_status: ClaimStatus, to_status: ClaimStatus) -> bool:
        """Check if a status transition is allowed."""
        valid = self.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid

    def get_history(self, claim_id: str) -> list[TimelineEvent]:
        """Get all timeline events for a claim."""
        return self._events.get(claim_id, [])

    def get_current_duration(self, claim_id: str) -> Optional[float]:
        """Get hours since the first event (total processing time)."""
        events = self._events.get(claim_id, [])
        if not events:
            return None
        first = events[0].timestamp
        return (datetime.now() - first).total_seconds() / 3600

    def get_status_durations(self, claim_id: str) -> dict[str, float]:
        """Get time spent in each status (in hours)."""
        events = self._events.get(claim_id, [])
        if len(events) < 2:
            return {}

        durations: dict[str, float] = {}
        for i in range(len(events) - 1):
            status = events[i].status.value
            duration = (events[i + 1].timestamp - events[i].timestamp).total_seconds() / 3600
            durations[status] = durations.get(status, 0) + duration

        return durations

    def initialize_claim(self, claim: Claim, actor: str = "system") -> TimelineEvent:
        """Create the initial submission event for a new claim."""
        event = TimelineEvent(
            status=ClaimStatus.SUBMITTED,
            actor=actor,
            description="Claim submitted for processing",
        )
        self._events[claim.claim_id] = [event]
        claim.status = ClaimStatus.SUBMITTED
        return event
