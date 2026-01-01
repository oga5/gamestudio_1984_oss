class StarLockOn extends GameEngine {
    constructor() {
        super('game-canvas', {
            title: 'Star Lock-On 1984',
            description: 'Lock onto multiple enemies and unleash homing missiles!'
        });

        this.particles = new ParticleSystem();
        this.screenEffects = new ScreenEffects();
        
        // Game constants from design
        this.PLAYER_SPEED = 220;
        this.LOCK_ON_RANGE = 200;
        this.LOCK_ON_ANGLE = 45; // degrees (half-cone)
        this.MAX_LOCKS = 8;
        this.SPAWN_RATE = 1.2;
        this.BOSS_SPAWN_TIME = 30.0;
        
        this.initGame();
    }

    loadAssets() {
        // Images
        this.assets.loadImage('player', 'assets/images/player.png');
        this.assets.loadImage('enemy_scout', 'assets/images/enemy_scout.png');
        this.assets.loadImage('enemy_interceptor', 'assets/images/enemy_interceptor.png');
        this.assets.loadImage('boss', 'assets/images/boss.png');
        this.assets.loadImage('missile', 'assets/images/missile.png');
        this.assets.loadImage('reticle', 'assets/images/reticle.png');

        // Sounds
        this.assets.loadSound('bgm', 'assets/sounds/bgm_space_battle.wav');
        this.assets.loadSound('lock_on', 'assets/sounds/lock_on.wav');
        this.assets.loadSound('missile_launch', 'assets/sounds/missile.wav');
        this.assets.loadSound('explosion', 'assets/sounds/explosion.wav');
        this.assets.loadSound('hit', 'assets/sounds/hit.wav');
    }

    initGame() {
        this.player = {
            x: 180,
            y: 450,
            width: 32,
            height: 32,
            radius: 12,
            lives: 3,
            invincible: 0,
            shootTimer: 0
        };

        this.enemies = [];
        this.missiles = [];
        this.enemyBullets = [];
        this.lockedTargets = []; // Array of enemy objects currently locked
        
        this.score = 0;
        this.gameTime = 0;
        this.spawnTimer = 0;
        this.bossSpawned = false;
        this.boss = null;
        
        this.stars = [];
        for (let i = 0; i < 50; i++) {
            this.stars.push({
                x: Math.random() * 360,
                y: Math.random() * 540,
                speed: 1 + Math.random() * 3,
                size: 1 + Math.random() * 2
            });
        }

        this.assets.stopAllLoops();
        this.assets.playSoundLoop('bgm');
        this.assets.setVolume('bgm', 0.4);
    }

    updateGame(deltaTime) {
        this.gameTime += deltaTime;
        this.particles.update(deltaTime);
        this.screenEffects.update(deltaTime);

        if (this.player.invincible > 0) {
            this.player.invincible -= deltaTime;
        }

        this.updateStars(deltaTime);
        this.handleInput(deltaTime);
        this.updateLockOn();
        this.updateEnemies(deltaTime);
        this.updateMissiles(deltaTime);
        this.updateEnemyBullets(deltaTime);
        this.handleSpawning(deltaTime);
        this.checkCollisions();

        if (this.player.lives <= 0) {
            this.gameOver();
        }
    }

    updateStars(deltaTime) {
        this.stars.forEach(star => {
            star.y += star.speed * 60 * deltaTime;
            if (star.y > 540) {
                star.y = 0;
                star.x = Math.random() * 360;
            }
        });
    }

    handleInput(deltaTime) {
        const h = this.controller.getHorizontal();
        const v = this.controller.getVertical();

        this.player.x += h * this.PLAYER_SPEED * deltaTime;
        this.player.y += v * this.PLAYER_SPEED * deltaTime;

        // Keep in bounds
        this.player.x = Math.max(16, Math.min(360 - 16, this.player.x));
        this.player.y = Math.max(16, Math.min(540 - 16, this.player.y));

        if (this.controller.isJustPressed('a')) {
            this.fireMissiles();
        }
    }

    updateLockOn() {
        // Clear targets that are dead or out of range
        this.lockedTargets = this.lockedTargets.filter(target => {
            if (target.dead) return false;
            
            const dx = target.x - this.player.x;
            const dy = target.y - this.player.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;
            
            // Player faces up (-90 degrees)
            const relativeAngle = Math.abs(angle + 90);
            const inCone = relativeAngle <= this.LOCK_ON_ANGLE || relativeAngle >= 360 - this.LOCK_ON_ANGLE;
            
            return dist <= this.LOCK_ON_RANGE && inCone;
        });

        // Look for new targets
        if (this.lockedTargets.length < this.MAX_LOCKS) {
            const potentialTargets = [...this.enemies];
            if (this.boss) potentialTargets.push(this.boss);

            for (const enemy of potentialTargets) {
                if (enemy.dead || this.lockedTargets.includes(enemy)) continue;

                const dx = enemy.x - this.player.x;
                const dy = enemy.y - this.player.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const angle = Math.atan2(dy, dx) * 180 / Math.PI;
                
                const relativeAngle = Math.abs(angle + 90);
                const inCone = relativeAngle <= this.LOCK_ON_ANGLE || relativeAngle >= 360 - this.LOCK_ON_ANGLE;

                if (dist <= this.LOCK_ON_RANGE && inCone) {
                    this.lockedTargets.push(enemy);
                    this.assets.playSound('lock_on');
                    if (this.lockedTargets.length >= this.MAX_LOCKS) break;
                }
            }
        }
    }

    fireMissiles() {
        if (this.lockedTargets.length === 0) return;

        const lockCount = this.lockedTargets.length;
        this.assets.playSound('missile_launch');
        
        this.lockedTargets.forEach(target => {
            this.missiles.push({
                x: this.player.x,
                y: this.player.y,
                vx: (Math.random() - 0.5) * 100,
                vy: -100,
                target: target,
                speed: 350,
                lockCount: lockCount, // Store for scoring
                life: 3.0
            });
        });

        // Clear locks after firing
        this.lockedTargets = [];
    }

    updateEnemies(deltaTime) {
        this.enemies.forEach(enemy => {
            if (enemy.type === 'scout') {
                enemy.y += enemy.speed * deltaTime;
                enemy.x += Math.sin(this.gameTime * 5) * 2;
            } else if (enemy.type === 'interceptor') {
                if (!enemy.diving && enemy.y > 100 && Math.abs(enemy.x - this.player.x) < 50) {
                    enemy.diving = true;
                }
                if (enemy.diving) {
                    enemy.y += enemy.speed * 1.5 * deltaTime;
                } else {
                    enemy.y += enemy.speed * deltaTime;
                }
            }
        });

        if (this.boss) {
            this.updateBoss(deltaTime);
        }

        // Remove off-screen or dead enemies
        this.enemies = this.enemies.filter(enemy => !enemy.dead && enemy.y < 600);
    }

    updateBoss(deltaTime) {
        const boss = this.boss;
        // Move side to side
        boss.x += Math.sin(this.gameTime) * boss.speed * deltaTime * 2;
        boss.y = Math.min(100, boss.y + boss.speed * deltaTime);

        // Boss firing
        boss.shootTimer -= deltaTime;
        if (boss.shootTimer <= 0) {
            boss.shootTimer = 1.5;
            // Fire 3 bullets
            for (let i = -1; i <= 1; i++) {
                this.enemyBullets.push({
                    x: boss.x + i * 20,
                    y: boss.y + 20,
                    vx: i * 50,
                    vy: 180,
                    radius: 4
                });
            }
        }

        if (boss.health <= 0) {
            boss.dead = true;
            this.score += 1000;
            this.particles.emit(boss.x, boss.y, {
                count: 50,
                color: '#ffaa00',
                speed: 5,
                lifetime: 1.0,
                size: 5
            });
            this.assets.playSound('explosion');
            this.screenEffects.shake(15, 0.5);
            this.boss = null;
            setTimeout(() => this.gameClear(), 2000);
        }
    }

    updateMissiles(deltaTime) {
        this.missiles.forEach(missile => {
            missile.life -= deltaTime;
            
            if (missile.target && !missile.target.dead) {
                const dx = missile.target.x - missile.x;
                const dy = missile.target.y - missile.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                const tx = (dx / dist) * missile.speed;
                const ty = (dy / dist) * missile.speed;
                
                // Smooth homing
                missile.vx += (tx - missile.vx) * 5 * deltaTime;
                missile.vy += (ty - missile.vy) * 5 * deltaTime;
            } else {
                // Target lost, just go straight
                missile.vy -= 10 * deltaTime;
            }

            missile.x += missile.vx * deltaTime;
            missile.y += missile.vy * deltaTime;

            // Trail effect
            this.screenEffects.addTrail(missile.x, missile.y, '#00ffff', 2, 0.15);
        });

        this.missiles = this.missiles.filter(m => m.life > 0 && m.y > -50 && m.y < 600 && m.x > -50 && m.x < 410);
    }

    updateEnemyBullets(deltaTime) {
        this.enemyBullets.forEach(bullet => {
            bullet.x += bullet.vx * deltaTime;
            bullet.y += bullet.vy * deltaTime;
        });
        this.enemyBullets = this.enemyBullets.filter(b => b.y < 600);
    }

    handleSpawning(deltaTime) {
        if (this.bossSpawned) return;

        if (this.gameTime >= this.BOSS_SPAWN_TIME) {
            this.spawnBoss();
            return;
        }

        this.spawnTimer -= deltaTime;
        if (this.spawnTimer <= 0) {
            const currentSpawnRate = this.gameTime > 15 ? 0.8 : 1.2;
            this.spawnTimer = currentSpawnRate;
            
            const type = Math.random() > 0.7 ? 'interceptor' : 'scout';
            this.enemies.push({
                type: type,
                x: 30 + Math.random() * 300,
                y: -30,
                width: type === 'scout' ? 24 : 20,
                height: type === 'scout' ? 24 : 20,
                radius: type === 'scout' ? 10 : 8,
                speed: type === 'scout' ? 100 : 150,
                health: 1,
                dead: false,
                diving: false
            });
        }
    }

    spawnBoss() {
        this.bossSpawned = true;
        this.boss = {
            x: 180,
            y: -100,
            width: 80,
            height: 60,
            speed: 40,
            health: 50,
            maxHealth: 50,
            shootTimer: 2.0,
            dead: false
        };
    }

    checkCollisions() {
        // Missiles vs Enemies
        this.missiles.forEach(missile => {
            // Check against regular enemies
            this.enemies.forEach(enemy => {
                if (!enemy.dead && CollisionSystem.circleCollision(
                    { x: missile.x, y: missile.y, radius: 4 },
                    { x: enemy.x, y: enemy.y, radius: enemy.radius }
                )) {
                    this.destroyEnemy(enemy, missile.lockCount);
                    missile.life = 0;
                }
            });

            // Check against boss
            if (this.boss && CollisionSystem.circleRectCollision(
                { x: missile.x, y: missile.y, radius: 4 },
                { x: this.boss.x - this.boss.width/2, y: this.boss.y - this.boss.height/2, width: this.boss.width, height: this.boss.height }
            )) {
                this.boss.health--;
                this.assets.playSound('hit');
                this.particles.emit(missile.x, missile.y, {
                    count: 5,
                    color: '#ffffff',
                    speed: 2,
                    lifetime: 0.3,
                    size: 2
                });
                missile.life = 0;
            }
        });

        // Player vs Enemies/Bullets
        if (this.player.invincible <= 0) {
            // vs Enemies
            this.enemies.forEach(enemy => {
                if (!enemy.dead && CollisionSystem.circleCollision(
                    { x: this.player.x, y: this.player.y, radius: this.player.radius },
                    { x: enemy.x, y: enemy.y, radius: enemy.radius }
                )) {
                    this.hitPlayer();
                }
            });

            // vs Bullets
            this.enemyBullets.forEach(bullet => {
                if (CollisionSystem.circleCollision(
                    { x: this.player.x, y: this.player.y, radius: this.player.radius },
                    { x: bullet.x, y: bullet.y, radius: bullet.radius }
                )) {
                    this.hitPlayer();
                }
            });

            // vs Boss
            if (this.boss && CollisionSystem.circleRectCollision(
                { x: this.player.x, y: this.player.y, radius: this.player.radius },
                { x: this.boss.x - this.boss.width/2, y: this.boss.y - this.boss.height/2, width: this.boss.width, height: this.boss.height }
            )) {
                this.hitPlayer();
            }
        }
    }

    destroyEnemy(enemy, lockCount) {
        enemy.dead = true;
        const basePoints = enemy.type === 'scout' ? 10 : 20;
        const multiplier = lockCount * lockCount;
        this.score += basePoints * multiplier;

        this.particles.emit(enemy.x, enemy.y, {
            count: 15,
            color: '#ffaa00',
            speed: 3,
            lifetime: 0.5,
            size: 3
        });
        this.assets.playSound('explosion');
        this.screenEffects.shake(3, 0.2);
    }

    hitPlayer() {
        this.player.lives--;
        this.player.invincible = 2.0;
        this.assets.playSound('hit');
        this.screenEffects.shake(10, 0.4);
        this.screenEffects.flash('#ffffff', 0.1);
        
        this.particles.emit(this.player.x, this.player.y, {
            count: 20,
            color: '#ff0000',
            speed: 4,
            lifetime: 0.6,
            size: 4
        });
    }

    drawGame(ctx) {
        // Background
        ctx.fillStyle = '#000010';
        ctx.fillRect(0, 0, 360, 540);

        // Stars
        ctx.fillStyle = '#ffffff';
        this.stars.forEach(star => {
            ctx.fillRect(star.x, star.y, star.size, star.size);
        });

        ctx.save();
        const shake = this.screenEffects.getShakeOffset();
        ctx.translate(shake.x, shake.y);

        this.screenEffects.drawTrails(ctx);

        // Enemies
        this.enemies.forEach(enemy => {
            const img = this.assets.getImage('enemy_' + enemy.type);
            if (img) {
                ctx.drawImage(img, enemy.x - enemy.width/2, enemy.y - enemy.height/2, enemy.width, enemy.height);
            }
        });

        // Boss
        if (this.boss) {
            const img = this.assets.getImage('boss');
            if (img) {
                ctx.drawImage(img, this.boss.x - this.boss.width/2, this.boss.y - this.boss.height/2, this.boss.width, this.boss.height);
            }
            // Health bar
            ctx.fillStyle = '#444';
            ctx.fillRect(this.boss.x - 40, this.boss.y - 45, 80, 5);
            ctx.fillStyle = '#f00';
            ctx.fillRect(this.boss.x - 40, this.boss.y - 45, 80 * (this.boss.health / this.boss.maxHealth), 5);
        }

        // Enemy Bullets
        ctx.fillStyle = '#ff00ff';
        this.enemyBullets.forEach(bullet => {
            ctx.beginPath();
            ctx.arc(bullet.x, bullet.y, bullet.radius, 0, Math.PI * 2);
            ctx.fill();
        });

        // Missiles
        this.missiles.forEach(missile => {
            const img = this.assets.getImage('missile');
            if (img) {
                ctx.save();
                ctx.translate(missile.x, missile.y);
                ctx.rotate(Math.atan2(missile.vy, missile.vx) + Math.PI/2);
                ctx.drawImage(img, -8, -8, 16, 16);
                ctx.restore();
            }
        });

        // Player
        if (this.player.invincible <= 0 || Math.floor(this.gameTime * 10) % 2 === 0) {
            const img = this.assets.getImage('player');
            if (img) {
                ctx.drawImage(img, this.player.x - 16, this.player.y - 16, 32, 32);
            }
        }

        // Lock-on Reticles
        this.lockedTargets.forEach(target => {
            const img = this.assets.getImage('reticle');
            if (img) {
                const size = 32 + Math.sin(this.gameTime * 10) * 4;
                ctx.drawImage(img, target.x - size/2, target.y - size/2, size, size);
            }
        });

        this.particles.draw(ctx);
        ctx.restore();

        this.screenEffects.drawFlash(ctx, 360, 540);

        // UI
        this.drawUI(ctx);
    }

    drawUI(ctx) {
        ctx.fillStyle = '#fff';
        ctx.font = '16px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`SCORE: ${this.score}`, 10, 25);
        
        ctx.textAlign = 'right';
        ctx.fillText(`LIVES: ${this.player.lives}`, 350, 25);

        // Lock-on indicator
        if (this.lockedTargets.length > 0) {
            ctx.textAlign = 'center';
            ctx.fillStyle = '#0ff';
            ctx.font = 'bold 20px monospace';
            ctx.fillText(`LOCK: ${this.lockedTargets.length}`, 180, 500);
            
            // Multiplier hint
            ctx.font = '12px monospace';
            ctx.fillText(`x${this.lockedTargets.length * this.lockedTargets.length} BONUS`, 180, 520);
        }

        // Boss warning
        if (this.gameTime > this.BOSS_SPAWN_TIME - 3 && this.gameTime < this.BOSS_SPAWN_TIME) {
            ctx.textAlign = 'center';
            ctx.fillStyle = '#f00';
            ctx.font = 'bold 24px monospace';
            ctx.fillText('WARNING: BOSS APPROACHING', 180, 200);
        }
    }
}

window.addEventListener('load', () => {
    const game = new StarLockOn();
    game.startGame();
});
