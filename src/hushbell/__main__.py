"""HushBell POC entry point.

Usage:
    python -m hushbell                          # Interactive (press Enter to ring)
    python -m hushbell --test                   # Single ring test
    python -m hushbell --freq-mode random       # Random frequency per ring
    python -m hushbell --freq-mode vagal        # Pleasant vagal range tones
    python -m hushbell --web                    # HTTP trigger server
"""
import argparse
import logging
import sys

from .config import AudioConfig, FrequencyMode, HushBellConfig
from .controller import HushBellController


def _run_interactive(ctrl: HushBellController) -> None:
    """Interactive keyboard mode -- press Enter to ring."""
    mode = ctrl.config.audio.frequency_mode.value
    print(f"HushBell POC ready (freq mode: {mode}). Press Enter to ring, Ctrl+C to quit.")
    try:
        while True:
            input()
            result = ctrl.ring()
            freq_info = f" @ {result.get('freq_hz', '?')}Hz" if result.get("ok") else ""
            print(f"  {result}{freq_info}")
    except KeyboardInterrupt:
        print(f"\nStats: {ctrl.stats()}")


def _build_audio_config(args: argparse.Namespace) -> AudioConfig:
    """Build AudioConfig from CLI frequency args."""
    kwargs: dict = {}
    if args.freq_mode:
        kwargs["frequency_mode"] = FrequencyMode(args.freq_mode)
    if args.freq_min is not None:
        kwargs["frequency_range_min_hz"] = args.freq_min
    if args.freq_max is not None:
        kwargs["frequency_range_max_hz"] = args.freq_max
    if args.freq_presets:
        kwargs["frequency_presets"] = [float(f) for f in args.freq_presets.split(",")]
    if args.envelope:
        kwargs["envelope_type"] = args.envelope
    return AudioConfig(**kwargs)


def _build_controller(args: argparse.Namespace) -> HushBellController:
    """Build controller from CLI args (DI-friendly factory)."""
    audio_config = _build_audio_config(args)
    config = HushBellConfig(audio=audio_config, http_port=args.port)
    ctrl = HushBellController(config, visual=args.visual)
    if not args.no_mqtt:
        ctrl.connect_mqtt()
    return ctrl


def main() -> int:
    parser = argparse.ArgumentParser(description="HushBell POC -- dog-friendly smart doorbell")
    parser.add_argument("--test", action="store_true", help="Single ring test")
    parser.add_argument("--web", action="store_true", help="Start HTTP trigger")
    parser.add_argument("--no-mqtt", action="store_true", help="Skip MQTT")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--visual", action="store_true", help="Show pygame LED strip simulator")
    parser.add_argument("--spectrum", action="store_true", help="Show FFT spectrum after ring")

    freq_group = parser.add_argument_group("frequency anti-conditioning")
    freq_group.add_argument(
        "--freq-mode",
        choices=["fixed", "random", "preset", "vagal"],
        default="fixed",
        help="Frequency selection strategy (default: fixed)",
    )
    freq_group.add_argument("--freq-min", type=float, help="Min frequency for random mode (Hz)")
    freq_group.add_argument("--freq-max", type=float, help="Max frequency for random mode (Hz)")
    freq_group.add_argument("--freq-presets", type=str, help="Comma-separated preset frequencies (Hz)")
    freq_group.add_argument(
        "--envelope",
        choices=["linear", "sine", "exponential"],
        default="linear",
        help="Fade-in envelope shape (default: linear)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    ctrl = _build_controller(args)

    if args.test:
        result = ctrl.ring(spectrum=args.spectrum)
        print(f"Ring result: {result}")
        return 0
    if args.web:
        from .triggers.http_trigger import start_server
        start_server(ctrl, port=ctrl.config.http_port)
        return 0

    _run_interactive(ctrl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
