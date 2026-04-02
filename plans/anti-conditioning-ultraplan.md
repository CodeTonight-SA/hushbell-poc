# Ultraplan: Anti-Conditioning Frequency Randomisation

**Origin**: Alex (Guild) bug report — dogs learn to associate fixed 2,000Hz tone with door activity via classical conditioning (household movement cues).
**Thomas addendum**: randomised sounds should be pleasant ("phat beats", vagal phonemes).

## Problem Statement

The current HushBell plays a fixed 2,000Hz tone every ring. Even though the 500ms fade-in defeats the acoustic startle reflex, the dog can still learn the association:
1. Fixed 2,000Hz sound plays
2. Humans move briskly toward front door
3. Dog connects sound -> door activity (Pavlovian conditioning)
4. Dog starts barking/reacting to 2,000Hz tone

**Root cause**: frequency is constant across all rings, making it a reliable predictor.

## Solution: Configurable Frequency Randomisation with Guaranteed Fade-In

Break the classical conditioning loop by varying the secondary frequency per-ring, so the dog cannot form a stable sound-to-event association. The fade-in envelope MUST be applied regardless of frequency.

---

## Architecture

### New: FrequencyStrategy (Strategy Pattern)

```
FrequencyStrategy (protocol)
  |-- FixedFrequency(freq_hz)           # Current behaviour (backwards compat)
  |-- RandomFrequency(min_hz, max_hz)   # Uniform random per ring
  |-- PresetRotation(presets: list)      # Cycle through user-defined frequencies
  |-- VagalRange(center_hz, spread_hz)  # Pleasant vagal nerve resonance range
```

### Key Constraint (PARAMOUNT)
Every frequency strategy MUST produce output through `generate_tone()` which ALWAYS applies the fade-in envelope. Fade-in is non-negotiable -- it's the anti-startle mechanism.

---

## Implementation Phases (Fibonacci Wave: 1-2-3-5-8)

### Wave 1 (depth 1): Core frequency strategy + config
**Files**: `config.py`, `audio_engine.py`
**Deliverables**:
- Add `FrequencyMode` enum: `fixed`, `random`, `preset`, `vagal`
- Add frequency strategy fields to `AudioConfig`:
  - `frequency_mode: FrequencyMode = "fixed"` (backwards compatible)
  - `frequency_range_min_hz: float = 800.0`
  - `frequency_range_max_hz: float = 3500.0`
  - `frequency_presets: list[float] = [1000, 1500, 2000, 2500, 3000]`
  - `vagal_center_hz: float = 900.0` (vagal nerve sweet spot)
  - `vagal_spread_hz: float = 200.0`
- Add `resolve_secondary_freq(config: AudioConfig) -> float` function
  - `fixed`: returns `config.secondary_freq_hz` (current behaviour)
  - `random`: `random.uniform(min, max)`
  - `preset`: cycles through presets list (modulo ring count)
  - `vagal`: `random.gauss(center, spread)` clamped to safe range
- Modify `generate_secondary()` to call `resolve_secondary_freq()`
- **CRITICAL**: fade-in ALWAYS applied regardless of resolved frequency

**Tests**:
- Each strategy resolves to frequency within expected range
- Fade-in envelope applied for all modes
- Fixed mode produces identical behaviour to current implementation
- Random mode produces varying frequencies across 100 calls

**Breathing pause**: verify FFT peaks shift with mode changes

---

### Wave 2 (depth 2): Controller + ring history tracking
**Files**: `controller.py`
**Deliverables**:
- Track `frequency_used` in ring status dict
- Add ring counter for preset rotation state
- Log frequency used per ring for debugging
- `ring()` returns `{"ok": True, ..., "freq_hz": 1847.3}`

**Tests**:
- Controller ring status includes frequency
- Preset rotation cycles correctly
- Battery drain unchanged by frequency mode

**Breathing pause**: run full test suite

---

### Wave 3 (depth 3): CLI configuration + MQTT
**Files**: `__main__.py`, `mqtt_bridge.py`
**Deliverables**:
- CLI args: `--freq-mode {fixed,random,preset,vagal}`
- CLI args: `--freq-min`, `--freq-max`, `--freq-presets`
- MQTT status payload includes `freq_hz`
- MQTT config topic for remote frequency mode switching

**Tests**:
- CLI arg parsing for all frequency modes
- MQTT payload includes frequency data

**Breathing pause**: manual test with `--test --freq-mode random`

---

### Wave 4 (depth 5): Web UI frequency controls
**Files**: `web/index.html`
**Deliverables**:
- Frequency mode selector (dropdown: Fixed / Random / Preset / Vagal)
- Min/max range sliders (when Random mode selected)
- Preset chips (when Preset mode selected, clickable to add/remove)
- Vagal center/spread controls (when Vagal mode selected)
- FFT spectrum marker updates to show ACTUAL frequency used (dynamic, not hardcoded 2000Hz)
- Status row shows current frequency
- Web Audio oscillator reads from selected mode

