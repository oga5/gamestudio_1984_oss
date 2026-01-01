# Python Synthesizer - Comprehensive Guide

For basic usage, see [README.md](./README.md). This guide covers detailed track configuration, sound design patterns, and FM synthesis techniques.

---

## JSON Pattern Format Details

### Global Parameters

```json
{
  "version": "1.0",
  "bpm": 120,              // Tempo (60-300, default: 120)
  "patternLength": 16,     // Number of steps (2-32, default: 16)
  "masterVolume": 0.7,     // Master volume (0.0-1.0)
  "tracks": { ... }
}
```

**BPM Guidelines:**
- **60-100**: Slow, suitable for background music
- **120-150**: Standard tempo, suitable for gameplay
- **160-200**: Fast, suitable for action sequences
- **240+**: Very fast, suitable for sound effects

**patternLength:**
- **2-4**: Short SFX (100-200ms)
- **8-16**: Standard music (1-8 seconds)
- **32**: Long BGM (20+ seconds)

---

## Track Types and Configuration

### 1. Drum Track

Real-time drum sound generation. No additional configuration required.

```json
"drum": {
  "muted": false,
  "volume": 0.8,
  "data": {
    "Kick": [true, false, false, false, ...],
    "Snare": [false, false, true, false, ...],
    "Hi-Hat": [true, true, true, true, ...],
    "Clap": [false, false, false, false, ...]
  }
}
```

**Available Drum Sounds:**

| Drum | Frequency | Decay | Purpose |
|------|-----------|-------|---------|
| `Kick` | 60Hz | 0.5s | Low bass punch, adds depth |
| `Snare` | 200Hz | 0.15s | Click noise, percussion |
| `Hi-Hat` | 8000Hz | 0.05s | Sharp highs, rhythm |
| `Clap` | 1000Hz | 0.1s | Hand clap, wide sound |

**Drum Pattern Example:**

```json
"drum": {
  "muted": false,
  "volume": 0.8,
  "data": {
    "Kick": [true, false, false, false, true, false, false, false, true, false, false, false, true, false, false, false],
    "Snare": [false, false, true, false, false, false, true, false, false, false, true, false, false, false, true, false],
    "Hi-Hat": [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]
  }
}
```

---

### 2. Oscillator Tracks (bass, melody, chord)

Waveform synthesis for custom tone generation. `waveform` is required.

```json
"bass": {
  "muted": false,
  "volume": 0.7,
  "waveform": "sawtooth",
  "data": {
    "C2": [true, false, false, false, ...],
    "G2": [false, false, true, false, ...]
  }
}
```

**Required Fields:**
- `waveform`: `sine`, `triangle`, `square`, `sawtooth`
- `data`: Note patterns (note names and step data)

#### 2a. Bass Track

Low frequency (C2-C3). Warm and powerful sound.

```json
"bass": {
  "muted": false,
  "volume": 0.7,
  "waveform": "square",  // or triangle, sine, sawtooth
  "data": {
    "C2": [true, false, false, false, ...],
    "G2": [false, false, true, false, ...],
    "D2": [false, false, false, false, true, false, ...]
  }
}
```

**Waveform Selection:**
- `sine`: Deep and pure bass
- `square`: Retro "video game" feel
- `triangle`: Warm and round bass
- `sawtooth`: Bright and aggressive bass

#### 2b. Melody Track

High frequency (C4-C5). Main melodic line.

```json
"melody": {
  "muted": false,
  "volume": 0.6,
  "waveform": "square",
  "data": {
    "C4": [true, false, false, false, ...],
    "E4": [false, true, false, false, ...],
    "G4": [false, false, true, false, ...]
  }
}
```

**Available Notes:**
```
Full Chromatic Scale Supported (C2 - C6)
Examples:
  Low range:    C2, C#2, D2, Eb2, E2... B2
  Mid range:    C3, C#3, D3... Ab3, A3, Bb3, B3
  High range:   C4... C5... up to C6
```

#### 2c. Chord Track

Play chords (multiple notes simultaneously). `waveform` is required.

```json
"chord": {
  "muted": false,
  "volume": 0.5,
  "waveform": "triangle",
  "data": {
    "C": [true, false, false, false, ...],
    "F": [false, false, false, false, true, ...],
    "G": [false, false, false, false, false, ...]
  }
}
```

