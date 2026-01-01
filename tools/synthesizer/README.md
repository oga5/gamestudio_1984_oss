# Python Synthesizer

A powerful, JSON-driven audio synthesizer for generating chiptune music and sound effects.

## Features

- **Multi-track sequencing**: Drums, bass, melody, chords, PCM samples, and FM synthesis
- **16-step pattern sequencer**: Industry-standard step sequencer interface
- **Multiple waveforms**: Sine, sawtooth, triangle, square oscillators
- **Drum machine**: Kick, Snare, Hi-Hat, Clap
- **PCM instruments**: Piano, Electric Piano, Organ, Strings
- **FM synthesis**: Classic FM modulation for rich timbres
- **Chord support**: Built-in chord definitions (C, Dm, Em, F, G, Am, Bdim, C7)

---

## Installation

```bash
cd tools/synthesizer
pip install numpy  # Required dependency
```

---

## Quick Start

### Generate audio from a JSON pattern:

```bash
python synth.py examples/simple_beat.json -o output.wav
```

### Command-line options:

```bash
# Specify output filename
python synth.py pattern.json -o my_sound.wav

# Set sample rate (default: 44100 Hz)
python synth.py pattern.json --sample-rate 48000

# Quiet mode (no info output)
python synth.py pattern.json -q

# Show pattern info without generating audio
python synth.py pattern.json --info-only
```

---

## JSON Pattern Format

### Basic Structure

```json
{
  "version": "1.0",
  "bpm": 120,
  "patternLength": 16,
  "masterVolume": 0.7,
  "tracks": {
    "track_name": {
      "muted": false,
      "volume": 0.8,
      "data": { ... }
    }
  }
}
```

### Global Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | string | "1.0" | Pattern format version |
| `bpm` | number | 120 | Tempo in beats per minute |
| `patternLength` | number | 16 | Number of steps in the pattern (8 or 16 recommended) |
| `masterVolume` | number | 0.7 | Global volume multiplier (0.0 to 1.0) |

---

## Track Types

### 1. Drum Track

Generate classic drum sounds: Kick, Snare, Hi-Hat, Clap.

**Track Configuration:**

```json
"drum": {
  "muted": false,
  "volume": 0.8,
  "data": {
    "Kick": [true, false, false, false, true, false, false, false, ...],
    "Snare": [false, false, true, false, false, false, true, false, ...],
    "Hi-Hat": [true, true, true, true, true, true, true, true, ...],
    "Clap": [false, false, false, false, true, false, false, false, ...]
  }
}
```

**Available Drum Sounds:**
- `Kick`: Deep bass drum (60 Hz, 0.5s decay)
- `Snare`: Snare with noise (200 Hz, 0.15s decay)
- `Hi-Hat`: Crisp hi-hat (8000 Hz, 0.05s decay, noise-based)
- `Clap`: Hand clap (1000 Hz, 0.1s decay, noise-based)

**Tips for Game Sound Effects:**
- **Explosion**: `Kick` with high volume
- **Hit/Impact**: `Snare` or `Clap`
- **Menu Select**: Single `Hi-Hat` step

---

### 2. Oscillator Tracks (bass, melody, chord)

Generate tonal sounds using synthesizer waveforms.

**Track Configuration:**

```json
"bass": {
  "muted": false,
  "volume": 0.7,
  "waveform": "sawtooth",
  "data": {
    "C2": [true, false, false, false, true, false, false, false, ...],
    "D2": [false, false, true, false, false, false, false, false, ...],
    "E2": [false, false, false, false, false, false, true, false, ...]
  }
}
```

**Required Fields:**
- `waveform`: Oscillator type (see below)
- `data`: Note patterns (use note names like "C2", "A4", "C5")

**Available Waveforms:**

| Waveform | Sound Character | Best For |
|----------|----------------|----------|
| `sine` | Pure, soft tone | Melodies, soft leads, simple tones |
| `sawtooth` | Bright, buzzy, rich harmonics | Bass lines, aggressive leads |
| `triangle` | Mellow, hollow | Chords, pads, retro melodies |
| `square` | Hollow, video-game-like | Chiptune melodies, retro bass |

**Available Notes:**

```
Low Octave:   C2, D2, E2, F2, G2, A2, B2
Mid Octave:   C3, D3, E3, F3, G3, A3, Bb3, B3
High Octave:  C4, D4, E4, F4, G4, A4, B4, C5
```

**Chord Support:**

Instead of individual notes, you can trigger full chords:

```json
"chord": {
  "volume": 0.6,
  "waveform": "triangle",
  "data": {
    "C": [true, false, false, false, false, false, false, false, ...],
    "F": [false, false, false, false, true, false, false, false, ...],
    "G": [false, false, false, false, false, false, false, false, ...]
  }
}
```

