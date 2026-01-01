/**
 * GameStudio 1984 v0.7 - Sample Game Implementation
 *
 * This file demonstrates a complete game implementation using gamelib.js v0.7 features:
 * - ParticleSystem for visual effects
 * - CollisionSystem for accurate hit detection
 * - Sound loop/stop for BGM management
 * - ScreenEffects for impact feedback
 *
 * The game is an Invaders-style shooter:
 * - Player controls a ship at the bottom
 * - Enemies descend from the top
 * - Player shoots to destroy enemies
 * - Game ends when enemies reach the bottom or player is hit
 *
 * TO CREATE YOUR OWN GAME:
 * 1. Replace this entire file with your own game class
 * 2. Extend GameEngine
 * 3. Implement initGame(), updateGame(), drawGame()
 * 4. Use this as a reference for structure and patterns
 * 5. DO NOT MODIFY gamelib.js
 */

class InvadersGame extends GameEngine {
    constructor() {
        super('game-canvas', {
            title: 'SPACE INVADERS',
            description: 'Destroy enemies before they reach you!'
        });

        // v0.6: Initialize particle system for explosions
        this.particles = new ParticleSystem();

        // v0.6: Initialize screen effects
        this.screenEffects = new ScreenEffects();

        // Game state
        this.player = {};
        this.enemies = [];
        this.bullets = [];
        this.enemyBullets = [];
    }

    /**
     * Load assets for this game
     */
    loadAssets() {
        // Load images
        this.assets.loadImage('player', 'assets/images/player.png');
        this.assets.loadImage('enemy', 'assets/images/enemy.png');
        this.assets.loadImage('bullet', 'assets/images/bullet.png');

        // Load sounds
        this.assets.loadSound('shoot', 'assets/sounds/shoot.wav');
        this.assets.loadSound('explosion', 'assets/sounds/explosion.wav');
        this.assets.loadSound('player_hit', 'assets/sounds/player_hit.wav');

        // v0.6: Load BGM (if available)
        this.assets.loadSound('bgm_game', 'assets/sounds/bgm_game.wav');
    }

    /**
     * Initialize game state
     * Called when transitioning from TITLE to PLAYING
     */
    initGame() {
        // Player setup - using circle hitbox for v0.6
        this.player = {
            x: this.canvas.width / 2 - 16,
            y: this.canvas.height - 60,
            width: 32,
            height: 32,
            radius: 14,  // v0.6: Circle hitbox radius
            speed: 180,  // pixels per second
            shootCooldown: 0,
            lives: 3,
            invincible: 0
        };

        // Create enemy grid
        this.enemies = [];
        const enemyRows = 4;
        const enemyCols = 6;
        const spacingX = 50;
        const spacingY = 50;

        for (let row = 0; row < enemyRows; row++) {
            for (let col = 0; col < enemyCols; col++) {
                this.enemies.push({
                    x: 30 + col * spacingX,
                    y: 40 + row * spacingY,
                    width: 28,
                    height: 28,
                    radius: 12,  // v0.6: Circle hitbox
                    speed: 1,
                    direction: 1,
                    type: row < 2 ? 'elite' : 'normal'
                });
            }
        }

        // Initialize arrays
        this.bullets = [];
        this.enemyBullets = [];
        this.score = 0;

        // Game settings
        this.enemySpeed = 40;
        this.enemyDirection = 1;
        this.enemyShootTimer = 0;

        // Clear particles
        this.particles.clear();
        this.screenEffects.reset();

        // v0.6: Start BGM loop
        this.assets.stopAllLoops();
        this.assets.playSoundLoop('bgm_game');
        this.assets.setVolume('bgm_game', 0.5);
    }

    /**
     * Update game logic
     * Called once per frame during PLAYING state
     */
    updateGame(deltaTime) {
        // v0.6: Update screen effects
        this.screenEffects.update(deltaTime);

        // v0.6: Update particles
        this.particles.update(deltaTime);

        // Update player
        this.updatePlayer(deltaTime);

        // Update bullets
        this.updateBullets(deltaTime);

        // Update enemies
        this.updateEnemies(deltaTime);

        // Update enemy bullets
        this.updateEnemyBullets(deltaTime);

        // Check collisions
        this.checkCollisions();

        // Enemy shooting
        this.handleEnemyShooting(deltaTime);

        // Win/lose conditions
        if (this.enemies.length === 0) {
            this.assets.stopAllLoops();
            this.gameClear();  // v0.7: Use gameClear() for victory instead of gameOver()
        }
    }

