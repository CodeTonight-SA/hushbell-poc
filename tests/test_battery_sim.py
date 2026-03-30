"""Tests for HushBell battery simulation.

Verifies the 1200 rings/charge spec from Thomas's design.
"""
from hushbell.battery_sim import BatterySimulator


class TestBatteryDrain:

    def test_full_drain(self):
        battery = BatterySimulator()
        for i in range(1200):
            assert battery.ring(), f"Ring {i+1} should succeed"
        assert battery.is_empty

    def test_empty_blocks_ring(self):
        battery = BatterySimulator()
        for _ in range(1200):
            battery.ring()
        assert not battery.ring()

    def test_charge_percent_decreases(self):
        battery = BatterySimulator()
        assert battery.charge_percent == 100
        for _ in range(600):
            battery.ring()
        assert 45 <= battery.charge_percent <= 55

    def test_rings_remaining_accurate(self):
        battery = BatterySimulator()
        assert battery.rings_remaining == 1200
        for _ in range(100):
            battery.ring()
        assert battery.rings_remaining == 1100


class TestRecharge:

    def test_recharge_restores_full(self):
        battery = BatterySimulator()
        for _ in range(600):
            battery.ring()
        battery.recharge()
        assert battery.charge_percent == 100

    def test_total_rings_persists_across_charges(self):
        battery = BatterySimulator()
        for _ in range(100):
            battery.ring()
        battery.recharge()
        for _ in range(50):
            battery.ring()
        assert battery.total_rings == 150


class TestStatus:

    def test_status_dict_keys(self):
        status = BatterySimulator().status()
        assert "charge_percent" in status
        assert "rings_remaining" in status
        assert "is_empty" in status
        assert status["charge_percent"] == 100