**Available Chords:**
- `C`: C major (C3, E3, G3)
- `Dm`: D minor (D3, F3, A3)
- `Em`: E minor (E3, G3, B3)
- `F`: F major (F3, A3, C4)
- `G`: G major (G3, B3, D4)
- `Am`: A minor (A3, C4, E4)
- `Bdim`: B diminished (B3, D4, F4)
- `C7`: C dominant 7th (C3, E3, G3, Bb3)

---

### 3. PCM Track

Use pre-rendered instrument samples with pitch shifting.

**Track Configuration:**

```json
"pcm": {
  "muted": false,
  "volume": 0.7,
  "sound": "piano",
  "data": {
    "C4": [true, false, false, false, false, false, false, false, ...],
    "E4": [false, false, true, false, false, false, false, false, ...],
    "G4": [false, false, false, false, true, false, false, false, ...]
  }
}
```

**Required Fields:**
- `sound`: Instrument type (see below)

**Available PCM Instruments:**

| Instrument | Description | Attack | Decay |
|------------|-------------|--------|-------|
| `piano` | Acoustic piano with harmonics | Fast | Medium (3s) |
| `epiano` | Electric piano | Fast | Fast (2s) |
| `organ` | Sustained organ | Medium | Sustained |
| `strings` | String ensemble | Slow (0.3s) | Slow |

**Best For:**
- `piano`: Melodic game music, menu themes
- `epiano`: Upbeat, energetic tracks
- `organ`: Retro arcade vibes
- `strings`: Emotional, cinematic moments

---

### 4. FM Synthesis Track

Generate complex, metallic timbres using frequency modulation.

**Track Configuration:**

```json
"fm": {
  "muted": false,
  "volume": 0.7,
  "ratio": 2.0,
  "depth": 500,
  "data": {
    "C4": [true, false, false, false, false, false, false, false, ...],
    "E4": [false, false, true, false, false, false, false, false, ...]
  }
}
```

**Required Fields:**
- `ratio`: Modulator frequency ratio (1.0 to 5.0 typical)
  - `1.0`: Subtle vibrato
  - `2.0`: Bell-like tones
  - `3.0-5.0`: Metallic, inharmonic sounds
- `depth`: Modulation depth in Hz (100 to 1000 typical)
  - Lower (100-300): Subtle timbre change
  - Higher (500-1000): Aggressive, harsh tones

**Best For:**
- Electric bass (ratio: 2.0, depth: 300)
- Bells/chimes (ratio: 3.5, depth: 800)
- Sci-fi/alien sounds (ratio: 4.0+, depth: 1000)

---

## Complete Examples

### Example 1: Simple 8-Bit Beat

Perfect for retro game background music.

```json
{
  "version": "1.0",
  "bpm": 140,
  "patternLength": 8,
  "masterVolume": 0.7,
  "tracks": {
    "drum": {
      "muted": false,
      "volume": 0.8,
      "data": {
        "Kick": [true, false, true, false, true, false, true, false],
        "Snare": [false, false, true, false, false, false, true, false],
        "Hi-Hat": [true, true, true, true, true, true, true, true]
      }
    },
    "bass": {
      "muted": false,
      "volume": 0.7,
      "waveform": "square",
      "data": {
        "C2": [true, false, false, false, true, false, false, false],
        "G2": [false, false, true, false, false, false, true, false]
      }
    },
    "melody": {
      "muted": false,
      "volume": 0.6,
      "waveform": "square",
      "data": {
        "C4": [true, false, false, false, false, false, false, false],
        "D4": [false, true, false, false, false, false, false, false],
        "E4": [false, false, true, false, false, false, false, false],
        "G4": [false, false, false, false, true, false, false, false]
      }
    }
  }
}
```

**Use Case**: Main gameplay loop, energetic arcade action

---

### Example 2: Laser Sound Effect

Short, punchy laser zap for shooting games.

```json
{
  "version": "1.0",
  "bpm": 240,
  "patternLength": 4,
  "masterVolume": 0.8,
  "tracks": {
    "melody": {
      "muted": false,
      "volume": 1.0,
      "waveform": "sine",
      "data": {
        "C5": [true, false, false, false],
        "C4": [false, true, false, false]
      }
    }
  }
}
```

**Duration**: ~100ms (fast BPM + short pattern)
**Tips**: Increase BPM for shorter sounds, use pitch sweep (high→low) for "zap" effect

---

### Example 3: Explosion Sound

Deep boom with rumble.

```json
{
  "version": "1.0",
  "bpm": 120,
  "patternLength": 4,
  "masterVolume": 0.9,
  "tracks": {
    "drum": {
      "muted": false,
      "volume": 1.0,
      "data": {
        "Kick": [true, true, false, false],
        "Snare": [false, true, true, false]
      }
    },
    "bass": {
      "muted": false,
      "volume": 0.8,
      "waveform": "sawtooth",
      "data": {
        "C2": [true, false, false, false]
      }
    }
  }
}
```

