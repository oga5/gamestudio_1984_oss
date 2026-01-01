# GameStudio 1984 v0.3 - Simple Game Template

## File Structure

```
game/
├── index.html          # Main HTML file
├── style.css           # All styles in one file
├── game.js             # All game code in one file (includes controller)
└── assets/
    ├── images/         # PNG images (360x540 or smaller)
    └── sounds/         # WAV sound files
```

## Key Features

- **Simple Structure**: Only 3 core files (HTML, CSS, JS)
- **No Build Process**: Works directly in browser, no bundler needed
- **No ES6 Modules**: Uses standard script tags for maximum compatibility
- **Integrated Controller**: Virtual controller code is part of game.js
- **Asset Loading**: Built-in image and sound loader with progress tracking

## How to Use

### 1. Add Your Assets First

Place your PNG and WAV files in the assets directories:

```
assets/images/player.png
assets/images/enemy.png
assets/sounds/jump.wav
assets/sounds/shoot.wav
```

### 2. Load Assets in game.js

In the `Game.init()` method:

```javascript
async init() {
    // Load images
    await this.assets.loadImage('player', 'assets/images/player.png');
    await this.assets.loadImage('enemy', 'assets/images/enemy.png');

    // Load sounds
    await this.assets.loadSound('jump', 'assets/sounds/jump.wav');
    await this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');

    this.isLoading = false;
    this.start();
}
```

### 3. Use Assets in Your Game

```javascript
// Draw image
const playerImg = this.assets.getImage('player');
if (playerImg) {
    this.ctx.drawImage(playerImg, this.player.x, this.player.y);
}

// Play sound
if (this.controller.isJustPressed('a')) {
    this.assets.playSound('jump');
}
```

## Controller API

```javascript
// Check if button is currently pressed
if (this.controller.isPressed('left')) { /* ... */ }
if (this.controller.isPressed('right')) { /* ... */ }
if (this.controller.isPressed('up')) { /* ... */ }
if (this.controller.isPressed('down')) { /* ... */ }
if (this.controller.isPressed('a')) { /* ... */ }
if (this.controller.isPressed('b')) { /* ... */ }

// Check if button was just pressed this frame
if (this.controller.isJustPressed('a')) { /* ... */ }

// Get directional input (-1, 0, 1)
const horizontal = this.controller.getHorizontal();  // -1 = left, 1 = right
const vertical = this.controller.getVertical();      // -1 = up, 1 = down
```

## Canvas Size

- Game canvas: 360x540 pixels
- Controller area: 360x100 pixels
- Total: 360x640 pixels (mobile vertical)

## Testing

1. Open `index.html` in a web browser
2. Use arrow keys or WASD on desktop
3. Use virtual controller on mobile/touch devices

## Tips for v0.3 Development

1. **Create assets first** using the image/sound generation tools
2. **Only use assets that were successfully created**
3. **Keep all game logic in game.js** - no additional files needed
4. **Test frequently** by opening index.html in browser
5. **Use console.log()** for debugging

## Common Patterns

### Loading Multiple Assets

```javascript
async init() {
    const assets = [
        this.assets.loadImage('bg', 'assets/images/background.png'),
        this.assets.loadImage('player', 'assets/images/player.png'),
        this.assets.loadSound('bgm', 'assets/sounds/music.wav')
    ];

    await Promise.all(assets);

    this.isLoading = false;
    this.start();
}
```

### Simple Collision Detection

```javascript
function collides(a, b) {
    return a.x < b.x + b.width &&
           a.x + a.width > b.x &&
           a.y < b.y + b.height &&
           a.y + a.height > b.y;
}
```

### Drawing Text

```javascript
this.ctx.fillStyle = '#fff';
this.ctx.font = '16px monospace';
this.ctx.textAlign = 'center';
this.ctx.fillText('SCORE: ' + this.score, 180, 30);
this.ctx.textAlign = 'left';
```
