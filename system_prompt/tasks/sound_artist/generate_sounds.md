Generate a SINGLE sound asset (WAV) based on the specification provided in your task prompt.

## CRITICAL: Single Asset Processing

**You will receive ONE asset specification in your task prompt.**

1. Generate ONLY the single sound specified in your task prompt
2. **SFX FIRST**: If it's a common sound effect (jump, hit, explosion, laser, coin, etc.), ALWAYS use `generate_sfx()`.
3. **CUSTOM/BGM**: Use `generate_sound()` only for background music or unique complex sounds.
4. Do NOT read `/work/sound_asset.json` - the specification is already in your prompt
5. Complete your task when that single sound is generated and validated

## Input

- **Asset specification**: Provided directly in your task prompt (NOT from a file)

## Output

- ONE WAV file in `/public/assets/sounds/` matching the specification

## CRITICAL: You MUST Use Tools

**IMPORTANT**: This task requires you to call a generation tool. You cannot complete this task without executing tools.

Before finishing:
- Verify you have called `generate_sfx()` or `generate_sound()` at least once
- Verify you have called `validate_asset()` to check the generated file
- If you complete without calling these tools, the task has FAILED

## Workflow

1. Study the asset specification from your task prompt (name, description, audio_details)
2. Choose tool:
   - **Standard SFX**: Use `generate_sfx(output_path, sfx_type, ...)`
   - **BGM or Unique sound**: Use `generate_sound(output_path, pattern_json)`
3. Visualize/Hear the sound mentally as if playing from a 1984 arcade cabinet
4. Design the sound with authentic 1984 arcade character
5. **EXECUTE**: Call the chosen generation tool
6. **EXECUTE**: Call `validate_asset(output_path)` to confirm validity
7. **DONE** - Task complete. Do NOT attempt to regenerate.

## SFX Type Reference (for `generate_sfx`)

Use these types for the `sfx_type` argument:
- `explosion`: Enemy destruction, bombs
- `laser`: Shooting, projectiles
- `hit`: Collisions, damage taken
- `powerup`: Collecting power-ups
- `coin`: Collecting items
- `jump`: Player jump
- `gameover`: Game over screen
- `victory`: Level complete
- `damage`: Player hurt
- `select`: UI selection
- `blip`: Simple feedback

## Sound Design Philosophy (1984 Authenticity)

- Channel the spirit of 1984 arcade audio (Space Invaders, Pac-Man, Galaga)
- Use simple, pure waveforms (sine, square, sawtooth, triangle)
- Create punchy sounds with immediate attack (<0.01s)
- Keep durations short (most SFX < 0.5 seconds)
- Think: "How would this sound through an arcade cabinet speaker?"
