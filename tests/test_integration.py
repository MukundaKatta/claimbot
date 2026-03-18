"""Integration tests for Claimbot."""
from src.core import Claimbot

class TestClaimbot:
    def setup_method(self):
        self.c = Claimbot()
    def test_10_ops(self):
        for i in range(10): self.c.analyze(i=i)
        assert self.c.get_stats()["ops"] == 10
    def test_service_name(self):
        assert self.c.analyze()["service"] == "claimbot"
    def test_different_inputs(self):
        self.c.analyze(type="a"); self.c.analyze(type="b")
        assert self.c.get_stats()["ops"] == 2
    def test_config(self):
        c = Claimbot(config={"debug": True})
        assert c.config["debug"] is True
    def test_empty_call(self):
        assert self.c.analyze()["ok"] is True
    def test_large_batch(self):
        for _ in range(100): self.c.analyze()
        assert self.c.get_stats()["ops"] == 100
