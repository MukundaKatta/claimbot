"""Claim intake processor - extracts structured data from claim descriptions."""

from __future__ import annotations

import re
from datetime import date

from claimbot.models import Claim, DamageItem, LiabilityDetermination, Severity


# Keyword patterns for damage categories and severity estimation.
DAMAGE_PATTERNS: dict[str, dict[str, list[str]]] = {
    "auto": {
        "collision": ["rear-ended", "collision", "crashed", "hit", "accident", "wreck", "impact", "t-boned", "sideswiped"],
        "comprehensive": ["theft", "stolen", "vandalism", "hail", "flood", "fire", "tree fell", "animal", "deer"],
        "medical": ["injury", "hospital", "er", "emergency room", "ambulance", "doctor", "broken", "fracture", "whiplash", "concussion"],
        "towing": ["towed", "towing", "roadside"],
    },
    "home": {
        "dwelling": ["roof", "foundation", "wall", "structural", "siding", "window", "door"],
        "personal_property": ["furniture", "electronics", "clothing", "jewelry", "appliance"],
        "liability": ["slip", "fall", "visitor", "guest", "injury on property"],
        "loss_of_use": ["uninhabitable", "displaced", "hotel", "temporary housing", "cannot live"],
    },
    "health": {
        "inpatient": ["hospitalized", "admitted", "surgery", "operation", "inpatient"],
        "outpatient": ["office visit", "outpatient", "clinic", "consultation", "check-up"],
        "emergency": ["emergency", "er visit", "urgent care", "911", "ambulance"],
        "prescription": ["medication", "prescription", "drug", "pharmacy"],
        "mental_health": ["therapy", "counseling", "psychiatrist", "mental health", "depression", "anxiety"],
    },
    "life": {
        "death_benefit": ["death", "deceased", "passed away", "died"],
        "accidental_death": ["accident", "accidental death"],
        "terminal_illness": ["terminal", "diagnosis", "prognosis"],
    },
    "commercial": {
        "commercial_property": ["building damage", "equipment", "inventory", "office"],
        "general_liability": ["customer injury", "third party", "slip and fall", "product liability"],
        "business_interruption": ["business closed", "lost revenue", "shutdown", "cannot operate"],
        "workers_compensation": ["employee injury", "workplace accident", "on the job", "workers comp"],
    },
}

SEVERITY_KEYWORDS: dict[Severity, list[str]] = {
    Severity.MINOR: ["scratch", "dent", "minor", "small", "slight", "superficial"],
    Severity.MODERATE: ["moderate", "damaged", "broken", "cracked", "partial"],
    Severity.SEVERE: ["severe", "major", "extensive", "significant", "serious", "destroyed"],
    Severity.CATASTROPHIC: ["catastrophic", "devastating", "complete destruction", "leveled"],
    Severity.TOTAL_LOSS: ["total loss", "totaled", "write-off", "beyond repair", "demolished"],
}

LIABILITY_KEYWORDS: dict[LiabilityDetermination, list[str]] = {
    LiabilityDetermination.CLAIMANT_AT_FAULT: [
        "my fault", "i caused", "i hit", "i ran", "i was speeding", "i lost control",
    ],
    LiabilityDetermination.THIRD_PARTY_AT_FAULT: [
        "other driver", "they hit", "rear-ended by", "hit by", "struck by",
        "other party", "their fault", "ran into me",
    ],
    LiabilityDetermination.ACT_OF_GOD: [
        "storm", "tornado", "hurricane", "earthquake", "lightning", "hail",
        "flood", "wildfire", "tree fell", "natural disaster",
    ],
}

# Rough cost estimation by category (used when no dollar amount is provided).
DEFAULT_COST_ESTIMATES: dict[str, dict[Severity, float]] = {
    "collision": {Severity.MINOR: 1500, Severity.MODERATE: 5000, Severity.SEVERE: 15000, Severity.CATASTROPHIC: 30000, Severity.TOTAL_LOSS: 25000},
    "comprehensive": {Severity.MINOR: 500, Severity.MODERATE: 2000, Severity.SEVERE: 8000, Severity.CATASTROPHIC: 20000, Severity.TOTAL_LOSS: 25000},
    "medical": {Severity.MINOR: 500, Severity.MODERATE: 3000, Severity.SEVERE: 15000, Severity.CATASTROPHIC: 50000, Severity.TOTAL_LOSS: 100000},
    "dwelling": {Severity.MINOR: 2000, Severity.MODERATE: 10000, Severity.SEVERE: 50000, Severity.CATASTROPHIC: 150000, Severity.TOTAL_LOSS: 300000},
    "personal_property": {Severity.MINOR: 500, Severity.MODERATE: 3000, Severity.SEVERE: 15000, Severity.CATASTROPHIC: 50000, Severity.TOTAL_LOSS: 100000},
    "inpatient": {Severity.MINOR: 5000, Severity.MODERATE: 20000, Severity.SEVERE: 75000, Severity.CATASTROPHIC: 200000, Severity.TOTAL_LOSS: 500000},
    "outpatient": {Severity.MINOR: 200, Severity.MODERATE: 1000, Severity.SEVERE: 5000, Severity.CATASTROPHIC: 10000, Severity.TOTAL_LOSS: 20000},
    "emergency": {Severity.MINOR: 1000, Severity.MODERATE: 5000, Severity.SEVERE: 25000, Severity.CATASTROPHIC: 100000, Severity.TOTAL_LOSS: 250000},
    "death_benefit": {Severity.MINOR: 500000, Severity.MODERATE: 500000, Severity.SEVERE: 500000, Severity.CATASTROPHIC: 500000, Severity.TOTAL_LOSS: 500000},
    "commercial_property": {Severity.MINOR: 5000, Severity.MODERATE: 25000, Severity.SEVERE: 100000, Severity.CATASTROPHIC: 500000, Severity.TOTAL_LOSS: 1000000},
    "business_interruption": {Severity.MINOR: 5000, Severity.MODERATE: 25000, Severity.SEVERE: 100000, Severity.CATASTROPHIC: 300000, Severity.TOTAL_LOSS: 500000},
    "workers_compensation": {Severity.MINOR: 2000, Severity.MODERATE: 10000, Severity.SEVERE: 50000, Severity.CATASTROPHIC: 200000, Severity.TOTAL_LOSS: 500000},
}


