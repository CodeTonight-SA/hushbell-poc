# HushBell POC

Dog-friendly smart doorbell -- laptop-first proof of concept.
Thomas Frumkin's design from the AI Craftspeople Guild.

## Architecture

- `src/hushbell/controller.py` -- Main orchestrator (ring lifecycle)
- `src/hushbell/audio_engine.py` -- 40Hz + variable-frequency tone generation with envelopes
- `src/hushbell/pleasant_tones.py` -- Harmonic layering + vibrato for warm tones
- `src/hushbell/visual_engine.py` -- WS2812B LED strip simulation (pygame)
- `src/hushbell/notification.py` -- Platform-specific notification facade
- `src/hushbell/mqtt_bridge.py` -- MQTT pub/sub (paho-mqtt)
- `src/hushbell/battery_sim.py` -- 1200 rings/charge state machine
- `src/hushbell/config.py` -- Pydantic settings with frequency strategy config
- `src/hushbell/spectrum.py` -- Real-time FFT visualiser with dynamic markers
- `src/hushbell/triggers/` -- Input sources (keyboard, MQTT, HTTP)
- `tests/` -- Pytest suite with FFT verification (87 tests)
- `web/` -- Browser demo (Web Audio API, frequency controls); `docs/index.html` is kept identical

## Design System — Swiss Nihilism (ENTER Konsult)

`web/index.html` and `docs/index.html` are **always identical**. Both follow Swiss Nihilism design language:

- **No border-radius.** 0px on every element.
- **No box-shadow.** Borders carry all depth signalling.
- **Monospace hierarchy.** Labels: `'Courier New', monospace; font-size: 11-13px; text-transform: uppercase; letter-spacing: 0.08-0.12em`.
- **System fonts for body.** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif`.
- **Orange accent.** `#ea580c` (light/dark), `#996F00` (neutral). Never deviate.
- **All colours via CSS custom properties.** `--bg`, `--surface`, `--border`, `--text`, `--text-muted`, `--accent`, `--amber`.

### Themes

| Theme | `--bg` | `--accent` |
|-------|--------|-----------|
| `light` | `#EAEAEA` | `#ea580c` |
| `neutral` | `#F0EDE8` | `#996F00` |
| `dark` | `#1e1e1e` | `#ea580c` |

Theme stored in `localStorage`, auto-detected from `prefers-color-scheme` on first visit.

### Emergent UI Pattern

Cards hidden (`opacity:0; max-height:0`) until behaviour rules fire:

| Card | Trigger |
|------|---------|
| Suggestion | 3 s idle, 0 rings |
| Battery Projection | 3+ rings |
| Frequency Education | Scroll to spectrum + 1+ ring |
| Comparison | 5+ rings |

Rules: `EMERGENT_RULES` array with `condition(ctx) / action(ctx)` pairs, evaluated on ring, scroll, and a 2 s interval.

### Web Audio Patterns

- Signal chain: `AudioContext → OscillatorNode → GainNode → AnalyserNode → destination`
- FFT: `fftSize = 2048`, `smoothingTimeConstant = 0.75`, drawn at 60 fps via `requestAnimationFrame`
- Frequency resolution mirrors `src/hushbell/config.py`: fixed / random / preset / vagal modes
- Envelopes: linear, approximated-sine, approximated-exponential — all guarantee zero onset (anti-startle safety guarantee)

## Key Parameters

- Primary frequency: 40Hz (below 67Hz dog hearing floor)
- Secondary frequency: configurable (defeats classical conditioning)
- Frequency modes: fixed, random, preset, vagal
- Fade-in: ALWAYS applied (anti-startle safety guarantee)
- Envelope types: linear, sine, exponential
- Battery: 1200 rings/charge (simulated)
- MQTT topics: hushbell/ring, hushbell/status, hushbell/battery, hushbell/config, hushbell/config/state
- Visual: Warm amber (#FFBF00), WS2812B simulation

## Frequency Modes (Anti-Conditioning)

| Mode | Behaviour | Use Case |
|------|-----------|----------|
| `fixed` | Original 2000Hz (default) | Backwards compatible |
| `random` | Uniform random 800-3500Hz | Maximum anti-conditioning |
| `preset` | Rotate through user list | Curated pleasant tones |
| `vagal` | Gaussian ~900Hz +/- 200Hz | Vagal nerve resonance (pleasant) |

## Commands

```bash
python -m hushbell                          # Interactive (fixed mode)
python -m hushbell --freq-mode random       # Random frequency per ring
python -m hushbell --freq-mode vagal        # Pleasant vagal range
python -m hushbell --freq-mode preset --freq-presets 800,1000,1500
python -m hushbell --envelope sine          # Smoother fade-in curve
python -m hushbell --pleasant               # Harmonic layering + vibrato
python -m hushbell --web                    # Start HTTP trigger server
python -m hushbell --test --spectrum        # Single ring with FFT display
PYTHONPATH=src pytest tests/                # Run tests (87 tests)

# MQTT runtime config (publish to broker):
mosquitto_pub -t hushbell/config -m '{"frequency_mode": "vagal", "pleasant": true}'
mosquitto_pub -t hushbell/config -m '{"envelope_type": "sine"}'
```

## Principles

KISS, YAGNI, DRY. Laptop-first, cross-platform later.
