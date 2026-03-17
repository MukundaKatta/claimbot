"""Deductible calculator - applies deductibles and copays to claim amounts."""

from __future__ import annotations

from typing import Any


class DeductibleCalculator:
    """Applies deductibles, copays, and coinsurance to compute net payable amounts."""

    def apply(
        self,
        amount: float,
        deductible: float = 0.0,
        copay_percent: float = 0.0,
        coinsurance_percent: float = 0.0,
        out_of_pocket_max: float | None = None,
    ) -> dict[str, Any]:
        """Calculate net amount after deductible, copay, and coinsurance.

        Args:
            amount: The total approved claim amount.
            deductible: Fixed dollar deductible the insured pays first.
            copay_percent: Percentage copay the insured pays on remainder.
            coinsurance_percent: Insurer's share percentage after deductible
                (e.g., 80 means insurer pays 80%).
            out_of_pocket_max: Maximum the insured pays out of pocket.

        Returns:
            Dict with net_amount, insured_pays, deductible_applied, copay_applied,
            coinsurance_applied.
        """
        if amount <= 0:
            return {
                "net_amount": 0.0,
                "insured_pays": 0.0,
                "deductible_applied": 0.0,
                "copay_applied": 0.0,
                "coinsurance_applied": 0.0,
            }

        # Step 1: Apply deductible.
        actual_deductible = min(deductible, amount)
        after_deductible = amount - actual_deductible

        # Step 2: Apply copay percentage (insured's share).
        copay_amount = after_deductible * (copay_percent / 100) if copay_percent > 0 else 0.0

        # Step 3: Apply coinsurance (insurer pays this percentage).
        if coinsurance_percent > 0:
            insurer_share = after_deductible * (coinsurance_percent / 100)
            coinsurance_cost = after_deductible - insurer_share
        else:
            insurer_share = after_deductible
            coinsurance_cost = 0.0

        # Total insured pays.
        insured_total = actual_deductible + copay_amount + coinsurance_cost

        # Apply out-of-pocket maximum if specified.
        if out_of_pocket_max is not None and insured_total > out_of_pocket_max:
            excess = insured_total - out_of_pocket_max
            insured_total = out_of_pocket_max
            insurer_share += excess

        net_amount = max(0.0, amount - insured_total)

        return {
            "net_amount": round(net_amount, 2),
            "insured_pays": round(insured_total, 2),
            "deductible_applied": round(actual_deductible, 2),
            "copay_applied": round(copay_amount, 2),
            "coinsurance_applied": round(coinsurance_cost, 2),
        }

    def calculate_health_cost_sharing(
        self,
        total_charges: float,
        deductible: float,
        deductible_met: float = 0.0,
        copay_flat: float = 0.0,
        coinsurance_percent: float = 80.0,
        out_of_pocket_max: float = 8000.0,
        out_of_pocket_spent: float = 0.0,
    ) -> dict[str, Any]:
        """Calculate health insurance cost sharing with accumulated deductible tracking.

        This models a more realistic health insurance scenario where the deductible
        accumulates over the plan year.

        Args:
            total_charges: Total medical charges.
            deductible: Annual deductible amount.
            deductible_met: How much of the deductible has already been met this year.
            copay_flat: Flat copay amount (e.g., $30 office visit).
            coinsurance_percent: Insurer's percentage after deductible (e.g., 80).
            out_of_pocket_max: Annual out-of-pocket maximum.
            out_of_pocket_spent: How much has already been spent out-of-pocket.
        """
        remaining_deductible = max(0, deductible - deductible_met)
        remaining_oop = max(0, out_of_pocket_max - out_of_pocket_spent)

        # Apply flat copay first.
        patient_pays = min(copay_flat, total_charges)
        remaining_charges = max(0, total_charges - copay_flat)

        # Apply remaining deductible.
        deductible_portion = min(remaining_deductible, remaining_charges)
        patient_pays += deductible_portion
        remaining_charges -= deductible_portion

        # Apply coinsurance on remaining.
        if remaining_charges > 0 and coinsurance_percent < 100:
            patient_coinsurance = remaining_charges * (1 - coinsurance_percent / 100)
            patient_pays += patient_coinsurance
        else:
            patient_coinsurance = 0.0

        # Cap at out-of-pocket max.
        if patient_pays > remaining_oop:
            patient_pays = remaining_oop

        insurer_pays = total_charges - patient_pays

        return {
            "total_charges": round(total_charges, 2),
            "patient_pays": round(patient_pays, 2),
            "insurer_pays": round(insurer_pays, 2),
            "deductible_applied": round(deductible_portion, 2),
            "copay_applied": round(min(copay_flat, total_charges), 2),
            "coinsurance_applied": round(patient_coinsurance, 2),
            "new_deductible_met": round(deductible_met + deductible_portion, 2),
            "new_oop_spent": round(out_of_pocket_spent + patient_pays, 2),
        }
