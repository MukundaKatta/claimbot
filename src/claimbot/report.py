"""Report generator - rich console reporting for claim processing results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from claimbot.models import (
    Assessment,
    Claim,
    ClaimStatus,
    FraudRiskLevel,
    Payout,
    RouteDecision,
    Severity,
)


console = Console()

# Color maps for statuses.
SEVERITY_COLORS = {
    Severity.MINOR: "green",
    Severity.MODERATE: "yellow",
    Severity.SEVERE: "red",
    Severity.CATASTROPHIC: "bold red",
    Severity.TOTAL_LOSS: "bold magenta",
}

FRAUD_COLORS = {
    FraudRiskLevel.LOW: "green",
    FraudRiskLevel.MEDIUM: "yellow",
    FraudRiskLevel.HIGH: "red",
    FraudRiskLevel.CRITICAL: "bold red",
}

ROUTE_COLORS = {
    RouteDecision.AUTO_APPROVE: "green",
    RouteDecision.MANUAL_REVIEW: "yellow",
    RouteDecision.INVESTIGATE: "red",
}

STATUS_COLORS = {
    ClaimStatus.SUBMITTED: "blue",
    ClaimStatus.UNDER_REVIEW: "cyan",
    ClaimStatus.APPROVED: "green",
    ClaimStatus.PARTIALLY_APPROVED: "yellow",
    ClaimStatus.DENIED: "red",
    ClaimStatus.INVESTIGATING: "magenta",
    ClaimStatus.PAID: "bold green",
    ClaimStatus.CLOSED: "dim",
}


def print_claim_summary(claim: Claim) -> None:
    """Print a summary panel for a single claim."""
    severity_color = SEVERITY_COLORS.get(claim.severity, "white")
    fraud_color = FRAUD_COLORS.get(claim.fraud_risk, "white")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value")

    table.add_row("Claim ID", claim.claim_id)
    table.add_row("Policy ID", claim.policy_id)
    table.add_row("Claimant", claim.claimant_name)
    table.add_row("Type", claim.insurance_type.upper())
    table.add_row("Date of Loss", str(claim.date_of_loss))
    table.add_row("Severity", Text(claim.severity.value, style=severity_color))
    table.add_row("Claimed Amount", f"${claim.claimed_amount:,.2f}")
    table.add_row("Status", Text(claim.status.value, style=STATUS_COLORS.get(claim.status, "white")))
    table.add_row("Fraud Risk", Text(claim.fraud_risk.value, style=fraud_color))
    table.add_row("Liability", claim.liability.value)
    table.add_row("Police Report", "Yes" if claim.police_report else "No")
    table.add_row("Witnesses", str(claim.witnesses))

    console.print(Panel(table, title=f"Claim: {claim.claim_id}", border_style="blue"))

    if claim.description:
        console.print(Panel(claim.description, title="Description", border_style="dim"))


def print_assessment(assessment: Assessment) -> None:
    """Print assessment results."""
    route_color = ROUTE_COLORS.get(assessment.route_decision, "white")
    fraud_color = FRAUD_COLORS.get(assessment.fraud_risk, "white")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value")

    table.add_row("Valid", "Yes" if assessment.is_valid else "No")
    table.add_row("Covered", "Yes" if assessment.is_covered else "No")
    table.add_row("Coverage Matched", assessment.coverage_matched or "N/A")
    table.add_row("Liability", assessment.liability.value)
    table.add_row("Coverage Limit", f"${assessment.coverage_limit:,.2f}")
    table.add_row("Deductible", f"${assessment.deductible_applied:,.2f}")
    table.add_row("Copay", f"${assessment.copay_applied:,.2f}")
    table.add_row("Risk Score", f"{assessment.risk_score:.1f}/100")
    table.add_row("Fraud Risk", Text(assessment.fraud_risk.value, style=fraud_color))
    table.add_row("Route", Text(assessment.route_decision.value, style=route_color))

    console.print(Panel(table, title="Assessment", border_style="cyan"))

    if assessment.denial_reasons:
        console.print("[bold red]Denial Reasons:[/bold red]")
        for reason in assessment.denial_reasons:
            console.print(f"  - {reason}")

    if assessment.fraud_indicators:
        console.print(f"[bold {fraud_color}]Fraud Indicators:[/bold {fraud_color}]")
        for indicator in assessment.fraud_indicators:
            console.print(f"  - {indicator}")


def print_payout(payout: Payout) -> None:
    """Print payout details."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value", justify="right")

    table.add_row("Claimed Amount", f"${payout.claimed_amount:,.2f}")
    table.add_row("Approved Amount", f"${payout.approved_amount:,.2f}")
    table.add_row("Deductible", f"-${payout.deductible:,.2f}")
    table.add_row("Copay", f"-${payout.copay:,.2f}")
    table.add_row("", "")
    net_color = "green" if payout.net_payout > 0 else "red"
    table.add_row("Net Payout", Text(f"${payout.net_payout:,.2f}", style=f"bold {net_color}"))

    console.print(Panel(table, title="Payout Calculation", border_style="green"))

    if payout.payout_breakdown:
        breakdown_table = Table(title="Breakdown by Category")
        breakdown_table.add_column("Category", style="cyan")
        breakdown_table.add_column("Amount", justify="right", style="green")

        for category, amount in payout.payout_breakdown.items():
            breakdown_table.add_row(category, f"${amount:,.2f}")

        console.print(breakdown_table)

    if payout.notes:
        for note in payout.notes:
            console.print(f"  [dim]{note}[/dim]")