**Tests**:
- Visual verification (manual)
- FFT marker moves with frequency
- All modes produce audible pleasant output

**Breathing pause**: full integration test, screenshot for Guild

---

### Wave 5 (depth 8): Spectrum visualiser + Thomas's "phat beats"
**Files**: `spectrum.py`, new `pleasant_tones.py`
**Deliverables**:
- Dynamic spectrum marker (moves with actual frequency, not hardcoded)
- Pleasant tone shaping: soft attack, slight vibrato for warmth
- Harmonic layering option: fundamental + soft 3rd harmonic for richness
- Envelope options beyond linear fade-in: sine fade, exponential fade
- `--envelope {linear,sine,exponential}` CLI option
- Documentation: which frequencies are most pleasant and why (vagal phoneme research notes)

**Tests**:
- FFT verifies harmonic content when layering enabled
- Envelope shape verification (sine curve check)
- All envelope types still defeat startle reflex (onset < threshold)

---

## RSI Sprint Configuration

### Mode Stack (Top 5, auto-selected)
1. **code** -- primary implementation mode (SOLID, design principles, test-first)
2. **testing** -- QA lifecycle with Devil's Advocate framework (FFT verification critical)
3. **architect** -- strategy pattern design, config schema decisions
4. **analysis** -- frequency range research, vagal phoneme investigation
5. **security** -- ensure no sound can be generated that bypasses fade-in (PARAMOUNT safety)

### Fibonacci Wave Depth Protocol
```
Wave 1: batch=1 (core strategy)     -> breathe
Wave 2: batch=2 (controller+MQTT)   -> breathe
Wave 3: batch=3 (CLI+integration)   -> breathe
Wave 4: batch=5 (web UI)            -> breathe
Wave 5: batch=8 (spectrum+pleasant) -> breathe + full measurement
```

### Broly-Auto Configuration
- Framework: convergence-first (each wave must pass criterion before next)
- Criterion per wave: "all tests pass AND fade-in verified AND no regression"
- Max iterations per wave: 3 (then escalate)
- Memory type: cross-wave (learnings from wave N inform wave N+1)

### Convergence Criteria
```
converge(
  task="Anti-conditioning frequency randomisation",
  criterion="ALL of: (1) 4 frequency modes working with tests, (2) fade-in ALWAYS applied regardless of mode, (3) CLI + web UI expose controls, (4) FFT verification proves frequency varies, (5) backwards compatible (fixed mode = current behaviour)",
  max_depth=11
)
```

### Quality Gates
- **Gate 0 (JIT)**: correct-by-construction during writing
- **Gate 1 (Pre-commit)**: all tests pass, CC < 15 per function
- **Gate 2 (Post-commit)**: FFT verification of frequency accuracy
- **Safety gate**: NO code path can generate audio without fade-in envelope

### Hypotheses to Register
- **H_HUSH_01**: "Random frequency mode prevents dogs from learning the sound-door association" (metric: behavioural observation over 2 weeks, prediction: barking rate unchanged from baseline)
- **H_HUSH_02**: "Vagal range frequencies (800-1100Hz) are rated more pleasant than random full-range by 3+ human testers" (metric: preference survey, prediction: >66% prefer vagal)
- **H_HUSH_03**: "All 4 frequency modes maintain sub-20ms onset via fade-in" (metric: FFT onset analysis, prediction: 0ms at t=0 for all modes)

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Dog learns movement pattern regardless of sound | Out of scope -- HushBell addresses auditory conditioning only |
| Some frequencies unpleasant to humans | Vagal mode defaults to researched pleasant range; presets are user-curated |
| Fade-in accidentally bypassed in new code path | Safety gate: `generate_tone()` is the ONLY audio generation function; all paths go through it |
| Random frequency hits dog-audible range (<67Hz) | Config validation: `frequency_range_min_hz >= 500Hz` (well above canine floor) |
| Web Audio API frequency precision | Web Audio oscillators are precise to sub-Hz; not a concern |

## Files Changed (Summary)

| File | Change Type |
|------|------------|
| `src/hushbell/config.py` | Modify -- add frequency mode fields |
| `src/hushbell/audio_engine.py` | Modify -- add resolve_secondary_freq(), update generate_secondary() |
| `src/hushbell/controller.py` | Modify -- track freq in ring status |
| `src/hushbell/__main__.py` | Modify -- add CLI args |
| `src/hushbell/mqtt_bridge.py` | Modify -- freq in MQTT payload |
| `src/hushbell/spectrum.py` | Modify -- dynamic frequency markers |
| `src/hushbell/pleasant_tones.py` | New -- harmonic layering + envelope shapes |
| `web/index.html` | Modify -- frequency mode UI controls |
| `tests/test_audio_engine.py` | Modify -- add frequency strategy tests |
| `tests/test_frequency_strategy.py` | New -- dedicated strategy tests |
| `CLAUDE.md` | Modify -- document new parameters |
