"""Insurance type definitions with coverage structures."""

from __future__ import annotations

from enum import Enum
from typing import Any

from claimbot.models import CoverageDetail


class InsuranceType(str, Enum):
    """Supported insurance product types."""

    AUTO = "auto"
    HOME = "home"
    HEALTH = "health"
    LIFE = "life"
    COMMERCIAL = "commercial"


# Standard coverage definitions per insurance type with typical limits and deductibles.

AUTO_COVERAGES: list[dict[str, Any]] = [
    {"name": "collision", "limit": 50000, "deductible": 500, "copay_percent": 0},
    {"name": "comprehensive", "limit": 50000, "deductible": 250, "copay_percent": 0},
    {"name": "liability_bodily_injury", "limit": 100000, "deductible": 0, "copay_percent": 0},
    {"name": "liability_property_damage", "limit": 50000, "deductible": 0, "copay_percent": 0},
    {"name": "medical_payments", "limit": 10000, "deductible": 0, "copay_percent": 20},
    {"name": "uninsured_motorist", "limit": 100000, "deductible": 0, "copay_percent": 0},
    {"name": "rental_reimbursement", "limit": 1500, "deductible": 0, "copay_percent": 0},
    {"name": "towing", "limit": 200, "deductible": 0, "copay_percent": 0},
]

HOME_COVERAGES: list[dict[str, Any]] = [
    {"name": "dwelling", "limit": 300000, "deductible": 1000, "copay_percent": 0},
    {"name": "other_structures", "limit": 30000, "deductible": 1000, "copay_percent": 0},
    {"name": "personal_property", "limit": 150000, "deductible": 500, "copay_percent": 0},
    {"name": "loss_of_use", "limit": 60000, "deductible": 0, "copay_percent": 0},
    {"name": "personal_liability", "limit": 300000, "deductible": 0, "copay_percent": 0},
    {"name": "medical_payments", "limit": 5000, "deductible": 0, "copay_percent": 0},
]

HEALTH_COVERAGES: list[dict[str, Any]] = [
    {"name": "inpatient", "limit": 500000, "deductible": 2000, "copay_percent": 20},
    {"name": "outpatient", "limit": 100000, "deductible": 500, "copay_percent": 30},
    {"name": "prescription", "limit": 10000, "deductible": 100, "copay_percent": 25},
    {"name": "emergency", "limit": 250000, "deductible": 500, "copay_percent": 20},
    {"name": "preventive", "limit": 5000, "deductible": 0, "copay_percent": 0},
    {"name": "mental_health", "limit": 50000, "deductible": 500, "copay_percent": 30},
    {"name": "rehabilitation", "limit": 30000, "deductible": 500, "copay_percent": 25},
]

LIFE_COVERAGES: list[dict[str, Any]] = [
    {"name": "death_benefit", "limit": 500000, "deductible": 0, "copay_percent": 0},
    {"name": "accidental_death", "limit": 1000000, "deductible": 0, "copay_percent": 0},
    {"name": "terminal_illness", "limit": 250000, "deductible": 0, "copay_percent": 0},
    {"name": "waiver_of_premium", "limit": 0, "deductible": 0, "copay_percent": 0},
]

COMMERCIAL_COVERAGES: list[dict[str, Any]] = [
    {"name": "commercial_property", "limit": 1000000, "deductible": 5000, "copay_percent": 0},
    {"name": "general_liability", "limit": 2000000, "deductible": 2500, "copay_percent": 0},
    {"name": "business_interruption", "limit": 500000, "deductible": 10000, "copay_percent": 0},
    {"name": "workers_compensation", "limit": 1000000, "deductible": 0, "copay_percent": 0},
    {"name": "professional_liability", "limit": 1000000, "deductible": 5000, "copay_percent": 0},
    {"name": "commercial_auto", "limit": 500000, "deductible": 1000, "copay_percent": 0},
    {"name": "cyber_liability", "limit": 500000, "deductible": 10000, "copay_percent": 0},
]

COVERAGE_MAP: dict[InsuranceType, list[dict[str, Any]]] = {
    InsuranceType.AUTO: AUTO_COVERAGES,
    InsuranceType.HOME: HOME_COVERAGES,
    InsuranceType.HEALTH: HEALTH_COVERAGES,
    InsuranceType.LIFE: LIFE_COVERAGES,
    InsuranceType.COMMERCIAL: COMMERCIAL_COVERAGES,
}

# Common exclusions per insurance type.

EXCLUSION_MAP: dict[InsuranceType, list[str]] = {
    InsuranceType.AUTO: [
        "intentional_damage",
        "racing",
        "commercial_use_on_personal_policy",
        "unlicensed_driver",
        "driving_under_influence",
        "wear_and_tear",
    ],
    InsuranceType.HOME: [
        "flood",
        "earthquake",
        "intentional_damage",
        "neglect",
        "war",
        "nuclear_hazard",
        "government_action",
        "mold_from_neglect",
    ],
    InsuranceType.HEALTH: [
        "cosmetic_surgery",
        "experimental_treatment",
        "pre_existing_waiting_period",
        "self_inflicted",
        "workers_comp_eligible",
        "out_of_network_unauthorized",
    ],
    InsuranceType.LIFE: [
        "suicide_within_contestability",
        "misrepresentation",
        "hazardous_activity_excluded",
        "war_act",
        "illegal_activity",
    ],
    InsuranceType.COMMERCIAL: [
        "intentional_acts",
        "employee_dishonesty_without_rider",
        "pollution_without_rider",
        "professional_errors_without_eo",
        "war_terrorism_without_rider",
        "contractual_liability",
    ],
}


def get_default_coverages(insurance_type: InsuranceType) -> list[CoverageDetail]:
    """Return default coverage details for a given insurance type."""
    coverage_defs = COVERAGE_MAP.get(insurance_type, [])
    return [CoverageDetail(**cov_def) for cov_def in coverage_defs]


def get_default_exclusions(insurance_type: InsuranceType) -> list[str]:
    """Return default exclusions for a given insurance type."""
    return EXCLUSION_MAP.get(insurance_type, [])


def get_max_coverage_limit(insurance_type: InsuranceType) -> float:
    """Return total maximum coverage across all coverage types."""
    coverages = COVERAGE_MAP.get(insurance_type, [])
    return sum(c["limit"] for c in coverages)
