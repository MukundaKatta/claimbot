"""Claim simulator - generates realistic test claims across insurance types."""

from __future__ import annotations

import random
from datetime import date, timedelta

from claimbot.models import Claim, CoverageDetail, DamageItem, Policy, Severity
from claimbot.policy.types import (
    InsuranceType,
    get_default_coverages,
    get_default_exclusions,
    get_max_coverage_limit,
)


# Realistic claim scenarios by insurance type.
CLAIM_SCENARIOS: dict[str, list[dict[str, str | float]]] = {
    "auto": [
        {"description": "Rear-ended at a red light on Main Street. Bumper and trunk damaged. Other driver admitted fault. Police report filed.", "severity": "moderate", "amount": 4500},
        {"description": "Hit a deer on Highway 101 at dusk. Front bumper, hood, and headlights destroyed. Windshield cracked.", "severity": "severe", "amount": 8500},
        {"description": "Hailstorm damaged roof, hood, and trunk of vehicle. Multiple dents and cracked windshield.", "severity": "moderate", "amount": 6000},
        {"description": "T-boned at intersection by driver who ran a stop sign. Airbags deployed. Driver taken to ER with whiplash. 2 witnesses confirmed other driver at fault.", "severity": "severe", "amount": 22000},
        {"description": "Vehicle stolen from parking lot overnight. Total loss.", "severity": "total_loss", "amount": 28000},
        {"description": "Minor fender bender in parking lot. Small dent on rear quarter panel.", "severity": "minor", "amount": 1200},
        {"description": "Sideswiped on the freeway. Driver side door and mirror damaged. No injuries.", "severity": "moderate", "amount": 3800},
        {"description": "Lost control on icy road, crashed into guardrail. Front end severe damage. Vehicle totaled. Towed from scene.", "severity": "total_loss", "amount": 32000},
    ],
    "home": [
        {"description": "Tree fell on roof during windstorm. Significant structural damage to roof and attic. Home uninhabitable.", "severity": "severe", "amount": 45000},
        {"description": "Kitchen fire from grease on stove. Cabinets, countertops, and appliances destroyed. Smoke damage throughout first floor.", "severity": "severe", "amount": 65000},
        {"description": "Burst pipe in basement. Flooring, drywall, and personal property damaged.", "severity": "moderate", "amount": 12000},
        {"description": "Visitor slipped on icy walkway and broke their arm. Medical bills submitted.", "severity": "moderate", "amount": 8000},
        {"description": "Theft of electronics and jewelry. Forced entry through back door. Police report filed.", "severity": "moderate", "amount": 15000},
        {"description": "Wind damage to siding and window. Minor roof shingle loss.", "severity": "minor", "amount": 3500},
    ],
    "health": [
        {"description": "Emergency room visit for chest pain. CT scan, blood work, and overnight observation. Diagnosed with anxiety.", "severity": "moderate", "amount": 12000},
        {"description": "Knee replacement surgery. Inpatient stay 3 days. Physical therapy prescribed.", "severity": "severe", "amount": 55000},
        {"description": "Annual preventive check-up with blood work and immunizations.", "severity": "minor", "amount": 500},
        {"description": "Mental health counseling - 12 sessions for depression treatment. Prescription for antidepressants.", "severity": "moderate", "amount": 3600},
        {"description": "Emergency appendectomy. 2-day hospitalization. Follow-up outpatient visit.", "severity": "severe", "amount": 35000},
        {"description": "Outpatient clinic visit for persistent back pain. MRI ordered and prescription pain medication.", "severity": "moderate", "amount": 4500},
    ],
    "life": [
        {"description": "Death benefit claim following natural causes. Policyholder passed away at age 72.", "severity": "moderate", "amount": 500000},
        {"description": "Accidental death claim. Policyholder died in automobile accident at age 45.", "severity": "severe", "amount": 1000000},
        {"description": "Terminal illness accelerated benefit claim. Policyholder diagnosed with stage 4 cancer, prognosis less than 12 months.", "severity": "severe", "amount": 250000},
    ],
    "commercial": [
        {"description": "Fire in warehouse destroyed inventory and equipment. Building structural damage. Business closed for repairs.", "severity": "catastrophic", "amount": 450000},
        {"description": "Employee injury on the job. Fell from ladder, broken leg. Workers compensation claim.", "severity": "severe", "amount": 35000},
        {"description": "Customer slip and fall in retail store. Fractured hip. Lawsuit filed.", "severity": "severe", "amount": 75000},
        {"description": "Storm damage to commercial building roof. Water damage to office equipment and inventory.", "severity": "moderate", "amount": 28000},
        {"description": "Business interruption due to mandatory evacuation. Lost revenue for 2 weeks.", "severity": "moderate", "amount": 85000},
        {"description": "Data breach exposed customer records. Cyber liability claim for notification and monitoring costs.", "severity": "severe", "amount": 120000},
    ],
}

