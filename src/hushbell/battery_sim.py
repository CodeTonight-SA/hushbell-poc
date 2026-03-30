"""Battery simulation -- 1200 rings per charge from Thomas's spec.

The TP4056 USB-C controller provides 1000mAh capacity.
At ~0.83mAh per ring cycle, that gives 1200 rings per charge.
"""
from .config import BatteryConfig


class BatterySimulator:
    """Simulate HushBell battery drain and charge cycles."""

    def __init__(self, config: BatteryConfig | None = None):
        self._config = config or BatteryConfig()
        self._charge = self._config.initial_charge
        self._ring_count = 0
        self._total_rings = 0

    @property
    def charge(self) -> float:
        return max(0.0, self._charge)

    @property
    def rings_remaining(self) -> int:
        if self._config.ring_drain <= 0:
            return self._config.max_rings
        return round(self.charge / self._config.ring_drain)

    @property
    def total_rings(self) -> int:
        return self._total_rings

    @property
    def is_empty(self) -> bool:
        return self._charge <= 0

    def ring(self) -> bool:
        """Consume one ring's worth of battery. Returns False if empty."""
        if self.is_empty:
            return False
        self._charge -= self._config.ring_drain
        self._ring_count += 1
        self._total_rings += 1
        return True

    def recharge(self) -> None:
        """Simulate USB-C recharge to full."""
        self._charge = 1.0
        self._ring_count = 0

    def status(self) -> dict:
        """Battery status dict for MQTT publishing."""
        return {
            "charge_percent": int(self.charge * 100),
            "rings_remaining": self.rings_remaining,
            "ring_count": self._ring_count,
            "total_rings": self._total_rings,
            "is_empty": self.is_empty,
        }
