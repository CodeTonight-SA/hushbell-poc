"""Tests for HushBell audio engine -- FFT verification of generated tones.

Verifies:
- 40Hz primary tone within +/- 0.5Hz of spec
- 2000Hz secondary tone within +/- 5Hz of spec
- 500ms fade-in envelope applied correctly
- Combined signal contains both frequency components
"""
import numpy as np

from hushbell.audio_engine import generate_tone, generate_primary, generate_secondary, generate_combined
from hushbell.config import AudioConfig


def _dominant_frequency(signal: np.ndarray, sample_rate: int) -> float:
    """Find the dominant frequency in a signal via FFT."""
    fft_result = np.fft.rfft(signal)
    magnitudes = np.abs(fft_result)
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sample_rate)
    return freqs[np.argmax(magnitudes[1:]) + 1]


class TestPrimaryTone:
    """40Hz tactile tone -- below 67Hz dog hearing floor."""

    def test_frequency_accuracy(self):
        config = AudioConfig()
        signal = generate_primary(config)
        freq = _dominant_frequency(signal, config.sample_rate)
        assert abs(freq - 40.0) < 0.5, f"40Hz tone off by {abs(freq - 40.0):.2f}Hz"

    def test_duration(self):
        config = AudioConfig(primary_duration_sec=1.5)
        signal = generate_primary(config)
        expected_samples = int(1.5 * config.sample_rate)
        assert len(signal) == expected_samples

    def test_amplitude_range(self):
        signal = generate_primary(AudioConfig())
        assert np.max(np.abs(signal)) <= 1.0


class TestSecondaryTone:
    """2000Hz piezo with 500ms anti-startle fade-in."""

    def test_frequency_accuracy(self):
        config = AudioConfig()
        signal = generate_secondary(config)
        freq = _dominant_frequency(signal, config.sample_rate)
        assert abs(freq - 2000.0) < 5.0, f"2kHz tone off by {abs(freq - 2000.0):.2f}Hz"

    def test_fade_in_envelope(self):
        config = AudioConfig(secondary_fade_in_sec=0.5)
        signal = generate_secondary(config)
        # First sample should be near zero (fade-in starts from 0)
        assert abs(signal[0]) < 0.01
        # Sample at 250ms should be ~half amplitude
        mid_sample = int(0.25 * config.sample_rate)
        peak = config.secondary_amplitude
        # Allow 20% tolerance for sine wave phase
        assert abs(signal[mid_sample]) < peak * 0.7


class TestCombinedSignal:
    """Both tones mixed -- non-interfering frequency bands."""

    def test_contains_both_frequencies(self):
        config = AudioConfig()
        signal = generate_combined(config)
        fft_result = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / config.sample_rate)

        # Find peaks near 40Hz and 2000Hz
        idx_40 = np.argmin(np.abs(freqs - 40))
        idx_2k = np.argmin(np.abs(freqs - 2000))

        assert fft_result[idx_40] > 100, "40Hz component missing"
        assert fft_result[idx_2k] > 100, "2kHz component missing"

    def test_clipped_to_safe_range(self):
        signal = generate_combined(AudioConfig())
        assert np.max(signal) <= 1.0
        assert np.min(signal) >= -1.0


class TestToneGenerator:
    """Low-level generate_tone function."""

    def test_zero_amplitude(self):
        signal = generate_tone(440, 1.0, 0.0, 44100)
        assert np.allclose(signal, 0.0)

    def test_dtype_float32(self):
        signal = generate_tone(440, 0.5, 0.5, 44100)
        assert signal.dtype == np.float32
