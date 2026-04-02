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
    assert len(_HA_CONFIGS) == 5


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


# --- Config message handling tests ---

def test_on_config_callback_stored():
    cb = lambda updates: updates
    bridge = MQTTBridge(on_config=cb)
    assert bridge._on_config is cb


def test_handle_config_valid_json():
    received = {}

    def on_config(updates):
        received.update(updates)
        return {"frequency_mode": "random"}

    bridge = MQTTBridge(on_config=on_config)
    bridge._handle_config(b'{"frequency_mode": "random"}')
    assert received == {"frequency_mode": "random"}


def test_handle_config_invalid_json():
    called = []
    bridge = MQTTBridge(on_config=lambda u: called.append(u))
    bridge._handle_config(b"not json{{{")
    assert called == []


def test_handle_config_non_dict_json():
    called = []
    bridge = MQTTBridge(on_config=lambda u: called.append(u))
    bridge._handle_config(b'[1, 2, 3]')
    assert called == []


def test_handle_config_no_callback_is_safe():
    bridge = MQTTBridge()
    bridge._handle_config(b'{"frequency_mode": "random"}')


def test_publish_config_state_no_client_is_safe():
    bridge = MQTTBridge()
    bridge.publish_config_state({"valid": True, "frequency_mode": "random"})


def test_initial_config_state_stored():
    bridge = MQTTBridge()
    state = {"frequency_mode": "fixed", "pleasant": False}
    bridge.set_initial_config_state(state)
    assert bridge._initial_config_state == state


# --- HA discovery config entity tests ---

def test_ha_discovery_has_select_entities():
    topics = [t for t, _ in _HA_CONFIGS]
    assert any("select" in t and "frequency_mode" in t for t in topics)
    assert any("select" in t and "envelope_type" in t for t in topics)


def test_ha_discovery_has_switch_entity():
    topics = [t for t, _ in _HA_CONFIGS]
    assert any("switch" in t and "pleasant" in t for t in topics)


def test_ha_config_entities_use_correct_state_topic():
    config_entities = [
        (t, p) for t, p in _HA_CONFIGS
        if "select" in t or "switch" in t
    ]
    for _, payload in config_entities:
        assert payload["state_topic"] == "hushbell/config/state"


def test_ha_config_entities_serialisable():
    config_entities = [
        (t, p) for t, p in _HA_CONFIGS
        if "select" in t or "switch" in t
    ]
    for _, payload in config_entities:
        serialised = json.dumps(payload)
        assert "hushbell" in serialised


def test_ha_frequency_mode_options():
    freq_payload = next(
        p for _, p in _HA_CONFIGS if "frequency_mode" in p.get("unique_id", "")
    )
    assert freq_payload["options"] == ["fixed", "random", "preset", "vagal"]
