"""Tests for policy components."""

from claimbot.models import CoverageDetail
from claimbot.policy.deductible import DeductibleCalculator
from claimbot.policy.types import InsuranceType, get_default_coverages, get_default_exclusions


class TestDeductibleCalculator:
    def setup_method(self):
        self.calculator = DeductibleCalculator()

    def test_no_deductible(self):
        result = self.calculator.apply(amount=10000, deductible=0)
        assert result["net_amount"] == 10000
        assert result["insured_pays"] == 0

    def test_deductible_applied(self):
        result = self.calculator.apply(amount=10000, deductible=500)
        assert result["net_amount"] == 9500
        assert result["deductible_applied"] == 500

    def test_deductible_exceeds_amount(self):
        result = self.calculator.apply(amount=200, deductible=500)
        assert result["net_amount"] == 0
        assert result["deductible_applied"] == 200

    def test_copay_applied(self):
        result = self.calculator.apply(amount=10000, deductible=0, copay_percent=20)
        assert result["net_amount"] == 8000
        assert result["copay_applied"] == 2000

    def test_deductible_and_copay(self):
        result = self.calculator.apply(amount=10000, deductible=1000, copay_percent=20)
        # After deductible: 9000, copay 20% of 9000 = 1800
        # Insured pays: 1000 + 1800 = 2800
        # Net: 10000 - 2800 = 7200
        assert result["net_amount"] == 7200.0
        assert result["deductible_applied"] == 1000
        assert result["copay_applied"] == 1800

    def test_coinsurance(self):
        result = self.calculator.apply(amount=10000, deductible=1000, coinsurance_percent=80)
        # After deductible: 9000
        # Insurer pays 80%: 7200, patient pays 20%: 1800
        # Total insured pays: 1000 + 1800 = 2800
        # Net: 7200
        assert result["net_amount"] == 7200

    def test_out_of_pocket_max(self):
        result = self.calculator.apply(
            amount=50000, deductible=5000, copay_percent=20, out_of_pocket_max=10000
        )
        # Deductible: 5000, copay: 20% of 45000 = 9000
        # Total insured: 14000, but capped at 10000
        assert result["insured_pays"] == 10000
        assert result["net_amount"] == 40000

    def test_zero_amount(self):
        result = self.calculator.apply(amount=0, deductible=500)
        assert result["net_amount"] == 0

    def test_health_cost_sharing(self):
        result = self.calculator.calculate_health_cost_sharing(
            total_charges=10000,
            deductible=2000,
            deductible_met=0,
            copay_flat=30,
            coinsurance_percent=80,
            out_of_pocket_max=8000,
        )
        assert result["total_charges"] == 10000
        assert result["patient_pays"] > 0
        assert result["insurer_pays"] > 0
        assert abs(result["patient_pays"] + result["insurer_pays"] - 10000) < 0.01


class TestInsuranceTypes:
    def test_all_types_have_coverages(self):
        for ins_type in InsuranceType:
            coverages = get_default_coverages(ins_type)
            assert len(coverages) > 0, f"{ins_type.value} has no coverages"

    def test_all_types_have_exclusions(self):
        for ins_type in InsuranceType:
            exclusions = get_default_exclusions(ins_type)
            assert len(exclusions) > 0, f"{ins_type.value} has no exclusions"

    def test_auto_has_collision(self):
        coverages = get_default_coverages(InsuranceType.AUTO)
        names = [c.name for c in coverages]
        assert "collision" in names

    def test_health_has_inpatient(self):
        coverages = get_default_coverages(InsuranceType.HEALTH)
        names = [c.name for c in coverages]
        assert "inpatient" in names

    def test_coverage_detail_types(self):
        coverages = get_default_coverages(InsuranceType.AUTO)
        for cov in coverages:
            assert isinstance(cov, CoverageDetail)
            assert cov.limit >= 0
