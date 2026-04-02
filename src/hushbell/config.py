"""HushBell configuration -- matches Thomas Frumkin's spec parameters.

Frequency modes defeat classical conditioning: varying the secondary tone
prevents dogs from associating a fixed sound with door activity.
"""
from enum import Enum

from pydantic import BaseModel, Field


class FrequencyMode(str, Enum):
    """Secondary tone frequency selection strategy.

    fixed:  Original 2kHz behaviour (backwards compatible).
    random: Uniform random per ring -- maximum anti-conditioning.
    preset: Cycle through user-defined frequency list.
    vagal:  Gaussian around vagal nerve resonance (~900Hz) -- pleasant tones.
    """

    FIXED = "fixed"
    RANDOM = "random"
    PRESET = "preset"
    VAGAL = "vagal"


class AudioConfig(BaseModel):
    """Audio generation parameters from HushBell spec."""

    # Primary: 40Hz tactile tone (below 67Hz dog hearing floor)
    primary_freq_hz: float = Field(default=40.0, ge=20.0, le=60.0)
    primary_duration_sec: float = Field(default=1.5, ge=0.5, le=5.0)
    primary_amplitude: float = Field(default=0.7, ge=0.0, le=1.0)

    # Secondary: 2000Hz piezo with 500ms fade-in (defeats startle reflex)
    secondary_freq_hz: float = Field(default=2000.0, ge=500.0, le=4000.0)
    secondary_duration_sec: float = Field(default=2.0, ge=0.5, le=5.0)
    secondary_fade_in_sec: float = Field(default=0.5, ge=0.1, le=2.0)
    secondary_amplitude: float = Field(default=0.3, ge=0.0, le=1.0)

    # Frequency mode: anti-conditioning strategy
    frequency_mode: FrequencyMode = Field(default=FrequencyMode.FIXED)
    frequency_range_min_hz: float = Field(default=800.0, ge=500.0, le=4000.0)
    frequency_range_max_hz: float = Field(default=3500.0, ge=500.0, le=4000.0)
    frequency_presets: list[float] = Field(
        default=[1000.0, 1500.0, 2000.0, 2500.0, 3000.0],
    )
    vagal_center_hz: float = Field(default=900.0, ge=500.0, le=1500.0)
    vagal_spread_hz: float = Field(default=200.0, ge=50.0, le=500.0)

    # Envelope shape for fade-in (all guarantee anti-startle onset)
    envelope_type: str = Field(default="linear")

    # Pleasant tone shaping (harmonics + vibrato for warmth)
    pleasant: bool = Field(default=False)

    sample_rate: int = Field(default=44100, ge=8000, le=96000)
    play_combined: bool = Field(default=True)


class VisualConfig(BaseModel):
    """LED strip simulation parameters."""

    led_count: int = Field(default=8, ge=1, le=60)
    colour_amber: str = Field(default="#FFBF00")
    pulse_freq_hz: float = Field(default=1.0)
    chase_speed_ms: int = Field(default=80)
    fade_out_sec: float = Field(default=3.0)


class MQTTConfig(BaseModel):
    """MQTT broker configuration."""

    broker_host: str = Field(default="localhost")
    broker_port: int = Field(default=1883)
    topic_ring: str = Field(default="hushbell/ring")
    topic_status: str = Field(default="hushbell/status")
    topic_battery: str = Field(default="hushbell/battery")
    topic_config: str = Field(default="hushbell/config")
    topic_config_state: str = Field(default="hushbell/config/state")
    client_id: str = Field(default="hushbell-poc")


class BatteryConfig(BaseModel):
    """Battery simulation from spec: 1200 rings per charge."""

    max_rings: int = Field(default=1200)
    initial_charge: float = Field(default=1.0, ge=0.0, le=1.0)
    ring_drain: float = Field(default=1.0 / 1200)


class HushBellConfig(BaseModel):
    """Top-level configuration."""

    audio: AudioConfig = Field(default_factory=AudioConfig)
    visual: VisualConfig = Field(default_factory=VisualConfig)
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    battery: BatteryConfig = Field(default_factory=BatteryConfig)
    trigger_key: str = Field(default="<cmd>+<shift>+d")
    http_port: int = Field(default=8080)
