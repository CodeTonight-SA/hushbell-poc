"""Audio engine -- generates 40Hz tactile + 2kHz piezo tones.

The dual-frequency notification stack is HushBell's core innovation:
- 40Hz sits below the 67Hz canine hearing floor (Heffner & Heffner, 1983)
- 2000Hz uses a 500ms fade-in to defeat the acoustic startle reflex (<20ms)
- Combined playback provides both felt (tactile) and heard (piezo) notification
"""
import numpy as np

from .config import AudioConfig


def generate_tone(
    freq_hz: float,
    duration_sec: float,
    amplitude: float,
    sample_rate: int,
    fade_in_sec: float = 0.0,
) -> np.ndarray:
    """Generate a sine wave with optional linear fade-in envelope.

    Args:
        freq_hz: Frequency in Hz.
        duration_sec: Duration in seconds.
        amplitude: Peak amplitude (0.0 to 1.0).
        sample_rate: Samples per second.
        fade_in_sec: Linear ramp duration. 0 = no fade.

    Returns:
        Float32 numpy array of audio samples.
    """
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False, dtype=np.float32)

    signal = amplitude * np.sin(2 * np.pi * freq_hz * t)

    if fade_in_sec > 0:
        envelope = np.minimum(t / fade_in_sec, 1.0).astype(np.float32)
        signal *= envelope

    return signal


def generate_primary(config: AudioConfig) -> np.ndarray:
    """Generate 40Hz tactile tone (below dog hearing floor)."""
    return generate_tone(
        freq_hz=config.primary_freq_hz,
        duration_sec=config.primary_duration_sec,
        amplitude=config.primary_amplitude,
        sample_rate=config.sample_rate,
    )


def generate_secondary(config: AudioConfig) -> np.ndarray:
    """Generate 2kHz piezo tone with 500ms anti-startle fade-in."""
    return generate_tone(
        freq_hz=config.secondary_freq_hz,
        duration_sec=config.secondary_duration_sec,
        amplitude=config.secondary_amplitude,
        sample_rate=config.sample_rate,
        fade_in_sec=config.secondary_fade_in_sec,
    )


def _pad_to_length(signal: np.ndarray, target_len: int) -> np.ndarray:
    """Zero-pad a signal to a target length."""
    if len(signal) < target_len:
        return np.pad(signal, (0, target_len - len(signal)))
    return signal


def generate_combined(config: AudioConfig) -> np.ndarray:
    """Generate both tones mixed together.

    The 40Hz and 2kHz signals occupy completely different
    frequency bands, so there is no destructive interference.
    """
    primary = generate_primary(config)
    secondary = generate_secondary(config)

    max_len = max(len(primary), len(secondary))
    primary = _pad_to_length(primary, max_len)
    secondary = _pad_to_length(secondary, max_len)

    combined = primary + secondary
    return np.clip(combined, -1.0, 1.0).astype(np.float32)


def play_audio(samples: np.ndarray, sample_rate: int = 44100) -> None:
    """Play audio samples through the default output device."""
    import sounddevice as sd
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


def ring(config: AudioConfig | None = None) -> np.ndarray:
    """Execute a full ring cycle. Returns the generated audio."""
    if config is None:
        config = AudioConfig()

    samples = generate_combined(config) if config.play_combined else generate_primary(config)
    play_audio(samples, config.sample_rate)
    return samples
