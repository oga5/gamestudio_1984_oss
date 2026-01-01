# Task: Create Game Concept

Design a simple, fun arcade game inspired by 1984-era classics.

## Output

Create `/work/design.json` with complete game specification using the **v0.7 enhanced schema**.

## v0.7 Enhanced Schema

v0.7 adds support for TileMap, Camera, and Stage systems, enabling more complex games.

```json
{
  "name": "Game Title (short, catchy)",
  "description": "1-2 sentence description",
  "genre": "shooter|platformer|puzzle|action|racing",
  "screen": {
    "width": 360,
    "height": 540,
    "background_color": "#000020"
  },
  "controls": {
    "keyboard": ["ArrowLeft", "ArrowRight", "Space"],
    "touch": true,
    "pause_enabled": true
  },
  "gameplay": {
    "objective": "What player needs to do to win/score",
    "mechanics": [
      "Core mechanic 1",
      "Core mechanic 2",
      "Core mechanic 3"
    ],
    "difficulty": "easy|medium|hard"
  },

  "entities": {
    "player": {
      "speed": 180,
      "size": { "width": 32, "height": 32 },
      "hitbox_type": "circle",
      "hitbox_radius": 14,
      "lives": 3,
      "invincibility_duration": 2.0,
      "shoot_cooldown": 0.2,
      "bullet_speed": 400
    },
    "enemies": [
      {
        "type": "basic",
        "speed": 60,
        "size": { "width": 28, "height": 28 },
        "hitbox_type": "circle",
        "hitbox_radius": 12,
        "score_value": 10,
        "behavior": "move_down|follow_player|patrol"
      },
      {
        "type": "elite",
        "speed": 80,
        "size": { "width": 32, "height": 32 },
        "hitbox_type": "circle",
        "hitbox_radius": 14,
        "score_value": 20,
        "behavior": "follow_player",
        "can_shoot": true,
        "shoot_interval": 2.0
      }
    ],
    "bullets": {
      "player": { "speed": 400, "radius": 4 },
      "enemy": { "speed": 200, "radius": 4 }
    }
  },

  "spawning": {
    "initial_enemies": 24,
    "spawn_rate": 2.0,
    "max_on_screen": 30,
    "spawn_pattern": "grid|random|wave"
  },

  "scoring": {
    "enemy_basic": 10,
    "enemy_elite": 20,
    "stage_clear_bonus": 500,
    "no_damage_bonus": 200
  },

  "difficulty_progression": [
    { "score_threshold": 0, "enemy_speed_mult": 1.0, "spawn_rate": 2.0 },
    { "score_threshold": 500, "enemy_speed_mult": 1.2, "spawn_rate": 1.5 },
    { "score_threshold": 1000, "enemy_speed_mult": 1.5, "spawn_rate": 1.0 }
  ],

  "stages": {
    "enabled": false,
    "count": 1,
    "clear_condition": "destroy_all|survive_time|reach_score"
  },

  "game_world": {
    "type": "single_screen|tilemap|scrolling",
    "width": 360,
    "height": 540,
    "tilemap": {
      "enabled": false,
      "tile_width": 16,
      "tile_height": 16,
      "map_width": 30,
      "map_height": 40,
      "solid_tiles": [1, 2],
      "tile_colors": {
        "0": "transparent",
        "1": "#888888",
        "2": "#444444"
      }
    }
  },

  "camera": {
    "type": "fixed|follow_player|auto_scroll",
    "follow_speed": 0.1,
    "world_bounds": {
      "width": 360,
      "height": 540
    }
  },

  "visual_effects": {
    "explosion": {
      "particle_count": 25,
      "color": "#ff6600",
      "speed": 4,
      "lifetime": 0.6,
      "size": 4,
      "gravity": 0.1
    },
    "muzzle_flash": {
      "particle_count": 5,
      "color": "#ffff00",
      "speed": 2,
      "lifetime": 0.15,
      "size": 3
    },
    "player_hit": {
      "screen_shake": { "intensity": 8, "duration": 0.3 },
      "screen_flash": { "color": "#ff0000", "duration": 0.2 }
    },
    "enemy_kill": {
      "screen_shake": { "intensity": 3, "duration": 0.1 }
    }
  },

  "audio": {
    "bgm_game": {
      "file": "bgm_game.wav",
      "volume": 0.5,
      "loop": true
    },
    "sfx": {
      "shoot": "shoot.wav",
      "explosion": "explosion.wav",
      "player_hit": "player_hit.wav"
    }
  }
}
```

## Design Principles

1. **Simple**: Can explain in 10 seconds
2. **Appropriate scope**: Choose between single-screen OR scrolling/tilemap based on game type
3. **Quick rounds**: Game over in 1-3 minutes per stage
4. **Clear goal**: Easy to understand objective
5. **v0.7**: Leverage TileMap, Camera, and Stage systems for richer gameplay

## Background Rules

**IMPORTANT**: Background color restrictions and implementation guidelines:

