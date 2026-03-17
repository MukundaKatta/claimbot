"""Tests for Pydantic data models."""

from datetime import date, timedelta

from claimbot.models import (
    Claim,
    ClaimStatus,
    CoverageDetail,
    DamageItem,
    Payout,
    Policy,
    Severity,
    TimelineEvent,
)


class TestClaim:
    def test_claim_defaults(self):
        claim = Claim()
        assert claim.claim_id.startswith("CLM-")
        assert claim.status == ClaimStatus.SUBMITTED
        assert claim.claimed_amount == 0.0

    def test_claim_total_damage_estimate(self):
        claim = Claim(
            damage_items=[
                DamageItem(description="bumper", category="collision", estimated_cost=2000),
                DamageItem(description="hood", category="collision", estimated_cost=3000),
            ]
        )
        assert claim.total_damage_estimate == 5000

    def test_claim_total_damage_falls_back_to_claimed(self):
        claim = Claim(claimed_amount=7500)
        assert claim.total_damage_estimate == 7500

    def test_claim_days_since_loss(self):
        claim = Claim(date_of_loss=date.today() - timedelta(days=10))
        assert claim.days_since_loss == 10


class TestPolicy:
    def test_policy_defaults(self):
        policy = Policy()
        assert policy.policy_id.startswith("POL-")
        assert policy.active is True

    def test_policy_is_expired(self):
        policy = Policy(expiration_date=date.today() - timedelta(days=1))
        assert policy.is_expired is True

    def test_policy_not_expired(self):
        policy = Policy(expiration_date=date.today() + timedelta(days=30))
        assert policy.is_expired is False

    def test_get_coverage(self):
        policy = Policy(
            coverages=[
                CoverageDetail(name="collision", limit=50000, deductible=500),
                CoverageDetail(name="comprehensive", limit=50000, deductible=250),
            ]
        )
        cov = policy.get_coverage("collision")
        assert cov is not None
        assert cov.limit == 50000

    def test_get_coverage_not_found(self):
        policy = Policy()
        assert policy.get_coverage("nonexistent") is None


class TestPayout:
    def test_payout_creation(self):
        payout = Payout(
            claim_id="CLM-001",
            policy_id="POL-001",
            claimed_amount=10000,
            approved_amount=10000,
            deductible=500,
            copay=0,
            net_payout=9500,
        )
        assert payout.net_payout == 9500
