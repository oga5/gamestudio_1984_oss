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
- Use simple, pure waveforms (sine, square, sawtooth, triangle)
- Create punchy sounds with immediate attack (<0.01s)
- Keep durations short (most SFX < 0.5 seconds)
- Use pitch modulation for emotional impact
- Think: "How would this sound through an arcade cabinet speaker?"

**Design from Emotion and Context**:
Instead of following templates, interpret the audio_details to create original sounds:
- Study the **character** (personality and quality)
- Implement the **pitch_envelope** (how pitch changes)
- Choose appropriate **timbre** (waveform and tone)
- Match the **mood** (emotion to convey)
- Reference **inspiration** (classic games) for authenticity, not imitation

**Creative Questions to Ask**:
- What emotion does this action evoke?
- How can simple waveforms express this uniquely?
- What would surprise yet still feel "1984 arcade"?
- Does this sound match the game's unique character?

### Step 3: Generate Sound

Call `generate_sound()` with appropriate JSON pattern:
- Choose BPM and patternLength for desired duration: `duration = (patternLength / bpm) * 60`
- Select waveforms that match the timbre described
- Design note patterns that implement the pitch_envelope
- Set volumes to create appropriate dynamics
- Use multiple tracks if needed for richness

Example tool call structure:
```
generate_sound(
  "/public/assets/sounds/[name from spec]",
  '[JSON pattern based on audio_details]'
)
```

### Step 4: Validate
```
validate_asset("/public/assets/sounds/[name]")
# Should return: "VALID: /public/assets/sounds/[name]"
```

## Sound Pattern Design Guidelines

**Track Types Available**:
- **melody/bass**: Use waveforms (sine, square, sawtooth, triangle) with note data
- **drum**: Use percussion (Kick, Snare, Hi-Hat, Clap) for impacts
- **chord**: Use chord names (C, Dm, Em, F, G, Am, Bdim, C7) for harmony
- **fm**: Use FM synthesis (ratio and depth) for complex tones

**Duration Control**:
- Formula: `duration = (patternLength / bpm) * 60` seconds
- Short SFX: BPM 240-360, patternLength 2-4 → 0.2-0.5s
- Medium SFX: BPM 180-240, patternLength 4-8 → 0.5-1.5s
- Long SFX: BPM 120-180, patternLength 8-16 → 2-5s

**Waveform Characteristics**:
- **Sine**: Smooth, pure tone - can be ethereal or piercing
- **Square**: Classic chip sound - harsh, 8-bit character
- **Sawtooth**: Bright, energetic - cuts through mix
- **Triangle**: Mellow, warm - good for bass

**Design Approach**:
1. Read the audio_details carefully
2. Interpret the emotional intent
3. Choose appropriate waveforms and patterns
4. Create original sound that fits the game's unique character
5. Don't rely on templates - design from the specification

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