**Available Chords:**

| Chord | Notes | Purpose |
|-------|-------|---------|
| `C` | C3, E3, G3 | C Major |
| `Dm` | D3, F3, A3 | D Minor |
| `Em` | E3, G3, B3 | E Minor |
| `F` | F3, A3, C4 | F Major |
| `G` | G3, B3, D4 | G Major |
| `Am` | A3, C4, E4 | A Minor |
| `Bdim` | B3, D4, F4 | B Diminished |
| `C7` | C3, E3, G3, Bb3 | C Dominant 7 |

---

### 3. PCM Track (Sample Instruments)

Pre-rendered instrument samples. Supports pitch shifting.

```json
"pcm": {
  "muted": false,
  "volume": 0.7,
  "sound": "piano",
  "data": {
    "C4": [true, false, false, false, ...],
    "E4": [false, false, true, false, ...],
    "G4": [false, false, false, false, true, ...]
  }
}
```

**Required Fields:**
- `sound`: `piano`, `epiano`, `organ`, `strings`

**Available Instruments:**

| Instrument | Attack | Decay | Characteristics | Purpose |
|-----------|--------|-------|-----------------|---------|
| `piano` | Fast | Medium (3s) | Natural, rich harmonics | Melody, game BGM |
| `epiano` | Fast | Fast (2s) | Bright, bouncy | Upbeat, jazz-style |
| `organ` | Medium | Sustained | Pipe organ sound | Arcade nostalgia, dramatic |
| `strings` | Slow (0.3s) | Slow | Rich string texture | Cinematic, emotional scenes |

**Usage Example:**

```json
"pcm": {
  "muted": false,
  "volume": 0.6,
  "sound": "piano",
  "data": {
    "C4": [true, false, false, false, false, false, false, false],
    "E4": [false, true, false, false, false, false, false, false],
    "G4": [false, false, true, false, false, false, false, false],
    "C5": [false, false, false, true, false, false, false, false]
  }
}
```

---

### 4. FM Synthesis Track (fm, fm2)

Frequency modulation synthesis for complex tones. Ideal for metallic, bell, and alien sounds.

```json
"fm": {
  "muted": false,
  "volume": 0.7,
  "ratio": 2.0,
  "depth": 500,
  "data": {
    "C4": [true, false, false, false, ...],
    "E4": [false, false, true, false, ...]
  }
}
```

**Required Fields:**
- `ratio`: Modulator frequency ratio (1.0-5.0)
- `depth`: Modulation depth (Hz, 100-1000)

#### FM Parameter Details

**ratio (Frequency Ratio):**
- **1.0**: Subtle vibrato effect
- **1.5**: Soft frequency modulation
- **2.0**: Bell/chime-like (most common)
- **3.0-4.0**: Metallic, dissonant
- **5.0+**: Alien, noise-like

**depth (Modulation Depth):**
- **100-300**: Subtle tone variation
- **500-700**: Clear FM effect
- **800-1000**: Aggressive, harsh tone

#### FM Sound Design Patterns

**Electric Bass (ratio: 2.0, depth: 300):**
```json
"fm": {
  "muted": false,
  "volume": 0.8,
  "ratio": 2.0,
  "depth": 300,
  "data": {
    "C2": [true, false, false, false, true, false, false, false, ...],
    "G2": [false, false, true, false, false, false, true, false, ...]
  }
}
```

**Bell/Chime (ratio: 3.5, depth: 800):**
```json
"fm": {
  "muted": false,
  "volume": 0.6,
  "ratio": 3.5,
  "depth": 800,
  "data": {
    "C4": [true, false, false, false, ...],
    "G4": [false, false, true, false, ...]
  }
}
```

**Alien/Sci-Fi (ratio: 4.5, depth: 1000):**
```json
"fm": {
  "muted": false,
  "volume": 0.5,
  "ratio": 4.5,
  "depth": 1000,
  "data": {
    "C3": [true, false, false, false, ...],
    "E3": [false, true, false, false, ...]
  }
}
```

---

## Practical Sound Design Examples

### SFX: Laser Shot

Short and sharp. Pitch sweep from high to low.

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

**Characteristics:**
- BPM 240 (fast = short duration)
- patternLength 4 (100ms)
- Pitch descending (C5 → C4)
- Sine waveform (smooth)