    updatePlayer(deltaTime) {
        // Movement
        const h = this.controller.getHorizontal();
        this.player.x += h * this.player.speed * deltaTime;

        // Keep player in bounds
        this.player.x = Math.max(0, Math.min(this.canvas.width - this.player.width, this.player.x));

        // Update invincibility
        if (this.player.invincible > 0) {
            this.player.invincible -= deltaTime;
        }

        // Handle shooting
        this.player.shootCooldown -= deltaTime;
        if (this.controller.isJustPressed('a') && this.player.shootCooldown <= 0) {
            this.bullets.push({
                x: this.player.x + this.player.width / 2 - 3,
                y: this.player.y,
                width: 6,
                height: 12,
                radius: 4,
                speed: 400
            });
            this.playSound('shoot');
            this.player.shootCooldown = 0.2;

            // v0.6: Muzzle flash particles
            this.particles.emit(
                this.player.x + this.player.width / 2,
                this.player.y,
                {
                    count: 5,
                    color: '#ffff00',
                    speed: 2,
                    lifetime: 0.15,
                    size: 3
                }
            );
        }
    }

    updateBullets(deltaTime) {
        this.bullets = this.bullets.filter(bullet => {
            bullet.y -= bullet.speed * deltaTime;
            return bullet.y > -bullet.height;
        });
    }

    updateEnemies(deltaTime) {
        if (this.enemies.length === 0) return;

        let shouldTurn = false;
        let shouldMoveDown = false;

        // Move enemies horizontally
        this.enemies.forEach(enemy => {
            enemy.x += this.enemySpeed * this.enemyDirection * deltaTime;

            // Check bounds
            if ((this.enemyDirection > 0 && enemy.x + enemy.width > this.canvas.width - 10) ||
                (this.enemyDirection < 0 && enemy.x < 10)) {
                shouldTurn = true;
            }

            // Check if enemies reached player
            if (enemy.y + enemy.height > this.player.y - 20) {
                this.assets.stopAllLoops();
                this.gameOver();
            }
        });

        // Turn enemies around and move down
        if (shouldTurn) {
            this.enemyDirection *= -1;
            this.enemies.forEach(enemy => {
                enemy.y += 15;
            });

            // Speed up enemies
            this.enemySpeed += 3;
        }
    }

    updateEnemyBullets(deltaTime) {
        this.enemyBullets = this.enemyBullets.filter(bullet => {
            bullet.y += bullet.speed * deltaTime;
            return bullet.y < this.canvas.height + 20;
        });
    }

    handleEnemyShooting(deltaTime) {
        this.enemyShootTimer -= deltaTime;

        if (this.enemyShootTimer <= 0 && this.enemies.length > 0) {
            // Random enemy shoots
            const shooter = this.enemies[Math.floor(Math.random() * this.enemies.length)];

            this.enemyBullets.push({
                x: shooter.x + shooter.width / 2 - 3,
                y: shooter.y + shooter.height,
                width: 6,
                height: 10,
                radius: 4,
                speed: 200
            });

            // Reset timer - faster as fewer enemies remain
            this.enemyShootTimer = 1.5 - (24 - this.enemies.length) * 0.04;
            this.enemyShootTimer = Math.max(0.3, this.enemyShootTimer);
        }
    }

    checkCollisions() {
        // Bullet vs Enemy - using v0.6 circle collision
        for (let i = this.bullets.length - 1; i >= 0; i--) {
            const bullet = this.bullets[i];
            const bulletCircle = {
                x: bullet.x + bullet.width / 2,
                y: bullet.y + bullet.height / 2,
                radius: bullet.radius
            };

            for (let j = this.enemies.length - 1; j >= 0; j--) {
                const enemy = this.enemies[j];
                const enemyCircle = {
                    x: enemy.x + enemy.width / 2,
                    y: enemy.y + enemy.height / 2,
                    radius: enemy.radius
                };

                // v0.6: Use circle collision for accurate hit detection
                if (CollisionSystem.circleCollision(bulletCircle, enemyCircle)) {
                    // v0.6: Emit explosion particles
                    const particleColor = enemy.type === 'elite' ? '#ff00ff' : '#ff6600';
                    this.particles.emit(
                        enemy.x + enemy.width / 2,
                        enemy.y + enemy.height / 2,
                        {
                            count: 25,
                            color: particleColor,
                            speed: 4,
                            lifetime: 0.6,
                            size: 4,
                            gravity: 0.1
                        }
                    );

                    // v0.6: Screen shake on kill
                    this.screenEffects.shake(3, 0.1);

                    // Remove enemy and bullet
                    this.enemies.splice(j, 1);
                    this.bullets.splice(i, 1);

                    // Score based on enemy type
                    this.score += enemy.type === 'elite' ? 20 : 10;
                    this.playSound('explosion');

                    break;
                }
            }
        }

        // Enemy bullet vs Player
        if (this.player.invincible <= 0) {
            const playerCircle = {
                x: this.player.x + this.player.width / 2,
                y: this.player.y + this.player.height / 2,
                radius: this.player.radius
            };

            for (let i = this.enemyBullets.length - 1; i >= 0; i--) {
                const bullet = this.enemyBullets[i];
                const bulletCircle = {
                    x: bullet.x + bullet.width / 2,
                    y: bullet.y + bullet.height / 2,
                    radius: bullet.radius
                };

                if (CollisionSystem.circleCollision(playerCircle, bulletCircle)) {
                    this.enemyBullets.splice(i, 1);
                    this.playerHit();
                    break;
                }
            }
        }
    }

