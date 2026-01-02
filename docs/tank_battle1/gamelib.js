/**
 * GameStudio 1984 v0.7 - Game Library (gamelib.js)
 *
 * DO NOT MODIFY THIS FILE
 *
 * This file provides the core game engine infrastructure:
 * - Game state management (LOADING, TITLE, PLAYING, GAME_OVER, GAME_CLEAR, STAGE_CLEAR, PAUSED, CUTSCENE, BOSS_FIGHT)
 * - Virtual controller input handling
 * - Asset loading and management (with loop/stop/volume support)
 * - Collision detection (AABB, circle, circle-rect)
 * - Particle system for visual effects
 * - Screen effects (shake, flash, trails)
 * - Sprite animation support
 * - Main game loop with FPS control
 * - UI rendering (title, game over, game clear, stage clear, pause screens)
 *
 * v0.7 New Features:
 * - GAME_CLEAR state: Distinct state for game victory (separate from GAME_OVER for defeat)
 * - gameClear() method: Call this when player completes the game successfully
 * - drawGameClear(): Golden "GAME CLEAR!" screen with congratulations message
 * - TileMapSystem, CameraSystem, StageSystem for complex game development
 *
 * v0.6 Features:
 * - CollisionSystem: circleCollision, circleRectCollision, distance
 * - ParticleSystem: emit, update, draw with gravity support
 * - ScreenEffects: shake, flash, trails
 * - SpriteAnimation: frame-based animation
 * - Extended states: STAGE_CLEAR, CUTSCENE, BOSS_FIGHT
 * - Sound: playSoundLoop, stopSound, setVolume, stopAllLoops
 *
 * Your game.js should extend GameEngine and implement:
 * - initGame()
 * - updateGame(deltaTime)
 * - drawGame(ctx)
 */

// ============================================
// GAME STATE MANAGER
// ============================================
class GameStateManager {
    static STATES = {
        LOADING: 'loading',
        TITLE: 'title',
        PLAYING: 'playing',
        GAME_OVER: 'gameOver',
        PAUSED: 'paused',
        // v0.6: Extended states
        STAGE_CLEAR: 'stageClear',
        CUTSCENE: 'cutscene',
        BOSS_FIGHT: 'bossFight',
        // v0.7: Game clear state (all stages completed)
        GAME_CLEAR: 'gameClear'
    };

    constructor() {
        this.current = GameStateManager.STATES.LOADING;
        this.stateTransitionTime = Date.now();
    }

    setState(newState) {
        if (Object.values(GameStateManager.STATES).includes(newState)) {
            this.current = newState;
            this.stateTransitionTime = Date.now();
        } else {
            throw new Error(`Invalid state: ${newState}. Valid states are: ${Object.values(GameStateManager.STATES).join(', ')}`);
        }
    }

    is(state) {
        return this.current === state;
    }

    /**
     * Check if enough time has passed since state transition to accept input
     * @param {number} minimumDelay - Minimum delay in milliseconds
     * @returns {boolean} True if input can be accepted
     */
    canAcceptInput(minimumDelay = 0) {
        return (Date.now() - this.stateTransitionTime) >= minimumDelay;
    }
}

// ============================================
// VIRTUAL CONTROLLER
// ============================================
class VirtualController {
    constructor() {
        // Button states
        this.buttons = {
            up: false,
            down: false,
            left: false,
            right: false,
            a: false,
            b: false,
            pause: false
        };

        // Previous frame states (for just pressed detection)
        this.prevButtons = { ...this.buttons };

        // DOM elements
        this.elements = {
            a: document.getElementById('btn-a'),
            b: document.getElementById('btn-b')
        };

        // Virtual joystick state
        this.joystick = {
            active: false,
            neutralX: 0,  // Tap start position as neutral
            neutralY: 0   // Tap start position as neutral
        };

        this.setupEventListeners();
        this.setupKeyboardListeners();
        this.setupJoystick();
        this.setupFullScreenTouchAreas();
    }

