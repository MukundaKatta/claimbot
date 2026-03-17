"""Tests for ClaimAssessor."""

from datetime import date, timedelta

from claimbot.models import (
    Claim,
    CoverageDetail,
    Policy,
    RouteDecision,
    Severity,
)
from claimbot.processor.assessor import ClaimAssessor


class TestClaimAssessor:
    def setup_method(self):
        self.assessor = ClaimAssessor()

    def _make_policy(self, **kwargs):
        defaults = {
            "insurance_type": "auto",
            "effective_date": date.today() - timedelta(days=180),
            "expiration_date": date.today() + timedelta(days=180),
            "coverages": [
                CoverageDetail(name="collision", limit=50000, deductible=500),
                CoverageDetail(name="comprehensive", limit=50000, deductible=250),
            ],
            "max_coverage_limit": 100000,
        }
        defaults.update(kwargs)
        return Policy(**defaults)

    def _make_claim(self, **kwargs):
        defaults = {
            "insurance_type": "auto",
            "claimed_amount": 5000,
            "date_of_loss": date.today() - timedelta(days=5),
            "severity": Severity.MODERATE,
        }
        defaults.update(kwargs)
        return Claim(**defaults)

    def test_valid_claim_is_covered(self):
        claim = self._make_claim()
        policy = self._make_policy()
        assessment = self.assessor.evaluate(claim, policy)
        assert assessment.is_valid is True
        assert assessment.is_covered is True

    def test_expired_policy_denied(self):
        claim = self._make_claim()
        policy = self._make_policy(
            expiration_date=date.today() - timedelta(days=10),
        )
        assessment = self.assessor.evaluate(claim, policy)
        assert assessment.is_valid is False
        assert "Policy is expired" in assessment.denial_reasons

    def test_type_mismatch_denied(self):
        claim = self._make_claim(insurance_type="home")
        policy = self._make_policy(insurance_type="auto")
        assessment = self.assessor.evaluate(claim, policy)
        assert assessment.is_valid is False

    def test_low_amount_auto_approve(self):
        claim = self._make_claim(claimed_amount=1000, severity=Severity.MINOR)
        policy = self._make_policy()
        assessment = self.assessor.evaluate(claim, policy)
        # Low risk, low amount should auto-approve.
        assert assessment.route_decision == RouteDecision.AUTO_APPROVE

    def test_high_amount_not_auto_approved(self):
        claim = self._make_claim(claimed_amount=80000, severity=Severity.CATASTROPHIC)
        policy = self._make_policy()
        assessment = self.assessor.evaluate(claim, policy)
        assert assessment.route_decision != RouteDecision.AUTO_APPROVE

    def test_deductible_applied(self):
        claim = self._make_claim(claimed_amount=5000)
        policy = self._make_policy()
        assessment = self.assessor.evaluate(claim, policy)
        assert assessment.deductible_applied > 0