    playerHit() {
        this.player.lives--;
        this.playSound('player_hit');

        // v0.6: Screen flash and shake on hit
        this.screenEffects.flash('#ff0000', 0.2);
        this.screenEffects.shake(8, 0.3);

        // v0.6: Damage particles
        this.particles.emit(
            this.player.x + this.player.width / 2,
            this.player.y + this.player.height / 2,
            {
                count: 15,
                color: '#ff0000',
                speed: 3,
                lifetime: 0.4,
                size: 3
            }
        );

        if (this.player.lives <= 0) {
            // v0.6: Big explosion on death
            this.particles.emit(
                this.player.x + this.player.width / 2,
                this.player.y + this.player.height / 2,
                {
                    count: 50,
                    color: '#ffff00',
                    speed: 5,
                    lifetime: 1.0,
                    size: 5,
                    gravity: 0.2
                }
            );

            this.assets.stopAllLoops();
            this.gameOver();
        } else {
            // Invincibility frames
            this.player.invincible = 2.0;
        }
    }

    /**
     * Draw game graphics
     * Called once per frame during PLAYING state
     */
    drawGame(ctx) {
        // v0.6: Apply screen effects (shake offset)
        ctx.save();
        const shakeOffset = this.screenEffects.getShakeOffset();
        ctx.translate(shakeOffset.x, shakeOffset.y);

        // Clear screen (use #000000, NOT #0f0f0f which is reserved for title)
        ctx.fillStyle = '#000010';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw starfield background
        this.drawStarfield(ctx);

        // Draw player (with blinking if invincible)
        if (this.player.invincible <= 0 || Math.floor(this.player.invincible * 10) % 2 === 0) {
            const playerImg = this.assets.getImage('player');
            if (playerImg) {
                ctx.drawImage(playerImg, this.player.x, this.player.y,
                             this.player.width, this.player.height);
            } else {
                ctx.fillStyle = '#0f0';
                ctx.fillRect(this.player.x, this.player.y,
                            this.player.width, this.player.height);
            }
        }

        // Draw enemies
        const enemyImg = this.assets.getImage('enemy');
        this.enemies.forEach(enemy => {
            if (enemy && typeof enemy.x === 'number' && typeof enemy.y === 'number' &&
                enemy.width > 0 && enemy.height > 0 &&
                !isNaN(enemy.x) && !isNaN(enemy.y)) {
                if (enemyImg) {
                    // Tint elite enemies
                    if (enemy.type === 'elite') {
                        ctx.globalAlpha = 0.3;
                        ctx.fillStyle = '#ff00ff';
                        ctx.fillRect(enemy.x - 2, enemy.y - 2, enemy.width + 4, enemy.height + 4);
                        ctx.globalAlpha = 1.0;
                    }
                    ctx.drawImage(enemyImg, enemy.x, enemy.y, enemy.width, enemy.height);
                } else {
                    ctx.fillStyle = enemy.type === 'elite' ? '#f0f' : '#f00';
                    ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
                }
            }
        });

        // Draw bullets
        ctx.fillStyle = '#0ff';
        this.bullets.forEach(bullet => {
            ctx.fillRect(bullet.x, bullet.y, bullet.width, bullet.height);
        });

        // Draw enemy bullets
        ctx.fillStyle = '#ff0';
        this.enemyBullets.forEach(bullet => {
            ctx.beginPath();
            ctx.arc(bullet.x + bullet.width / 2, bullet.y + bullet.height / 2,
                   bullet.radius, 0, Math.PI * 2);
            ctx.fill();
        });

        // v0.6: Draw particles
        this.particles.draw(ctx);

        ctx.restore();

        // v0.6: Draw flash effect (after restore so it covers full screen)
        this.screenEffects.drawFlash(ctx, this.canvas.width, this.canvas.height);

        // Draw UI (not affected by shake)
        this.drawUI(ctx);
    }

    drawStarfield(ctx) {
        ctx.fillStyle = '#ffffff';
        // Simple static starfield
        const stars = [
            [50, 80], [120, 40], [200, 120], [280, 60], [340, 100],
            [30, 200], [90, 250], [180, 180], [250, 220], [320, 280],
            [60, 350], [150, 400], [220, 320], [300, 380], [40, 450]
        ];
        stars.forEach(([x, y]) => {
            ctx.fillRect(x, y, 2, 2);
        });
    }

    drawUI(ctx) {
        // Score
        this.uiManager.drawScore(this.score);

        // Lives
        ctx.fillStyle = '#0f0';
        ctx.font = '14px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`LIVES: ${this.player.lives}`, this.canvas.width - 10, 20);

        // Enemy count
        ctx.fillStyle = '#ff0';
        ctx.fillText(`ENEMIES: ${this.enemies.length}`, this.canvas.width - 10, 40);
    }
}

// ============================================
// START GAME
// ============================================
window.addEventListener('load', () => {
    const game = new InvadersGame();
    game.startGame();
});
