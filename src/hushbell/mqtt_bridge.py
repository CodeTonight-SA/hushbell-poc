"""MQTT bridge -- subscribe to ring triggers, publish status/battery.

Includes Home Assistant MQTT discovery so HA auto-discovers the doorbell.
Works with a local Mosquitto broker (default localhost:1883).
"""
import json
import logging
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

_HA_PREFIX = "homeassistant"
_DEVICE = {
    "identifiers": ["hushbell_poc"],
    "name": "HushBell",
    "model": "HushBell POC",
    "manufacturer": "HushBell",
}

_HA_CONFIGS = [
    (
        f"{_HA_PREFIX}/binary_sensor/hushbell/doorbell/config",
        {
            "name": "HushBell Doorbell",
            "state_topic": "hushbell/status",
            "value_template": "{{ 'ON' if value_json.ok else 'OFF' }}",
            "device_class": "occupancy",
            "unique_id": "hushbell_doorbell",
            "device": _DEVICE,
        },
    ),
    (
        f"{_HA_PREFIX}/sensor/hushbell/battery/config",
        {
            "name": "HushBell Battery",
            "state_topic": "hushbell/battery",
            "value_template": "{{ (value_json.charge * 100) | round(1) }}",
            "unit_of_measurement": "%",
            "device_class": "battery",
            "unique_id": "hushbell_battery",
            "device": _DEVICE,
        },
    ),
    (
        f"{_HA_PREFIX}/select/hushbell/frequency_mode/config",
        {
            "name": "HushBell Frequency Mode",
            "command_topic": "hushbell/config",
            "command_template": '{"frequency_mode": "{{ value }}"}',
            "state_topic": "hushbell/config/state",
            "value_template": "{{ value_json.frequency_mode }}",
            "options": ["fixed", "random", "preset", "vagal"],
            "unique_id": "hushbell_frequency_mode",
            "device": _DEVICE,
            "icon": "mdi:sine-wave",
        },
    ),
    (
        f"{_HA_PREFIX}/switch/hushbell/pleasant/config",
        {
            "name": "HushBell Pleasant Tones",
            "command_topic": "hushbell/config",
            "payload_on": '{"pleasant": true}',
            "payload_off": '{"pleasant": false}',
            "state_topic": "hushbell/config/state",
            "value_template": "{{ 'ON' if value_json.pleasant else 'OFF' }}",
            "unique_id": "hushbell_pleasant",
            "device": _DEVICE,
            "icon": "mdi:music-note",
        },
    ),
    (
        f"{_HA_PREFIX}/select/hushbell/envelope_type/config",
        {
            "name": "HushBell Envelope",
            "command_topic": "hushbell/config",
            "command_template": '{"envelope_type": "{{ value }}"}',
            "state_topic": "hushbell/config/state",
            "value_template": "{{ value_json.envelope_type }}",
            "options": ["linear", "sine", "exponential"],
            "unique_id": "hushbell_envelope_type",
            "device": _DEVICE,
            "icon": "mdi:chart-bell-curve",
        },
    ),
]


class MQTTBridge:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        on_ring: Callable | None = None,
        on_config: Callable[[dict], dict | None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._on_ring = on_ring
        self._on_config = on_config
        self._client: "mqtt.Client | None" = None
        self._initial_config_state: dict | None = None

    def connect(self) -> bool:
        if not HAS_MQTT:
            logger.warning("paho-mqtt not installed -- MQTT disabled")
            return False
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="hushbell-poc")
            client.on_connect = self._on_connect
            client.on_message = self._on_message
            client.connect(self.host, self.port, keepalive=60)
            client.loop_start()
            self._client = client
            return True
        except Exception as exc:
            logger.warning("MQTT connect failed: %s", exc)
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def set_initial_config_state(self, state: dict) -> None:
        """Set initial config state to publish on connect."""
        self._initial_config_state = state

    def publish_status(self, status: dict) -> None:
        self._publish("hushbell/status", status)

    def publish_battery(self, battery: dict) -> None:
        self._publish("hushbell/battery", battery)

    def publish_config_state(self, state: dict) -> None:
        """Publish current config state for HA and other subscribers."""
        self._publish("hushbell/config/state", state)

    def _publish(self, topic: str, payload: dict) -> None:
        if self._client is None:
            return
        try:
            self._client.publish(topic, json.dumps(payload), retain=False)
        except Exception as exc:
            logger.debug("MQTT publish failed: %s", exc)

    def _publish_ha_discovery(self) -> None:
        for topic, payload in _HA_CONFIGS:
            if self._client:
                self._client.publish(topic, json.dumps(payload), retain=True)
        logger.info("HA discovery payloads published (%d entities)", len(_HA_CONFIGS))

    def _handle_config(self, payload: bytes) -> None:
        """Parse config JSON and invoke the on_config callback."""
        try:
            updates = json.loads(payload)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("MQTT config: invalid JSON: %s", exc)
            self.publish_config_state({"valid": False, "error": str(exc)})
            return

        if not isinstance(updates, dict):
            logger.warning("MQTT config: payload is not a JSON object")
            self.publish_config_state({"valid": False, "error": "expected JSON object"})
            return

        if self._on_config:
            result = self._on_config(updates)
            if result is not None:
                self.publish_config_state({"valid": True, **result})

    _MESSAGE_HANDLERS = {
        "hushbell/ring": "_dispatch_ring",
        "hushbell/config": "_dispatch_config",
    }

    def _dispatch_ring(self, msg) -> None:
        logger.info("MQTT ring trigger")
        if self._on_ring:
            self._on_ring()

    def _dispatch_config(self, msg) -> None:
        self._handle_config(msg.payload)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        logger.info("MQTT connected (rc=%s)", reason_code)
        client.subscribe("hushbell/ring")
        client.subscribe("hushbell/config")
        self._publish_ha_discovery()
        if self._initial_config_state:
            self.publish_config_state(self._initial_config_state)

    def _on_message(self, client, userdata, msg) -> None:
        handler_name = self._MESSAGE_HANDLERS.get(msg.topic)
        if handler_name:
            getattr(self, handler_name)(msg)
        else:
            logger.debug("MQTT unknown topic: %s", msg.topic)
