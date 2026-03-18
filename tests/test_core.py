"""Tests for Claimbot."""
from src.core import Claimbot
def test_init(): assert Claimbot().get_stats()["ops"] == 0
def test_op(): c = Claimbot(); c.analyze(x=1); assert c.get_stats()["ops"] == 1
def test_multi(): c = Claimbot(); [c.analyze() for _ in range(5)]; assert c.get_stats()["ops"] == 5
def test_reset(): c = Claimbot(); c.analyze(); c.reset(); assert c.get_stats()["ops"] == 0
def test_service_name(): c = Claimbot(); r = c.analyze(); assert r["service"] == "claimbot"
