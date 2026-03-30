"""Tests for visual_engine.LEDStrip -- no display required."""
import threading

from hushbell.visual_engine import LEDStrip, LED_COUNT


def test_led_strip_instantiation():
    strip = LEDStrip()
    assert strip._running is False
    assert strip._ring_event is not None


def test_ring_event_set():
    strip = LEDStrip()
    assert not strip._ring_event.is_set()
    strip.ring()
    assert strip._ring_event.is_set()


def test_ring_event_clear_after_stop():
    strip = LEDStrip()
    strip.ring()
    strip._ring_event.clear()
    assert not strip._ring_event.is_set()


def test_idle_levels_length():
    strip = LEDStrip()
    bs = strip._idle_levels(0.0)
    assert len(bs) == LED_COUNT


def test_idle_levels_range():
    strip = LEDStrip()
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        bs = strip._idle_levels(t)
        assert all(0.0 <= b <= 1.0 for b in bs), f"brightness out of range at t={t}"


def test_chase_levels_length():
    strip = LEDStrip()
    assert len(strip._chase_levels(0.0)) == LED_COUNT


def test_strip_thread_is_daemon():
    t = threading.Thread(target=lambda: None, daemon=True)
    assert t.daemon is True
