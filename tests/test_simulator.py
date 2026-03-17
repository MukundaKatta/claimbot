"""Tests for claim simulator."""

import random

from claimbot.models import Claim, Policy
from claimbot.simulator import generate_batch, generate_claim, generate_policy


class TestSimulator:
    def test_generate_policy(self):
        policy = generate_policy("auto", "Test User")
        assert isinstance(policy, Policy)
        assert policy.insurance_type == "auto"
        assert policy.policyholder_name == "Test User"
        assert len(policy.coverages) > 0

    def test_generate_claim(self):
        random.seed(42)
        claim, policy = generate_claim("auto")
        assert isinstance(claim, Claim)
        assert isinstance(policy, Policy)
        assert claim.insurance_type == "auto"
        assert claim.claimed_amount > 0

    def test_generate_batch(self):
        random.seed(42)
        batch = generate_batch(5)
        assert len(batch) == 5
        for claim, policy in batch:
            assert isinstance(claim, Claim)
            assert isinstance(policy, Policy)

    def test_generate_all_types(self):
        random.seed(42)
        for ins_type in ["auto", "home", "health", "life", "commercial"]:
            claim, policy = generate_claim(ins_type)
            assert claim.insurance_type == ins_type
            assert policy.insurance_type == ins_type
