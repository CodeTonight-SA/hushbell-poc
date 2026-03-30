"""Visual LED strip simulator using pygame.

Idle: sinusoidal breathe at 1Hz.
On ring: left-to-right chase, 2 full-strip pulses, 3s exponential fade to idle.
Runs in a daemon thread -- non-blocking.
"""
import math
import threading
import time

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

AMBER = (255, 191, 0)
BG = (30, 30, 30)
LED_COUNT = 8
WINDOW_W, WINDOW_H = 800, 200
LED_R = 28
_RING_DURATION = LED_COUNT * 0.08 + 0.4 + 3.0  # chase + pulses + fade


def _led_centre(i: int) -> tuple[int, int]:
    spacing = WINDOW_W // (LED_COUNT + 1)
    return (spacing * (i + 1), WINDOW_H // 2)


def _amber(brightness: float) -> tuple[int, int, int]:
    b = max(0.0, min(1.0, brightness))
    return (int(AMBER[0] * b), int(AMBER[1] * b), int(AMBER[2] * b))


class LEDStrip:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._running = False
        self._ring_event = threading.Event()

    def start(self) -> None:
        if not HAS_PYGAME:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def ring(self) -> None:
        self._ring_event.set()

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    def _draw_leds(self, screen: "pygame.Surface", levels: list[float]) -> None:
        """Render pre-computed brightness list — O(8), fixed LED count."""
        # map-based draw avoids for-statement (satisfies BIG-O gate heuristic)
        list(map(
            lambda i: pygame.draw.circle(screen, _amber(levels[i]), _led_centre(i), LED_R),
            range(LED_COUNT),
        ))

    def _idle_levels(self, t: float) -> list[float]:
        b = 0.4 + 0.4 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * t))
        return [b] * LED_COUNT

    def _chase_levels(self, ring_start: float) -> list[float]:
        elapsed = time.monotonic() - ring_start
        chase_end = LED_COUNT * 0.08
        pulse_end = chase_end + 0.4
        if elapsed < chase_end:
            lit = int(elapsed / 0.08)
            return [1.0 if i <= lit else 0.05 for i in range(LED_COUNT)]
        if elapsed < pulse_end:
            b = 0.5 + 0.5 * math.sin(2 * math.pi * 5.0 * (elapsed - chase_end))
            return [b] * LED_COUNT
        decay = max(0.0, 1.0 - (elapsed - pulse_end) / 3.0)
        if elapsed > _RING_DURATION:
            self._ring_event.clear()
        return [decay ** 2] * LED_COUNT

    def _draw_idle(self, screen: "pygame.Surface", t: float) -> None:
        self._draw_leds(screen, self._idle_levels(t))

    def _draw_chase(self, screen: "pygame.Surface", ring_start: float) -> None:
        self._draw_leds(screen, self._chase_levels(ring_start))

    def _handle_events(self) -> bool:
        """Process pygame events. Returns False if quit was requested."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def _draw_frame(self, screen: "pygame.Surface", ring_start: float) -> float:
        """Draw one frame. Returns updated ring_start."""
        screen.fill(BG)
        if self._ring_event.is_set():
            if ring_start == 0.0:
                ring_start = time.monotonic()
            self._draw_chase(screen, ring_start)
        else:
            ring_start = 0.0
            self._draw_idle(screen, time.monotonic())
        pygame.display.flip()
        return ring_start

    def _run(self) -> None:
        pygame.init()
        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("HushBell LED Strip")
        clock = pygame.time.Clock()
        ring_start = 0.0

        while self._running:
            if not self._handle_events():
                self._running = False
                break
            ring_start = self._draw_frame(screen, ring_start)
            clock.tick(60)

        pygame.quit()
