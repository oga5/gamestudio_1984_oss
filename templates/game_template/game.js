/**
 * GameStudio 1984 v0.3 - Simple Game Template
 * All game code in one file for easy debugging
 */

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
            b: false
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
            'ShiftRight': 'b'
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

    getImage(name) {
        return this.images[name] || null;
    }
}

// ============================================
// GAME TEMPLATE
// ============================================
class Game {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.controller = new VirtualController();
        this.assets = new AssetLoader();

        this.isLoading = true;
        this.lastTime = 0;
        this.fps = 60;
        this.frameInterval = 1000 / this.fps;

        this.init();
    }

    async init() {
        // Load assets here
        // Example:
        // await this.assets.loadImage('player', 'assets/images/player.png');
        // await this.assets.loadSound('jump', 'assets/sounds/jump.wav');

        // For now, just wait a bit to show loading screen
        await new Promise(resolve => setTimeout(resolve, 500));

        this.isLoading = false;
        this.start();
    }

    start() {
        // Initialize game state here
        this.player = {
            x: 180,
            y: 270,
            width: 20,
            height: 20,
            speed: 3
        };

        requestAnimationFrame((time) => this.gameLoop(time));
    }

    gameLoop(currentTime) {
        requestAnimationFrame((time) => this.gameLoop(time));

        const deltaTime = currentTime - this.lastTime;

        if (deltaTime < this.frameInterval) {
            return;
        }

        this.lastTime = currentTime - (deltaTime % this.frameInterval);

        if (this.isLoading) {
            this.drawLoading();
        } else {
            this.update();
            this.draw();
            this.controller.update();
        }
    }

    update() {
        // Update game logic here

        // Example: Move player with controller
        const h = this.controller.getHorizontal();
        const v = this.controller.getVertical();

        this.player.x += h * this.player.speed;
        this.player.y += v * this.player.speed;

        // Keep player in bounds
        this.player.x = Math.max(0, Math.min(360 - this.player.width, this.player.x));
        this.player.y = Math.max(0, Math.min(540 - this.player.height, this.player.y));
    }

    draw() {
        // Clear screen
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, 360, 540);

        // Draw game objects here

        // Example: Draw player
        this.ctx.fillStyle = '#0f0';
        this.ctx.fillRect(this.player.x, this.player.y, this.player.width, this.player.height);

        // Example: Draw instructions
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '12px monospace';
        this.ctx.fillText('Use D-PAD or Arrow Keys to move', 10, 20);
    }

    drawLoading() {
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, 360, 540);

        this.ctx.fillStyle = '#fff';
        this.ctx.font = '16px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('LOADING...', 180, 270);

        const progress = this.assets.getProgress();
        this.ctx.fillRect(80, 290, 200 * progress, 10);
        this.ctx.strokeStyle = '#fff';
        this.ctx.strokeRect(80, 290, 200, 10);

        this.ctx.textAlign = 'left';
    }
}

// ============================================
// START GAME
// ============================================
window.addEventListener('load', () => {
    const game = new Game();
});
