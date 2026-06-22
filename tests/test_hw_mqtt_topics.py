"""Static-HTML assertions for the hardware-readiness upgrade (no browser needed).

Goodhart-resistant:
  * topic strings live in ONE TOPICS object — a re-inlined 'hushbell/...' literal fails
    the no-bare-literal test, so a web<->firmware topic typo cannot silently reappear;
  * auto-reconnect (_reconnect + _wantConnected) must exist, so the resilience that
    keeps the ESP32 bridge alive through a wifi blip cannot be silently dropped.
Both docs/index.html and web/index.html are checked (they stay byte-identical).
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_FILES = [REPO_ROOT / "docs" / "index.html", REPO_ROOT / "web" / "index.html"]


@pytest.fixture(params=HTML_FILES, ids=lambda p: p.parent.name)
def html(request):
    return request.param.read_text(encoding="utf-8")


def test_topics_object_present(html):
    assert "const TOPICS" in html
    # All four canonical topics defined in the single source of truth.
    for topic in ("hushbell/ring", "hushbell/status", "hushbell/battery", "hushbell/config/state"):
        assert f"'{topic}'" in html


def test_no_bare_hushbell_literal_outside_topics(html):
    # Every quoted 'hushbell/...' literal must be a TOPICS member definition.
    # The only legitimate quoted occurrences are the four lines inside `const TOPICS`,
    # each of the form  KEY: 'hushbell/...'. Any other quoted occurrence is a re-inline.
    quoted = re.findall(r"'(hushbell/[^']*)'", html)
    assert len(quoted) == 4, f"expected exactly 4 topic literals (the TOPICS members), found {len(quoted)}: {quoted}"
    # And each must sit on a line that is a TOPICS member assignment (KEY: 'hushbell/...').
    for line in html.splitlines():
        if re.search(r"'hushbell/", line):
            assert re.search(r"^\s*[A-Z_]+:\s*'hushbell/", line), \
                f"bare hushbell/ literal not in a TOPICS member: {line.strip()}"


def test_auto_reconnect_present(html):
    assert "_reconnect" in html
    assert "_wantConnected" in html
    # Bounded exponential backoff capped at 16s, ≤5 attempts.
    assert "2 ** this._reconnectAttempt" in html
    assert "16000" in html


def test_reconnects_counter_surfaced(html):
    assert 'id="mqttReconnects"' in html
    assert "onReconnect" in html


def test_named_hardware_parts_in_status_card(html):
    assert "ESP32-WROOM-32E" in html
    assert "Dayton TT25-8" in html
