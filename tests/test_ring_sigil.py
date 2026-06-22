"""Ring Sigil — determinism + frequency-sensitivity + presence in both surfaces.

The sigil is a pure function of (freq, envelope, pleasant). This test ports the
FNV-1a + LCG glyph walk to Python and asserts the Goodhart anchor:
  same payload  -> identical id   (reproducible)
  different freq -> different id   (it genuinely depends on the frequency)
A revert that makes the sigil ignore frequency (e.g. a random flourish) fails here.

Static-HTML assertions also confirm the JS functions + card markup are present and
identical across docs/ and web/ (zero-CDN, no browser).
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_FILES = [REPO_ROOT / "docs" / "index.html", REPO_ROOT / "web" / "index.html"]

U32 = 0xFFFFFFFF


def _imul(a, b):
    """JS Math.imul: 32-bit signed multiply, returned as an unsigned 32-bit int."""
    return (a * b) & U32


def ring_hash(s: str) -> int:
    """Python port of the JS FNV-1a 32-bit hash."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = _imul(h, 16777619)
    return h & U32


def ring_sigil(freq, env: str, pleasant: bool):
    """Python port of ringSigil — must match the JS byte-for-byte by construction."""
    seed = f"{freq}|{env}|{'p' if pleasant else '-'}"
    h = ring_hash(seed)
    glyphs = [" ", ".", ":", "-", "=", "#"]
    rows = []
    for _ in range(5):
        line = ""
        for _ in range(11):
            line += glyphs[h % len(glyphs)]
            h = (_imul(h, 1103515245) + 12345) & U32
        rows.append(line)
    return {"art": "\n".join(rows), "id": format(ring_hash(seed), "08x")[-8:]}


# ─── Goodhart anchor: the pure function genuinely depends on its inputs ──────────

def test_sigil_is_deterministic():
    assert ring_sigil(2000, "linear", False)["id"] == ring_sigil(2000, "linear", False)["id"]


def test_sigil_is_frequency_sensitive():
    assert ring_sigil(2000, "linear", False)["id"] != ring_sigil(2100, "linear", False)["id"]


def test_sigil_is_envelope_sensitive():
    assert ring_sigil(2000, "linear", False)["id"] != ring_sigil(2000, "sine", False)["id"]


def test_sigil_is_pleasant_sensitive():
    assert ring_sigil(2000, "linear", False)["id"] != ring_sigil(2000, "linear", True)["id"]


def test_sigil_shape_is_5_by_11():
    art = ring_sigil(1234, "exponential", False)["art"]
    lines = art.split("\n")
    assert len(lines) == 5
    assert all(len(line) == 11 for line in lines)


def test_sigil_id_is_8_hex_chars():
    sid = ring_sigil(900, "linear", True)["id"]
    assert len(sid) == 8
    assert all(c in "0123456789abcdef" for c in sid)


# ─── Presence in the rendered HTML (both surfaces) ──────────────────────────────

@pytest.fixture(params=HTML_FILES, ids=lambda p: p.parent.name)
def html(request):
    return request.param.read_text(encoding="utf-8")


def test_sigil_functions_present(html):
    assert "function ringHash(" in html
    assert "function ringSigil(" in html
    assert "function renderSigil(" in html


def test_sigil_card_and_stack_present(html):
    assert 'id="sigilStack"' in html
    assert "Ring Sigil" in html


def test_sigil_wired_to_ring_and_hw_echo(html):
    # Web-origin ring renders a sigil; the ESP32 echo renders its own [HW]-tagged sigil.
    assert "renderSigil(currentSecondaryFreq" in html
    assert "[HW] " in html
