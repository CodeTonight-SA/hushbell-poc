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
]


class MQTTBridge:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        on_ring: Callable | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._on_ring = on_ring
        self._client: "mqtt.Client | None" = None

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

    def publish_status(self, status: dict) -> None:
        self._publish("hushbell/status", status)

    def publish_battery(self, battery: dict) -> None:
        self._publish("hushbell/battery", battery)

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

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        logger.info("MQTT connected (rc=%s)", reason_code)
        client.subscribe("hushbell/ring")
        self._publish_ha_discovery()

    def _on_message(self, client, userdata, msg) -> None:
        logger.info("MQTT ring trigger on %s", msg.topic)
        if self._on_ring:
            self._on_ring()
