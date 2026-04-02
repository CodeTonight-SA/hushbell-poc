"""Tests for frequency anti-conditioning strategies and pleasant tones.

Verifies:
- All frequency modes produce values within safe range (500-4000Hz)
- Preset rotation wraps correctly
- Vagal distribution centres around configured mean
- Pleasant tone shaping preserves fundamental frequency
- Harmonics and vibrato don't clip beyond safe amplitude
- PARAMOUNT: fade-in always applied regardless of any combination of settings
"""
import numpy as np

from hushbell.audio_engine import (
    generate_secondary,
    resolve_secondary_freq,
    reset_preset_index,
    _build_envelope,
)
from hushbell.config import AudioConfig, FrequencyMode
from hushbell.pleasant_tones import add_harmonics, add_vibrato, make_pleasant


def _dominant_frequency(signal: np.ndarray, sample_rate: int) -> float:
    fft_result = np.fft.rfft(signal)
    magnitudes = np.abs(fft_result)
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sample_rate)
    return freqs[np.argmax(magnitudes[1:]) + 1]


class TestFrequencyResolution:
    """Frequency strategy resolves within safe bounds."""

    def test_fixed_always_returns_configured(self):
        config = AudioConfig(frequency_mode=FrequencyMode.FIXED, secondary_freq_hz=1500.0)
        for _ in range(20):
            assert resolve_secondary_freq(config) == 1500.0

    def test_random_within_range(self):
        config = AudioConfig(
            frequency_mode=FrequencyMode.RANDOM,
            frequency_range_min_hz=1000.0,
            frequency_range_max_hz=2000.0,
        )
        freqs = [resolve_secondary_freq(config) for _ in range(100)]
        assert all(1000.0 <= f <= 2000.0 for f in freqs)
        assert len(set(round(f) for f in freqs)) > 20  # sufficient variance

    def test_preset_empty_falls_back(self):
        reset_preset_index()
        config = AudioConfig(
            frequency_mode=FrequencyMode.PRESET,
            frequency_presets=[],
            secondary_freq_hz=2000.0,
        )
        assert resolve_secondary_freq(config) == 2000.0

    def test_preset_single_item(self):
        reset_preset_index()
        config = AudioConfig(
            frequency_mode=FrequencyMode.PRESET,
            frequency_presets=[1234.0],
        )
        for _ in range(5):
            assert resolve_secondary_freq(config) == 1234.0

    def test_vagal_clamped_to_safe_range(self):
        config = AudioConfig(
            frequency_mode=FrequencyMode.VAGAL,
            vagal_center_hz=500.0,
            vagal_spread_hz=500.0,
        )
        freqs = [resolve_secondary_freq(config) for _ in range(500)]
        assert all(500.0 <= f <= 4000.0 for f in freqs), "Vagal produced out-of-range frequency"


class TestAntiConditioningEffectiveness:
    """The core claim: varying frequencies prevent pattern formation."""

    def test_random_mode_entropy(self):
        """Random mode should produce high entropy (many distinct values)."""
        config = AudioConfig(frequency_mode=FrequencyMode.RANDOM)
        freqs = [resolve_secondary_freq(config) for _ in range(100)]
        # Bin into 100Hz buckets
        buckets = set(int(f / 100) for f in freqs)
        assert len(buckets) >= 10, f"Only {len(buckets)} frequency buckets -- too predictable"

    def test_preset_never_repeats_consecutively(self):
        """Preset rotation means no two consecutive rings have the same frequency."""
        reset_preset_index()
        presets = [1000.0, 1500.0, 2000.0, 2500.0, 3000.0]
        config = AudioConfig(
            frequency_mode=FrequencyMode.PRESET,
            frequency_presets=presets,
        )
        freqs = [resolve_secondary_freq(config) for _ in range(10)]
        for i in range(len(freqs) - 1):
            assert freqs[i] != freqs[i + 1], "Consecutive duplicate frequency"