    setupEventListeners() {
        const buttonNames = ['a', 'b'];

        buttonNames.forEach(name => {
            const element = this.elements[name];
            if (!element) return;

            // Touch events
            element.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.setButton(name, true);
            }, { passive: false });

            element.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.setButton(name, false);
            }, { passive: false });

            element.addEventListener('touchcancel', (e) => {
                e.preventDefault();
                this.setButton(name, false);
            }, { passive: false });

            // Mouse events (for desktop testing)
            element.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.setButton(name, true);
            });

            element.addEventListener('mouseup', (e) => {
                e.preventDefault();
                this.setButton(name, false);
            });

            element.addEventListener('mouseleave', () => {
                this.setButton(name, false);
            });
        });
    }

    setupKeyboardListeners() {
        const keyMap = {
            'ArrowUp': 'up',
            'ArrowDown': 'down',
            'ArrowLeft': 'left',
            'ArrowRight': 'right',
            'KeyW': 'up',
            'KeyS': 'down',
            'KeyA': 'left',
            'KeyD': 'right',
            'KeyZ': 'a',
            'KeyX': 'b',
            'Space': 'a',
            'ShiftLeft': 'b',
            'ShiftRight': 'b',
            'KeyP': 'pause'
        };

        document.addEventListener('keydown', (e) => {
            const button = keyMap[e.code];
            if (button) {
                e.preventDefault();
                this.setButton(button, true);
            }
        });

        document.addEventListener('keyup', (e) => {
            const button = keyMap[e.code];
            if (button) {
                e.preventDefault();
                this.setButton(button, false);
            }
        });
    }

    setButton(name, pressed) {
        this.buttons[name] = pressed;
        const element = this.elements[name];
        if (element) {
            if (pressed) {
                element.classList.add('pressed');
            } else {
                element.classList.remove('pressed');
            }
        }
    }

    isPressed(button) {
        return this.buttons[button] === true;
    }

    isJustPressed(button) {
        return this.buttons[button] && !this.prevButtons[button];
    }

    isJustReleased(button) {
        return !this.buttons[button] && this.prevButtons[button];
    }

    getHorizontal() {
        let h = 0;
        if (this.buttons.left) h -= 1;
        if (this.buttons.right) h += 1;
        return h;
    }

    getVertical() {
        let v = 0;
        if (this.buttons.up) v -= 1;
        if (this.buttons.down) v += 1;
        return v;
    }

    update() {
        this.prevButtons = { ...this.buttons };
    }

    reset() {
        Object.keys(this.buttons).forEach(key => {
            this.setButton(key, false);
        });
        this.prevButtons = { ...this.buttons };
    }

    setupJoystick() {
        const joystickTouchArea = document.getElementById('joystickTouchArea');
        const joystickBase = document.getElementById('joystickBase');
        const joystickStick = document.getElementById('joystickStick');

        if (!joystickTouchArea || !joystickBase || !joystickStick) {
            console.warn('Joystick elements not found');
            return;
        }

        const handleJoystickStart = (e) => {
            e.preventDefault();
            this.joystick.active = true;
            const touch = e.touches ? e.touches[0] : e;
            // Set tap start position as neutral (center) point
            this.joystick.neutralX = touch.clientX;
            this.joystick.neutralY = touch.clientY;
            this.updateJoystick(touch, joystickBase, joystickStick);
        };

        const handleJoystickMove = (e) => {
            if (!this.joystick.active) return;
            e.preventDefault();
            const touch = e.touches ? e.touches[0] : e;
            this.updateJoystick(touch, joystickBase, joystickStick);
        };

        const handleJoystickEnd = (e) => {
            e.preventDefault();
            this.joystick.active = false;
            joystickStick.style.transform = 'translate(0, 0)';
            this.buttons.left = false;
            this.buttons.right = false;
            this.buttons.up = false;
            this.buttons.down = false;
        };

        // Touch events
        joystickTouchArea.addEventListener('touchstart', handleJoystickStart, { passive: false });
        joystickTouchArea.addEventListener('touchmove', handleJoystickMove, { passive: false });
        joystickTouchArea.addEventListener('touchend', handleJoystickEnd, { passive: false });

        // Mouse events (for desktop testing)
        joystickTouchArea.addEventListener('mousedown', handleJoystickStart);
        window.addEventListener('mousemove', handleJoystickMove);
        window.addEventListener('mouseup', handleJoystickEnd);
    }

    updateJoystick(touch, base, stick) {
        // Calculate delta from neutral (tap start) position
        let deltaX = touch.clientX - this.joystick.neutralX;
        let deltaY = touch.clientY - this.joystick.neutralY;

        const distance = Math.sqrt(deltaX ** 2 + deltaY ** 2);
        const rect = base.getBoundingClientRect();
        const maxDistance = rect.width / 2 - 10;

        // Clamp to maximum distance
        if (distance > maxDistance) {
            const angle = Math.atan2(deltaY, deltaX);
            deltaX = Math.cos(angle) * maxDistance;
            deltaY = Math.sin(angle) * maxDistance;
        }

        // Update visual position
        stick.style.transform = `translate(${deltaX}px, ${deltaY}px)`;

        // Update input state based on threshold (supports diagonal input)
        const threshold = 20;
        this.buttons.left = deltaX < -threshold;
        this.buttons.right = deltaX > threshold;
        this.buttons.up = deltaY < -threshold;
        this.buttons.down = deltaY > threshold;
    }

    setupFullScreenTouchAreas() {
        const gameContainer = document.getElementById('game-container');
        if (!gameContainer) {
            console.warn('game-container not found');
            return;
        }

        // Track active touches for each area
        this.touchTracking = {
            joystick: null,
            aButton: null
        };

        const handleTouchStart = (e) => {
            const touches = e.changedTouches;
            for (let i = 0; i < touches.length; i++) {
                const touch = touches[i];
                const rect = gameContainer.getBoundingClientRect();
                const x = touch.clientX - rect.left;
                const y = touch.clientY - rect.top;

                // Check if touch is on B button first (priority)
                const btnB = this.elements.b;
                if (btnB) {
                    const btnRect = btnB.getBoundingClientRect();
                    const containerRect = gameContainer.getBoundingClientRect();
                    const btnRelativeX = btnRect.left - containerRect.left;
                    const btnRelativeY = btnRect.top - containerRect.top;
                    const btnWidth = btnRect.width;
                    const btnHeight = btnRect.height;

                    if (x >= btnRelativeX && x <= btnRelativeX + btnWidth &&
                        y >= btnRelativeY && y <= btnRelativeY + btnHeight) {
                        // B button takes priority - let the existing handler deal with it
                        continue;
                    }
                }

                // Bottom-left quarter: joystick area (x < 180, y >= 320)
                if (x < 180 && y >= 320) {
                    // Only activate if no joystick touch is active
                    if (!this.touchTracking.joystick) {
                        this.touchTracking.joystick = touch.identifier;
                        this.joystick.active = true;
                        this.joystick.neutralX = touch.clientX;
                        this.joystick.neutralY = touch.clientY;

                        const joystickBase = document.getElementById('joystickBase');
                        const joystickStick = document.getElementById('joystickStick');
                        if (joystickBase && joystickStick) {
                            this.updateJoystick(touch, joystickBase, joystickStick);
                        }
                    }
                }
                // Bottom-right quarter: A button area (x >= 180, y >= 320)
                else if (x >= 180 && y >= 320) {
                    // Only activate if no A button touch is active
                    if (!this.touchTracking.aButton) {
                        this.touchTracking.aButton = touch.identifier;
                        this.setButton('a', true);
                    }
                }
            }
        };

        const handleTouchMove = (e) => {
            const touches = e.changedTouches;
            for (let i = 0; i < touches.length; i++) {
                const touch = touches[i];

                // Update joystick if this is the joystick touch
                if (this.touchTracking.joystick === touch.identifier && this.joystick.active) {
                    const joystickBase = document.getElementById('joystickBase');
                    const joystickStick = document.getElementById('joystickStick');
                    if (joystickBase && joystickStick) {
                        this.updateJoystick(touch, joystickBase, joystickStick);
                    }
                }
            }
        };

        const handleTouchEnd = (e) => {
            const touches = e.changedTouches;
            for (let i = 0; i < touches.length; i++) {
                const touch = touches[i];

                // Release joystick if this was the joystick touch
                if (this.touchTracking.joystick === touch.identifier) {
                    this.touchTracking.joystick = null;
                    this.joystick.active = false;
                    const joystickStick = document.getElementById('joystickStick');
                    if (joystickStick) {
                        joystickStick.style.transform = 'translate(0, 0)';
                    }
                    this.buttons.left = false;
                    this.buttons.right = false;
                    this.buttons.up = false;
                    this.buttons.down = false;
                }

                // Release A button if this was the A button touch
                if (this.touchTracking.aButton === touch.identifier) {
                    this.touchTracking.aButton = null;
                    this.setButton('a', false);
                }
            }
        };

        // Add touch event listeners to game container
        gameContainer.addEventListener('touchstart', handleTouchStart, { passive: true });
        gameContainer.addEventListener('touchmove', handleTouchMove, { passive: true });
        gameContainer.addEventListener('touchend', handleTouchEnd, { passive: true });
        gameContainer.addEventListener('touchcancel', handleTouchEnd, { passive: true });
    }
}