CLAIMANT_NAMES = [
    "Alice Johnson", "Bob Martinez", "Carol Williams", "David Chen",
    "Emily Thompson", "Frank Okafor", "Grace Kim", "Henry Patel",
    "Isabella Rodriguez", "James Wilson", "Karen Lee", "Liam O'Brien",
    "Maria Garcia", "Nathan Brooks", "Olivia Davis", "Patrick Murphy",
    "Quinn Anderson", "Rachel Singh", "Samuel Taylor", "Teresa Nguyen",
]


def generate_policy(insurance_type: str, policyholder: str = "") -> Policy:
    """Generate a realistic policy for a given insurance type."""
    try:
        ins_type = InsuranceType(insurance_type)
    except ValueError:
        ins_type = InsuranceType.AUTO

    coverages = get_default_coverages(ins_type)
    exclusions = get_default_exclusions(ins_type)
    max_limit = get_max_coverage_limit(ins_type)

    effective = date.today() - timedelta(days=random.randint(30, 365))
    expiration = effective + timedelta(days=365)

    premium_ranges = {
        "auto": (800, 3000),
        "home": (1200, 4000),
        "health": (3000, 12000),
        "life": (500, 5000),
        "commercial": (5000, 50000),
    }
    pmin, pmax = premium_ranges.get(insurance_type, (1000, 5000))

    return Policy(
        policyholder_name=policyholder or random.choice(CLAIMANT_NAMES),
        insurance_type=insurance_type,
        effective_date=effective,
        expiration_date=expiration,
        premium=round(random.uniform(pmin, pmax), 2),
        coverages=coverages,
        exclusions=exclusions,
        max_coverage_limit=max_limit,
    )


def generate_claim(
    insurance_type: str | None = None,
    policy: Policy | None = None,
) -> tuple[Claim, Policy]:
    """Generate a random realistic claim with matching policy.

    Returns:
        Tuple of (Claim, Policy).
    """
    if insurance_type is None:
        insurance_type = random.choice(list(InsuranceType)).value

    claimant = random.choice(CLAIMANT_NAMES)

    if policy is None:
        policy = generate_policy(insurance_type, claimant)

    scenarios = CLAIM_SCENARIOS.get(insurance_type, CLAIM_SCENARIOS["auto"])
    scenario = random.choice(scenarios)

    severity = Severity(scenario["severity"])
    amount = float(scenario["amount"])
    # Add some variance.
    amount *= random.uniform(0.8, 1.3)
    amount = round(amount, 2)

    loss_date = date.today() - timedelta(days=random.randint(1, 60))
    # Ensure loss date is within policy period.
    if loss_date < policy.effective_date:
        loss_date = policy.effective_date + timedelta(days=random.randint(1, 30))

    description = str(scenario["description"])

    # Build damage items from description keywords.
    from claimbot.processor.intake import ClaimIntake
    intake = ClaimIntake()
    claim = intake.extract(
        description=description,
        insurance_type=insurance_type,
        claimant_name=claimant,
        policy_id=policy.policy_id,
        date_of_loss=loss_date,
    )
    claim.claimed_amount = amount
    claim.severity = severity

    return claim, policy


def generate_batch(count: int = 10, insurance_type: str | None = None) -> list[tuple[Claim, Policy]]:
    """Generate a batch of random claims.

    Args:
        count: Number of claims to generate.
        insurance_type: If set, all claims are this type. Otherwise, random mix.

    Returns:
        List of (Claim, Policy) tuples.
    """
    results = []
    for _ in range(count):
        claim, policy = generate_claim(insurance_type=insurance_type)
        results.append((claim, policy))
    return results