---

### SFX: Explosion

Low punch + noise. Long decay.

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
    },
    "fm": {
      "muted": false,
      "volume": 0.7,
      "ratio": 3.0,
      "depth": 800,
      "data": {
        "C3": [true, false, false, false]
      }
    }
  }
}
```

---

### SFX: Power-up

Rising arpeggio. Fun, rewarding sound.

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

---

### BGM: 8-Bit Beat

Game BGM using all features.

```json
{
  "version": "1.0",
  "bpm": 140,
  "patternLength": 16,
  "masterVolume": 0.7,
  "tracks": {
    "drum": {
      "muted": false,
      "volume": 0.8,
      "data": {
        "Kick": [true, false, false, false, true, false, false, false, true, false, false, false, true, false, false, false],
        "Snare": [false, false, true, false, false, false, true, false, false, false, true, false, false, false, true, false],
        "Hi-Hat": [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]
      }
    },
    "bass": {
      "muted": false,
      "volume": 0.7,
      "waveform": "square",
      "data": {
        "C2": [true, false, false, false, true, false, false, false, false, false, false, false, false, false, false, false],
        "G2": [false, false, false, false, false, false, false, false, true, false, false, false, true, false, false, false]
      }
    },
    "melody": {
      "muted": false,
      "volume": 0.6,
      "waveform": "square",
      "data": {
        "C4": [true, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false],
        "D4": [false, true, false, false, false, false, false, false, false, false, false, false, false, false, false, false],
        "E4": [false, false, true, false, false, false, false, false, false, false, false, false, false, false, false, false],
        "G4": [false, false, false, false, true, false, false, false, false, false, false, false, false, false, false, false]
      }
    }
  }
}
```

---

## Volume Balancing Guide

### Master Volume
- **BGM**: 0.6-0.8
- **SFX**: 0.8-1.0

### Track Volumes
```
drum:   0.7-0.9
bass:   0.6-0.8
melody: 0.5-0.7
chord:  0.4-0.6
pcm:    0.5-0.7
fm:     0.5-0.8
```

### Clipping Prevention

When using multiple tracks simultaneously, ensure the total doesn't exceed 1.0.

```
Example: Kick 1.0 + other drums causes distortion
→ Reduce to Kick 0.7, Snare 0.6, Hi-Hat 0.5
```

---

## SFX Creation Quick Guide

### Short SFX (UI, blinks)
```json
{
  "bpm": 300,
  "patternLength": 2,
  "masterVolume": 0.6,
  "tracks": { ... }
}
// Duration: ~40ms
```

### Standard SFX (Shoot, Hit)
```json
{
  "bpm": 200-240,
  "patternLength": 4,
  "masterVolume": 0.8,
  "tracks": { ... }
}
// Duration: 50-150ms
```

### Long SFX (Explosion, Power-up)
```json
{
  "bpm": 120-160,
  "patternLength": 8,
  "masterVolume": 0.8,
  "tracks": { ... }
}
// Duration: 300-600ms
```

---

## Creating BGM Loops

### Loop Point Calculation

```
Duration = (patternLength × 60 / bpm) seconds

Example:
BPM 120, patternLength 16
= (16 × 60 / 120) = 8 seconds
```

### Tips for Natural Loops

1. **Don't fade at the last step**
   ```json
   "data": {
     "C4": [..., true],  // Sound on last step
   }
   ```

2. **BGM should use beat multiples**
   ```
   Recommended: 4, 8, 16, 32 steps
   Avoid: 3, 5, 7 steps (unnatural)
   ```

3. **Match key and tonality**
   ```
   Start and end in C Major
   ```

---

## Common Errors and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Distorted audio | `masterVolume` or track volume too high | Reduce values by 0.1 |
| Audio too quiet | Volume too low | Increase `masterVolume` by 0.1 |
| BGM has clicks at loop point | Unnatural envelope | Mute last few steps |
| Track plays continuously | Too many true values in `data` | Add more false values |
| Invalid note name | Wrong case or octave | Use format C4 (uppercase + digit) |

---

## Next Steps

- [README.md](./README.md) - Basic usage
- [artist_guide.md](../../system_prompt/tool_guides/artist_guide.md) - Complete workflow
- [synthesizer source code](./synthesizer/) - Implementation details
