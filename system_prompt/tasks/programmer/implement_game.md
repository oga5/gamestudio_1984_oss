# Task: Implement Game

Create a complete, working arcade game using the **2-layer game template**.

## Template Architecture

v0.4 uses an **advanced 2-layer template** that separates infrastructure from game logic:

- **gamelib.js** (Layer 1): Core game engine - manages states, input, assets, UI
  - DO NOT MODIFY - already in `/public/`

- **game.js** (Layer 2): Your game implementation - game logic only
  - CREATE YOUR OWN original implementation
  - Implement 3 required methods
  - Focus on game mechanics, movement, collision, scoring

## Pre-configured Files (Already Set Up)

The following files are **already copied** to `/public/`:
- `/public/index.html` - HTML structure (DO NOT MODIFY)
- `/public/style.css` - CSS styling (DO NOT MODIFY)
- `/public/gamelib.js` - Game library (DO NOT MODIFY)

**You only need to create `/public/game.js`**

## Input

- `/work/design.json`: **DETAILED** game design specification (v0.6 enhanced schema)
  - Contains specific numbers for speeds, timings, spawn rates
  - Detailed entity behaviors, progression stages, scoring rules
  - **READ CAREFULLY** - all implementation details are here
- `/public/assets/images/*.png`: Available sprite images
- `/public/assets/sounds/*.wav`: Available sound files (including BGM)
- **REFERENCE**: `/templates/game_template_advanced/game.js` - Example implementation
- **REFERENCE**: `/templates/design_schema_enhanced.json` - Enhanced design schema example

## Output

- `/public/game.js`: YOUR original game implementation

## Requirements

### 1. Create game.js

Use `/templates/game_template_advanced/game.js` as a **reference** for structure and patterns, but create your **own original implementation** based on the game design.

### 2. Your game.js Must

```javascript
// [1] Extend GameEngine
class MyGame extends GameEngine {
    constructor() {
        super('game-canvas', {
            title: 'YOUR GAME TITLE',
            description: 'Brief game description'
        });
    }

    // [2] Load assets
    loadAssets() {
        this.assets.loadImage('player', 'assets/images/player.png');
        this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');
    }

    // [3] Initialize game state
    initGame() {
        this.player = { x: 0, y: 0, ... };
        this.score = 0;
        // Setup game entities
    }

    // [4] Update game logic
    updateGame(deltaTime) {
        // Move player based on controller input
        // Update enemies, physics, collisions
        // Check win/loss conditions
    }

    // [5] Draw game graphics
    drawGame(ctx) {
        // Clear canvas
        // Draw sprites and UI
    }
}

// [6] Start the game
window.addEventListener('load', () => {
    const game = new MyGame();
    game.startGame();
});
```

### 3. What gamelib.js Provides Automatically

✅ **You DON'T need to implement**:
- Main game loop (gamelib.js handles 60 FPS)
- Title screen (shown automatically)
- Game over screen (shown automatically)
- State management (LOADING → TITLE → PLAYING → GAME_OVER)
- Input handling (use `this.controller`)
- Asset loading async (gamelib.js waits for completion)
- Canvas and context setup
- Virtual controller UI

### 4. Access gamelib.js Features

In your game.js methods:

```javascript
// Input
this.controller.getHorizontal()         // -1, 0, or 1
this.controller.getVertical()           // -1, 0, or 1
this.controller.isPressed('a')          // Boolean
this.controller.isJustPressed('a')      // Boolean on first frame

// Assets
this.assets.loadImage('name', 'path')
this.assets.getImage('name')
this.assets.playSound('name')

// v0.6 NEW: Sound Management
this.assets.playSoundLoop('bgm_game')   // Loop background music
this.assets.stopSound('bgm_game')       // Stop looping sound
this.assets.setVolume('bgm_game', 0.5)  // Set volume (0.0-1.0)
this.assets.stopAllLoops()              // Stop all looping sounds

// v0.6: Collision Detection
CollisionSystem.circleCollision(        // Circle-to-circle
  {x: bullet.x, y: bullet.y, radius: 5},
  {x: enemy.x, y: enemy.y, radius: 10}
)
CollisionSystem.circleRectCollision(circle, rect)  // Circle-to-rect
CollisionSystem.rectCollision(rect1, rect2)        // Rectangle AABB
CollisionSystem.distance(x1, y1, x2, y2)           // Distance utility

// v0.7 NEW: TileMap System
this.tileMap = new TileMapSystem(tileWidth, tileHeight, mapWidth, mapHeight);
this.tileMap.loadMap(mapData);          // Load 2D array of tile IDs
this.tileMap.getTile(x, y);             // Get tile at grid position
this.tileMap.setTile(x, y, tileId);     // Set tile at grid position
this.tileMap.getTileAtPosition(worldX, worldY);  // Get tile at pixel position
this.tileMap.checkCollision(rect, solidTiles);   // Check collision with solid tiles
this.tileMap.draw(ctx, camera, tileColors);      // Draw tilemap

// v0.7 NEW: Camera System
this.camera = new CameraSystem(screenWidth, screenHeight, worldWidth, worldHeight);
this.camera.follow(this.player, 0.1);   // Follow player smoothly (0.1 = smooth, 1.0 = instant)
this.camera.setPosition(x, y);          // Set camera position directly
this.camera.move(dx, dy);               // Move camera by offset
this.camera.shake(intensity, duration); // Camera shake effect
this.camera.update(deltaTime);          // Update camera (call in updateGame)
const offset = this.camera.getOffset(); // Get camera offset for drawing
this.camera.worldToScreen(worldX, worldY);  // Convert world to screen coords
this.camera.screenToWorld(screenX, screenY);  // Convert screen to world coords
this.camera.isVisible(rect);            // Check if object is visible

// v0.7 NEW: Stage System
this.stages = new StageSystem();
this.stages.loadStages([stage1, stage2, stage3]);  // Load stage array
this.stages.getCurrentStage();          // Get current stage data
this.stages.nextStage();                // Move to next stage
this.stages.gotoStage(index);           // Go to specific stage
this.stages.getStageNumber();           // Get current stage number (1-based)
this.stages.getTotalStages();           // Get total number of stages
this.stages.isLastStage();              // Check if this is the last stage

// State Management
this.stateManager.setState(GameStateManager.STATES.GAME_OVER)
// Valid states: LOADING, TITLE, PLAYING, GAME_OVER, GAME_CLEAR, PAUSED

// Screen
this.gameOver()                         // End the game (player lost)
this.gameClear()                        // Complete the game (player won)
this.getScreenWidth()                   // 360
this.getScreenHeight()                  // 540

// Utilities
this.collides(rect1, rect2)            // AABB collision (legacy, use CollisionSystem)
this.score                             // Current score
this.canvas                            // Canvas element
this.ctx                               // 2D context
```

### 5. Button/Key Mapping

**Virtual Controller Buttons**:
- `'up'`, `'down'`, `'left'`, `'right'` - D-PAD
- `'a'`, `'b'` - ACTION BUTTONS

**Keyboard Equivalents**:
- Arrow keys or WASD → D-PAD
- Space, Z → A button
- Shift → B button

### 6. Asset Loading Rules

**IMPORTANT**:
- Use `loadImage()` and `loadSound()` in `loadAssets()` method
- Use relative paths: `'assets/images/player.png'`
- NOT absolute paths: `/assets/...` or `/public/assets/...`
- Load ALL generated assets (designers created them for a reason)

```javascript
loadAssets() {
    // Load all sprites
    this.assets.loadImage('player', 'assets/images/player.png');
    this.assets.loadImage('enemy', 'assets/images/enemy.png');

    // Load all sounds
    this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');
}
```

## Implementation Steps

1. **Read design FIRST**: `read_file("/work/design.json")`
   - **v0.6 IMPORTANT**: This contains ALL implementation details
   - Extract specific numbers from `entities.player`, `entities.enemies[]`, etc.
   - Note `scoring` rules, `difficulty_progression` stages
   - Check `game_mechanics` for particle effects, sound triggers, special features
   - Review `visual_feedback` for UI/animation requirements

2. **Check assets**: `list_directory("/public/assets/images")` and `list_directory("/public/assets/sounds")`
   - Plan to use ALL available assets in your game
   - Note if BGM files exist (e.g., `bgm_title.wav`, `bgm_game.wav`)

3. **Study reference**: `read_file("/templates/game_template_advanced/game.js")`
   - This is a complete Space Invaders-like game
   - Shows patterns for movement, collision, scoring, etc.
   - Use as REFERENCE, not copy!

4. **Create game.js**: Write your **original implementation**
   - Extend GameEngine
   - Implement loadAssets(), initGame(), updateGame(), drawGame()
   - Use the game design and available assets

5. **Check syntax**: `check_syntax("/public/game.js")`

6. **Fix errors**: Use `file_edit()` for small changes, `replace_file()` for large rewrites

## Example: Moving the Player

```javascript
updateGame(deltaTime) {
    // Get input (-1, 0, or 1 for each axis)
    const h = this.controller.getHorizontal();
    const v = this.controller.getVertical();

    // Update position
    this.player.x += h * this.player.speed * deltaTime;
    this.player.y += v * this.player.speed * deltaTime;

    // Keep in bounds
    this.player.x = Math.max(0, Math.min(360 - this.player.width, this.player.x));
    this.player.y = Math.max(0, Math.min(540 - this.player.height, this.player.y));
}
```

