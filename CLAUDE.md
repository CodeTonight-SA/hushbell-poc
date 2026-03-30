# HushBell POC

Dog-friendly smart doorbell -- laptop-first proof of concept.
Thomas Frumkin's design from the AI Craftspeople Guild.

## Architecture

- `src/hushbell/controller.py` -- Main orchestrator (ring lifecycle)
- `src/hushbell/audio_engine.py` -- 40Hz + 2kHz tone generation with envelopes
- `src/hushbell/visual_engine.py` -- WS2812B LED strip simulation (pygame)
- `src/hushbell/notification.py` -- Platform-specific notification facade
- `src/hushbell/mqtt_bridge.py` -- MQTT pub/sub (paho-mqtt)
- `src/hushbell/battery_sim.py` -- 1200 rings/charge state machine
- `src/hushbell/config.py` -- Pydantic settings matching spec parameters
- `src/hushbell/spectrum.py` -- Real-time FFT visualiser for demo proof
- `src/hushbell/triggers/` -- Input sources (keyboard, MQTT, HTTP)
- `tests/` -- Pytest suite with FFT verification
- `web/` -- Browser demo (Web Audio API, Phase 2)
- `docs/` -- Architecture, roadmap, spec mapping

## Key Parameters (from Thomas's spec)

- Primary frequency: 40Hz (below 67Hz dog hearing floor)
- Secondary frequency: 2000Hz with 500ms fade-in (defeats startle reflex)
- Battery: 1200 rings/charge (simulated)
- MQTT topics: hushbell/ring, hushbell/status, hushbell/battery
- Visual: Warm amber (#FFBF00), WS2812B simulation
- BOM target: $29.43

## Commands

```bash
python -m hushbell              # Run the POC
python -m hushbell --web        # Start HTTP trigger server
python -m pytest tests/         # Run tests
```

## Principles

KISS, YAGNI, DRY. Laptop-first, cross-platform later.
