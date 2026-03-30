"""HushBell controller -- orchestrates the ring lifecycle.

A ring cycle: trigger -> battery check -> audio -> notify -> LED -> MQTT -> drain.
"""
import logging
import time

from .audio_engine import generate_combined, play_audio
from .battery_sim import BatterySimulator
from .config import HushBellConfig
from .mqtt_bridge import MQTTBridge
from .notification import notify
from .visual_engine import LEDStrip

logger = logging.getLogger(__name__)


class HushBellController:
    """Main ring lifecycle orchestrator."""

    def __init__(self, config: HushBellConfig | None = None, visual: bool = False):
        self.config = config or HushBellConfig()
        self.battery = BatterySimulator(self.config.battery)
        self._ring_history: list[float] = []
        self._mqtt: MQTTBridge | None = None
        self._leds = LEDStrip()
        if visual:
            self._leds.start()

    def ring(self, spectrum: bool = False) -> dict:
        """Execute a full ring cycle. Returns status dict."""
        if self.battery.is_empty:
            logger.warning("Battery empty -- ring suppressed")
            return {"ok": False, "reason": "battery_empty"}

        start = time.monotonic()
        samples = generate_combined(self.config.audio)
        self._leds.ring()
        play_audio(samples, self.config.audio.sample_rate)
        if spectrum:
            from .spectrum import plot_spectrum
            plot_spectrum(samples, self.config.audio.sample_rate)
        notify("HushBell", "Someone is at the door")
        self.battery.ring()

        elapsed_ms = (time.monotonic() - start) * 1000
        self._ring_history.append(elapsed_ms)
        status = {"ok": True, "elapsed_ms": round(elapsed_ms, 1), "battery": self.battery.status()}
        if self._mqtt:
            self._mqtt.publish_status(status)
            self._mqtt.publish_battery(self.battery.status())
        return status

    def connect_mqtt(self, bridge: MQTTBridge | None = None) -> bool:
        """Connect to MQTT broker. Accepts pre-built bridge (DI) or builds default."""
        if bridge is None:
            cfg = self.config.mqtt
            bridge = MQTTBridge(host=cfg.broker_host, port=cfg.broker_port, on_ring=self.ring)
        self._mqtt = bridge
        return self._mqtt.connect()

    def stats(self) -> dict:
        """Session statistics."""
        avg = round(sum(self._ring_history) / len(self._ring_history), 1) if self._ring_history else 0
        return {"total_rings": len(self._ring_history), "avg_latency_ms": avg, "battery": self.battery.status()}
