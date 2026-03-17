"""Pydantic data models for insurance claim processing."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    """Lifecycle status of an insurance claim."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ADDITIONAL_INFO_REQUESTED = "additional_info_requested"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    DENIED = "denied"
    INVESTIGATING = "investigating"
    PAID = "paid"
    CLOSED = "closed"
    APPEALED = "appealed"


class Severity(str, Enum):
    """Damage severity levels."""

    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"
    TOTAL_LOSS = "total_loss"


class LiabilityDetermination(str, Enum):
    """Who bears liability for the loss."""

    CLAIMANT_AT_FAULT = "claimant_at_fault"
    THIRD_PARTY_AT_FAULT = "third_party_at_fault"
    SHARED_FAULT = "shared_fault"
    ACT_OF_GOD = "act_of_god"
    UNDETERMINED = "undetermined"


class RouteDecision(str, Enum):
    """Claim routing decisions."""

    AUTO_APPROVE = "auto_approve"
    MANUAL_REVIEW = "manual_review"
    INVESTIGATE = "investigate"


class FraudRiskLevel(str, Enum):
    """Fraud risk classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DamageItem(BaseModel):
    """Individual damage component within a claim."""

    description: str
    category: str
    estimated_cost: float = Field(ge=0)
    severity: Severity = Severity.MODERATE


class Claim(BaseModel):
    """An insurance claim submitted by a policyholder."""

    claim_id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:8].upper()}")
    policy_id: str = ""
    claimant_name: str = ""
    insurance_type: str = "auto"
    date_of_loss: date = Field(default_factory=date.today)
    date_filed: datetime = Field(default_factory=datetime.now)
    description: str = ""
    damage_items: list[DamageItem] = Field(default_factory=list)
    claimed_amount: float = Field(default=0.0, ge=0)
    severity: Severity = Severity.MODERATE
    liability: LiabilityDetermination = LiabilityDetermination.UNDETERMINED
    location: str = ""
    witnesses: int = 0
    police_report: bool = False
    status: ClaimStatus = ClaimStatus.SUBMITTED
    fraud_risk: FraudRiskLevel = FraudRiskLevel.LOW
    fraud_indicators: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def total_damage_estimate(self) -> float:
        if self.damage_items:
            return sum(item.estimated_cost for item in self.damage_items)
        return self.claimed_amount

    @property
    def days_since_loss(self) -> int:
        return (date.today() - self.date_of_loss).days


class CoverageDetail(BaseModel):
    """Details of a specific coverage within a policy."""

    name: str
    limit: float = Field(ge=0)
    deductible: float = Field(default=0.0, ge=0)
    copay_percent: float = Field(default=0.0, ge=0, le=100)
    covered: bool = True


class Policy(BaseModel):
    """An insurance policy defining coverage terms."""

    policy_id: str = Field(default_factory=lambda: f"POL-{uuid.uuid4().hex[:8].upper()}")
    policyholder_name: str = ""
    insurance_type: str = "auto"
    effective_date: date = Field(default_factory=date.today)
    expiration_date: Optional[date] = None
    premium: float = Field(default=0.0, ge=0)
    coverages: list[CoverageDetail] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    max_coverage_limit: float = Field(default=100000.0, ge=0)
    active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expiration_date is None:
            return False
        return date.today() > self.expiration_date

    def get_coverage(self, name: str) -> Optional[CoverageDetail]:
        for cov in self.coverages:
            if cov.name.lower() == name.lower():
                return cov
        return None


class Assessment(BaseModel):
    """Result of evaluating a claim's validity and coverage."""

    claim_id: str
    policy_id: str
    is_valid: bool = True
    is_covered: bool = True
    coverage_matched: str = ""
    liability: LiabilityDetermination = LiabilityDetermination.UNDETERMINED
    coverage_limit: float = 0.0
    deductible_applied: float = 0.0
    copay_applied: float = 0.0
    denial_reasons: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0, le=100)
    route_decision: RouteDecision = RouteDecision.MANUAL_REVIEW
    fraud_risk: FraudRiskLevel = FraudRiskLevel.LOW
    fraud_indicators: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Payout(BaseModel):
    """Computed payout for a claim after deductibles and limits."""

    claim_id: str
    policy_id: str
    claimed_amount: float = Field(ge=0)
    approved_amount: float = Field(ge=0)
    deductible: float = Field(default=0.0, ge=0)
    copay: float = Field(default=0.0, ge=0)
    net_payout: float = Field(ge=0)
    coverage_limit_applied: bool = False
    payout_breakdown: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    """A single event in a claim's lifecycle."""

    timestamp: datetime = Field(default_factory=datetime.now)
    status: ClaimStatus
    actor: str = "system"
    description: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)
