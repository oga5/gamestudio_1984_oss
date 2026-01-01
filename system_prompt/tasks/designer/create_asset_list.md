# Task: Create Asset List

Specify all images and sounds needed for the game.

## Input

- `/work/design.json`: Game design (created previously)

## Output

1. Create `/work/image_asset.json` - Specifications for images that need generation
2. Create `/work/sound_asset.json` - Specifications for sounds that need generation

## Required Format

### `/work/image_asset.json`

```json
{
  "images": [
    {
      "id": 1,
      "name": "player.png",
      "size": "32x32",
      "description": "Player character sprite - A detailed, multi-sentence description with specific visual guidance",
      "visual_details": {
        "shape": "Describe the overall silhouette and form (e.g., 'Sleek triangular spaceship with angular wings')",
        "colors": "List primary colors and where they appear (e.g., 'Bright cyan (#00FFFF) for the hull, white (#FFFFFF) highlights on edges, red (#FF0000) for the cockpit')",
        "style": "Describe the artistic style (e.g., '1984 arcade-style with bold outlines, high contrast, geometric shapes reminiscent of Galaga or Space Invaders')",
        "key_features": "Notable elements that make it distinctive (e.g., 'Twin laser cannons on sides, glowing engine exhaust at rear, small cockpit window at center')",
        "inspiration": "Reference classic 1984 arcade games or design elements (e.g., 'Inspired by the Vic Viper from Gradius, with clean lines and symmetrical design')"
      }
    }
  ]
}
```

### `/work/sound_asset.json`

```json
{
  "sounds": [
    {
      "id": 10,
      "name": "bgm_game.wav",
      "description": "Gameplay background music - An energetic, loopable soundtrack that drives the action forward while maintaining the 1984 arcade aesthetic. This music should create tension and excitement without overwhelming the sound effects.",
      "audio_details": {
        "character": "Overall sonic character (e.g., 'Driving, pulse-pounding melody reminiscent of Galaga or Xevious, with a catchy hook that loops seamlessly')",
        "pitch_envelope": "Musical structure (e.g., 'A-B structure with main melody in mid-high range (C4-G5), bass line driving in low range (C2-C3), 20-30 second loop')",
        "timbre": "Tonal quality and waveform suggestion (e.g., 'Square wave for melody (classic chip sound), sawtooth wave for bass (punchy and driving), triangle wave for harmony')",
        "dynamics": "Volume and intensity curve (e.g., 'Consistent moderate volume (0.5-0.6) to avoid fatigue, with slight emphasis on downbeats')",
        "mood": "Emotional quality (e.g., 'Energetic and focused, building urgency without being stressful, encouraging fast-paced gameplay')",
        "inspiration": "Reference classic 1984 arcade game sounds (e.g., 'Similar to the main theme from Pac-Man or the stage music from Galaga, with simple but memorable melodic hooks')"
      }
    },
    {
      "id": 11,
      "name": "shoot.wav",
      "description": "Laser shoot sound effect - A detailed, multi-sentence description with specific audio guidance",
      "audio_details": {
        "character": "Overall sonic character (e.g., 'Sharp, cutting laser blast reminiscent of Space Invaders, with a satisfying punch')",
        "pitch_envelope": "How pitch changes over time (e.g., 'Starts at high frequency (C5-D5) and rapidly descends to mid-low (C4) over 0.2 seconds, creating classic arcade laser doppler effect')",
        "timbre": "Tonal quality and waveform suggestion (e.g., 'Pure sine wave for clean retro sound, or square wave for harsher 8-bit character')",
        "dynamics": "Volume and intensity curve (e.g., 'Sharp attack with immediate peak volume, quick decay to silence, total duration 0.15-0.25 seconds')",
        "mood": "Emotional quality (e.g., 'Aggressive and energetic, conveying power and precision')",
        "inspiration": "Reference classic 1984 arcade game sounds (e.g., 'Similar to Galaga or Xevious weapon fire, with that iconic arcade cabinet presence')"
      }
    }
  ]
}
```

## Guidelines

### Images (`/work/image_asset.json`)
- **Count**: 3-8 sprites maximum
- **Sizes**: 16x16, 32x32, or 64x64 pixels (small sprites only)
- **Description Length**: 3-5 sentences minimum, providing rich visual context
- **Visual Details**: REQUIRED - Fill out all five fields (shape, colors, style, key_features, inspiration)
- **Names**: Descriptive filenames (player.png, enemy.png, bullet.png)
- **1984 Authenticity**: Reference classic arcade games, use period-appropriate color palettes (CGA/EGA colors), emphasize geometric simplicity