## Example: Firing Bullets

```javascript
updateGame(deltaTime) {
    // Handle shooting with A button
    if (this.controller.isJustPressed('a')) {
        this.bullets.push({
            x: this.player.x + this.player.width / 2,
            y: this.player.y,
            speed: 300  // pixels per second
        });
        this.playSound('shoot');
    }

    // Update bullets
    this.bullets = this.bullets.filter(bullet => {
        bullet.y -= bullet.speed * deltaTime;
        return bullet.y > 0;
    });
}
```

## Example: Collision Detection

```javascript
updateGame(deltaTime) {
    for (let i = 0; i < this.bullets.length; i++) {
        const bullet = this.bullets[i];

        for (let j = 0; j < this.enemies.length; j++) {
            const enemy = this.enemies[j];

            // v0.6: Use circle collision for more accurate hit detection
            if (CollisionSystem.circleCollision(
                {x: bullet.x, y: bullet.y, radius: bullet.radius},
                {x: enemy.x, y: enemy.y, radius: enemy.radius}
            )) {
                // v0.6: Add particle explosion effect
                this.particles.emit(enemy.x, enemy.y, {
                    count: 15,
                    color: '#ff0000',
                    speed: 3,
                    lifetime: 0.5,
                    size: 3
                });

                this.bullets.splice(i, 1);
                this.enemies.splice(j, 1);
                this.score += 10;
                this.playSound('explosion');
                break;
            }
        }
    }
}
```

## v0.6 NEW: Particle System

**Add visual effects with ParticleSystem:**

```javascript
// In constructor()
constructor() {
    super('game-canvas', { title: 'MY GAME' });
    this.particles = new ParticleSystem();  // v0.6 feature
}

// In updateGame()
updateGame(deltaTime) {
    // Update particles every frame
    this.particles.update(deltaTime);

    // Emit particles on events (e.g., enemy destroyed)
    if (enemyDestroyed) {
        this.particles.emit(enemy.x, enemy.y, {
            count: 20,        // Number of particles
            color: '#ff0000', // Particle color
            speed: 3,         // Spread speed
            lifetime: 0.5,    // Duration in seconds
            size: 4,          // Particle size
            gravity: 0.1      // Downward pull (optional)
        });
    }
}

// In drawGame()
drawGame(ctx) {
    // ... draw game entities ...

    // Draw particles on top
    this.particles.draw(ctx);
}
```

## v0.6 NEW: Background Music (BGM)

**If design specifies BGM, use sound loops:**

```javascript
// In initGame() - Start game BGM
initGame() {
    // ... initialize game state ...

    // Stop all previous BGM
    this.assets.stopAllLoops();

    // Start game BGM (loops automatically)
    this.assets.playSoundLoop('bgm_game');
    this.assets.setVolume('bgm_game', 0.6);  // 60% volume
}

// On game over (player lost) - Stop BGM
playerDied() {
    this.assets.stopAllLoops();
    this.gameOver();
}

// On game clear (player won) - Stop BGM
allEnemiesDefeated() {
    this.assets.stopAllLoops();
    this.gameClear();
}
```

## v0.6 NEW: Screen Effects

**Add impactful visual feedback with ScreenEffects:**

```javascript
// In constructor()
constructor() {
    super('game-canvas', { title: 'MY GAME' });
    this.particles = new ParticleSystem();
    this.screenEffects = new ScreenEffects();  // v0.6 feature
}

// In updateGame()
updateGame(deltaTime) {
    // Update screen effects every frame
    this.screenEffects.update(deltaTime);
    this.particles.update(deltaTime);
    // ... rest of game logic ...
}

// Trigger effects on events
if (enemyDestroyed) {
    this.screenEffects.shake(5, 0.15);  // intensity, duration
}

if (playerHit) {
    this.screenEffects.flash('#ff0000', 0.2);  // color, duration
    this.screenEffects.shake(8, 0.3);
}

// Add missile/bullet trails
this.screenEffects.addTrail(bullet.x, bullet.y, '#00ffff', 3, 0.15);

// In drawGame()
drawGame(ctx) {
    // Apply screen shake
    ctx.save();
    const shakeOffset = this.screenEffects.getShakeOffset();
    ctx.translate(shakeOffset.x, shakeOffset.y);

    // ... draw game content ...

    // Draw trails before other effects
    this.screenEffects.drawTrails(ctx);

    // Draw particles
    this.particles.draw(ctx);

    ctx.restore();

    // Draw flash effect (after restore, covers full screen)
    this.screenEffects.drawFlash(ctx, this.canvas.width, this.canvas.height);

    // Draw UI (not affected by shake)
    this.uiManager.drawScore(this.score);
}
```

