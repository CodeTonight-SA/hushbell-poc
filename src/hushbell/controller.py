"""HushBell controller -- orchestrates the ring lifecycle.

A ring cycle: trigger -> battery check -> audio -> notify -> MQTT -> drain.
"""
import logging
import time

from .audio_engine import generate_combined, play_audio
from .battery_sim import BatterySimulator
from .config import HushBellConfig
from .notification import notify

logger = logging.getLogger(__name__)


class HushBellController:
    """Main ring lifecycle orchestrator."""

    def __init__(self, config: HushBellConfig | None = None):
        self.config = config or HushBellConfig()
        self.battery = BatterySimulator(self.config.battery)
        self._ring_history: list[float] = []
        self._mqtt_client = None

    def ring(self) -> dict:
        """Execute a full ring cycle. Returns status dict."""
        if self.battery.is_empty:
            logger.warning("Battery empty -- ring suppressed")
            return {"ok": False, "reason": "battery_empty"}

        start = time.monotonic()
        samples = generate_combined(self.config.audio)
        play_audio(samples, self.config.audio.sample_rate)
        notify("HushBell", "Someone is at the door")
        self.battery.ring()

        elapsed_ms = (time.monotonic() - start) * 1000
        self._ring_history.append(elapsed_ms)
        status = {"ok": True, "elapsed_ms": round(elapsed_ms, 1), "battery": self.battery.status()}
        self._publish_mqtt(status)
        return status

    def _publish_mqtt(self, status: dict) -> None:
        """Publish ring status via MQTT (best-effort)."""
        if self._mqtt_client is None:
            return
        try:
            import json
            self._mqtt_client.publish(self.config.mqtt.topic_status, json.dumps(status))
        except Exception:
            logger.debug("MQTT publish failed (non-critical)")

    def connect_mqtt(self) -> bool:
        """Connect to MQTT broker."""
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.config.mqtt.client_id)
            client.connect(self.config.mqtt.broker_host, self.config.mqtt.broker_port)
            client.loop_start()
            self._mqtt_client = client
            return True
        except Exception as e:
            logger.warning("MQTT connection failed: %s", e)
            return False

    def stats(self) -> dict:
        """Session statistics."""
        avg = round(sum(self._ring_history) / len(self._ring_history), 1) if self._ring_history else 0
        return {"total_rings": len(self._ring_history), "avg_latency_ms": avg, "battery": self.battery.status()}