def print_batch_report(
    results: list[tuple[Claim, Assessment, Payout]],
) -> None:
    """Print a summary report for a batch of processed claims."""
    console.print()
    console.rule("[bold]ClaimBot Batch Processing Report[/bold]")
    console.print()

    # Summary statistics.
    total = len(results)
    total_claimed = sum(c.claimed_amount for c, _, _ in results)
    total_payout = sum(p.net_payout for _, _, p in results)

    approved = sum(1 for _, a, _ in results if a.is_covered)
    denied = total - approved

    auto_approved = sum(1 for _, a, _ in results if a.route_decision == RouteDecision.AUTO_APPROVE)
    manual_review = sum(1 for _, a, _ in results if a.route_decision == RouteDecision.MANUAL_REVIEW)
    investigate = sum(1 for _, a, _ in results if a.route_decision == RouteDecision.INVESTIGATE)

    stats_table = Table(title="Summary Statistics", show_header=False, box=None)
    stats_table.add_column("Metric", style="bold", width=25)
    stats_table.add_column("Value", justify="right")

    stats_table.add_row("Total Claims", str(total))
    stats_table.add_row("Total Claimed", f"${total_claimed:,.2f}")
    stats_table.add_row("Total Payout", f"${total_payout:,.2f}")
    stats_table.add_row("Loss Ratio", f"{(total_payout / total_claimed * 100) if total_claimed > 0 else 0:.1f}%")
    stats_table.add_row("", "")
    stats_table.add_row("Approved", f"{approved} ({approved/total*100:.0f}%)")
    stats_table.add_row("Denied", f"{denied} ({denied/total*100:.0f}%)")
    stats_table.add_row("", "")
    stats_table.add_row("Auto-Approved", str(auto_approved))
    stats_table.add_row("Manual Review", str(manual_review))
    stats_table.add_row("Investigation", str(investigate))

    console.print(Panel(stats_table, border_style="blue"))

    # Claims table.
    claims_table = Table(title="All Claims")
    claims_table.add_column("Claim ID", style="cyan", no_wrap=True)
    claims_table.add_column("Type")
    claims_table.add_column("Claimant")
    claims_table.add_column("Severity")
    claims_table.add_column("Claimed", justify="right")
    claims_table.add_column("Payout", justify="right")
    claims_table.add_column("Risk", justify="right")
    claims_table.add_column("Fraud")
    claims_table.add_column("Route")

    for claim, assessment, payout in results:
        sev_color = SEVERITY_COLORS.get(claim.severity, "white")
        fraud_color = FRAUD_COLORS.get(assessment.fraud_risk, "white")
        route_color = ROUTE_COLORS.get(assessment.route_decision, "white")

        claims_table.add_row(
            claim.claim_id,
            claim.insurance_type,
            claim.claimant_name,
            Text(claim.severity.value, style=sev_color),
            f"${claim.claimed_amount:,.2f}",
            f"${payout.net_payout:,.2f}",
            f"{assessment.risk_score:.0f}",
            Text(assessment.fraud_risk.value, style=fraud_color),
            Text(assessment.route_decision.value, style=route_color),
        )

    console.print(claims_table)

    # By-type breakdown.
    type_table = Table(title="Breakdown by Insurance Type")
    type_table.add_column("Type", style="bold")
    type_table.add_column("Count", justify="right")
    type_table.add_column("Claimed", justify="right")
    type_table.add_column("Payout", justify="right")
    type_table.add_column("Avg Risk", justify="right")

    type_groups: dict[str, list[tuple[Claim, Assessment, Payout]]] = {}
    for c, a, p in results:
        type_groups.setdefault(c.insurance_type, []).append((c, a, p))

    for ins_type, group in sorted(type_groups.items()):
        count = len(group)
        claimed = sum(c.claimed_amount for c, _, _ in group)
        paid = sum(p.net_payout for _, _, p in group)
        avg_risk = sum(a.risk_score for _, a, _ in group) / count

        type_table.add_row(
            ins_type.upper(),
            str(count),
            f"${claimed:,.2f}",
            f"${paid:,.2f}",
            f"{avg_risk:.1f}",
        )

    console.print(type_table)
    console.print()