class ClaimIntake:
    """Extracts structured claim data from free-text descriptions."""

    def extract(
        self,
        description: str,
        insurance_type: str = "auto",
        claimant_name: str = "",
        policy_id: str = "",
        date_of_loss: date | None = None,
    ) -> Claim:
        """Parse a claim description and return a structured Claim object."""
        desc_lower = description.lower()

        severity = self._detect_severity(desc_lower)
        liability = self._detect_liability(desc_lower)
        damage_items = self._extract_damage_items(desc_lower, insurance_type, severity)
        claimed_amount = self._extract_dollar_amount(description)
        has_police = self._detect_police_report(desc_lower)
        witnesses = self._detect_witnesses(desc_lower)
        location = self._extract_location(description)

        if claimed_amount == 0 and damage_items:
            claimed_amount = sum(item.estimated_cost for item in damage_items)

        return Claim(
            policy_id=policy_id,
            claimant_name=claimant_name,
            insurance_type=insurance_type,
            date_of_loss=date_of_loss or date.today(),
            description=description,
            damage_items=damage_items,
            claimed_amount=claimed_amount,
            severity=severity,
            liability=liability,
            location=location,
            witnesses=witnesses,
            police_report=has_police,
        )

    def _detect_severity(self, text: str) -> Severity:
        """Determine damage severity from description keywords."""
        # Check from most severe to least severe.
        for severity in [Severity.TOTAL_LOSS, Severity.CATASTROPHIC, Severity.SEVERE, Severity.MODERATE, Severity.MINOR]:
            for keyword in SEVERITY_KEYWORDS[severity]:
                if keyword in text:
                    return severity
        return Severity.MODERATE

    def _detect_liability(self, text: str) -> LiabilityDetermination:
        """Determine liability from description keywords."""
        for determination, keywords in LIABILITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return determination
        return LiabilityDetermination.UNDETERMINED

    def _extract_damage_items(
        self, text: str, insurance_type: str, severity: Severity
    ) -> list[DamageItem]:
        """Identify individual damage components from description."""
        items: list[DamageItem] = []
        patterns = DAMAGE_PATTERNS.get(insurance_type, {})

        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text:
                    cost_map = DEFAULT_COST_ESTIMATES.get(category, {})
                    estimated_cost = cost_map.get(severity, 2000.0)
                    items.append(
                        DamageItem(
                            description=f"{keyword} damage",
                            category=category,
                            estimated_cost=estimated_cost,
                            severity=severity,
                        )
                    )
                    break  # One item per category.

        return items

    def _extract_dollar_amount(self, text: str) -> float:
        """Extract dollar amounts from text using regex."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*dollars',
        ]
        amounts: list[float] = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amounts.append(float(match.replace(",", "")))
                except ValueError:
                    pass
        return max(amounts) if amounts else 0.0

    def _detect_police_report(self, text: str) -> bool:
        """Check if a police report was filed."""
        indicators = ["police report", "police were called", "filed a report", "officer", "incident report"]
        return any(ind in text for ind in indicators)

    def _detect_witnesses(self, text: str) -> int:
        """Estimate witness count from description."""
        match = re.search(r'(\d+)\s*witness', text)
        if match:
            return int(match.group(1))
        if "witness" in text:
            return 1
        return 0

    def _extract_location(self, text: str) -> str:
        """Extract location information from description."""
        location_patterns = [
            r'(?:at|near|on|in)\s+(?:the\s+)?(?:intersection\s+of\s+)?([\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|highway|hwy|drive|dr|lane|ln))',
            r'(?:at|near|on|in)\s+([\w\s]+(?:parking lot|mall|store|highway|freeway|interstate))',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