1. **No Background Images**: Do NOT create large background images (e.g., 360x540 PNG files)
   - Background images waste tokens and file size
   - Use canvas background color instead

2. **Canvas Background Color**: Implement backgrounds using HTML5 canvas `fillStyle`
   - Example: `ctx.fillStyle = '#000020'; ctx.fillRect(0, 0, width, height);`
   - This is efficient and authentic to 1984 arcade hardware

3. **Reserved Color**: `#0f0f0f` (dark gray) is reserved for the title screen only
   - Choose a different background color for the game screen (e.g., `#000000`, `#001020`, `#100010`, etc.)
   - This ensures visual distinction between title and gameplay for automated testing

**Summary**: Backgrounds must be solid colors rendered via canvas, NOT image assets

## v0.7 Feature Recommendations

When designing, consider leveraging these v0.7 capabilities:

### NEW: TileMap System (v0.7)
- **Platformers**: Solid tiles for floors, walls, platforms
- **Maze Games**: Tile-based level layouts
- **RPG-style**: Top-down dungeons with collision walls
- **Tile Colors**: Simple colored tiles (no tileset image needed for MVP)
- **World Size**: Larger than screen for exploration games

### NEW: Camera System (v0.7)
- **Follow Player**: Smooth camera tracking (scrolling platformers, top-down games)
- **Auto Scroll**: Automatic scrolling (horizontal shooters)
- **Camera Shake**: Enhanced impact effects combined with particles
- **World Bounds**: Define playable area larger than 360x540

### NEW: Stage System (v0.7)
- **Multi-Stage**: 3-5 stages with increasing difficulty
- **Stage Progression**: Clear condition per stage (destroy all, survive time, collect items)
- **Stage-Specific**: Different enemies, layouts, or mechanics per stage

### v0.6 Features (Still Available)
- **Particles**: Explosions, trails, pickups, impacts
- **Screen Effects**: Shake and flash for feedback
- **Sound Loop**: BGM with volume control
- **Circle Collision**: Round objects (bullets, asteroids)
- **Pause**: B button support

## Examples

### v0.7 Enhanced Games

**Platform Runner (v0.7 NEW)**:
- Type: `tilemap` + `follow_player` camera
- Objective: Reach the goal while avoiding obstacles
- Mechanics: Jump over gaps, collect coins, 3 stages
- v0.7: TileMap for platforms, Camera follows player, StageSystem for levels

**Scrolling Shooter (v0.7 NEW)**:
- Type: `scrolling` + `auto_scroll` camera
- Objective: Destroy enemy waves across 5 stages
- Mechanics: Move in all directions, shoot, dodge bullets
- v0.7: Auto-scrolling background, StageSystem for progression

**Maze Chase (v0.7 NEW)**:
- Type: `tilemap` + `follow_player` camera
- Objective: Collect all items while avoiding enemies
- Mechanics: Navigate maze, eat power pellets, chase enemies
- v0.7: TileMap for maze walls, Camera follows in large maze

### v0.6 Single-Screen Games (Still Valid)

**Space Shooter**:
- Type: `single_screen` + `fixed` camera
- Objective: Shoot all aliens before they reach bottom
- Mechanics: Move left/right, shoot, avoid enemy fire
- v0.6: Explosion particles, screen shake on kill, BGM loop

**Breakout Clone**:
- Type: `single_screen` + `fixed` camera
- Objective: Break all bricks with ball
- Mechanics: Move paddle, bounce ball, break bricks
- v0.6: Brick destruction particles, screen shake on combo

**Survival Action**:
- Objective: Survive 90 seconds against waves
- Mechanics: Move freely, shoot enemies, collect power-ups
- v0.6: Difficulty progression, spawn waves, boss at 60s mark

## Steps

1. Choose a game concept (inspired by classics)
2. Write `/work/design.json` with all required fields using v0.6 schema
3. Include specific numbers for speeds, timings, spawn rates
4. Define particle effects for key events
5. Plan BGM and SFX usage
6. Keep it SIMPLE (implementable in one game.js file)

## CRITICAL: File Writing Rules

**DO NOT edit `/work/workflow.json`** - Manager's territory, managed by the system

**Your ONLY output file:** `/work/design.json`

**IMPORTANT - DO NOT EDIT THESE FILES:**
- `/work/workflow.json` - Managed by Manager and system automatically
- `/work/test_report.json` - Tester's responsibility
- `/public/game.js` - Programmer's responsibility

## Validation

- [ ] All required fields present
- [ ] Clear, achievable objective
- [ ] 2-4 core mechanics maximum
- [ ] Single-screen design
- [ ] Appropriate for 1984 hardware
- [ ] Did NOT edit workflow.json
- [ ] **v0.6**: Entity speeds/sizes specified
- [ ] **v0.6**: Visual effects defined
- [ ] **v0.6**: Audio plan included

Simple, focused concept with v0.6 visual polish!