**Use Case**: Enemy destruction, impact effects

---

### Example 4: Menu Select Sound

Short, pleasant confirmation sound.

```json
{
  "version": "1.0",
  "bpm": 300,
  "patternLength": 2,
  "masterVolume": 0.6,
  "tracks": {
    "melody": {
      "muted": false,
      "volume": 0.8,
      "waveform": "sine",
      "data": {
        "C5": [true, false],
        "E5": [false, true]
      }
    }
  }
}
```

**Use Case**: UI interactions, button clicks

---

### Example 5: Power-Up Sound

Ascending arpeggio for collecting items.

```json
{
  "version": "1.0",
  "bpm": 200,
  "patternLength": 8,
  "masterVolume": 0.7,
  "tracks": {
    "melody": {
      "muted": false,
      "volume": 0.8,
      "waveform": "square",
      "data": {
        "C4": [true, false, false, false, false, false, false, false],
        "E4": [false, true, false, false, false, false, false, false],
        "G4": [false, false, true, false, false, false, false, false],
        "C5": [false, false, false, true, false, false, false, false]
      }
    }
  }
}
```

**Use Case**: Item collection, level up, achievement unlocked

---

### Example 6: Background Music Loop

Full 16-step house music pattern (see `examples/presets/house.json`).

---

## Tips for Game Developers

### Sound Effect Design

| Game Event | Recommended Pattern | Notes |
|------------|-------------------|-------|
| **Player Jump** | Single hi-hat or short sine wave (C4→C3) | Fast BPM (300+), 2 steps |
| **Player Shoot** | Sine wave pitch sweep (C5→C3) | Fast decay, 2-4 steps |
| **Enemy Hit** | Snare + low sawtooth bass | 2-4 steps |
| **Enemy Death** | Kick + Snare combo with sawtooth | 4-8 steps |
| **Coin Collect** | Ascending notes (C4→E4→G4) | Square wave, 4 steps |
| **Power-Up** | Ascending arpeggio + triangle wave | 8 steps, major chord |
| **Game Over** | Descending bass line (C3→A2→F2→C2) | Slow, sawtooth wave |
| **Victory** | Major chord progression (C→F→G→C) | Triangle wave, 16 steps |

### Volume Guidelines

- **Master Volume**: 0.6-0.8 for music, 0.8-1.0 for sound effects
- **Track Volume**:
  - Drums: 0.7-0.9
  - Bass: 0.6-0.8
  - Melody: 0.5-0.7
  - Chords: 0.4-0.6

### Pattern Length for Sound Effects

- **Very Short (UI)**: 1-2 steps, BPM 300+
- **Short (Actions)**: 2-4 steps, BPM 200-300
- **Medium (Events)**: 4-8 steps, BPM 120-200
- **Long (Music)**: 16 steps, BPM 100-140

---

## Common Issues & Solutions

### Sound is too quiet
- Increase `masterVolume` (max 1.0)
- Increase track `volume` (max 1.0)
- Use `--no-normalize` flag if auto-normalization is reducing volume

### Sound is clipping/distorting
- Decrease `masterVolume` to 0.5-0.6
- Reduce number of simultaneous notes
- Lower track volumes

### Sound effect is too long
- Increase BPM (e.g., 300 for very short sounds)
- Reduce `patternLength` (e.g., 2-4 steps)

### Drums sound too harsh
- Lower drum track `volume` to 0.5-0.7
- Use fewer simultaneous drum hits per step

### Notes are out of tune
- Double-check note names (e.g., "C4" not "c4" or "C-4")
- Use exact note names from the NOTE_FREQUENCIES list above

---

## Advanced: Creating Multi-Sound Patterns

You can create multiple sounds in one pattern by using different sections:

```json
{
  "bpm": 120,
  "patternLength": 16,
  "tracks": {
    "melody": {
      "volume": 0.7,
      "waveform": "square",
      "data": {
        "C4": [true, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false],
        "E4": [false, false, false, false, true, false, false, false, false, false, false, false, false, false, false, false],
        "G4": [false, false, false, false, false, false, false, false, true, false, false, false, false, false, false, false]
      }
    }
  }
}
```

This creates 3 distinct sounds spaced 4 steps apart.

---

## File Structure

```
tools/synthesizer/
├── synth.py                  # CLI tool
├── synthesizer/
│   ├── audio_engine.py       # Sound generation engine
│   ├── sequencer.py          # Pattern sequencer
│   └── wav_writer.py         # WAV file output
├── examples/
│   ├── simple_beat.json      # Basic 8-step example
│   └── presets/
│       └── house.json        # Full 16-step music loop
└── README.md                 # This file
```

---

## License

This synthesizer is part of the DeepAgents game development toolkit.

---

## Credits

Built for the "Arcade Spirit" - bringing 1980s Japanese arcade game audio to modern AI-generated games.
