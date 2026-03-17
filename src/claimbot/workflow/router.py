"""Claim router - directs claims to appropriate processing queues."""

from __future__ import annotations

from dataclasses import dataclass, field

from claimbot.models import (
    Assessment,
    Claim,
    FraudRiskLevel,
    RouteDecision,
    Severity,
)


@dataclass
class RoutingResult:
    """Result of claim routing decision."""

    decision: RouteDecision
    reasons: list[str] = field(default_factory=list)
    priority: int = 5  # 1 = highest, 10 = lowest
    assigned_queue: str = "general"
    estimated_processing_days: int = 5


class ClaimRouter:
    """Routes claims to auto-approve, manual-review, or investigation queues.

    Routing logic considers:
    - Fraud risk assessment
    - Claim amount thresholds
    - Severity level
    - Assessment risk score
    - Policy type-specific rules
    """

    # Auto-approve thresholds by insurance type.
    AUTO_APPROVE_LIMITS: dict[str, float] = {
        "auto": 3000,
        "home": 5000,
        "health": 2000,
        "life": 0,  # Life claims always require manual review.
        "commercial": 5000,
    }

    def route(self, claim: Claim, assessment: Assessment) -> RoutingResult:
        """Determine routing for a claim based on its assessment."""
        reasons: list[str] = []

        # Critical fraud -> investigate immediately.
        if assessment.fraud_risk == FraudRiskLevel.CRITICAL:
            return RoutingResult(
                decision=RouteDecision.INVESTIGATE,
                reasons=["Critical fraud risk detected"] + assessment.fraud_indicators,
                priority=1,
                assigned_queue="special_investigations_unit",
                estimated_processing_days=30,
            )

        # High fraud risk -> investigate.
        if assessment.fraud_risk == FraudRiskLevel.HIGH:
            return RoutingResult(
                decision=RouteDecision.INVESTIGATE,
                reasons=["High fraud risk"] + assessment.fraud_indicators,
                priority=2,
                assigned_queue="fraud_review",
                estimated_processing_days=21,
            )

        # Not covered -> manual review for denial processing.
        if not assessment.is_covered:
            return RoutingResult(
                decision=RouteDecision.MANUAL_REVIEW,
                reasons=["Claim not covered: " + "; ".join(assessment.denial_reasons)],
                priority=4,
                assigned_queue="denials",
                estimated_processing_days=7,
            )

        # High risk score -> manual review.
        if assessment.risk_score >= 60:
            return RoutingResult(
                decision=RouteDecision.INVESTIGATE,
                reasons=[f"Risk score {assessment.risk_score:.0f} exceeds investigation threshold"],
                priority=2,
                assigned_queue="complex_claims",
                estimated_processing_days=14,
            )

        if assessment.risk_score >= 35:
            reasons.append(f"Risk score {assessment.risk_score:.0f} requires manual review")

        # Severity-based routing.
        if claim.severity in (Severity.CATASTROPHIC, Severity.TOTAL_LOSS):
            reasons.append(f"Severity level: {claim.severity.value}")
            return RoutingResult(
                decision=RouteDecision.MANUAL_REVIEW,
                reasons=reasons,
                priority=3,
                assigned_queue="major_losses",
                estimated_processing_days=14,
            )

        # Amount-based auto-approve check.
        auto_limit = self.AUTO_APPROVE_LIMITS.get(claim.insurance_type, 3000)
        if (
            claim.claimed_amount <= auto_limit
            and assessment.risk_score < 35
            and assessment.fraud_risk == FraudRiskLevel.LOW
            and assessment.is_covered
            and claim.severity in (Severity.MINOR, Severity.MODERATE)
        ):
            return RoutingResult(
                decision=RouteDecision.AUTO_APPROVE,
                reasons=[f"Low-risk claim under ${auto_limit:,.0f} threshold"],
                priority=8,
                assigned_queue="auto_processing",
                estimated_processing_days=1,
            )

        # Medium fraud risk -> manual review.
        if assessment.fraud_risk == FraudRiskLevel.MEDIUM:
            reasons.append("Medium fraud risk detected")

        # Default: manual review.
        if not reasons:
            reasons.append("Standard claim requires manual review")

        queue = self._assign_queue(claim)
        est_days = self._estimate_processing_time(claim, assessment)

        return RoutingResult(
            decision=RouteDecision.MANUAL_REVIEW,
            reasons=reasons,
            priority=5,
            assigned_queue=queue,
            estimated_processing_days=est_days,
        )

    def _assign_queue(self, claim: Claim) -> str:
        """Assign claim to a processing queue based on type."""
        queue_map = {
            "auto": "auto_claims",
            "home": "property_claims",
            "health": "medical_claims",
            "life": "life_claims",
            "commercial": "commercial_claims",
        }
        return queue_map.get(claim.insurance_type, "general")

    def _estimate_processing_time(self, claim: Claim, assessment: Assessment) -> int:
        """Estimate processing time in business days."""
        base_days = 5

        if claim.claimed_amount > 50000:
            base_days += 5
        elif claim.claimed_amount > 20000:
            base_days += 3

        if assessment.risk_score > 50:
            base_days += 5
        elif assessment.risk_score > 30:
            base_days += 2

        if claim.severity in (Severity.CATASTROPHIC, Severity.TOTAL_LOSS):
            base_days += 5

        return base_days
