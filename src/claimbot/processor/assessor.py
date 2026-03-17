"""Claim assessor - evaluates validity, coverage, and liability."""

from __future__ import annotations

from claimbot.models import (
    Assessment,
    Claim,
    ClaimStatus,
    FraudRiskLevel,
    LiabilityDetermination,
    Policy,
    RouteDecision,
    Severity,
)
from claimbot.policy.checker import PolicyChecker
from claimbot.workflow.fraud import FraudIndicatorDetector


class ClaimAssessor:
    """Evaluates claim validity, coverage applicability, and liability."""

    def __init__(self) -> None:
        self.policy_checker = PolicyChecker()
        self.fraud_detector = FraudIndicatorDetector()

    def evaluate(self, claim: Claim, policy: Policy) -> Assessment:
        """Perform a full assessment of a claim against a policy.

        Steps:
        1. Validate basic claim requirements
        2. Check policy coverage and exclusions
        3. Determine liability
        4. Run fraud detection
        5. Compute risk score
        6. Decide routing
        """
        denial_reasons: list[str] = []
        notes: list[str] = []

        # Step 1: Basic validation.
        if not self._validate_basics(claim, policy, denial_reasons):
            return Assessment(
                claim_id=claim.claim_id,
                policy_id=policy.policy_id,
                is_valid=False,
                is_covered=False,
                denial_reasons=denial_reasons,
                route_decision=RouteDecision.MANUAL_REVIEW,
            )

        # Step 2: Policy coverage check.
        coverage_result = self.policy_checker.check(claim, policy)
        is_covered = coverage_result["is_covered"]
        coverage_matched = coverage_result.get("coverage_matched", "")
        coverage_limit = coverage_result.get("coverage_limit", 0.0)
        deductible = coverage_result.get("deductible", 0.0)
        copay_percent = coverage_result.get("copay_percent", 0.0)

        if not is_covered:
            denial_reasons.extend(coverage_result.get("reasons", ["Coverage not applicable"]))

        if coverage_result.get("exclusion_matched"):
            denial_reasons.append(f"Exclusion applies: {coverage_result['exclusion_matched']}")
            is_covered = False

        # Step 3: Liability determination.
        liability = self._assess_liability(claim, notes)

        # Step 4: Fraud detection.
        fraud_result = self.fraud_detector.analyze(claim, policy)
        fraud_risk = fraud_result["risk_level"]
        fraud_indicators = fraud_result["indicators"]

        # Step 5: Risk score.
        risk_score = self._compute_risk_score(claim, fraud_risk, is_covered, liability)

        # Step 6: Routing decision.
        route = self._decide_route(claim, risk_score, fraud_risk, is_covered)

        copay_applied = (claim.claimed_amount - deductible) * (copay_percent / 100) if copay_percent > 0 else 0.0

        return Assessment(
            claim_id=claim.claim_id,
            policy_id=policy.policy_id,
            is_valid=True,
            is_covered=is_covered,
            coverage_matched=coverage_matched,
            liability=liability,
            coverage_limit=coverage_limit,
            deductible_applied=deductible,
            copay_applied=max(0, copay_applied),
            denial_reasons=denial_reasons,
            risk_score=risk_score,
            route_decision=route,
            fraud_risk=fraud_risk,
            fraud_indicators=fraud_indicators,
            notes=notes,
        )

    def _validate_basics(
        self, claim: Claim, policy: Policy, denial_reasons: list[str]
    ) -> bool:
        """Check fundamental validity requirements."""
        valid = True

        if policy.is_expired:
            denial_reasons.append("Policy is expired")
            valid = False

        if not policy.active:
            denial_reasons.append("Policy is inactive")
            valid = False

        if claim.insurance_type != policy.insurance_type:
            denial_reasons.append(
                f"Claim type '{claim.insurance_type}' does not match policy type '{policy.insurance_type}'"
            )
            valid = False

        if claim.date_of_loss < policy.effective_date:
            denial_reasons.append("Date of loss is before policy effective date")
            valid = False

        if policy.expiration_date and claim.date_of_loss > policy.expiration_date:
            denial_reasons.append("Date of loss is after policy expiration")
            valid = False

        if claim.claimed_amount <= 0 and not claim.damage_items:
            denial_reasons.append("No claimed amount or damage items specified")
            valid = False

        return valid

    def _assess_liability(
        self, claim: Claim, notes: list[str]
    ) -> LiabilityDetermination:
        """Refine liability determination based on claim details."""
        liability = claim.liability

        if liability == LiabilityDetermination.CLAIMANT_AT_FAULT:
            notes.append("Claimant at fault - coverage may be limited to collision only")
        elif liability == LiabilityDetermination.SHARED_FAULT:
            notes.append("Shared fault - payout may be reduced proportionally")
        elif liability == LiabilityDetermination.ACT_OF_GOD:
            notes.append("Act of God - comprehensive coverage applies if available")

        return liability

    def _compute_risk_score(
        self,
        claim: Claim,
        fraud_risk: FraudRiskLevel,
        is_covered: bool,
        liability: LiabilityDetermination,
    ) -> float:
        """Compute a 0-100 risk score for the claim."""
        score = 20.0  # Baseline.

        # Amount-based risk.
        if claim.claimed_amount > 50000:
            score += 20
        elif claim.claimed_amount > 20000:
            score += 10
        elif claim.claimed_amount > 10000:
            score += 5

        # Severity-based risk.
        severity_scores = {
            Severity.MINOR: 0,
            Severity.MODERATE: 5,
            Severity.SEVERE: 15,
            Severity.CATASTROPHIC: 25,
            Severity.TOTAL_LOSS: 20,
        }
        score += severity_scores.get(claim.severity, 5)

        # Fraud risk contribution.
        fraud_scores = {
            FraudRiskLevel.LOW: 0,
            FraudRiskLevel.MEDIUM: 15,
            FraudRiskLevel.HIGH: 30,
            FraudRiskLevel.CRITICAL: 45,
        }
        score += fraud_scores.get(fraud_risk, 0)

        # Liability adjustments.
        if liability == LiabilityDetermination.CLAIMANT_AT_FAULT:
            score += 5
        elif liability == LiabilityDetermination.UNDETERMINED:
            score += 10

        # Coverage mismatch.
        if not is_covered:
            score += 10

        # No police report for high-value claims.
        if claim.claimed_amount > 5000 and not claim.police_report:
            score += 5

        # Late filing.
        if claim.days_since_loss > 30:
            score += 5
        if claim.days_since_loss > 90:
            score += 10

        return min(score, 100.0)

    def _decide_route(
        self,
        claim: Claim,
        risk_score: float,
        fraud_risk: FraudRiskLevel,
        is_covered: bool,
    ) -> RouteDecision:
        """Determine claim routing based on risk assessment."""
        if fraud_risk in (FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL):
            return RouteDecision.INVESTIGATE

        if not is_covered:
            return RouteDecision.MANUAL_REVIEW

        if risk_score >= 60:
            return RouteDecision.INVESTIGATE
        elif risk_score >= 35:
            return RouteDecision.MANUAL_REVIEW

        # Auto-approve low-risk, low-amount claims.
        if claim.claimed_amount <= 5000 and risk_score < 35:
            return RouteDecision.AUTO_APPROVE

        return RouteDecision.MANUAL_REVIEW
