"""HushBell configuration -- matches Thomas Frumkin's spec parameters."""
from pydantic import BaseModel, Field


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
