"""Tests for HushBell audio engine -- FFT verification of generated tones.

Verifies:
- 40Hz primary tone within +/- 0.5Hz of spec
- Secondary tone frequency accuracy across all modes
- Fade-in envelope applied correctly for all envelope types
- Combined signal contains both frequency components
- Anti-conditioning: frequency varies in random/preset/vagal modes
"""
import numpy as np

from hushbell.audio_engine import (
    generate_tone,
    generate_primary,
    generate_secondary,
    generate_combined,
    resolve_secondary_freq,
    reset_preset_index,
    _build_envelope,
)
from hushbell.config import AudioConfig, FrequencyMode


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
    """Secondary piezo with anti-startle fade-in -- variable frequency."""

    def test_frequency_accuracy_fixed_mode(self):
        config = AudioConfig(frequency_mode=FrequencyMode.FIXED)
        signal, freq_used = generate_secondary(config)
        detected = _dominant_frequency(signal, config.sample_rate)
        assert abs(detected - 2000.0) < 5.0, f"Fixed mode: off by {abs(detected - 2000.0):.2f}Hz"
        assert freq_used == 2000.0

    def test_fade_in_envelope_always_applied(self):
        """PARAMOUNT: fade-in must be applied regardless of frequency mode."""
        for mode in FrequencyMode:
            config = AudioConfig(frequency_mode=mode, secondary_fade_in_sec=0.5)
            signal, _ = generate_secondary(config)
            assert abs(signal[0]) < 0.01, f"Mode {mode.value}: first sample not near zero (fade-in missing)"

    def test_fade_in_all_envelope_types(self):
        """All envelope shapes must start at zero (anti-startle guarantee)."""
        for env_type in ["linear", "sine", "exponential"]:
            config = AudioConfig(envelope_type=env_type, secondary_fade_in_sec=0.5)
            signal, _ = generate_secondary(config)
            assert abs(signal[0]) < 0.01, f"Envelope {env_type}: first sample not near zero"

    def test_random_mode_varies_frequency(self):
        config = AudioConfig(
            frequency_mode=FrequencyMode.RANDOM,
            frequency_range_min_hz=800.0,
            frequency_range_max_hz=3500.0,
        )
        freqs = [resolve_secondary_freq(config) for _ in range(50)]
        unique_freqs = set(round(f, 1) for f in freqs)
        assert len(unique_freqs) > 10, f"Random mode produced only {len(unique_freqs)} unique frequencies"
        assert all(800.0 <= f <= 3500.0 for f in freqs), "Frequency outside configured range"

    def test_preset_mode_cycles(self):
        reset_preset_index()
        presets = [1000.0, 1500.0, 2000.0]
        config = AudioConfig(
            frequency_mode=FrequencyMode.PRESET,
            frequency_presets=presets,
        )
        resolved = [resolve_secondary_freq(config) for _ in range(6)]
        assert resolved == [1000.0, 1500.0, 2000.0, 1000.0, 1500.0, 2000.0]

    def test_vagal_mode_centres_around_config(self):
        config = AudioConfig(
            frequency_mode=FrequencyMode.VAGAL,
            vagal_center_hz=900.0,
            vagal_spread_hz=200.0,
        )
        freqs = [resolve_secondary_freq(config) for _ in range(200)]
        mean_freq = sum(freqs) / len(freqs)
        assert 700.0 < mean_freq < 1100.0, f"Vagal mean {mean_freq:.0f}Hz not centred around 900Hz"
        assert all(500.0 <= f <= 4000.0 for f in freqs), "Vagal frequency outside safe range"

    def test_fixed_mode_backwards_compatible(self):
        """Default config must produce identical behaviour to original."""
        config = AudioConfig()
        assert config.frequency_mode == FrequencyMode.FIXED
        freq = resolve_secondary_freq(config)
        assert freq == 2000.0


class TestCombinedSignal:
    """Both tones mixed -- non-interfering frequency bands."""

    def test_contains_both_frequencies(self):
        config = AudioConfig()
        signal, freq_used = generate_combined(config)
        fft_result = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / config.sample_rate)

        idx_40 = np.argmin(np.abs(freqs - 40))
        idx_secondary = np.argmin(np.abs(freqs - freq_used))

        assert fft_result[idx_40] > 100, "40Hz component missing"
        assert fft_result[idx_secondary] > 100, f"{freq_used}Hz component missing"

    def test_clipped_to_safe_range(self):
        signal, _ = generate_combined(AudioConfig())
        assert np.max(signal) <= 1.0
        assert np.min(signal) >= -1.0

    def test_returns_frequency_used(self):
        _, freq = generate_combined(AudioConfig())
        assert isinstance(freq, float)
        assert freq > 0

    def test_random_mode_combined_varies(self):
        config = AudioConfig(frequency_mode=FrequencyMode.RANDOM)
        freqs = [generate_combined(config)[1] for _ in range(20)]
        assert len(set(round(f, 1) for f in freqs)) > 5, "Combined random mode not varying"


class TestToneGenerator:
    """Low-level generate_tone function."""

    def test_zero_amplitude(self):
        signal = generate_tone(440, 1.0, 0.0, 44100)
        assert np.allclose(signal, 0.0)

    def test_dtype_float32(self):
        signal = generate_tone(440, 0.5, 0.5, 44100)
        assert signal.dtype == np.float32

    def test_custom_frequency_with_fade_in(self):
        signal = generate_tone(1500, 1.0, 0.5, 44100, fade_in_sec=0.3)
        assert abs(signal[0]) < 0.01
        freq = _dominant_frequency(signal, 44100)
        assert abs(freq - 1500) < 5.0


class TestEnvelopeBuilder:
    """Envelope shape verification."""

    def test_linear_envelope(self):
        t = np.linspace(0, 1.0, 44100, dtype=np.float32)
        env = _build_envelope(t, 0.5, "linear")
        assert abs(env[0]) < 0.001
        mid = int(0.25 * 44100)
        assert 0.4 < env[mid] < 0.6

    def test_sine_envelope(self):
        t = np.linspace(0, 1.0, 44100, dtype=np.float32)
        env = _build_envelope(t, 0.5, "sine")
        assert abs(env[0]) < 0.001
        assert env[-1] == 1.0

    def test_exponential_envelope(self):
        t = np.linspace(0, 1.0, 44100, dtype=np.float32)
        env = _build_envelope(t, 0.5, "exponential")
        assert abs(env[0]) < 0.001
        assert env[-1] == 1.0

    def test_all_envelopes_start_at_zero(self):
        """Anti-startle guarantee: every envelope type starts at zero."""
        t = np.linspace(0, 1.0, 44100, dtype=np.float32)
        for env_type in ["linear", "sine", "exponential"]:
            env = _build_envelope(t, 0.5, env_type)
            assert abs(env[0]) < 0.001, f"{env_type} envelope doesn't start at zero"

    def test_unknown_envelope_falls_back_to_linear(self):
        t = np.linspace(0, 1.0, 44100, dtype=np.float32)
        env = _build_envelope(t, 0.5, "unknown_type")
        env_linear = _build_envelope(t, 0.5, "linear")
        assert np.allclose(env, env_linear)
