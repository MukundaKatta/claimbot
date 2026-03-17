"""Damage estimator - computes payout amounts from damage descriptions."""

from __future__ import annotations

from claimbot.models import Assessment, Claim, Payout, Policy
from claimbot.policy.deductible import DeductibleCalculator


class DamageEstimator:
    """Computes payout amounts based on claim damage, assessment, and policy terms."""

    def __init__(self) -> None:
        self.deductible_calculator = DeductibleCalculator()

    def compute(self, claim: Claim, assessment: Assessment, policy: Policy) -> Payout:
        """Calculate the net payout for a claim.

        Calculation:
        1. Start with claimed amount or sum of damage estimates
        2. Cap at coverage limit
        3. Subtract deductible
        4. Apply copay percentage
        5. Compute net payout
        """
        claimed_amount = claim.total_damage_estimate

        # If claim is not covered, payout is zero.
        if not assessment.is_covered:
            return Payout(
                claim_id=claim.claim_id,
                policy_id=policy.policy_id,
                claimed_amount=claimed_amount,
                approved_amount=0.0,
                deductible=0.0,
                copay=0.0,
                net_payout=0.0,
                notes=["Claim denied: " + "; ".join(assessment.denial_reasons)],
            )

        # Build line-item breakdown.
        breakdown: dict[str, float] = {}
        for item in claim.damage_items:
            breakdown[item.category] = breakdown.get(item.category, 0) + item.estimated_cost

        if not breakdown and claimed_amount > 0:
            breakdown["general"] = claimed_amount

        # Apply coverage limit.
        coverage_limit = assessment.coverage_limit
        limit_applied = False
        approved_amount = claimed_amount

        if coverage_limit > 0 and approved_amount > coverage_limit:
            reduction_ratio = coverage_limit / approved_amount
            approved_amount = coverage_limit
            breakdown = {k: v * reduction_ratio for k, v in breakdown.items()}
            limit_applied = True

        # Apply deductible and copay.
        deductible = assessment.deductible_applied
        copay = assessment.copay_applied

        deductible_result = self.deductible_calculator.apply(
            amount=approved_amount,
            deductible=deductible,
            copay_percent=0,  # Copay already computed by assessor.
        )

        net_after_deductible = deductible_result["net_amount"]
        net_payout = max(0.0, net_after_deductible - copay)

        notes: list[str] = []
        if limit_applied:
            notes.append(f"Coverage limit of ${coverage_limit:,.2f} applied")
        if deductible > 0:
            notes.append(f"Deductible of ${deductible:,.2f} applied")
        if copay > 0:
            notes.append(f"Copay of ${copay:,.2f} applied")

        return Payout(
            claim_id=claim.claim_id,
            policy_id=policy.policy_id,
            claimed_amount=claimed_amount,
            approved_amount=approved_amount,
            deductible=deductible,
            copay=copay,
            net_payout=round(net_payout, 2),
            coverage_limit_applied=limit_applied,
            payout_breakdown=breakdown,
            notes=notes,
        )
