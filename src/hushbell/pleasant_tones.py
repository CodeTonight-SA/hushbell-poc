"""Pleasant tone generation -- vagal phoneme research and harmonic layering.

Vagal nerve stimulation frequencies (800-1100Hz) resonate with the human
vagus nerve, producing a calming effect. This module provides tone shaping
that makes randomised doorbell frequencies sound pleasant rather than jarring.

References:
  - Porges (2011): Polyvagal Theory -- prosodic frequencies 500-1000Hz
  - Vagal tone and acoustic stimulation research
  - Thomas Frumkin's "phat beats" / vagal phonemes suggestion
"""
import numpy as np

from .config import AudioConfig

# Vagal nerve resonance sweet spots (Hz)
VAGAL_SWEET_SPOTS = [800, 850, 900, 950, 1000, 1050, 1100]

# Pleasant interval ratios (musical harmony)
HARMONIC_RATIOS = {
    "octave": 2.0,
    "fifth": 1.5,
    "third": 1.25,
}


def add_harmonics(
    signal: np.ndarray,
    freq_hz: float,
    duration_sec: float,
    sample_rate: int,
    harmonic_gain: float = 0.15,
) -> np.ndarray:
    """Layer soft 3rd harmonic for warmth and richness.

    The 3rd harmonic (1.25x fundamental) adds musical richness without
    making the tone sound artificial. Gain is kept low to maintain
    the fundamental as the dominant frequency.
    """
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False, dtype=np.float32)

    harmonic_freq = freq_hz * HARMONIC_RATIOS["third"]
    if harmonic_freq > 4000:
        return signal

    harmonic = harmonic_gain * np.sin(2 * np.pi * harmonic_freq * t)

    result = signal[:num_samples] + harmonic[:num_samples].astype(np.float32)
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def add_vibrato(
    signal: np.ndarray,
    duration_sec: float,
    sample_rate: int,
    vibrato_rate_hz: float = 5.0,
    vibrato_depth: float = 0.02,
) -> np.ndarray:
    """Add slight vibrato for warmth (human voice quality).

    Vibrato rate of 5Hz with 2% depth mimics natural vocal vibrato,
    making the tone feel less synthetic. This is the "phat beats"
    quality Thomas suggested.
    """
    num_samples = min(len(signal), int(duration_sec * sample_rate))
    t = np.linspace(0, duration_sec, num_samples, endpoint=False, dtype=np.float32)

    modulator = 1.0 + vibrato_depth * np.sin(2 * np.pi * vibrato_rate_hz * t)
    signal[:num_samples] = (signal[:num_samples] * modulator).astype(np.float32)
    return np.clip(signal, -1.0, 1.0).astype(np.float32)


def make_pleasant(
    signal: np.ndarray,
    freq_hz: float,
    config: AudioConfig,
) -> np.ndarray:
    """Apply pleasant tone shaping: harmonics + vibrato.

    Designed to make any frequency in the 500-4000Hz range sound
    warm and musical rather than harsh and clinical.
    """
    shaped = add_harmonics(
        signal,
        freq_hz,
        config.secondary_duration_sec,
        config.sample_rate,
    )
    shaped = add_vibrato(
        shaped,
        config.secondary_duration_sec,
        config.sample_rate,
    )
    return shaped
