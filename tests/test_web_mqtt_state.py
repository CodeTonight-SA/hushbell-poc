"""Static-HTML assertions for the MQTT state-machine upgrade (no browser needed).

Goodhart-resistant: each test fails if someone reverts the explicit state machine
back to a boolean `this.connected` flag, or drops the handler-nulling in `_cleanup`.
Both docs/index.html and web/index.html are checked — they must stay byte-identical,
so a regression on either surface is caught.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_FILES = [REPO_ROOT / "docs" / "index.html", REPO_ROOT / "web" / "index.html"]


@pytest.fixture(params=HTML_FILES, ids=lambda p: p.parent.name)
def html(request):
    return request.param.read_text(encoding="utf-8")


def test_no_boolean_connected_flag(html):
    # The ad-hoc boolean flag is gone — state is a string machine instead.
    assert "this.connected =" not in html
    assert "mqtt.connected" not in html


def test_state_machine_present(html):
    assert "_setState(" in html
    assert "this.state = 'disconnected'" in html
    # Every documented state must be reachable in the code.
    for state in ("connecting", "connected", "error", "disconnected"):
        assert f"'{state}'" in html


def test_single_state_change_callback(html):
    # One onStateChange callback replaces the old onDisconnect + mqttSetStatus juggling.
    assert "onStateChange" in html
    assert "onDisconnect" not in html
    assert "function mqttSetStatus" not in html


def test_cleanup_nulls_all_four_ws_handlers(html):
    # The hardened cleanup must detach onopen/onmessage/onclose/onerror before
    # dropping the socket — proof the zombie-callback class is closed.
    assert "this.ws.onopen = this.ws.onmessage = this.ws.onclose = this.ws.onerror = null" in html
    assert "_cleanup()" in html


def test_publish_and_subscribe_guard_on_state(html):
    # Guards key off the state machine, not the removed boolean.
    assert "this.state !== 'connected'" in html
    assert "this.state === 'connected'" in html


def test_working_ui_ids_preserved(html):
    # Main's richer feed UI ids must survive the graft unchanged.
    for el_id in (
        "mqttFeed", "mqttConnBtn", "mqttIndicator",
        "mqttHwStatus", "mqttHwBattery", "mqttLastTopic", "mqttLastPayload",
    ):
        assert f'id="{el_id}"' in html
