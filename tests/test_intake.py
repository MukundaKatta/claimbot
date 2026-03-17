"""Tests for ClaimIntake processor."""

from claimbot.models import LiabilityDetermination, Severity
from claimbot.processor.intake import ClaimIntake


class TestClaimIntake:
    def setup_method(self):
        self.intake = ClaimIntake()

    def test_extract_basic_auto_claim(self):
        claim = self.intake.extract(
            "Rear-ended at a red light. Bumper damaged.",
            insurance_type="auto",
            claimant_name="John Doe",
        )
        assert claim.insurance_type == "auto"
        assert claim.claimant_name == "John Doe"
        assert len(claim.damage_items) > 0

    def test_extract_severity_minor(self):
        claim = self.intake.extract("Minor scratch on the door")
        assert claim.severity == Severity.MINOR

    def test_extract_severity_total_loss(self):
        claim = self.intake.extract("Vehicle totaled in the crash")
        assert claim.severity == Severity.TOTAL_LOSS

    def test_extract_liability_third_party(self):
        claim = self.intake.extract("Hit by other driver who ran a red light")
        assert claim.liability == LiabilityDetermination.THIRD_PARTY_AT_FAULT

    def test_extract_liability_act_of_god(self):
        claim = self.intake.extract("Tornado destroyed the garage and car")
        assert claim.liability == LiabilityDetermination.ACT_OF_GOD

    def test_extract_dollar_amount(self):
        claim = self.intake.extract("Damage estimated at $12,500.00")
        assert claim.claimed_amount == 12500.00

    def test_extract_police_report(self):
        claim = self.intake.extract("Police report was filed at the scene")
        assert claim.police_report is True

    def test_extract_witnesses(self):
        claim = self.intake.extract("3 witnesses saw the accident")
        assert claim.witnesses == 3

    def test_extract_home_claim(self):
        claim = self.intake.extract(
            "Roof damaged by fallen tree during storm",
            insurance_type="home",
        )
        assert claim.insurance_type == "home"
        assert len(claim.damage_items) > 0
        categories = {item.category for item in claim.damage_items}
        assert "dwelling" in categories

    def test_extract_health_claim(self):
        claim = self.intake.extract(
            "Emergency room visit after chest pain. Ambulance called.",
            insurance_type="health",
        )
        assert claim.insurance_type == "health"
        assert len(claim.damage_items) > 0