## v0.6 NEW: Extended Game States

**Use stage clear and pause states:**

```javascript
// Stage clear (when all enemies defeated)
if (this.enemies.length === 0) {
    this.stageClear(500);  // 500 bonus points
    // Game will show stage clear screen, then call onStageClearComplete()
}

// Override to set up next stage
onStageClearComplete() {
    this.currentStage++;
    this.spawnNextWave();
    this.stateManager.setState(GameStateManager.STATES.PLAYING);
}

// Boss fight state (optional)
if (this.score >= 1000 && !this.bossSpawned) {
    this.startBossFight();
    this.spawnBoss();
}

// Pause is automatic with B button, but you can also:
// - Game loop already handles PAUSED state
// - Drawing game + pause overlay is automatic
```

## IMPORTANT: Background Color Restriction

**DO NOT use `#0f0f0f` as the game background color.**

- `#0f0f0f` is reserved for the title screen only
- Use `#000000` (pure black) or other dark colors for game backgrounds
- This is required for automated visual testing to detect the title→game transition

## Example: Drawing Sprites

```javascript
drawGame(ctx) {
    // Clear screen - use #000000 (NOT #0f0f0f which is reserved for title)
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw player
    const playerImg = this.assets.getImage('player');
    if (playerImg) {
        ctx.drawImage(playerImg, this.player.x, this.player.y,
                     this.player.width, this.player.height);
    } else {
        // Fallback if image didn't load
        ctx.fillStyle = '#0f0';
        ctx.fillRect(this.player.x, this.player.y,
                    this.player.width, this.player.height);
    }

    // Draw enemies with validation to prevent drawImage errors
    this.enemies.forEach(enemy => {
        // CRITICAL: Validate coordinates and dimensions before drawing
        if (enemy && typeof enemy.x === 'number' && typeof enemy.y === 'number' &&
            enemy.width > 0 && enemy.height > 0 &&
            !isNaN(enemy.x) && !isNaN(enemy.y)) {
            const enemyImg = this.assets.getImage('enemy');
            if (enemyImg) {
                ctx.drawImage(enemyImg, enemy.x, enemy.y, enemy.width, enemy.height);
            } else {
                ctx.fillStyle = '#f00';
                ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            }
        }
    });

    // Draw score (UIManager handles this)
    this.uiManager.drawScore(this.score);
}
```

**IMPORTANT - Preventing drawImage Errors**:
The most common runtime error is `"Failed to execute 'drawImage': Overload resolution failed"`.
This happens when coordinates or dimensions are NaN, undefined, or invalid.

**ALWAYS validate before drawing**:
- Check `typeof x === 'number' && typeof y === 'number'`
- Check `!isNaN(x) && !isNaN(y)`
- Check `width > 0 && height > 0`
- Validate especially when drawing arrays of objects (forEach loops)

## Validation Checklist

Before finishing:
- [ ] `/public/game.js` is YOUR original implementation
- [ ] Game class extends GameEngine
- [ ] `loadAssets()` implemented
- [ ] `initGame()` implemented
- [ ] `updateGame()` implemented
- [ ] `drawGame()` implemented
- [ ] `check_syntax("/public/game.js")` returns "OK"
- [ ] No import/export statements
- [ ] Uses assets from `/public/assets/`
- [ ] Responds to controller input (D-PAD or arrow keys)
- [ ] Title screen displays on startup
- [ ] Game responds to SPACE/click to start
- [ ] Game over screen displays with score
- [ ] Can restart with SPACE/click

## Common Mistakes to Avoid

❌ Modifying gamelib.js, index.html, or style.css
❌ Not extending GameEngine
❌ Missing required methods (initGame, updateGame, drawGame)
❌ Creating custom game loop (gamelib.js provides this)
❌ Using non-existent assets
❌ Absolute paths for assets
❌ Import/export statements
❌ Not registering assets with loadImage/loadSound
❌ Copying the reference game.js without changes

✅ Extend GameEngine
✅ Implement the 3 required methods
✅ Use this.controller for input
✅ Use this.assets for sprites/sounds
✅ Focus on game logic ONLY
✅ Reference template game.js for PATTERNS
✅ Create ORIGINAL implementation
✅ Use relative asset paths

## Reference Implementation

The template includes a complete Space Invaders-like game:
- `/templates/game_template_advanced/game.js`

This shows:
- How to extend GameEngine
- Asset loading patterns
- Movement and collision detection
- Enemy AI patterns
- Scoring system
- Particle effects (explosions)

**Use this as a REFERENCE for patterns, but create something ORIGINAL based on the game design!**