// ============================================
// ASSET LOADER
// ============================================
class AssetLoader {
    constructor() {
        this.images = {};
        this.sounds = {};
        this.loadedCount = 0;
        this.totalCount = 0;
        this.loopingSounds = new Set(); // Track looping sounds
    }

    loadImage(name, path) {
        this.totalCount++;
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.images[name] = img;
                this.loadedCount++;
                resolve(img);
            };
            img.onerror = () => {
                console.warn(`Failed to load image: ${path}`);
                this.loadedCount++;
                resolve(null);
            };
            img.src = path;
        });
    }

    loadSound(name, path) {
        this.totalCount++;
        return new Promise((resolve) => {
            const audio = new Audio();
            audio.oncanplaythrough = () => {
                this.sounds[name] = audio;
                this.loadedCount++;
                resolve(audio);
            };
            audio.onerror = () => {
                console.warn(`Failed to load sound: ${path}`);
                this.loadedCount++;
                resolve(null);
            };
            audio.src = path;
        });
    }

    getProgress() {
        if (this.totalCount === 0) return 1;
        return this.loadedCount / this.totalCount;
    }

    playSound(name) {
        const sound = this.sounds[name];
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(e => console.warn('Sound play failed:', e));
        }
    }

    // v0.6: Loop sound playback
    playSoundLoop(name) {
        const sound = this.sounds[name];
        if (sound) {
            sound.loop = true;
            sound.play().catch(e => console.warn('Sound loop failed:', e));
            this.loopingSounds.add(name);
        }
    }

    // v0.6: Stop sound playback
    stopSound(name) {
        const sound = this.sounds[name];
        if (sound) {
            sound.pause();
            sound.currentTime = 0;
            sound.loop = false;
            this.loopingSounds.delete(name);
        }
    }

    // v0.6: Stop all looping sounds
    stopAllLoops() {
        this.loopingSounds.forEach(name => this.stopSound(name));
    }

    // v0.6: Set volume (0.0 to 1.0)
    setVolume(name, volume) {
        const sound = this.sounds[name];
        if (sound) {
            sound.volume = Math.max(0, Math.min(1, volume));
        }
    }

    getImage(name) {
        return this.images[name] || null;
    }

    getSound(name) {
        return this.sounds[name] || null;
    }
}

// ============================================
// COLLISION SYSTEM (v0.6)
// ============================================
class CollisionSystem {
    /**
     * Check collision between two rectangles (AABB)
     */
    static rectCollision(rect1, rect2) {
        return rect1.x < rect2.x + rect2.width &&
               rect1.x + rect1.width > rect2.x &&
               rect1.y < rect2.y + rect2.height &&
               rect1.y + rect1.height > rect2.y;
    }

    /**
     * Check collision between two circles
     * @param {Object} circle1 - {x, y, radius}
     * @param {Object} circle2 - {x, y, radius}
     */
    static circleCollision(circle1, circle2) {
        const dx = circle1.x - circle2.x;
        const dy = circle1.y - circle2.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        return distance < circle1.radius + circle2.radius;
    }

    /**
     * Check collision between a circle and a rectangle
     * @param {Object} circle - {x, y, radius}
     * @param {Object} rect - {x, y, width, height}
     */
    static circleRectCollision(circle, rect) {
        // Find the closest point on the rectangle to the circle
        const closestX = Math.max(rect.x, Math.min(circle.x, rect.x + rect.width));
        const closestY = Math.max(rect.y, Math.min(circle.y, rect.y + rect.height));

        // Calculate distance from circle center to closest point
        const dx = circle.x - closestX;
        const dy = circle.y - closestY;

        return (dx * dx + dy * dy) < (circle.radius * circle.radius);
    }

    /**
     * Get distance between two points
     */
    static distance(x1, y1, x2, y2) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        return Math.sqrt(dx * dx + dy * dy);
    }
}

// ============================================
// PARTICLE SYSTEM (v0.6)
// ============================================
class ParticleSystem {
    constructor() {
        this.particles = [];
    }

    /**
     * Emit particles from a position
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {Object} config - Configuration object
     *   - count: number of particles (default: 10)
     *   - color: particle color (default: '#ffff00')
     *   - speed: particle speed (default: 2)
     *   - lifetime: particle lifetime in seconds (default: 1.0)
     *   - size: particle size (default: 3)
     *   - gravity: gravity effect (default: 0)
     */
    emit(x, y, config = {}) {
        const count = config.count || 10;
        const color = config.color || '#ffff00';
        const speed = config.speed || 2;
        const lifetime = config.lifetime || 1.0;
        const size = config.size || 3;
        const gravity = config.gravity || 0;

        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const randomSpeed = speed * (0.5 + Math.random());
            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * randomSpeed,
                vy: Math.sin(angle) * randomSpeed,
                color: color,
                size: size,
                life: lifetime,
                maxLife: lifetime,
                gravity: gravity
            });
        }
    }

    /**
     * Update all particles
     */
    update(deltaTime) {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];

            // Update position
            p.x += p.vx * deltaTime * 60;
            p.y += p.vy * deltaTime * 60;

            // Apply gravity
            p.vy += p.gravity * deltaTime * 60;

            // Update lifetime
            p.life -= deltaTime;

            // Remove dead particles
            if (p.life <= 0) {
                this.particles.splice(i, 1);
            }
        }
    }

    /**
     * Draw all particles
     */
    draw(ctx) {
        this.particles.forEach(p => {
            const alpha = p.life / p.maxLife;
            ctx.fillStyle = p.color;
            ctx.globalAlpha = alpha;
            ctx.fillRect(p.x - p.size/2, p.y - p.size/2, p.size, p.size);
        });
        ctx.globalAlpha = 1.0;
    }

    /**
     * Clear all particles
     */
    clear() {
        this.particles = [];
    }

    /**
     * Get particle count
     */
    getCount() {
        return this.particles.length;
    }
}