### ⛔ PROHIBITED: Background Images
- **DO NOT create background images** (e.g., 360x540 or any screen-sized PNG files)
- **DO NOT create**: background.png, bg.png, backdrop.png, layer_*.png
- **Reason**: Background images are inefficient and waste tokens
- **Solution**: Use canvas background color in JavaScript instead
  ```javascript
  // In game.js, use canvas fillStyle for backgrounds
  ctx.fillStyle = '#000000'; // or any color
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ```

### ✅ ALLOWED: Game Objects Only
- **Player sprites**: Characters, ships, avatars (16x16, 32x32, 64x64)
- **Enemy sprites**: Opponents, obstacles (16x16, 32x32, 64x64)
- **Interactive objects**: Bullets, items, power-ups (8x8, 16x16, 32x32)
- **UI elements**: Score icons, life indicators (8x8, 16x16)

### Sounds (`/work/sound_asset.json`)
- **Count**: 4-8 sounds maximum (including BGM + SFX)
- **Types**:
  - **BGM (Background Music)**: 1-2 tracks recommended for title screen and/or gameplay (10-30 seconds, loopable)
  - **SFX (Sound Effects)**: 3-6 short effects (<1 second) for game actions
- **v0.6 Feature**: BGM is STRONGLY ENCOURAGED! Use v0.6's sound loop features (`assets.playSoundLoop()`) for immersive arcade experience
- **Description Length**: 3-5 sentences minimum, providing rich audio context
- **Audio Details**: REQUIRED - Fill out all six fields (character, pitch_envelope, timbre, dynamics, mood, inspiration)
- **1984 Authenticity**: Reference classic arcade game sounds, specify simple waveforms (sine, square, sawtooth), emphasize punchy and immediate responses

## Writing Style for Descriptions

### DO: Write Rich, Detailed Descriptions
✅ "A menacing alien invader sprite with a bulbous, organic form reminiscent of Space Invaders' iconic enemies. The creature features a large rounded head in bright green (#00FF00) with two glowing red eyes (#FF0000) positioned asymmetrically for an alien look. Tentacle-like appendages extend from the bottom in a darker green (#008800), creating a sense of movement even when static. The design uses bold, chunky pixels with minimal anti-aliasing to maintain that authentic 1984 arcade cabinet aesthetic."

### DON'T: Write Short, Vague Descriptions
❌ "Green alien sprite, 32x32, looks like Space Invaders enemy"

## Common Asset Categories

### Typical Shooter Assets
- **Images**: player.png, enemy.png, bullet.png, powerup.png
- **Sounds**:
  - **BGM**: bgm_title.wav (15-20 seconds, loopable), bgm_game.wav (20-30 seconds, loopable)
  - **SFX**: shoot.wav, explosion.wav, powerup.wav, hit.wav

### Typical Platformer Assets
- **Images**: player.png, enemy.png, platform.png, coin.png
- **Sounds**:
  - **BGM**: bgm_game.wav (20-30 seconds, loopable)
  - **SFX**: jump.wav, collect.wav, hurt.wav, gameover.wav

## Steps

1. Read `/work/design.json` to understand game mechanics, genre, and theme
2. Determine minimum required assets for core gameplay
3. Create `/work/image_asset.json` with detailed specifications
4. Create `/work/sound_asset.json` with detailed specifications
5. Keep count LOW (quality over quantity) but descriptions LONG (depth over brevity)

## Validation

### For `/work/image_asset.json`:
- [ ] 3-8 images specified
- [ ] Each image has 3-5 sentence description
- [ ] Each image has ALL visual_details fields filled (shape, colors, style, key_features, inspiration)
- [ ] Sizes specified (16x16, 32x32, or 64x64)
- [ ] IDs are unique (1-9)
- [ ] 1984 arcade style references included

### For `/work/sound_asset.json`:
- [ ] 4-8 sounds specified (including 1-2 BGM tracks)
- [ ] At least 1 BGM track included for immersive experience (v0.6 feature!)
- [ ] Each sound has 3-5 sentence description
- [ ] Each sound has ALL audio_details fields filled (character, pitch_envelope, timbre, dynamics, mood, inspiration)
- [ ] IDs are unique (10-19)
- [ ] 1984 arcade sound references included
- [ ] BGM tracks are marked as loopable with appropriate duration (10-30 seconds)

✅ Complete specifications in SEPARATE files
✅ DETAILED, multi-sentence descriptions with visual/audio details
✅ Authentic 1984 arcade game aesthetic guidance
✅ Realistic asset count
