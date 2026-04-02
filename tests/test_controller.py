"""Tests for HushBellController runtime config updates.

Verifies:
- Partial audio config updates via update_audio_config()
- Frequency mode string-to-enum coercion
- Invalid values rejected with proper exceptions
- Pydantic immutability preserved (original config untouched)
"""
import pytest
from pydantic import ValidationError

from hushbell.config import AudioConfig, FrequencyMode, HushBellConfig
from hushbell.controller import HushBellController


class TestUpdateAudioConfig:
    """Runtime audio config updates via update_audio_config()."""

    def test_change_frequency_mode(self):
        ctrl = HushBellController()
        assert ctrl.config.audio.frequency_mode == FrequencyMode.FIXED
        ctrl.update_audio_config({"frequency_mode": "random"})
        assert ctrl.config.audio.frequency_mode == FrequencyMode.RANDOM

    def test_change_pleasant(self):
        ctrl = HushBellController()
        assert ctrl.config.audio.pleasant is False
        ctrl.update_audio_config({"pleasant": True})
        assert ctrl.config.audio.pleasant is True

    def test_partial_update_preserves_other_fields(self):
        ctrl = HushBellController()
        original_freq = ctrl.config.audio.primary_freq_hz
        original_amplitude = ctrl.config.audio.secondary_amplitude
        ctrl.update_audio_config({"frequency_mode": "vagal"})
        assert ctrl.config.audio.primary_freq_hz == original_freq
        assert ctrl.config.audio.secondary_amplitude == original_amplitude

    def test_invalid_mode_raises(self):
        ctrl = HushBellController()
        with pytest.raises(ValueError):
            ctrl.update_audio_config({"frequency_mode": "nonexistent"})

    def test_invalid_range_raises(self):
        ctrl = HushBellController()
        with pytest.raises(ValidationError):
            ctrl.update_audio_config({"primary_freq_hz": 999.0})

    def test_returns_new_audio_config(self):
        ctrl = HushBellController()
        result = ctrl.update_audio_config({"envelope_type": "sine"})
        assert isinstance(result, AudioConfig)
        assert result.envelope_type == "sine"

    def test_multi_field_update(self):
        ctrl = HushBellController()
        ctrl.update_audio_config({
            "frequency_mode": "vagal",
            "pleasant": True,
            "envelope_type": "exponential",
        })
        assert ctrl.config.audio.frequency_mode == FrequencyMode.VAGAL
        assert ctrl.config.audio.pleasant is True
        assert ctrl.config.audio.envelope_type == "exponential"

    def test_original_config_immutability(self):
        ctrl = HushBellController()
        original_config = ctrl.config
        ctrl.update_audio_config({"pleasant": True})
        assert original_config.audio.pleasant is False
        assert ctrl.config.audio.pleasant is True


class TestHandleMqttConfig:
    """MQTT config handler returns serialised dict or None."""

    def test_valid_update_returns_dict(self):
        ctrl = HushBellController()
        result = ctrl._handle_mqtt_config({"frequency_mode": "random"})
        assert result is not None
        assert result["frequency_mode"] == "random"

    def test_invalid_update_returns_none(self):
        ctrl = HushBellController()
        result = ctrl._handle_mqtt_config({"frequency_mode": "bad_value"})
        assert result is None

    def test_returns_full_config(self):
        ctrl = HushBellController()
        result = ctrl._handle_mqtt_config({"pleasant": True})
        assert "pleasant" in result
        assert "frequency_mode" in result
        assert "secondary_freq_hz" in result
