"""Audio engine -- generates 40Hz tactile + variable-frequency piezo tones.

The dual-frequency notification stack is HushBell's core innovation:
- 40Hz sits below the 67Hz canine hearing floor (Heffner & Heffner, 1983)
- Secondary tone uses fade-in to defeat the acoustic startle reflex (<20ms)
- Frequency varies per ring to prevent classical conditioning (Alex's fix)
- Combined playback provides both felt (tactile) and heard (piezo) notification
"""
import random

import numpy as np

from .config import AudioConfig, FrequencyMode

# Preset rotation counter (module-level for cross-call persistence)
_preset_index = 0


def _build_envelope(
    t: np.ndarray,
    fade_in_sec: float,
    envelope_type: str = "linear",
) -> np.ndarray:
    """Build fade-in envelope. ALWAYS produces zero onset (anti-startle).

    Supported types:
      linear:      straight ramp (original behaviour)
      sine:        quarter-sine curve (smoother onset)
      exponential: exponential rise (gentle start, quick finish)
    """
    if fade_in_sec <= 0:
        return np.ones_like(t, dtype=np.float32)

    normalised = np.minimum(t / fade_in_sec, 1.0).astype(np.float32)

    _ENVELOPE_FNS = {
        "linear": lambda n: n,
        "sine": lambda n: np.sin(n * np.pi / 2).astype(np.float32),
        "exponential": lambda n: ((np.exp(3 * n) - 1) / (np.exp(3.0) - 1)).astype(
            np.float32
        ),
    }
    fn = _ENVELOPE_FNS.get(envelope_type, _ENVELOPE_FNS["linear"])
    return fn(normalised)


def generate_tone(
    freq_hz: float,
    duration_sec: float,
    amplitude: float,
    sample_rate: int,
    fade_in_sec: float = 0.0,
    envelope_type: str = "linear",
) -> np.ndarray:
    """Generate a sine wave with fade-in envelope.

    Args:
        freq_hz: Frequency in Hz.
        duration_sec: Duration in seconds.
        amplitude: Peak amplitude (0.0 to 1.0).
        sample_rate: Samples per second.
        fade_in_sec: Fade-in ramp duration. 0 = no fade.
        envelope_type: Shape of fade-in curve (linear/sine/exponential).

    Returns:
        Float32 numpy array of audio samples.
    """
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False, dtype=np.float32)

    signal = amplitude * np.sin(2 * np.pi * freq_hz * t)

    if fade_in_sec > 0:
        envelope = _build_envelope(t, fade_in_sec, envelope_type)
        signal *= envelope

    return signal


def resolve_secondary_freq(config: AudioConfig) -> float:
    """Resolve the secondary frequency based on the configured strategy.

    Each mode guarantees a frequency within the safe human-audible range
    (500-4000Hz), well above the 67Hz canine hearing floor.

    Returns:
        Resolved frequency in Hz for this ring.
    """
    global _preset_index

    _RESOLVERS = {
        FrequencyMode.FIXED: lambda: config.secondary_freq_hz,
        FrequencyMode.RANDOM: lambda: random.uniform(
            config.frequency_range_min_hz,
            config.frequency_range_max_hz,
        ),
        FrequencyMode.PRESET: lambda: _resolve_preset(config),
        FrequencyMode.VAGAL: lambda: max(
            500.0,
            min(4000.0, random.gauss(config.vagal_center_hz, config.vagal_spread_hz)),
        ),
    }
    resolver = _RESOLVERS.get(FrequencyMode(config.frequency_mode), _RESOLVERS[FrequencyMode.FIXED])
    return resolver()


def _resolve_preset(config: AudioConfig) -> float:
    """Resolve preset frequency with rotation."""
    global _preset_index
    presets = config.frequency_presets
    if not presets:
        return config.secondary_freq_hz
    freq = presets[_preset_index % len(presets)]
    _preset_index += 1
    return freq


def reset_preset_index() -> None:
    """Reset preset rotation counter (for testing)."""
    global _preset_index
    _preset_index = 0


def generate_primary(config: AudioConfig) -> np.ndarray:
    """Generate 40Hz tactile tone (below dog hearing floor)."""
    return generate_tone(
        freq_hz=config.primary_freq_hz,
        duration_sec=config.primary_duration_sec,
        amplitude=config.primary_amplitude,
        sample_rate=config.sample_rate,
    )


def generate_secondary(config: AudioConfig, freq_override: float | None = None) -> tuple[np.ndarray, float]:
    """Generate secondary piezo tone with anti-startle fade-in.

    The frequency is resolved from the configured strategy unless
    freq_override is provided. Fade-in is ALWAYS applied regardless
    of frequency -- this is the anti-startle safety guarantee.

    When config.pleasant is True, harmonic layering and vibrato are
    applied for warmer, more musical tones.
    """
    freq = freq_override if freq_override is not None else resolve_secondary_freq(config)
    signal = generate_tone(
        freq_hz=freq,
        duration_sec=config.secondary_duration_sec,
        amplitude=config.secondary_amplitude,
        sample_rate=config.sample_rate,
        fade_in_sec=config.secondary_fade_in_sec,
        envelope_type=config.envelope_type,
    )
    if config.pleasant:
        from .pleasant_tones import make_pleasant
        signal = make_pleasant(signal, freq, config)
    return signal, freq


def _pad_to_length(signal: np.ndarray, target_len: int) -> np.ndarray:
    """Zero-pad a signal to a target length."""
    if len(signal) < target_len:
        return np.pad(signal, (0, target_len - len(signal)))
    return signal


def generate_combined(config: AudioConfig) -> tuple[np.ndarray, float]:
    """Generate both tones mixed together.

    The 40Hz and variable-frequency signals occupy completely different
    frequency bands, so there is no destructive interference.

    Returns:
        Tuple of (audio samples, secondary frequency used).
    """
    primary = generate_primary(config)
    secondary_samples, freq_used = generate_secondary(config)

    max_len = max(len(primary), len(secondary_samples))
    primary = _pad_to_length(primary, max_len)
    secondary_samples = _pad_to_length(secondary_samples, max_len)

    combined = primary + secondary_samples
    return np.clip(combined, -1.0, 1.0).astype(np.float32), freq_used


def play_audio(samples: np.ndarray, sample_rate: int = 44100) -> None:
    """Play audio samples through the default output device."""
    import sounddevice as sd
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


def ring(config: AudioConfig | None = None) -> tuple[np.ndarray, float]:
    """Execute a full ring cycle. Returns (audio, freq_used)."""
    if config is None:
        config = AudioConfig()

    if config.play_combined:
        samples, freq = generate_combined(config)
    else:
        samples = generate_primary(config)
        freq = 0.0
    play_audio(samples, config.sample_rate)
    return samples, freq
