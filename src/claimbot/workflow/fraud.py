"""Fraud indicator detector - flags suspicious claim patterns."""

from __future__ import annotations

import re
from typing import Any

from claimbot.models import Claim, FraudRiskLevel, Policy, Severity


class FraudIndicatorDetector:
    """Analyzes claims for fraud indicators and suspicious patterns.

    Common insurance fraud indicators checked:
    - Round-number claims (padding)
    - Extremely high amounts relative to severity
    - Late reporting of loss
    - Inconsistent severity vs. amount
    - Missing police reports for significant losses
    - Vague or overly detailed descriptions
    - Known fraud keywords
    - Multiple damage categories (kitchen-sink claims)
    - Claims filed shortly after policy inception
    """

    # Thresholds for fraud scoring.
    LATE_REPORT_DAYS = 30
    VERY_LATE_REPORT_DAYS = 90
    HIGH_AMOUNT_THRESHOLD = 25000
    VERY_HIGH_AMOUNT_THRESHOLD = 100000
    NEW_POLICY_DAYS = 60
    ROUND_NUMBER_TOLERANCE = 100

    # Suspicious keywords in descriptions.
    FRAUD_KEYWORDS = [
        "cash only", "no receipt", "no documentation", "lost all records",
        "cannot prove", "estimated value", "approximately", "friend told me",
        "heard from someone", "i think it was worth",
    ]

    # Inconsistency patterns: severity that does not match typical claim amounts.
    SEVERITY_AMOUNT_RANGES: dict[Severity, tuple[float, float]] = {
        Severity.MINOR: (0, 5000),
        Severity.MODERATE: (500, 25000),
        Severity.SEVERE: (2000, 100000),
        Severity.CATASTROPHIC: (10000, 500000),
        Severity.TOTAL_LOSS: (5000, 1000000),
    }

    def analyze(self, claim: Claim, policy: Policy) -> dict[str, Any]:
        """Analyze a claim for fraud indicators.

        Returns:
            Dict with risk_level (FraudRiskLevel), indicators (list[str]),
            score (float 0-100).
        """
        indicators: list[str] = []
        score = 0.0

        # Check each fraud pattern.
        score += self._check_round_numbers(claim, indicators)
        score += self._check_amount_severity_mismatch(claim, indicators)
        score += self._check_late_reporting(claim, indicators)
        score += self._check_missing_documentation(claim, indicators)
        score += self._check_description_anomalies(claim, indicators)
        score += self._check_new_policy(claim, policy, indicators)
        score += self._check_kitchen_sink(claim, indicators)
        score += self._check_excessive_amount(claim, indicators)

        score = min(score, 100.0)

        risk_level = self._score_to_risk_level(score)

        return {
            "risk_level": risk_level,
            "indicators": indicators,
            "score": score,
        }

    def _check_round_numbers(self, claim: Claim, indicators: list[str]) -> float:
        """Flag claims with suspiciously round numbers."""
        amount = claim.claimed_amount
        if amount > 0 and amount % 1000 == 0 and amount >= 5000:
            indicators.append(f"Round-number claim amount: ${amount:,.0f}")
            return 10
        if amount > 0 and amount % 500 == 0 and amount >= 2500:
            indicators.append(f"Round-number claim amount: ${amount:,.0f}")
            return 5
        return 0

    def _check_amount_severity_mismatch(self, claim: Claim, indicators: list[str]) -> float:
        """Flag when claimed amount does not match reported severity."""
        expected_range = self.SEVERITY_AMOUNT_RANGES.get(claim.severity)
        if expected_range is None:
            return 0

        low, high = expected_range
        amount = claim.claimed_amount

        if amount > 0 and amount > high * 1.5:
            indicators.append(
                f"Claimed ${amount:,.2f} exceeds expected range for {claim.severity.value} severity "
                f"(${low:,.0f}-${high:,.0f})"
            )
            return 20
        if amount > 0 and amount < low * 0.1 and claim.severity in (Severity.SEVERE, Severity.CATASTROPHIC):
            indicators.append(
                f"Claimed ${amount:,.2f} is unusually low for {claim.severity.value} severity"
            )
            return 5
        return 0

    def _check_late_reporting(self, claim: Claim, indicators: list[str]) -> float:
        """Flag claims filed long after the loss date."""
        days = claim.days_since_loss
        if days > self.VERY_LATE_REPORT_DAYS:
            indicators.append(f"Claim filed {days} days after loss (very late)")
            return 15
        if days > self.LATE_REPORT_DAYS:
            indicators.append(f"Claim filed {days} days after loss (late)")
            return 8
        return 0

    def _check_missing_documentation(self, claim: Claim, indicators: list[str]) -> float:
        """Flag high-value claims without police reports or witnesses."""
        score = 0.0
        if claim.claimed_amount > 5000 and not claim.police_report:
            indicators.append("No police report for high-value claim")
            score += 8
        if claim.claimed_amount > 10000 and claim.witnesses == 0:
            indicators.append("No witnesses for significant claim")
            score += 5
        return score

    def _check_description_anomalies(self, claim: Claim, indicators: list[str]) -> float:
        """Flag suspicious keywords or patterns in claim description."""
        desc_lower = claim.description.lower()
        score = 0.0

        for keyword in self.FRAUD_KEYWORDS:
            if keyword in desc_lower:
                indicators.append(f"Suspicious language in description: '{keyword}'")
                score += 10
                break  # Only flag once for keywords.

        # Vague description (too short).
        if len(claim.description) < 20 and claim.claimed_amount > 5000:
            indicators.append("Vague description for high-value claim")
            score += 5

        # Overly specific dollar amounts in description (pre-calculated).
        dollar_matches = re.findall(r'\$[\d,]+\.\d{2}', claim.description)
        if len(dollar_matches) > 3:
            indicators.append("Multiple precise dollar amounts in description (possible pre-calculation)")
            score += 8

        return score

    def _check_new_policy(self, claim: Claim, policy: Policy, indicators: list[str]) -> float:
        """Flag claims filed shortly after policy inception."""
        days_active = (claim.date_of_loss - policy.effective_date).days
        if 0 <= days_active <= self.NEW_POLICY_DAYS:
            indicators.append(f"Claim filed only {days_active} days after policy started")
            return 12
        return 0

    def _check_kitchen_sink(self, claim: Claim, indicators: list[str]) -> float:
        """Flag claims with an unusual number of damage categories."""
        if len(claim.damage_items) > 5:
            indicators.append(f"Unusually high number of damage items ({len(claim.damage_items)})")
            return 10
        return 0

    def _check_excessive_amount(self, claim: Claim, indicators: list[str]) -> float:
        """Flag extremely high claim amounts."""
        if claim.claimed_amount > self.VERY_HIGH_AMOUNT_THRESHOLD:
            indicators.append(f"Very high claim amount: ${claim.claimed_amount:,.2f}")
            return 10
        if claim.claimed_amount > self.HIGH_AMOUNT_THRESHOLD:
            indicators.append(f"High claim amount: ${claim.claimed_amount:,.2f}")
            return 5
        return 0

    def _score_to_risk_level(self, score: float) -> FraudRiskLevel:
        """Convert numeric score to risk level."""
        if score >= 60:
            return FraudRiskLevel.CRITICAL
        if score >= 40:
            return FraudRiskLevel.HIGH
        if score >= 20:
            return FraudRiskLevel.MEDIUM
        return FraudRiskLevel.LOW
