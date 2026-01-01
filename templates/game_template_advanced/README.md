# GameStudio 1984 v0.4 - Advanced Game Template

## Overview

This is the **advanced game template** with a 2-layer architecture that separates:

- **gamelib.js** - Core game engine (DO NOT MODIFY)
- **game.js** - Your custom game implementation (REPLACE COMPLETELY)

This design allows you to focus entirely on game logic while the infrastructure (state management, UI, input handling) is managed automatically.

## Architecture

### Layer 1: gamelib.js (Game Library)

The game library provides:

- **GameStateManager**: Handles LOADING → TITLE → PLAYING → GAME_OVER states
- **VirtualController**: Input handling for all buttons/keys
- **AssetLoader**: Async image and sound loading
- **UIManager**: Title screen, game over screen, score display
- **GameEngine**: Main loop with 60 FPS control and state machine

### Layer 2: game.js (Your Game)

Your game extends `GameEngine` and implements:

- **initGame()**: Initialize game state
- **updateGame(deltaTime)**: Update game logic each frame
- **drawGame(ctx)**: Render graphics each frame

## Files

```
game_template_advanced/
├── gamelib.js       ← Core library (DO NOT MODIFY)
├── game.js          ← Sample implementation (REPLACE WITH YOUR GAME)
├── index.html       ← Can customize title/styling
├── style.css        ← Can customize appearance
└── README.md        ← This file
```

## Quick Start

### 1. Replace game.js

The sample `game.js` shows a Space Invaders-like game. To create your own:

```javascript
class MyGame extends GameEngine {
    constructor() {
        super('game-canvas', {
            title: 'MY GAME',
            description: 'Brief description'
        });
    }

    loadAssets() {
        this.assets.loadImage('player', 'assets/images/player.png');
        this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');
    }

    initGame() {
        // Set up game state
        this.score = 0;
        this.player = { x: 0, y: 0, ... };
    }

    updateGame(deltaTime) {
        // Update game logic
    }

    drawGame(ctx) {
        // Draw game graphics
    }
}

window.addEventListener('load', () => {
    const game = new MyGame();
    game.startGame();
});
```

### 2. Use gamelib.js Features

Access these in your game methods:

```javascript
// Input
this.controller.getHorizontal()          // -1, 0, or 1
this.controller.isPressed('a')           // Boolean
this.controller.isJustPressed('a')       // Boolean

// State Management
this.stateManager.setState(GameStateManager.STATES.GAME_OVER)
// Valid states: LOADING, TITLE, PLAYING, GAME_OVER, PAUSED

// Assets
this.assets.loadImage('name', 'path')
this.assets.playSound('shoot')
this.assets.getImage('name')

// UI
this.uiManager.drawScore(score)

// Screen
this.gameOver()                          // End the game
this.getScreenWidth()                    // 360
this.getScreenHeight()                   // 540

// Collision
this.collides(rect1, rect2)
```

### 3. Register and Use Assets

```javascript
// In loadAssets()
this.assets.loadImage('player', 'assets/images/player.png');
this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');

// In drawGame()
const img = this.assets.getImage('player');
if (img) {
    ctx.drawImage(img, x, y, width, height);
}

// In updateGame()
if (this.controller.isJustPressed('a')) {
    this.playSound('shoot');
}
```

## Game Flow

```
Window Load
    ↓
loadAssets() - Load images and sounds
    ↓
initGame() - Initialize game state
    ↓
TITLE STATE - Show title screen
    ↓ (SPACE/CLICK)
PLAYING STATE - Run game logic
    ├─ updateGame()
    └─ drawGame()
    ↓ (Game Over)
GAME_OVER STATE - Show game over screen
    ↓ (SPACE/CLICK)
TITLE STATE - Back to title
```

## Example Implementation (Space Invaders)

See the provided `game.js` for a complete working example including:

- Player movement
- Enemy AI
- Bullet physics
- Collision detection
- Score tracking
- Explosion effects

## What gamelib.js Provides

✅ **Automatic**:
- Main game loop (60 FPS)
- Title screen display
- Game over screen display
- State transitions
- Input handling (keyboard + touch)
- Loading screen

❌ **NOT Automatic** (You implement in game.js):
- Game logic
- Sprite movement
- Collision detection
- Scoring system
- Game mechanics

## DO NOT

❌ Modify gamelib.js
❌ Create multiple .js files
❌ Use ES6 modules (import/export)
❌ Manually implement game loop
❌ Manually implement state machine

## DO

✅ Extend GameEngine
✅ Implement the 3 required methods
✅ Use assets from /public/assets/
✅ Reference the sample game.js
✅ Focus on game logic only

## Testing Your Game

1. Place assets in `/public/assets/images/` and `/public/assets/sounds/`
2. Test locally with a web server
3. Check browser console for errors
4. Use firefoxtester for automated testing

## Common Patterns

### Controlling the Player

```javascript
updateGame(deltaTime) {
    const h = this.controller.getHorizontal();
    this.player.x += h * this.player.speed;
}
```

### Shooting

```javascript
if (this.controller.isJustPressed('a')) {
    this.bullets.push({
        x: this.player.x,
        y: this.player.y,
        speed: 300
    });
    this.playSound('shoot');
}
```

### Collision Detection

```javascript
for (let i = 0; i < this.enemies.length; i++) {
    if (this.collides(this.player, this.enemies[i])) {
        this.gameOver();
    }
}
```

### End Game

```javascript
if (this.enemies.length === 0) {
    this.gameOver();
}
```

## Debugging Tips

- Check browser console for JavaScript errors
- Use `console.log()` in updateGame/drawGame
- Check that assets are in correct paths
- Verify `check_syntax()` passes
- Test with firefoxtester

## Questions?

Refer to the sample `game.js` for implementation patterns and the gamelib.js source code for available methods.
