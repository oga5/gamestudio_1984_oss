# Task: Generate Sound

Generate a SINGLE sound effect based on the specification provided in your task prompt.

## CRITICAL: Single Asset Processing

**You will receive ONE asset specification in your task prompt.** The system handles multiple assets by calling you separately for each one. Your job is to:

1. Generate ONLY the single sound specified in your task prompt
2. Do NOT read `/work/sound_asset.json` - the specification is already in your prompt
3. Do NOT try to process multiple assets - focus on the ONE you were given
4. Complete your task when that single sound is generated and validated

## Input

- **Asset specification**: Provided directly in your task prompt (NOT from a file)

## Output

- ONE WAV file in `/public/assets/sounds/` matching the specification

## CRITICAL: You MUST Use Tools

**IMPORTANT**: This task requires you to call the `generate_sound()` tool. You cannot complete this task without executing tools. If you describe what you would do without actually calling the tools, the task will fail.

Before finishing:
- Verify you have called `generate_sound()` at least once
- Verify you have called `validate_asset()` to check the generated file
- If you complete without calling these tools, the task has FAILED

## Workflow

1. Study the asset specification from your task prompt (name, description, audio_details)
2. Hear the sound mentally as if playing from a 1984 arcade cabinet
3. Design the sound pattern with authentic 1984 arcade character
4. **EXECUTE**: Call `generate_sound(output_path, pattern_json)`
5. **EXECUTE**: Call `validate_asset(output_path)` to verify
6. If invalid (.err file created), regenerate with improvements (max 3 attempts)
7. **DONE** - Task complete when this single sound is validated

## Sound Creation Process

### Step 1: Study Asset Specification (from your task prompt)

**The specification includes**:
- **name**: Output filename (e.g., "shoot.wav")
- **description**: Overall concept and context
- **audio_details.character**: Sonic personality and quality
- **audio_details.pitch_envelope**: How pitch changes over time
- **audio_details.timbre**: Waveform type and tonal quality
- **audio_details.dynamics**: Volume curve and intensity
- **audio_details.mood**: Emotional quality to convey
- **audio_details.inspiration**: Classic arcade game sound references

### Step 2: Design Sound with 1984 Authenticity

**Sound Design Philosophy**:
- Channel the spirit of 1984 arcade audio (Space Invaders, Pac-Man, Galaga, Donkey Kong)
- Use simple, pure waveforms (sine, square, sawtooth)
- Create punchy sounds with immediate attack
- Keep durations short (most SFX < 0.5 seconds)
- Use pitch modulation for classic arcade character
- Think: "How would this sound through an arcade cabinet speaker?"

**Technical Approach Based on Description**:
- **"shoot/laser"** → Descending pitch sweep (C5 → C4), sine or square wave, 0.15-0.3s
- **"explosion"** → Drum hits (Kick + Snare) or noise burst, 0.2-0.4s
- **"jump"** → Rising pitch (C4 → E4/G4), square wave, 0.15-0.25s
- **"collect/coin/powerup"** → Ascending arpeggio (C4 → E4 → G4 → C5), 0.3-0.6s
- **"hit/damage"** → Descending pitch or harsh noise, 0.1-0.2s
- **"menu/UI"** → Single blip or two-note, 0.05-0.15s

### Step 3: Generate Sound
```
generate_sound(
  "/public/assets/sounds/[name from spec]",
  '{
    "bpm": 300,
    "patternLength": 2,
    "masterVolume": 0.8,
    "tracks": {
      "melody": {
        "volume": 1.0,
        "waveform": "sine",
        "data": {
          "C5": [true, false],
          "C4": [false, true]
        }
      }
    }
  }'
)
```

### Step 4: Validate
```
validate_asset("/public/assets/sounds/[name]")
# Should return: "VALID: /public/assets/sounds/[name]"
```

## 1984 Arcade Sound Recipes

**Laser/Shoot (Space Invaders/Galaga style)**:
```json
{
  "bpm": 300,
  "patternLength": 2,
  "masterVolume": 0.8,
  "tracks": {
    "melody": {
      "volume": 1.0,
      "waveform": "sine",
      "data": {
        "C5": [true, false],
        "C4": [false, true]
      }
    }
  }
}
```

**Explosion (Arcade impact)**:
```json
{
  "bpm": 240,
  "patternLength": 3,
  "masterVolume": 0.9,
  "tracks": {
    "drum": {
      "volume": 1.0,
      "data": {
        "Kick": [true, true, false],
        "Snare": [false, true, true]
      }
    }
  }
}
```

**Jump/Bounce (Donkey Kong style)**:
```json
{
  "bpm": 360,
  "patternLength": 2,
  "masterVolume": 0.7,
  "tracks": {
    "melody": {
      "volume": 0.9,
      "waveform": "square",
      "data": {
        "C4": [true, false],
        "E4": [false, true]
      }
    }
  }
}
```

**Power-Up/Collect (Pac-Man style)**:
```json
{
  "bpm": 240,
  "patternLength": 4,
  "masterVolume": 0.75,
  "tracks": {
    "melody": {
      "volume": 0.9,
      "waveform": "sine",
      "data": {
        "C4": [true, false, false, false],
        "E4": [false, true, false, false],
        "G4": [false, false, true, false],
        "C5": [false, false, false, true]
      }
    }
  }
}
```

## Validation Checklist

For your single sound:
- [ ] Generated in `/public/assets/sounds/`
- [ ] Validated (returns "VALID")
- [ ] Implements ALL audio_details from specification
- [ ] Appropriate duration (most SFX < 0.5 seconds, max 1 second)
- [ ] Simple, authentic 1984 waveforms (sine, square, sawtooth)
- [ ] Punchy with immediate attack
- [ ] Clear pitch envelope matching audio_details
- [ ] Reflects inspiration from classic arcade games
- [ ] Conveys the mood described
- [ ] No .err file exists

## Common Issues

❌ **Reading sound_asset.json** → Specification is in your task prompt! Don't read files
❌ **Trying to process multiple assets** → You have ONE asset, generate only that
❌ Too long (>1 sec) → Increase BPM (240-360), reduce patternLength (2-4)
❌ Complex, modern sound design → Use simple pure waveforms
❌ Slow attack → Sounds should be punchy and immediate
❌ Wrong pitch envelope → Match the audio_details.pitch_envelope
❌ Missing arcade character → Channel classic games like Galaga and Pac-Man
❌ Invalid file (.err) → Regenerate with fixed JSON (max 3 attempts)

✅ Focus on the SINGLE asset from your task prompt
✅ Punchy, iconic 1984 arcade sound effects
✅ Short durations for tight arcade gameplay feel
✅ Validate before completing