// ============================================
// TILEMAP SYSTEM (v0.7)
// ============================================
class TileMapSystem {
    /**
     * Create a tilemap system
     * @param {number} tileWidth - Width of each tile in pixels
     * @param {number} tileHeight - Height of each tile in pixels
     * @param {number} mapWidth - Width of the map in tiles
     * @param {number} mapHeight - Height of the map in tiles
     */
    constructor(tileWidth, tileHeight, mapWidth, mapHeight) {
        this.tileWidth = tileWidth;
        this.tileHeight = tileHeight;
        this.mapWidth = mapWidth;
        this.mapHeight = mapHeight;
        this.tiles = [];
        this.tileset = null; // Optional tileset image

        // Initialize empty map
        for (let y = 0; y < mapHeight; y++) {
            this.tiles[y] = [];
            for (let x = 0; x < mapWidth; x++) {
                this.tiles[y][x] = 0; // 0 = empty tile
            }
        }
    }

    /**
     * Load map data from 2D array
     * @param {number[][]} mapData - 2D array of tile IDs
     */
    loadMap(mapData) {
        this.mapHeight = mapData.length;
        this.mapWidth = mapData[0] ? mapData[0].length : 0;
        this.tiles = mapData.map(row => [...row]);
    }

    /**
     * Set tileset image
     * @param {HTMLImageElement} image - Tileset image
     */
    setTileset(image) {
        this.tileset = image;
    }

    /**
     * Get tile at position
     * @param {number} x - X position in tiles
     * @param {number} y - Y position in tiles
     * @returns {number} Tile ID
     */
    getTile(x, y) {
        if (x < 0 || x >= this.mapWidth || y < 0 || y >= this.mapHeight) {
            return -1; // Out of bounds
        }
        return this.tiles[y][x];
    }

    /**
     * Set tile at position
     * @param {number} x - X position in tiles
     * @param {number} y - Y position in tiles
     * @param {number} tileId - Tile ID to set
     */
    setTile(x, y, tileId) {
        if (x >= 0 && x < this.mapWidth && y >= 0 && y < this.mapHeight) {
            this.tiles[y][x] = tileId;
        }
    }

    /**
     * Get tile at world position
     * @param {number} worldX - X position in pixels
     * @param {number} worldY - Y position in pixels
     * @returns {number} Tile ID
     */
    getTileAtPosition(worldX, worldY) {
        const tileX = Math.floor(worldX / this.tileWidth);
        const tileY = Math.floor(worldY / this.tileHeight);
        return this.getTile(tileX, tileY);
    }

