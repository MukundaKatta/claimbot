# ClaimBot

AI-powered Insurance Claim Processor that automates claim intake, assessment, fraud detection, and payout estimation across multiple insurance types.

## Features

- **Claim Intake**: Extract structured data from free-text claim descriptions using pattern matching and NLP heuristics
- **Policy Verification**: Check claims against policy terms, exclusions, coverage limits, and deductibles
- **Risk Assessment**: Evaluate claim validity, liability, and coverage applicability
- **Damage Estimation**: Compute payout amounts based on damage type, severity, and policy limits
- **Fraud Detection**: Flag suspicious patterns such as frequent claims, inflated amounts, timing anomalies, and inconsistencies
- **Workflow Routing**: Automatically route claims to auto-approve, manual review, or investigation queues
- **Claim Lifecycle Tracking**: Track claim status through submission, review, approval, and payout stages
- **Simulation**: Generate realistic test claims across auto, home, health, life, and commercial insurance types
- **Rich Reporting**: Console-based reports with tables, charts, and color-coded risk indicators

## Supported Insurance Types

| Type | Coverage Areas |
|------|---------------|
| **Auto** | Collision, comprehensive, liability, medical payments, uninsured motorist |
| **Home** | Dwelling, personal property, liability, medical payments, loss of use |
| **Health** | Inpatient, outpatient, prescription, emergency, preventive, mental health |
| **Life** | Death benefit, accidental death, terminal illness, waiver of premium |
| **Commercial** | Property, general liability, business interruption, workers comp, professional liability |

## Installation

```bash
pip install -e .
```

## Usage

### CLI Commands

```bash
# Process a single claim
claimbot process --claim-file claim.json

# Run a simulation with N random claims
claimbot simulate --count 50

# Generate a portfolio report
claimbot report --output-dir ./reports

# Check a claim against a policy
claimbot check --claim-id CLM-001 --policy-id POL-001
```

### Python API

```python
from claimbot.models import Claim, Policy
from claimbot.processor.intake import ClaimIntake
from claimbot.processor.assessor import ClaimAssessor
from claimbot.processor.estimator import DamageEstimator
from claimbot.workflow.router import ClaimRouter

# Parse a claim description
intake = ClaimIntake()
claim = intake.extract("Rear-ended at intersection, airbags deployed, driver taken to ER")

# Assess the claim
assessor = ClaimAssessor()
assessment = assessor.evaluate(claim, policy)

# Estimate payout
estimator = DamageEstimator()
payout = estimator.compute(claim, assessment, policy)

# Route for processing
router = ClaimRouter()
decision = router.route(claim, assessment)
```

## Project Structure

```
src/claimbot/
    cli.py              # Click CLI interface
    models.py           # Pydantic data models
    simulator.py        # Claim generation for testing
    report.py           # Rich console reporting
    processor/
        intake.py       # ClaimIntake - extract structured data
        assessor.py     # ClaimAssessor - evaluate validity
        estimator.py    # DamageEstimator - compute payouts
    policy/
        checker.py      # PolicyChecker - verify against terms
        types.py        # InsuranceType enum with coverage defs
        deductible.py   # DeductibleCalculator - apply deductibles
    workflow/
        router.py       # ClaimRouter - route by risk level
        fraud.py        # FraudIndicatorDetector - flag fraud
        timeline.py     # ClaimTimeline - lifecycle tracking
```

## Testing

```bash
pytest
```

## License

MIT
