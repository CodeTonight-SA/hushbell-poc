"""HushBell POC entry point.

Usage:
    python -m hushbell              # Interactive (press Enter to ring)
    python -m hushbell --test       # Single ring test
    python -m hushbell --web        # HTTP trigger server
"""
import argparse
import logging
import sys

from .config import HushBellConfig
from .controller import HushBellController


def _run_interactive(ctrl: HushBellController) -> None:
    """Interactive keyboard mode -- press Enter to ring."""
    print("HushBell POC ready. Press Enter to ring, Ctrl+C to quit.")
    try:
        while True:
            input()
            print(f"  {ctrl.ring()}")
    except KeyboardInterrupt:
        print(f"\nStats: {ctrl.stats()}")


def _build_controller(args: argparse.Namespace) -> HushBellController:
    """Build controller from CLI args (DI-friendly factory)."""
    config = HushBellConfig(http_port=args.port) if args.web else HushBellConfig()
    ctrl = HushBellController(config, visual=args.visual)
    if not args.no_mqtt:
        ctrl.connect_mqtt()
    return ctrl


def main() -> int:
    parser = argparse.ArgumentParser(description="HushBell POC")
    parser.add_argument("--test", action="store_true", help="Single ring test")
    parser.add_argument("--web", action="store_true", help="Start HTTP trigger")
    parser.add_argument("--no-mqtt", action="store_true", help="Skip MQTT")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--visual", action="store_true", help="Show pygame LED strip simulator")
    parser.add_argument("--spectrum", action="store_true", help="Show FFT spectrum after ring")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    ctrl = _build_controller(args)

    if args.test:
        print(f"Ring result: {ctrl.ring(spectrum=args.spectrum)}")
        return 0
    if args.web:
        from .triggers.http_trigger import start_server
        start_server(ctrl, port=ctrl.config.http_port)
        return 0

    _run_interactive(ctrl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
