"""ClaimBot CLI - command-line interface for insurance claim processing."""

from __future__ import annotations

import json

import click
from rich.console import Console

from claimbot.models import Assessment, Claim, Payout
from claimbot.processor.assessor import ClaimAssessor
from claimbot.processor.estimator import DamageEstimator
from claimbot.processor.intake import ClaimIntake
from claimbot.report import print_batch_report, print_assessment, print_claim_summary, print_payout
from claimbot.simulator import generate_batch, generate_claim, generate_policy
from claimbot.workflow.router import ClaimRouter
from claimbot.workflow.timeline import ClaimTimeline

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """ClaimBot - AI Insurance Claim Processor."""


@cli.command()
@click.option("--description", "-d", required=True, help="Free-text claim description")
@click.option("--type", "-t", "insurance_type", default="auto",
              type=click.Choice(["auto", "home", "health", "life", "commercial"]),
              help="Insurance type")
@click.option("--claimant", "-c", default="", help="Claimant name")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def process(description: str, insurance_type: str, claimant: str, verbose: bool) -> None:
    """Process a single claim from a text description."""
    intake = ClaimIntake()
    assessor = ClaimAssessor()
    estimator = DamageEstimator()
    router = ClaimRouter()
    timeline = ClaimTimeline()

    # Generate a matching policy.
    policy = generate_policy(insurance_type, claimant)

    # Extract claim data.
    claim = intake.extract(
        description=description,
        insurance_type=insurance_type,
        claimant_name=claimant or "Anonymous",
        policy_id=policy.policy_id,
    )

    # Initialize timeline.
    timeline.initialize_claim(claim)

    # Assess the claim.
    assessment = assessor.evaluate(claim, policy)
    claim.fraud_risk = assessment.fraud_risk
    claim.fraud_indicators = assessment.fraud_indicators

    # Compute payout.
    payout = estimator.compute(claim, assessment, policy)

    # Route the claim.
    routing = router.route(claim, assessment)

    # Display results.
    print_claim_summary(claim)
    print_assessment(assessment)
    print_payout(payout)

    if verbose:
        console.print()
        console.print(f"[bold]Routing Decision:[/bold] {routing.decision.value}")
        console.print(f"  Queue: {routing.assigned_queue}")
        console.print(f"  Priority: {routing.priority}")
        console.print(f"  Est. Processing: {routing.estimated_processing_days} days")
        for reason in routing.reasons:
            console.print(f"  - {reason}")


@cli.command()
@click.option("--count", "-n", default=10, help="Number of claims to simulate")
@click.option("--type", "-t", "insurance_type", default=None,
              type=click.Choice(["auto", "home", "health", "life", "commercial"]),
              help="Insurance type (omit for random mix)")
@click.option("--seed", "-s", default=None, type=int, help="Random seed for reproducibility")
def simulate(count: int, insurance_type: str | None, seed: int | None) -> None:
    """Run a simulation with randomly generated claims."""
    import random
    if seed is not None:
        random.seed(seed)

    console.print(f"[bold]Generating {count} claims...[/bold]")

    assessor = ClaimAssessor()
    estimator = DamageEstimator()

    batch = generate_batch(count, insurance_type)
    results: list[tuple[Claim, Assessment, Payout]] = []

    for claim, policy in batch:
        assessment = assessor.evaluate(claim, policy)
        claim.fraud_risk = assessment.fraud_risk
        claim.fraud_indicators = assessment.fraud_indicators
        payout = estimator.compute(claim, assessment, policy)
        results.append((claim, assessment, payout))

    print_batch_report(results)


@cli.command()
@click.option("--claim-file", "-f", type=click.Path(exists=True), help="JSON file with claim data")
@click.option("--policy-file", "-p", type=click.Path(exists=True), help="JSON file with policy data")
def check(claim_file: str | None, policy_file: str | None) -> None:
    """Check a claim against a policy from JSON files."""
    if claim_file:
        with open(claim_file) as f:
            claim_data = json.load(f)
        claim = Claim(**claim_data)
    else:
        console.print("[red]Please provide a claim file with --claim-file[/red]")
        return

    if policy_file:
        with open(policy_file) as f:
            policy_data = json.load(f)
        from claimbot.models import Policy
        policy = Policy(**policy_data)
    else:
        policy = generate_policy(claim.insurance_type, claim.claimant_name)
        console.print("[yellow]No policy file provided. Generated default policy.[/yellow]")

    assessor = ClaimAssessor()
    estimator = DamageEstimator()

    assessment = assessor.evaluate(claim, policy)
    payout = estimator.compute(claim, assessment, policy)

    print_claim_summary(claim)
    print_assessment(assessment)
    print_payout(payout)


@cli.command()
@click.option("--count", "-n", default=20, help="Number of claims in the report")
@click.option("--seed", "-s", default=42, type=int, help="Random seed")
def report(count: int, seed: int) -> None:
    """Generate a comprehensive portfolio report."""
    import random
    random.seed(seed)

    assessor = ClaimAssessor()
    estimator = DamageEstimator()

    batch = generate_batch(count)
    results: list[tuple[Claim, Assessment, Payout]] = []

    for claim, policy in batch:
        assessment = assessor.evaluate(claim, policy)
        claim.fraud_risk = assessment.fraud_risk
        payout = estimator.compute(claim, assessment, policy)
        results.append((claim, assessment, payout))

    print_batch_report(results)


if __name__ == "__main__":
    cli()
