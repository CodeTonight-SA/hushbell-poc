"""Tests for MQTTBridge -- no broker required."""
import json

from hushbell.mqtt_bridge import MQTTBridge, _HA_CONFIGS


def test_instantiation_no_broker():
    bridge = MQTTBridge()
    assert bridge.host == "localhost"
    assert bridge.port == 1883
    assert bridge._client is None


def test_custom_host_port():
    bridge = MQTTBridge(host="192.168.1.10", port=1884)
    assert bridge.host == "192.168.1.10"
    assert bridge.port == 1884


def test_on_ring_callback_stored():
    cb = lambda: None
    bridge = MQTTBridge(on_ring=cb)
    assert bridge._on_ring is cb


def test_connect_without_paho_returns_false(monkeypatch):
    import hushbell.mqtt_bridge as mod
    monkeypatch.setattr(mod, "HAS_MQTT", False)
    bridge = MQTTBridge()
    assert bridge.connect() is False


def test_disconnect_no_client_is_safe():
    bridge = MQTTBridge()
    bridge.disconnect()  # must not raise


def test_publish_no_client_is_safe():
    bridge = MQTTBridge()
    bridge.publish_status({"ok": True})  # must not raise
    bridge.publish_battery({"charge": 0.9})  # must not raise


def test_ha_discovery_payload_count():
    assert len(_HA_CONFIGS) == 2


def test_ha_discovery_topics():
    topics = [t for t, _ in _HA_CONFIGS]
    assert any("binary_sensor" in t for t in topics)
    assert any("sensor" in t for t in topics)


def test_ha_discovery_device_identifiers():
    for _, payload in _HA_CONFIGS:
        assert payload["device"]["identifiers"] == ["hushbell_poc"]


def test_ha_discovery_payloads_serialisable():
    for _, payload in _HA_CONFIGS:
        serialised = json.dumps(payload)
        assert "hushbell" in serialised


def test_ha_battery_payload_has_unit():
    battery_payload = next(p for _, p in _HA_CONFIGS if "battery" in p.get("unique_id", ""))
    assert battery_payload["unit_of_measurement"] == "%"
    assert battery_payload["device_class"] == "battery"