    /**
     * Check collision with solid tiles
     * @param {Object} rect - Rectangle with x, y, width, height
     * @param {number[]} solidTiles - Array of solid tile IDs
     * @returns {boolean} True if colliding with solid tile
     */
    checkCollision(rect, solidTiles = [1]) {
        const left = Math.floor(rect.x / this.tileWidth);
        const right = Math.floor((rect.x + rect.width - 1) / this.tileWidth);
        const top = Math.floor(rect.y / this.tileHeight);
        const bottom = Math.floor((rect.y + rect.height - 1) / this.tileHeight);

        for (let y = top; y <= bottom; y++) {
            for (let x = left; x <= right; x++) {
                const tile = this.getTile(x, y);
                if (solidTiles.includes(tile)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Draw tilemap with camera offset
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Object} camera - Camera object with x, y properties
     * @param {Object} tileColors - Map of tile IDs to colors
     */
    draw(ctx, camera = {x: 0, y: 0}, tileColors = {}) {
        // Calculate visible tile range
        const startX = Math.max(0, Math.floor(camera.x / this.tileWidth));
        const startY = Math.max(0, Math.floor(camera.y / this.tileHeight));
        const endX = Math.min(this.mapWidth, Math.ceil((camera.x + ctx.canvas.width) / this.tileWidth));
        const endY = Math.min(this.mapHeight, Math.ceil((camera.y + ctx.canvas.height) / this.tileHeight));

        // Draw visible tiles
        for (let y = startY; y < endY; y++) {
            for (let x = startX; x < endX; x++) {
                const tileId = this.getTile(x, y);
                if (tileId === 0) continue; // Skip empty tiles

                const screenX = x * this.tileWidth - camera.x;
                const screenY = y * this.tileHeight - camera.y;

                if (this.tileset && tileId > 0) {
                    // Draw from tileset image (if available)
                    const tilesPerRow = Math.floor(this.tileset.width / this.tileWidth);
                    const srcX = ((tileId - 1) % tilesPerRow) * this.tileWidth;
                    const srcY = Math.floor((tileId - 1) / tilesPerRow) * this.tileHeight;

                    ctx.drawImage(
                        this.tileset,
                        srcX, srcY, this.tileWidth, this.tileHeight,
                        screenX, screenY, this.tileWidth, this.tileHeight
                    );
                } else {
                    // Draw colored rectangles
                    ctx.fillStyle = tileColors[tileId] || '#888';
                    ctx.fillRect(screenX, screenY, this.tileWidth, this.tileHeight);
                }
            }
        }
    }

    /**
     * Get map dimensions in pixels
     */
    getPixelWidth() {
        return this.mapWidth * this.tileWidth;
    }

    getPixelHeight() {
        return this.mapHeight * this.tileHeight;
    }
}

// ============================================
// CAMERA SYSTEM (v0.7)
// ============================================
class CameraSystem {
    /**
     * Create a camera system
     * @param {number} screenWidth - Width of the screen
     * @param {number} screenHeight - Height of the screen
     * @param {number} worldWidth - Width of the game world
     * @param {number} worldHeight - Height of the game world
     */
    constructor(screenWidth, screenHeight, worldWidth = screenWidth, worldHeight = screenHeight) {
        this.x = 0;
        this.y = 0;
        this.screenWidth = screenWidth;
        this.screenHeight = screenHeight;
        this.worldWidth = worldWidth;
        this.worldHeight = worldHeight;

        // Follow settings
        this.target = null;
        this.followSpeed = 1.0; // 1.0 = instant, lower = smooth
        this.deadzone = {
            x: screenWidth * 0.2,
            y: screenHeight * 0.2,
            width: screenWidth * 0.2,
            height: screenHeight * 0.2
        };

        // Shake effect
        this.shakeIntensity = 0;
        this.shakeDuration = 0;
        this.shakeOffset = {x: 0, y: 0};
    }

    /**
     * Set camera bounds
     * @param {number} worldWidth - Width of the world
     * @param {number} worldHeight - Height of the world
     */
    setBounds(worldWidth, worldHeight) {
        this.worldWidth = worldWidth;
        this.worldHeight = worldHeight;
    }

    /**
     * Set target to follow
     * @param {Object} target - Object with x, y properties
     * @param {number} speed - Follow speed (0-1, default 1.0)
     */
    follow(target, speed = 1.0) {
        this.target = target;
        this.followSpeed = speed;
    }

    /**
     * Stop following target
     */
    stopFollow() {
        this.target = null;
    }

    /**
     * Set camera position directly
     * @param {number} x - X position
     * @param {number} y - Y position
     */
    setPosition(x, y) {
        this.x = x;
        this.y = y;
        this.clampToBounds();
    }

    /**
     * Move camera by offset
     * @param {number} dx - X offset
     * @param {number} dy - Y offset
     */
    move(dx, dy) {
        this.x += dx;
        this.y += dy;
        this.clampToBounds();
    }

    /**
     * Clamp camera to world bounds
     */
    clampToBounds() {
        this.x = Math.max(0, Math.min(this.x, this.worldWidth - this.screenWidth));
        this.y = Math.max(0, Math.min(this.y, this.worldHeight - this.screenHeight));
    }

    /**
     * Shake the camera
     * @param {number} intensity - Shake intensity in pixels
     * @param {number} duration - Shake duration in seconds
     */
    shake(intensity, duration) {
        this.shakeIntensity = intensity;
        this.shakeDuration = duration;
    }

    /**
     * Update camera (call every frame)
     * @param {number} deltaTime - Time since last frame in seconds
     */
    update(deltaTime) {
        // Follow target
        if (this.target) {
            const targetX = this.target.x - this.screenWidth / 2;
            const targetY = this.target.y - this.screenHeight / 2;

            if (this.followSpeed >= 1.0) {
                // Instant follow
                this.x = targetX;
                this.y = targetY;
            } else {
                // Smooth follow
                this.x += (targetX - this.x) * this.followSpeed;
                this.y += (targetY - this.y) * this.followSpeed;
            }

            this.clampToBounds();
        }

        // Update shake
        if (this.shakeDuration > 0) {
            this.shakeDuration -= deltaTime;
            const angle = Math.random() * Math.PI * 2;
            this.shakeOffset.x = Math.cos(angle) * this.shakeIntensity;
            this.shakeOffset.y = Math.sin(angle) * this.shakeIntensity;
        } else {
            this.shakeOffset.x = 0;
            this.shakeOffset.y = 0;
        }
    }

    /**
     * Get camera offset including shake
     * @returns {Object} Object with x, y properties
     */
    getOffset() {
        return {
            x: this.x + this.shakeOffset.x,
            y: this.y + this.shakeOffset.y
        };
    }

    /**
     * Convert world coordinates to screen coordinates
     * @param {number} worldX - World X position
     * @param {number} worldY - World Y position
     * @returns {Object} Object with x, y screen coordinates
     */
    worldToScreen(worldX, worldY) {
        const offset = this.getOffset();
        return {
            x: worldX - offset.x,
            y: worldY - offset.y
        };
    }

    /**
     * Convert screen coordinates to world coordinates
     * @param {number} screenX - Screen X position
     * @param {number} screenY - Screen Y position
     * @returns {Object} Object with x, y world coordinates
     */
    screenToWorld(screenX, screenY) {
        const offset = this.getOffset();
        return {
            x: screenX + offset.x,
            y: screenY + offset.y
        };
    }

    /**
     * Check if a rectangle is visible on screen
     * @param {Object} rect - Rectangle with x, y, width, height
     * @returns {boolean} True if visible
     */
    isVisible(rect) {
        const offset = this.getOffset();
        return !(
            rect.x + rect.width < offset.x ||
            rect.x > offset.x + this.screenWidth ||
            rect.y + rect.height < offset.y ||
            rect.y > offset.y + this.screenHeight
        );
    }
}

// ============================================
// STAGE SYSTEM (v0.7)
// ============================================
class StageSystem {
    /**
     * Create a stage system
     */
    constructor() {
        this.stages = [];
        this.currentStageIndex = 0;
        this.stageData = null;
    }

    /**
     * Add a stage
     * @param {Object} stageConfig - Stage configuration
     */
    addStage(stageConfig) {
        this.stages.push(stageConfig);
    }

    /**
     * Load stages from array
     * @param {Object[]} stagesArray - Array of stage configurations
     */
    loadStages(stagesArray) {
        this.stages = stagesArray;
        this.currentStageIndex = 0;
    }

    /**
     * Get current stage
     * @returns {Object} Current stage data
     */
    getCurrentStage() {
        if (this.currentStageIndex >= 0 && this.currentStageIndex < this.stages.length) {
            return this.stages[this.currentStageIndex];
        }
        return null;
    }

    /**
     * Go to next stage
     * @returns {boolean} True if there is a next stage
     */
    nextStage() {
        if (this.currentStageIndex < this.stages.length - 1) {
            this.currentStageIndex++;
            return true;
        }
        return false;
    }

    /**
     * Go to previous stage
     * @returns {boolean} True if there is a previous stage
     */
    previousStage() {
        if (this.currentStageIndex > 0) {
            this.currentStageIndex--;
            return true;
        }
        return false;
    }

    /**
     * Go to specific stage
     * @param {number} stageIndex - Stage index
     * @returns {boolean} True if stage exists
     */
    gotoStage(stageIndex) {
        if (stageIndex >= 0 && stageIndex < this.stages.length) {
            this.currentStageIndex = stageIndex;
            return true;
        }
        return false;
    }

    /**
     * Get current stage number (1-based)
     * @returns {number} Current stage number
     */
    getStageNumber() {
        return this.currentStageIndex + 1;
    }

    /**
     * Get total number of stages
     * @returns {number} Total stages
     */
    getTotalStages() {
        return this.stages.length;
    }

    /**
     * Check if this is the last stage
     * @returns {boolean} True if last stage
     */
    isLastStage() {
        return this.currentStageIndex >= this.stages.length - 1;
    }

    /**
     * Check if this is the first stage
     * @returns {boolean} True if first stage
     */
    isFirstStage() {
        return this.currentStageIndex === 0;
    }

    /**
     * Reset to first stage
     */
    reset() {
        this.currentStageIndex = 0;
    }
}

// ============================================
// SCREEN EFFECTS (v0.6)
// ============================================
class ScreenEffects {
    constructor() {
        this.shakeIntensity = 0;
        this.shakeDuration = 0;
        this.shakeOffset = { x: 0, y: 0 };

        this.flashColor = null;
        this.flashDuration = 0;
        this.flashMaxDuration = 0;

        this.trails = [];
    }

    /**
     * Reset all effects
     */
    reset() {
        this.shakeIntensity = 0;
        this.shakeDuration = 0;
        this.shakeOffset = { x: 0, y: 0 };
        this.flashColor = null;
        this.flashDuration = 0;
        this.trails = [];
    }

    /**
     * Trigger screen shake effect
     * @param {number} intensity - Shake intensity in pixels (1-20)
     * @param {number} duration - Duration in seconds
     */
    shake(intensity, duration) {
        this.shakeIntensity = Math.min(20, Math.max(1, intensity));
        this.shakeDuration = duration;
    }

    /**
     * Trigger screen flash effect
     * @param {string} color - Flash color (e.g., '#ff0000')
     * @param {number} duration - Duration in seconds
     */
    flash(color, duration) {
        this.flashColor = color;
        this.flashDuration = duration;
        this.flashMaxDuration = duration;
    }

    /**
     * Add a trail point (for bullet/missile trails)
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {string} color - Trail color
     * @param {number} size - Trail size
     * @param {number} lifetime - Lifetime in seconds
     */
    addTrail(x, y, color = '#00ffff', size = 3, lifetime = 0.3) {
        this.trails.push({
            x: x,
            y: y,
            color: color,
            size: size,
            life: lifetime,
            maxLife: lifetime
        });
    }

    /**
     * Update all effects
     */
    update(deltaTime) {
        // Update shake
        if (this.shakeDuration > 0) {
            this.shakeDuration -= deltaTime;
            const intensity = this.shakeIntensity * (this.shakeDuration > 0 ? 1 : 0);
            this.shakeOffset.x = (Math.random() - 0.5) * 2 * intensity;
            this.shakeOffset.y = (Math.random() - 0.5) * 2 * intensity;
        } else {
            this.shakeOffset.x = 0;
            this.shakeOffset.y = 0;
        }

        // Update flash
        if (this.flashDuration > 0) {
            this.flashDuration -= deltaTime;
        }

        // Update trails
        for (let i = this.trails.length - 1; i >= 0; i--) {
            this.trails[i].life -= deltaTime;
            if (this.trails[i].life <= 0) {
                this.trails.splice(i, 1);
            }
        }
    }

    /**
     * Get current shake offset
     */
    getShakeOffset() {
        return this.shakeOffset;
    }

    /**
     * Draw flash effect (call after ctx.restore())
     */
    drawFlash(ctx, width, height) {
        if (this.flashDuration > 0 && this.flashColor) {
            const alpha = (this.flashDuration / this.flashMaxDuration) * 0.5;
            ctx.fillStyle = this.flashColor;
            ctx.globalAlpha = alpha;
            ctx.fillRect(0, 0, width, height);
            ctx.globalAlpha = 1.0;
        }
    }

    /**
     * Draw all trails
     */
    drawTrails(ctx) {
        this.trails.forEach(trail => {
            const alpha = trail.life / trail.maxLife;
            const size = trail.size * alpha;
            ctx.fillStyle = trail.color;
            ctx.globalAlpha = alpha * 0.7;
            ctx.beginPath();
            ctx.arc(trail.x, trail.y, size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1.0;
    }
}

// ============================================
// SPRITE ANIMATION (v0.6)
// ============================================
class SpriteAnimation {
    /**
     * Create a sprite animation
     * @param {Array} frames - Array of image names (from assets)
     * @param {number} frameTime - Time per frame in seconds
     * @param {boolean} loop - Whether to loop the animation
     */
    constructor(frames, frameTime = 0.1, loop = true) {
        this.frames = frames;
        this.frameTime = frameTime;
        this.loop = loop;
        this.currentFrame = 0;
        this.timer = 0;
        this.finished = false;
    }

    /**
     * Update animation
     */
    update(deltaTime) {
        if (this.finished) return;

        this.timer += deltaTime;
        if (this.timer >= this.frameTime) {
            this.timer -= this.frameTime;
            this.currentFrame++;

            if (this.currentFrame >= this.frames.length) {
                if (this.loop) {
                    this.currentFrame = 0;
                } else {
                    this.currentFrame = this.frames.length - 1;
                    this.finished = true;
                }
            }
        }
    }

    /**
     * Get current frame image name
     */
    getCurrentFrame() {
        return this.frames[this.currentFrame];
    }

    /**
     * Draw current frame
     * @param {CanvasRenderingContext2D} ctx
     * @param {AssetLoader} assets
     * @param {number} x
     * @param {number} y
     * @param {number} width
     * @param {number} height
     */
    draw(ctx, assets, x, y, width, height) {
        const frameName = this.getCurrentFrame();
        const img = assets.getImage(frameName);
        if (img) {
            ctx.drawImage(img, x, y, width, height);
        }
    }

    /**
     * Reset animation to beginning
     */
    reset() {
        this.currentFrame = 0;
        this.timer = 0;
        this.finished = false;
    }

    /**
     * Check if animation is finished (for non-looping)
     */
    isFinished() {
        return this.finished;
    }
}

// ============================================
// UI MANAGER
// ============================================
class UIManager {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
    }

    drawTitle(titleText, description = '') {
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Background - Use #010101 (near-black) for title screen
        // This is reserved for title screen only - game screens must NOT use #010101
        this.ctx.fillStyle = '#010101';
        this.ctx.fillRect(0, 0, w, h);

        // Glow effect background
        this.ctx.fillStyle = 'rgba(0, 255, 0, 0.05)';
        for (let i = 0; i < 3; i++) {
            this.ctx.strokeStyle = `rgba(0, 255, 0, ${0.3 - i * 0.08})`;
            this.ctx.lineWidth = 2;
            const margin = 40 + i * 20;
            this.ctx.strokeRect(margin, margin, w - margin * 2, h - margin * 2);
        }

        // Title
        this.ctx.fillStyle = '#0f0';
        this.ctx.font = 'bold 36px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(titleText, w / 2, h / 3);

        // Description (if provided)
        if (description) {
            this.ctx.fillStyle = '#0ff';
            this.ctx.font = '14px monospace';
            this.ctx.fillText(description, w / 2, h / 2 - 20);
        }

        // Start instruction
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '14px monospace';
        const blinkAlpha = (Math.sin(Date.now() / 500) + 1) / 2;
        this.ctx.globalAlpha = blinkAlpha;
        this.ctx.fillText('PRESS SPACE OR CLICK TO START', w / 2, h * 2 / 3 + 40);
        this.ctx.globalAlpha = 1.0;
    }

    drawGameOver(score = 0, canAcceptInput = true) {
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Semi-transparent overlay
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(0, 0, w, h);

        // Game Over text
        this.ctx.fillStyle = '#f00';
        this.ctx.font = 'bold 48px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('GAME OVER', w / 2, h / 3);

        // Score
        this.ctx.fillStyle = '#0f0';
        this.ctx.font = 'bold 24px monospace';
        this.ctx.fillText(`SCORE: ${score}`, w / 2, h / 2);

        // Restart instruction (only show when input is accepted)
        if (canAcceptInput) {
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '14px monospace';
            const blinkAlpha = (Math.sin(Date.now() / 500) + 1) / 2;
            this.ctx.globalAlpha = blinkAlpha;
            this.ctx.fillText('PRESS SPACE OR CLICK TO RESTART', w / 2, h * 2 / 3);
            this.ctx.globalAlpha = 1.0;
        }
    }

    drawScore(score, x = 10, y = 20) {
        this.ctx.fillStyle = '#0f0';
        this.ctx.font = '14px monospace';
        this.ctx.textAlign = 'left';
        this.ctx.fillText(`SCORE: ${score}`, x, y);
    }

    /**
     * v0.6: Draw stage clear screen
     */
    drawStageClear(stageNum = 1, score = 0, bonus = 0) {
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Semi-transparent overlay
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(0, 0, w, h);

        // Stage Clear text
        this.ctx.fillStyle = '#0f0';
        this.ctx.font = 'bold 36px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('STAGE CLEAR!', w / 2, h / 3);

        // Stage number
        this.ctx.fillStyle = '#ff0';
        this.ctx.font = 'bold 24px monospace';
        this.ctx.fillText(`STAGE ${stageNum}`, w / 2, h / 3 + 50);

        // Score
        this.ctx.fillStyle = '#0ff';
        this.ctx.font = '18px monospace';
        this.ctx.fillText(`SCORE: ${score}`, w / 2, h / 2 + 20);

        // Bonus
        if (bonus > 0) {
            this.ctx.fillStyle = '#f0f';
            this.ctx.fillText(`BONUS: +${bonus}`, w / 2, h / 2 + 50);
        }

        // Continue instruction
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '14px monospace';
        const blinkAlpha = (Math.sin(Date.now() / 500) + 1) / 2;
        this.ctx.globalAlpha = blinkAlpha;
        this.ctx.fillText('PRESS SPACE TO CONTINUE', w / 2, h * 2 / 3 + 40);
        this.ctx.globalAlpha = 1.0;
    }

    /**
     * v0.7: Draw game clear screen (all stages completed)
     */
    drawGameClear(score = 0, canAcceptInput = true) {
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Semi-transparent overlay with celebratory color
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(0, 0, w, h);

        // Game Clear text with golden color
        this.ctx.fillStyle = '#ffd700';
        this.ctx.font = 'bold 42px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('GAME CLEAR!', w / 2, h / 3);

        // Congratulations text
        this.ctx.fillStyle = '#0ff';
        this.ctx.font = 'bold 18px monospace';
        this.ctx.fillText('CONGRATULATIONS!', w / 2, h / 3 + 50);

        // Final score
        this.ctx.fillStyle = '#0f0';
        this.ctx.font = 'bold 24px monospace';
        this.ctx.fillText(`FINAL SCORE: ${score}`, w / 2, h / 2 + 20);

        // Return to title instruction (only show when input is accepted)
        if (canAcceptInput) {
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '14px monospace';
            const blinkAlpha = (Math.sin(Date.now() / 500) + 1) / 2;
            this.ctx.globalAlpha = blinkAlpha;
            this.ctx.fillText('PRESS SPACE OR CLICK TO RETURN', w / 2, h * 2 / 3 + 40);
            this.ctx.globalAlpha = 1.0;
        }
    }

    /**
     * v0.6: Draw pause screen
     */
    drawPause() {
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Semi-transparent overlay
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        this.ctx.fillRect(0, 0, w, h);

        // Pause text
        this.ctx.fillStyle = '#fff';
        this.ctx.font = 'bold 48px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('PAUSED', w / 2, h / 2);

        // Resume instruction
        this.ctx.font = '14px monospace';
        const blinkAlpha = (Math.sin(Date.now() / 500) + 1) / 2;
        this.ctx.globalAlpha = blinkAlpha;
        this.ctx.fillText('PRESS B TO RESUME', w / 2, h / 2 + 50);
        this.ctx.globalAlpha = 1.0;
    }

    drawLoadingScreen() {
        const w = this.canvas.width;
        const h = this.canvas.height;

        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, w, h);

        this.ctx.fillStyle = '#0f0';
        this.ctx.font = '24px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('LOADING...', w / 2, h / 2 - 40);

        // Progress bar
        const progress = arguments[1] || 0;
        const barWidth = 200;
        const barHeight = 10;
        const barX = (w - barWidth) / 2;
        const barY = h / 2 + 20;

        this.ctx.strokeStyle = '#0f0';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(barX, barY, barWidth, barHeight);

        this.ctx.fillStyle = '#0f0';
        this.ctx.fillRect(barX + 2, barY + 2, (barWidth - 4) * progress, barHeight - 4);
    }
}

// ============================================
// GAME ENGINE (BASE CLASS)
// ============================================
class GameEngine {
    constructor(canvasId, config = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas element with id "${canvasId}" not found`);
        }

        this.ctx = this.canvas.getContext('2d');

        // Game configuration
        this.gameConfig = {
            title: 'GAME STUDIO 1984',
            description: 'An arcade game'
        };
        Object.assign(this.gameConfig, config);

        // Components
        this.stateManager = new GameStateManager();
        this.controller = new VirtualController();
        this.assets = new AssetLoader();
        this.uiManager = new UIManager(this.canvas, this.ctx);

        // Game state
        this.score = 0;
        this.lastTime = 0;
        this.fps = 60;
        this.frameInterval = 1000 / this.fps;

        // Handle canvas clicks for title/game-over/game-clear screen transitions
        // This allows players to tap anywhere on the screen to start/restart
        this.canvas.addEventListener('click', () => {
            if (this.stateManager.is(GameStateManager.STATES.TITLE)) {
                this.initGame();
                this.stateManager.setState(GameStateManager.STATES.PLAYING);
                this.controller.reset();
            } else if (this.stateManager.is(GameStateManager.STATES.GAME_OVER)) {
                // Wait 3 seconds before accepting input
                if (this.stateManager.canAcceptInput(3000)) {
                    this.stateManager.setState(GameStateManager.STATES.TITLE);
                    this.controller.reset();
                }
            } else if (this.stateManager.is(GameStateManager.STATES.GAME_CLEAR)) {
                // Wait 3 seconds before accepting input
                if (this.stateManager.canAcceptInput(3000)) {
                    this.stateManager.setState(GameStateManager.STATES.TITLE);
                    this.controller.reset();
                }
            }
        });
    }

    /**
     * Start the game (call this from window.addEventListener('load', ...))
     */
    startGame() {
        this.loadAssets();
        Promise.resolve().then(() => this.onAssetsLoaded());
    }

    /**
     * Load assets (override in subclass if needed)
     */
    loadAssets() {
        // Override in subclass to load your game assets
    }

    /**
     * Called after assets are loaded
     */
    async onAssetsLoaded() {
        this.stateManager.setState(GameStateManager.STATES.TITLE);
        // initGame will be called when transitioning from TITLE to PLAYING
        this.gameLoop(0);
    }

    /**
     * Initialize game state (override in subclass)
     * Called after assets are loaded
     */
    initGame() {
        throw new Error('Subclass must implement initGame()');
    }

    /**
     * Update game logic (override in subclass)
     * Called once per frame during PLAYING state
     */
    updateGame(deltaTime) {
        throw new Error('Subclass must implement updateGame()');
    }

    /**
     * Draw game (override in subclass)
     * Called once per frame during PLAYING state
     */
    drawGame(ctx) {
        throw new Error('Subclass must implement drawGame()');
    }

    /**
     * Main game loop
     */
    gameLoop(currentTime) {
        requestAnimationFrame((time) => this.gameLoop(time));

        const deltaTime = currentTime - this.lastTime;

        // FPS control
        if (deltaTime < this.frameInterval) {
            return;
        }

        this.lastTime = currentTime - (deltaTime % this.frameInterval);

        // State-based rendering
        if (this.stateManager.is(GameStateManager.STATES.LOADING)) {
            this.uiManager.drawLoadingScreen(this.assets.getProgress());
        } else if (this.stateManager.is(GameStateManager.STATES.TITLE)) {
            this.uiManager.drawTitle(
                this.gameConfig.title,
                this.gameConfig.description
            );

            // Transition to playing on input
            if (this.controller.isJustPressed('a')) {
                this.initGame();
                this.stateManager.setState(GameStateManager.STATES.PLAYING);
                this.controller.reset();
            }
        } else if (this.stateManager.is(GameStateManager.STATES.PLAYING)) {
            this.updateGame(deltaTime / 1000);
            this.drawGame(this.ctx);

            // v0.6: Handle pause with P key (keyboard only)
            if (this.controller.isJustPressed('pause')) {
                this.stateManager.setState(GameStateManager.STATES.PAUSED);
            }
        } else if (this.stateManager.is(GameStateManager.STATES.PAUSED)) {
            // v0.6: Draw game then pause overlay
            this.drawGame(this.ctx);
            this.uiManager.drawPause();

            // Resume with P key or A button
            if (this.controller.isJustPressed('pause') || this.controller.isJustPressed('a')) {
                this.stateManager.setState(GameStateManager.STATES.PLAYING);
                this.controller.reset();
            }
        } else if (this.stateManager.is(GameStateManager.STATES.STAGE_CLEAR)) {
            // v0.6: Stage clear screen (game draws underneath)
            this.drawGame(this.ctx);
            this.uiManager.drawStageClear(this.currentStage || 1, this.score, this.stageBonus || 0);

            // Continue on input
            if (this.controller.isJustPressed('a')) {
                this.onStageClearComplete();
                this.controller.reset();
            }
        } else if (this.stateManager.is(GameStateManager.STATES.BOSS_FIGHT)) {
            // v0.6: Boss fight uses same update/draw as playing
            this.updateGame(deltaTime / 1000);
            this.drawGame(this.ctx);
        } else if (this.stateManager.is(GameStateManager.STATES.GAME_OVER)) {
            const canAcceptInput = this.stateManager.canAcceptInput(3000);
            this.uiManager.drawGameOver(this.score, canAcceptInput);

            // Transition to title on input (wait 3 seconds before accepting)
            if (this.controller.isJustPressed('a') && canAcceptInput) {
                this.stateManager.setState(GameStateManager.STATES.TITLE);
                this.controller.reset();
            }
        } else if (this.stateManager.is(GameStateManager.STATES.GAME_CLEAR)) {
            // v0.7: Game clear screen (victory)
            const canAcceptInput = this.stateManager.canAcceptInput(3000);
            this.uiManager.drawGameClear(this.score, canAcceptInput);

            // Transition to title on input (wait 3 seconds before accepting)
            if (this.controller.isJustPressed('a') && canAcceptInput) {
                this.stateManager.setState(GameStateManager.STATES.TITLE);
                this.controller.reset();
            }
        }

        this.controller.update();
    }

    /**
     * End the game (player lost)
     */
    gameOver() {
        this.stateManager.setState(GameStateManager.STATES.GAME_OVER);
    }

    /**
     * v0.7: Complete the game (player won)
     */
    gameClear() {
        this.stateManager.setState(GameStateManager.STATES.GAME_CLEAR);
    }

    /**
     * v0.6: Trigger stage clear
     * @param {number} bonus - Bonus points for clearing stage
     */
    stageClear(bonus = 0) {
        this.stageBonus = bonus;
        this.score += bonus;
        this.stateManager.setState(GameStateManager.STATES.STAGE_CLEAR);
    }

    /**
     * v0.6: Called when player continues from stage clear
     * Override in subclass to set up next stage
     */
    onStageClearComplete() {
        this.currentStage = (this.currentStage || 1) + 1;
        this.stateManager.setState(GameStateManager.STATES.PLAYING);
    }

    /**
     * v0.6: Enter boss fight state
     */
    startBossFight() {
        this.stateManager.setState(GameStateManager.STATES.BOSS_FIGHT);
    }

    /**
     * Utility: Check collision between two rectangles (legacy)
     * For v0.6+, prefer using CollisionSystem.rectCollision() or CollisionSystem.circleCollision()
     */
    collides(rect1, rect2) {
        return CollisionSystem.rectCollision(rect1, rect2);
    }

    /**
     * Utility: Play sound
     */
    playSound(name) {
        this.assets.playSound(name);
    }

    /**
     * Utility: Get screen dimensions
     */
    getScreenWidth() {
        return this.canvas.width;
    }

    getScreenHeight() {
        return this.canvas.height;
    }
}
