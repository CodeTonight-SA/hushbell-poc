"""HushBell controller -- orchestrates the ring lifecycle.

A ring cycle: trigger -> battery check -> audio -> notify -> LED -> MQTT -> drain.
"""
import logging
import time

from .audio_engine import generate_combined, play_audio
from .battery_sim import BatterySimulator
from .config import AudioConfig, FrequencyMode, HushBellConfig
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
        """Execute a full ring cycle. Returns status dict including freq_hz."""
        if self.battery.is_empty:
            logger.warning("Battery empty -- ring suppressed")
            return {"ok": False, "reason": "battery_empty"}

        start = time.monotonic()
        samples, freq_used = generate_combined(self.config.audio)
        self._leds.ring()
        play_audio(samples, self.config.audio.sample_rate)
        if spectrum:
            from .spectrum import plot_spectrum
            plot_spectrum(samples, self.config.audio.sample_rate, marker_freq=freq_used)
        notify("HushBell", "Someone is at the door")
        self.battery.ring()

        elapsed_ms = (time.monotonic() - start) * 1000
        self._ring_history.append(elapsed_ms)
        logger.info("Ring: %.1fHz (mode=%s) in %.1fms", freq_used, self.config.audio.frequency_mode.value, elapsed_ms)
        status = {
            "ok": True,
            "elapsed_ms": round(elapsed_ms, 1),
            "freq_hz": round(freq_used, 1),
            "frequency_mode": self.config.audio.frequency_mode.value,
            "battery": self.battery.status(),
        }
        if self._mqtt:
            self._mqtt.publish_status(status)
            self._mqtt.publish_battery(self.battery.status())
        return status

    def update_audio_config(self, updates: dict) -> AudioConfig:
        """Apply partial updates to audio config at runtime.

        Uses Pydantic model_copy for immutable replacement.
        Raises ValueError/ValidationError on invalid input.
        """
        if "frequency_mode" in updates and isinstance(updates["frequency_mode"], str):
            updates["frequency_mode"] = FrequencyMode(updates["frequency_mode"])
        new_audio = self.config.audio.model_copy(update=updates)
        new_audio = AudioConfig.model_validate(new_audio.model_dump())
        self.config = self.config.model_copy(update={"audio": new_audio})
        return new_audio

    def _handle_mqtt_config(self, updates: dict) -> dict | None:
        """Handle MQTT config update. Returns new config dict or None on error."""
        try:
            new_audio = self.update_audio_config(updates)
            result = new_audio.model_dump()
            result["frequency_mode"] = result["frequency_mode"].value if hasattr(result["frequency_mode"], "value") else result["frequency_mode"]
            logger.info("Config updated via MQTT: mode=%s, pleasant=%s", new_audio.frequency_mode.value, new_audio.pleasant)
            return result
        except (ValueError, Exception) as exc:
            logger.warning("MQTT config rejected: %s", exc)
            if self._mqtt:
                self._mqtt.publish_config_state({"valid": False, "error": str(exc)})
            return None

    def _audio_config_dict(self) -> dict:
        """Serialise current audio config for MQTT state publishing."""
        d = self.config.audio.model_dump()
        d["frequency_mode"] = self.config.audio.frequency_mode.value
        return d

    def connect_mqtt(self, bridge: MQTTBridge | None = None) -> bool:
        """Connect to MQTT broker. Accepts pre-built bridge (DI) or builds default."""
        if bridge is None:
            cfg = self.config.mqtt
            bridge = MQTTBridge(
                host=cfg.broker_host,
                port=cfg.broker_port,
                on_ring=self.ring,
                on_config=self._handle_mqtt_config,
            )
        self._mqtt = bridge
        bridge.set_initial_config_state(self._audio_config_dict())
        return self._mqtt.connect()

    def stats(self) -> dict:
        """Session statistics."""
        avg = round(sum(self._ring_history) / len(self._ring_history), 1) if self._ring_history else 0
        return {"total_rings": len(self._ring_history), "avg_latency_ms": avg, "battery": self.battery.status()}
