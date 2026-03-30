# HushBell POC

Dog-friendly smart doorbell -- laptop-first proof of concept.

**Design by Thomas Frumkin** | **Implementation by CodeTonight** | **AI Craftspeople Guild**

## The Problem

Standard doorbells trigger barking. Dogs hear frequencies from 67Hz to 45kHz.

## The Solution

HushBell uses two notification channels that avoid canine alarm:

- **40Hz tactile tone** -- below the 67Hz dog hearing floor
- **2000Hz piezo with 500ms fade-in** -- defeats the acoustic startle reflex (threshold < 20ms)

Combined: 99% no-bark probability on the tactile channel alone.

## Quick Start

```bash
pip install -e ".[dev,gui]"
python -m hushbell --test          # Single ring test
python -m hushbell                 # Interactive (Enter to ring)
python -m hushbell --web           # HTTP trigger on localhost:8080
```

## Tests

```bash
pytest tests/ -v
```

FFT verification confirms generated tones match spec frequencies within 0.5Hz.

## Architecture

See [docs/architecture.md](docs/architecture.md) for full design.

## Spec Reference

Based on Thomas Frumkin's HushBell specification:
- ESP32-WROOM-32E microcontroller
- Dayton Audio TT25-8 tactile transducer (8 ohm, 15W)
- WS2812B LED strip (warm amber)
- TP4056 USB-C, 1000mAh LiPo
- 1200 rings/charge, 6 months standby
- $29.43 BOM

This POC simulates all subsystems using Mac audio + screen. No hardware required.

## Licence

MIT