class TestFadeInSafetyGuarantee:
    """PARAMOUNT: every combination of mode x envelope starts at zero amplitude."""

    def test_all_mode_envelope_combinations(self):
        for mode in FrequencyMode:
            for env in ["linear", "sine", "exponential"]:
                config = AudioConfig(
                    frequency_mode=mode,
                    envelope_type=env,
                    secondary_fade_in_sec=0.5,
                )
                signal, _ = generate_secondary(config)
                assert abs(signal[0]) < 0.01, (
                    f"SAFETY VIOLATION: mode={mode.value}, envelope={env} "
                    f"first sample={signal[0]:.4f} (must be near zero)"
                )


class TestPleasantTones:
    """Pleasant tone shaping (Thomas's 'phat beats' requirement)."""

    def test_harmonics_preserve_fundamental(self):
        sr = 44100
        dur = 1.0
        freq = 1000.0
        t = np.linspace(0, dur, int(dur * sr), endpoint=False, dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * freq * t)
        shaped = add_harmonics(signal, freq, dur, sr)
        detected = _dominant_frequency(shaped, sr)
        assert abs(detected - freq) < 5.0, f"Fundamental shifted to {detected}Hz"

    def test_harmonics_dont_clip(self):
        sr = 44100
        dur = 1.0
        freq = 1000.0
        t = np.linspace(0, dur, int(dur * sr), endpoint=False, dtype=np.float32)
        signal = 0.8 * np.sin(2 * np.pi * freq * t)
        shaped = add_harmonics(signal, freq, dur, sr)
        assert np.max(np.abs(shaped)) <= 1.0

    def test_vibrato_adds_modulation(self):
        sr = 44100
        dur = 1.0
        t = np.linspace(0, dur, int(dur * sr), endpoint=False, dtype=np.float32)
        signal = 0.5 * np.sin(2 * np.pi * 1000 * t)
        vibrated = add_vibrato(signal.copy(), dur, sr)
        # Vibrato should change the signal (not identical)
        assert not np.allclose(signal, vibrated, atol=0.001)

    def test_make_pleasant_safe_amplitude(self):
        config = AudioConfig()
        sr = config.sample_rate
        dur = config.secondary_duration_sec
        t = np.linspace(0, dur, int(dur * sr), endpoint=False, dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * 1000 * t)
        shaped = make_pleasant(signal, 1000.0, config)
        assert np.max(np.abs(shaped)) <= 1.0

    def test_high_frequency_skips_harmonic(self):
        """Harmonics above 4000Hz should be skipped (above display range)."""
        sr = 44100
        dur = 1.0
        freq = 3500.0  # 3rd harmonic = 4375Hz > 4000Hz limit
        t = np.linspace(0, dur, int(dur * sr), endpoint=False, dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * freq * t)
        shaped = add_harmonics(signal, freq, dur, sr)
        # Signal should be unchanged (no harmonic added)
        assert np.allclose(signal, shaped)


class TestPleasantIntegration:
    """Pleasant mode integrated into the audio pipeline."""

    def test_pleasant_flag_applies_shaping(self):
        config = AudioConfig(pleasant=True)
        signal_plain, _ = generate_secondary(AudioConfig(pleasant=False))
        signal_pleasant, _ = generate_secondary(config)
        # Pleasant shaping should alter the signal
        assert not np.allclose(signal_plain, signal_pleasant, atol=0.001)

    def test_pleasant_still_has_fade_in(self):
        """PARAMOUNT: pleasant mode must not bypass fade-in."""
        config = AudioConfig(pleasant=True, secondary_fade_in_sec=0.5)
        signal, _ = generate_secondary(config)
        assert abs(signal[0]) < 0.01

    def test_pleasant_safe_amplitude(self):
        config = AudioConfig(pleasant=True)
        signal, _ = generate_secondary(config)
        assert np.max(np.abs(signal)) <= 1.0

    def test_pleasant_with_all_modes(self):
        for mode in FrequencyMode:
            config = AudioConfig(frequency_mode=mode, pleasant=True)
            signal, freq = generate_secondary(config)
            assert abs(signal[0]) < 0.01, f"Pleasant + {mode.value}: fade-in missing"
            assert np.max(np.abs(signal)) <= 1.0, f"Pleasant + {mode.value}: clipping"
