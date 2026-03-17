"""Policy checker - verifies claims against policy terms, exclusions, and limits."""

from __future__ import annotations

from typing import Any

from claimbot.models import Claim, CoverageDetail, Policy
from claimbot.policy.types import InsuranceType, get_default_exclusions


class PolicyChecker:
    """Verifies whether a claim is covered under a given policy."""

    def check(self, claim: Claim, policy: Policy) -> dict[str, Any]:
        """Check claim against policy terms.

        Returns a dict with:
            is_covered: bool
            coverage_matched: str (coverage name)
            coverage_limit: float
            deductible: float
            copay_percent: float
            exclusion_matched: str or None
            reasons: list[str] (reasons for denial if not covered)
        """
        reasons: list[str] = []

        # Type mismatch check.
        if claim.insurance_type != policy.insurance_type:
            return {
                "is_covered": False,
                "coverage_matched": "",
                "coverage_limit": 0.0,
                "deductible": 0.0,
                "copay_percent": 0.0,
                "exclusion_matched": None,
                "reasons": [f"Claim type '{claim.insurance_type}' does not match policy type '{policy.insurance_type}'"],
            }

        # Check exclusions.
        exclusion = self._check_exclusions(claim, policy)
        if exclusion:
            return {
                "is_covered": False,
                "coverage_matched": "",
                "coverage_limit": 0.0,
                "deductible": 0.0,
                "copay_percent": 0.0,
                "exclusion_matched": exclusion,
                "reasons": [f"Claim matches exclusion: {exclusion}"],
            }

        # Find matching coverage.
        matched_coverage = self._find_coverage(claim, policy)

        if matched_coverage is None:
            return {
                "is_covered": False,
                "coverage_matched": "",
                "coverage_limit": 0.0,
                "deductible": 0.0,
                "copay_percent": 0.0,
                "exclusion_matched": None,
                "reasons": ["No matching coverage found in policy"],
            }

        # Check if claimed amount exceeds the overall policy limit.
        notes_reasons = []
        if claim.claimed_amount > policy.max_coverage_limit:
            notes_reasons.append(
                f"Claimed amount ${claim.claimed_amount:,.2f} exceeds policy max ${policy.max_coverage_limit:,.2f}"
            )

        return {
            "is_covered": True,
            "coverage_matched": matched_coverage.name,
            "coverage_limit": matched_coverage.limit,
            "deductible": matched_coverage.deductible,
            "copay_percent": matched_coverage.copay_percent,
            "exclusion_matched": None,
            "reasons": notes_reasons,
        }

    def _check_exclusions(self, claim: Claim, policy: Policy) -> str | None:
        """Check if claim description or damage categories match any exclusion."""
        desc_lower = claim.description.lower()

        # Check policy-specific exclusions.
        all_exclusions = list(policy.exclusions)

        # Also check type-default exclusions.
        try:
            ins_type = InsuranceType(policy.insurance_type)
            all_exclusions.extend(get_default_exclusions(ins_type))
        except ValueError:
            pass

        # Exclusion keyword matching (convert underscore-separated to spaces).
        for exclusion in all_exclusions:
            exclusion_words = exclusion.replace("_", " ").lower()
            if exclusion_words in desc_lower:
                return exclusion

        # Specific pattern checks.
        exclusion_patterns: dict[str, list[str]] = {
            "driving_under_influence": ["dui", "dwi", "drunk driving", "intoxicated", "under the influence"],
            "intentional_damage": ["intentional", "on purpose", "deliberately"],
            "racing": ["racing", "drag race", "street race"],
            "fraud": ["fake", "staged", "fabricated"],
            "cosmetic_surgery": ["cosmetic", "elective surgery", "plastic surgery"],
            "experimental_treatment": ["experimental", "clinical trial", "unapproved"],
            "suicide_within_contestability": ["suicide"],
        }

        for exclusion_name, patterns in exclusion_patterns.items():
            if exclusion_name in all_exclusions:
                for pattern in patterns:
                    if pattern in desc_lower:
                        return exclusion_name

        return None

    def _find_coverage(self, claim: Claim, policy: Policy) -> CoverageDetail | None:
        """Find the best matching coverage for a claim's damage categories."""
        if not policy.coverages:
            return None

        # Try to match by damage item categories.
        for item in claim.damage_items:
            for coverage in policy.coverages:
                if coverage.covered and item.category.lower() in coverage.name.lower():
                    return coverage
                if coverage.covered and coverage.name.lower() in item.category.lower():
                    return coverage

        # Fallback: find coverage by insurance type heuristics.
        type_coverage_map: dict[str, list[str]] = {
            "auto": ["collision", "comprehensive", "liability"],
            "home": ["dwelling", "personal_property", "personal_liability"],
            "health": ["inpatient", "outpatient", "emergency"],
            "life": ["death_benefit"],
            "commercial": ["commercial_property", "general_liability"],
        }

        preferred = type_coverage_map.get(claim.insurance_type, [])
        for pref_name in preferred:
            for coverage in policy.coverages:
                if coverage.covered and pref_name in coverage.name.lower():
                    return coverage

        # Last resort: return the first active coverage.
        for coverage in policy.coverages:
            if coverage.covered:
                return coverage

        return None
