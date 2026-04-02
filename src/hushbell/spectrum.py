"""Real-time FFT spectrum display for HushBell audio.

Shows 0-4000Hz with 40Hz (tactile) and dynamic secondary frequency markers.
Non-blocking -- uses plt.show(block=False).
"""
import numpy as np


def _style_dark(ax, fig) -> None:
    """Apply dark theme to axes and figure."""
    ax.set_facecolor("#1e1e1e")
    fig.patch.set_facecolor("#1e1e1e")
    ax.tick_params(colors="#e0e0e0")
    ax.xaxis.label.set_color("#e0e0e0")
    ax.yaxis.label.set_color("#e0e0e0")
    ax.title.set_color("#ea580c")


def plot_spectrum(
    samples: np.ndarray,
    sample_rate: int = 44100,
    marker_freq: float = 2000.0,
) -> None:
    """Display FFT spectrum of audio samples with dynamic frequency marker."""
    import matplotlib.pyplot as plt

    fft = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)
    mask = freqs <= 4000

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(freqs[mask], fft[mask], color="#ea580c", linewidth=0.8)
    ax.axvline(40, color="#FFBF00", linestyle="--", alpha=0.7, label="40Hz (tactile)")
    ax.axvline(
        marker_freq,
        color="#FFBF00",
        linestyle="--",
        alpha=0.7,
        label=f"{marker_freq:.0f}Hz (piezo)",
    )
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("HushBell Frequency Spectrum")
    ax.legend()
    _style_dark(ax, fig)
    plt.tight_layout()
    plt.show(block=False)
