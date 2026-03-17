"""Tests for workflow components."""

import pytest
from datetime import date, timedelta

from claimbot.models import (
    Assessment,
    Claim,
    ClaimStatus,
    CoverageDetail,
    FraudRiskLevel,
    Policy,
    RouteDecision,
    Severity,
)
from claimbot.workflow.fraud import FraudIndicatorDetector
from claimbot.workflow.router import ClaimRouter
from claimbot.workflow.timeline import ClaimTimeline


class TestFraudDetector:
    def setup_method(self):
        self.detector = FraudIndicatorDetector()

    def _make_policy(self):
        return Policy(
            insurance_type="auto",
            effective_date=date.today() - timedelta(days=180),
            expiration_date=date.today() + timedelta(days=180),
        )

    def test_low_risk_claim(self):
        claim = Claim(
            claimed_amount=2000,
            severity=Severity.MINOR,
            description="Minor fender bender in a parking lot",
            police_report=True,
            date_of_loss=date.today() - timedelta(days=2),
        )
        result = self.detector.analyze(claim, self._make_policy())
        assert result["risk_level"] == FraudRiskLevel.LOW

    def test_round_number_flagged(self):
        claim = Claim(
            claimed_amount=50000,
            severity=Severity.SEVERE,
            description="Major accident on the highway",
            date_of_loss=date.today() - timedelta(days=2),
        )
        result = self.detector.analyze(claim, self._make_policy())
        assert any("round" in ind.lower() for ind in result["indicators"])

    def test_late_reporting_flagged(self):
        claim = Claim(
            claimed_amount=5000,
            severity=Severity.MODERATE,
            description="Car was damaged",
            date_of_loss=date.today() - timedelta(days=100),
        )
        result = self.detector.analyze(claim, self._make_policy())
        assert any("late" in ind.lower() for ind in result["indicators"])

    def test_suspicious_keywords_flagged(self):
        claim = Claim(
            claimed_amount=8000,
            severity=Severity.MODERATE,
            description="I think it was worth about $8000, cash only please, no receipt available",
            date_of_loss=date.today() - timedelta(days=2),
        )
        result = self.detector.analyze(claim, self._make_policy())
        assert any("suspicious" in ind.lower() for ind in result["indicators"])

    def test_new_policy_flagged(self):
        policy = Policy(
            insurance_type="auto",
            effective_date=date.today() - timedelta(days=10),
        )
        claim = Claim(
            claimed_amount=20000,
            severity=Severity.SEVERE,
            description="Vehicle severely damaged",
            date_of_loss=date.today() - timedelta(days=5),
        )
        result = self.detector.analyze(claim, policy)
        assert any("policy started" in ind.lower() for ind in result["indicators"])


class TestClaimRouter:
    def setup_method(self):
        self.router = ClaimRouter()

    def test_auto_approve_low_risk(self):
        claim = Claim(claimed_amount=1000, severity=Severity.MINOR, insurance_type="auto")
        assessment = Assessment(
            claim_id=claim.claim_id,
            policy_id="POL-001",
            is_covered=True,
            risk_score=15,
            fraud_risk=FraudRiskLevel.LOW,
        )
        result = self.router.route(claim, assessment)
        assert result.decision == RouteDecision.AUTO_APPROVE

    def test_investigate_critical_fraud(self):
        claim = Claim(claimed_amount=50000, severity=Severity.SEVERE)
        assessment = Assessment(
            claim_id=claim.claim_id,
            policy_id="POL-001",
            fraud_risk=FraudRiskLevel.CRITICAL,
            fraud_indicators=["Multiple suspicious indicators"],
        )
        result = self.router.route(claim, assessment)
        assert result.decision == RouteDecision.INVESTIGATE
        assert result.assigned_queue == "special_investigations_unit"

    def test_manual_review_not_covered(self):
        claim = Claim(claimed_amount=5000, severity=Severity.MODERATE)
        assessment = Assessment(
            claim_id=claim.claim_id,
            policy_id="POL-001",
            is_covered=False,
            denial_reasons=["Coverage not found"],
        )
        result = self.router.route(claim, assessment)
        assert result.decision == RouteDecision.MANUAL_REVIEW

    def test_catastrophic_requires_review(self):
        claim = Claim(claimed_amount=100000, severity=Severity.CATASTROPHIC)
        assessment = Assessment(
            claim_id=claim.claim_id,
            policy_id="POL-001",
            is_covered=True,
            risk_score=30,
            fraud_risk=FraudRiskLevel.LOW,
        )
        result = self.router.route(claim, assessment)
        assert result.decision == RouteDecision.MANUAL_REVIEW


class TestClaimTimeline:
    def setup_method(self):
        self.timeline = ClaimTimeline()

    def test_initialize_claim(self):
        claim = Claim()
        self.timeline.initialize_claim(claim)
        assert claim.status == ClaimStatus.SUBMITTED
        history = self.timeline.get_history(claim.claim_id)
        assert len(history) == 1

    def test_valid_transition(self):
        claim = Claim()
        self.timeline.initialize_claim(claim)
        self.timeline.record_event(claim, ClaimStatus.UNDER_REVIEW)
        assert claim.status == ClaimStatus.UNDER_REVIEW

    def test_invalid_transition_raises(self):
        claim = Claim()
        self.timeline.initialize_claim(claim)
        with pytest.raises(ValueError, match="Invalid transition"):
            self.timeline.record_event(claim, ClaimStatus.PAID)

    def test_full_lifecycle(self):
        claim = Claim()
        self.timeline.initialize_claim(claim)
        self.timeline.record_event(claim, ClaimStatus.UNDER_REVIEW)
        self.timeline.record_event(claim, ClaimStatus.APPROVED)
        self.timeline.record_event(claim, ClaimStatus.PAID)
        self.timeline.record_event(claim, ClaimStatus.CLOSED)
        assert claim.status == ClaimStatus.CLOSED
        history = self.timeline.get_history(claim.claim_id)
        assert len(history) == 5  # init + 4 transitions
