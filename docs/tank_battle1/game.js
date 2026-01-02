/**
 * CyberTank 1984
 * A futuristic tank shooter with energy management and homing missiles.
 */

class CyberTank extends GameEngine {
    constructor() {
        super('game-canvas', {
            title: 'CYBER TANK 1984',
            description: 'Manage energy to use homing missiles and barrier.'
        });

        // Systems
        this.particles = new ParticleSystem();
        this.screenEffects = new ScreenEffects();
        this.stages = new StageSystem();
        this.tileMap = new TileMapSystem(30, 30, 12, 18);

        // Game State
        this.player = null;
        this.enemies = [];
        this.projectiles = [];
        this.enemyProjectiles = [];
        this.currentStageData = null;
        this.isEnergyLowSoundPlaying = false;
    }

    loadAssets() {
        // Images
        this.assets.loadImage('player', 'assets/images/player_tank.png');
        this.assets.loadImage('enemy_turret', 'assets/images/enemy_turret.png');
        this.assets.loadImage('enemy_scout', 'assets/images/enemy_scout.png');
        this.assets.loadImage('missile', 'assets/images/missile.png');
        this.assets.loadImage('bullet', 'assets/images/bullet.png');
        this.assets.loadImage('barrier', 'assets/images/barrier.png');
        this.assets.loadImage('wall', 'assets/images/wall.png');

        // Sounds
        this.assets.loadSound('bgm_game', 'assets/sounds/bgm_game.wav');
        this.assets.loadSound('shoot', 'assets/sounds/missile_launch.wav');
        this.assets.loadSound('explosion', 'assets/sounds/explosion.wav');
        this.assets.loadSound('barrier_hum', 'assets/sounds/barrier_hum.wav');
        this.assets.loadSound('energy_low', 'assets/sounds/energy_low.wav');
        this.assets.loadSound('hit', 'assets/sounds/player_hit.wav');
    }

    initGame() {
        this.score = 0;
        this.stages.reset();
        
        // Load stage data from design.json (hardcoded here for simplicity as per design)
        const stageData = [
            { id: 1, name: "Entry Point", walls: [[4,6], [5,6], [6,6], [4,12], [5,12], [6,12]], enemies: [{type: "turret", x: 180, y: 100}] },
            { id: 2, name: "Corridor", walls: [[2,8], [3,8], [8,8], [9,8], [5,4], [6,4]], enemies: [{type: "turret", x: 60, y: 80}, {type: "turret", x: 300, y: 80}] },
            { id: 3, name: "Crossfire", walls: [[5,8], [6,8], [5,9], [6,9]], enemies: [{type: "scout", x: 50, y: 150}, {type: "scout", x: 310, y: 150}, {type: "turret", x: 180, y: 50}] },
            { id: 4, name: "The Wall", walls: [[0,10], [1,10], [2,10], [3,10], [6,10], [7,10], [8,10], [9,10]], enemies: [{type: "turret", x: 180, y: 80}, {type: "turret", x: 100, y: 50}, {type: "turret", x: 260, y: 50}] },
            { id: 5, name: "Ambush", walls: [[3,5], [8,5], [3,15], [8,15]], enemies: [{type: "scout", x: 180, y: 100}, {type: "scout", x: 180, y: 200}, {type: "turret", x: 50, y: 50}, {type: "turret", x: 310, y: 50}] },
            { id: 6, name: "Maze Lite", walls: [[2,4], [2,5], [2,6], [9,12], [9,13], [9,14], [5,9], [6,9]], enemies: [{type: "turret", x: 50, y: 50}, {type: "turret", x: 310, y: 50}, {type: "scout", x: 180, y: 250}] },
            { id: 7, name: "Fortress", walls: [[4,4], [5,4], [6,4], [4,5], [6,5], [4,6], [5,6], [6,6]], enemies: [{type: "turret", x: 180, y: 50}, {type: "scout", x: 50, y: 100}, {type: "scout", x: 310, y: 100}, {type: "scout", x: 180, y: 300}] },
            { id: 8, name: "Final Conflict", walls: [[2,2], [9,2], [2,16], [9,16], [5,9], [6,9]], enemies: [{type: "turret", x: 180, y: 40}, {type: "turret", x: 100, y: 40}, {type: "turret", x: 260, y: 40}, {type: "scout", x: 50, y: 200}, {type: "scout", x: 310, y: 200}] }
        ];
        this.stages.loadStages(stageData);
        
        this.startStage();
    }

    startStage() {
        this.currentStageData = this.stages.getCurrentStage();
        this.currentStage = this.stages.getStageNumber();
        
        // Initialize TileMap
        const map = [];
        for (let y = 0; y < 18; y++) {
            map[y] = [];
            for (let x = 0; x < 12; x++) {
                map[y][x] = 0;
            }
        }
        this.currentStageData.walls.forEach(([wx, wy]) => {
            if (map[wy] && map[wy][wx] !== undefined) map[wy][wx] = 1;
        });
        this.tileMap.loadMap(map);

        // Initialize Player
        this.player = {
            x: 180,
            y: 480,
            width: 32,
            height: 32,
            radius: 14,
            angle: -Math.PI / 2, // Facing up
            speed: 150,
            rotationSpeed: Math.PI, // 180 degrees per second
            energy: 100,
            maxEnergy: 100,
            recoveryRate: 25,
            missileCost: 15,
            barrierCostIdle: 10,
            barrierCostMoving: 30,
            shootCooldown: 0,
            maxShootCooldown: 0.4,
            barrierActive: false,
            invincible: 0
        };

        // Initialize Enemies
        this.enemies = this.currentStageData.enemies.map(e => {
            const type = e.type === 'turret' ? 'turret' : 'scout';
            return {
                type: type,
                x: e.x,
                y: e.y,
                width: type === 'turret' ? 28 : 24,
                height: type === 'turret' ? 28 : 24,
                radius: type === 'turret' ? 12 : 10,
                angle: Math.PI / 2, // Facing down
                health: 1,
                shootTimer: Math.random() * 2,
                shootInterval: type === 'turret' ? 2.0 : 2.5,
                speed: type === 'turret' ? 0 : 60,
                dir: 1, // For scout patrol
                scoreValue: type === 'turret' ? 100 : 150
            };
        });

        this.projectiles = [];
        this.enemyProjectiles = [];
        this.particles.clear();
        this.screenEffects.reset();

        // BGM
        this.assets.stopAllLoops();
        this.assets.playSoundLoop('bgm_game');
        this.assets.setVolume('bgm_game', 0.4);
        this.isEnergyLowSoundPlaying = false;
    }

    updateGame(deltaTime) {
        if (this.stateManager.is(GameStateManager.STATES.PLAYING)) {
            this.updatePlayer(deltaTime);
            this.updateEnemies(deltaTime);
            this.updateProjectiles(deltaTime);
            this.checkCollisions();
            
            this.particles.update(deltaTime);
            this.screenEffects.update(deltaTime);

            // Check Stage Clear
            if (this.enemies.length === 0) {
                this.assets.stopAllLoops();
                if (this.stages.isLastStage()) {
                    this.gameClear();
                } else {
                    this.stageClear(1000);
                }
            }
        }
    }

    updatePlayer(deltaTime) {
        const p = this.player;
        
        // Rotation
        const h = this.controller.getHorizontal();
        p.angle += h * p.rotationSpeed * deltaTime;

        // Movement
        const v = -this.controller.getVertical();
        let isMoving = false;
        if (v !== 0) {
            const nextX = p.x + Math.cos(p.angle) * v * p.speed * deltaTime;
            const nextY = p.y + Math.sin(p.angle) * v * p.speed * deltaTime;
            
            // Wall Collision
            const rect = { x: nextX - p.width/2, y: nextY - p.height/2, width: p.width, height: p.height };
            if (!this.tileMap.checkCollision(rect, [1])) {
                p.x = nextX;
                p.y = nextY;
                isMoving = true;
            }
            
            // Screen Bounds
            p.x = Math.max(p.width/2, Math.min(360 - p.width/2, p.x));
            p.y = Math.max(p.height/2, Math.min(540 - p.height/2, p.y));
        }

        // Barrier
        const bPressed = this.controller.isPressed('b');
        if (bPressed && p.energy > 0) {
            if (!p.barrierActive) {
                this.assets.playSoundLoop('barrier_hum');
                this.assets.setVolume('barrier_hum', 0.3);
            }
            p.barrierActive = true;
            const cost = isMoving ? p.barrierCostMoving : p.barrierCostIdle;
            p.energy -= cost * deltaTime;
        } else {
            if (p.barrierActive) {
                this.assets.stopSound('barrier_hum');
            }
            p.barrierActive = false;
        }

        // Energy Recovery
        if (!p.barrierActive && !isMoving && v === 0 && h === 0) {
            p.energy = Math.min(p.maxEnergy, p.energy + p.recoveryRate * deltaTime);
        }

        // Energy Low SFX
        if (p.energy < 20 && !this.isEnergyLowSoundPlaying) {
            this.assets.playSoundLoop('energy_low');
            this.assets.setVolume('energy_low', 0.5);
            this.isEnergyLowSoundPlaying = true;
        } else if (p.energy >= 20 && this.isEnergyLowSoundPlaying) {
            this.assets.stopSound('energy_low');
            this.isEnergyLowSoundPlaying = false;
        }
        
        if (p.energy <= 0) {
            p.energy = 0;
            p.barrierActive = false;
            this.assets.stopSound('barrier_hum');
        }

        // Shooting
        if (p.shootCooldown > 0) p.shootCooldown -= deltaTime;
        if (this.controller.isJustPressed('a') && p.shootCooldown <= 0 && p.energy >= p.missileCost) {
            this.fireMissile();
            p.energy -= p.missileCost;
            p.shootCooldown = p.maxShootCooldown;
            this.playSound('shoot');
        }

        // Invincibility
        if (p.invincible > 0) p.invincible -= deltaTime;
    }

    fireMissile() {
        const p = this.player;
        this.projectiles.push({
            x: p.x + Math.cos(p.angle) * 20,
            y: p.y + Math.sin(p.angle) * 20,
            angle: p.angle,
            startAngle: p.angle,
            speed: 300,
            radius: 4,
            lifetime: 3.0,
            homingLimit: 30 * Math.PI / 180, // 30 degrees
            turnRate: 120 * Math.PI / 180 // 120 degrees per second
        });
    }

    updateEnemies(deltaTime) {
        this.enemies.forEach(e => {
            // Behavior
            if (e.type === 'turret') {
                // Rotate to player
                const targetAngle = Math.atan2(this.player.y - e.y, this.player.x - e.x);
                e.angle = targetAngle;
            } else if (e.type === 'scout') {
                // Patrol horizontal
                const nextX = e.x + e.speed * e.dir * deltaTime;
                const rect = { x: nextX - e.width/2, y: e.y - e.height/2, width: e.width, height: e.height };
                if (this.tileMap.checkCollision(rect, [1]) || nextX < e.width/2 || nextX > 360 - e.width/2) {
                    e.dir *= -1;
                } else {
                    e.x = nextX;
                }
                e.angle = e.dir > 0 ? 0 : Math.PI;
            }

            // Shooting
            e.shootTimer -= deltaTime;
            if (e.shootTimer <= 0) {
                this.enemyFire(e);
                e.shootTimer = e.shootInterval;
            }
        });
    }

    enemyFire(e) {
        const angle = e.type === 'turret' ? e.angle : Math.atan2(this.player.y - e.y, this.player.x - e.x);
        this.enemyProjectiles.push({
            x: e.x + Math.cos(angle) * 15,
            y: e.y + Math.sin(angle) * 15,
            vx: Math.cos(angle) * 180,
            vy: Math.sin(angle) * 180,
            radius: 3
        });
    }

    updateProjectiles(deltaTime) {
        // Player Missiles (Homing)
        this.projectiles.forEach(m => {
            m.lifetime -= deltaTime;
            
            // Find nearest enemy for homing
            let nearest = null;
            let minDist = Infinity;
            this.enemies.forEach(e => {
                const d = CollisionSystem.distance(m.x, m.y, e.x, e.y);
                if (d < minDist) {
                    minDist = d;
                    nearest = e;
                }
            });

            if (nearest) {
                const targetAngle = Math.atan2(nearest.y - m.y, nearest.x - m.x);
                let angleDiff = targetAngle - m.angle;
                while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
                while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

                // Check if within 30 degrees of START angle (as per requirement)
                // Actually, the requirement says "from firing direction"
                let diffFromStart = targetAngle - m.startAngle;
                while (diffFromStart > Math.PI) diffFromStart -= Math.PI * 2;
                while (diffFromStart < -Math.PI) diffFromStart += Math.PI * 2;

                if (Math.abs(diffFromStart) <= m.homingLimit) {
                    const turn = Math.sign(angleDiff) * m.turnRate * deltaTime;
                    if (Math.abs(turn) > Math.abs(angleDiff)) {
                        m.angle = targetAngle;
                    } else {
                        m.angle += turn;
                    }
                }
            }

            m.x += Math.cos(m.angle) * m.speed * deltaTime;
            m.y += Math.sin(m.angle) * m.speed * deltaTime;

            // Trail
            this.screenEffects.addTrail(m.x, m.y, '#00ffff', 4, 0.2);
        });
        this.projectiles = this.projectiles.filter(m => m.lifetime > 0);

        // Enemy Bullets
        this.enemyProjectiles.forEach(b => {
            b.x += b.vx * deltaTime;
            b.y += b.vy * deltaTime;
        });
        this.enemyProjectiles = this.enemyProjectiles.filter(b => 
            b.x > -10 && b.x < 370 && b.y > -10 && b.y < 550
        );
    }

    checkCollisions() {
        // Player Missiles vs Enemies
        for (let i = this.projectiles.length - 1; i >= 0; i--) {
            const m = this.projectiles[i];
            
            // vs Walls
            if (this.tileMap.getTileAtPosition(m.x, m.y) === 1) {
                this.createExplosion(m.x, m.y, '#00ffff');
                this.projectiles.splice(i, 1);
                continue;
            }

            // vs Enemies
            for (let j = this.enemies.length - 1; j >= 0; j--) {
                const e = this.enemies[j];
                if (CollisionSystem.circleCollision(m, e)) {
                    this.createExplosion(e.x, e.y, '#ffaa00');
                    this.score += e.scoreValue;
                    this.enemies.splice(j, 1);
                    this.projectiles.splice(i, 1);
                    this.playSound('explosion');
                    break;
                }
            }
        }

        // Enemy Bullets vs Player/Walls
        for (let i = this.enemyProjectiles.length - 1; i >= 0; i--) {
            const b = this.enemyProjectiles[i];

            // vs Walls
            if (this.tileMap.getTileAtPosition(b.x, b.y) === 1) {
                this.enemyProjectiles.splice(i, 1);
                continue;
            }

            // vs Player
            if (CollisionSystem.circleCollision(b, this.player)) {
                if (this.player.barrierActive) {
                    // Blocked by barrier
                    this.createExplosion(b.x, b.y, '#00ffff', 5);
                    this.enemyProjectiles.splice(i, 1);
                } else if (this.player.invincible <= 0) {
                    // Hit!
                    this.playerHit();
                    this.enemyProjectiles.splice(i, 1);
                }
            }
        }
    }

    playerHit() {
        this.assets.stopAllLoops();
        this.playSound('hit');
        this.screenEffects.shake(10, 0.4);
        this.screenEffects.flash('#ff0000', 0.1);
        this.createExplosion(this.player.x, this.player.y, '#ff0000', 40);
        this.gameOver();
    }

    createExplosion(x, y, color, count = 20) {
        this.particles.emit(x, y, {
            count: count,
            color: color,
            speed: 4,
            lifetime: 0.6,
            size: 3
        });
    }

    onStageClearComplete() {
        if (this.stages.nextStage()) {
            this.startStage();
            this.stateManager.setState(GameStateManager.STATES.PLAYING);
        } else {
            this.gameClear();
        }
    }

    drawGame(ctx) {
        // Background
        ctx.fillStyle = '#000015';
        ctx.fillRect(0, 0, 360, 540);

        // Apply Camera Shake
        ctx.save();
        const shake = this.screenEffects.getShakeOffset();
        ctx.translate(shake.x, shake.y);

        // Draw Walls
        this.tileMap.draw(ctx, {x: 0, y: 0}, { 1: '#444466' });

        // Draw Trails
        this.screenEffects.drawTrails(ctx);

        // Draw Enemies
        this.enemies.forEach(e => {
            ctx.save();
            ctx.translate(e.x, e.y);
            ctx.rotate(e.angle + Math.PI/2);
            const img = this.assets.getImage(e.type === 'turret' ? 'enemy_turret' : 'enemy_scout');
            if (img) ctx.drawImage(img, -e.width/2, -e.height/2, e.width, e.height);
            ctx.restore();
        });

        // Draw Player
        const p = this.player;
        if (p.invincible <= 0 || Math.floor(Date.now() / 100) % 2 === 0) {
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(p.angle + Math.PI/2);
            const pImg = this.assets.getImage('player');
            if (pImg) ctx.drawImage(pImg, -p.width/2, -p.height/2, p.width, p.height);
            ctx.restore();

            // Barrier
            if (p.barrierActive) {
                ctx.save();
                ctx.translate(p.x, p.y);
                const bImg = this.assets.getImage('barrier');
                const bSize = p.width * 1.5;
                const pulse = 1 + Math.sin(Date.now() / 100) * 0.05;
                if (bImg) {
                    ctx.globalAlpha = 0.6;
                    ctx.drawImage(bImg, -bSize*pulse/2, -bSize*pulse/2, bSize*pulse, bSize*pulse);
                    ctx.globalAlpha = 1.0;
                }
                ctx.restore();
            }
        }

        // Draw Projectiles
        this.projectiles.forEach(m => {
            ctx.save();
            ctx.translate(m.x, m.y);
            ctx.rotate(m.angle + Math.PI/2);
            const mImg = this.assets.getImage('missile');
            if (mImg) ctx.drawImage(mImg, -8, -8, 16, 16);
            ctx.restore();
        });

        this.enemyProjectiles.forEach(b => {
            const bImg = this.assets.getImage('bullet');
            if (bImg) ctx.drawImage(bImg, b.x - 6, b.y - 6, 12, 12);
        });

        // Particles
        this.particles.draw(ctx);

        ctx.restore();

        // Flash
        this.screenEffects.drawFlash(ctx, 360, 540);

        // HUD
        this.drawHUD(ctx);
    }

    drawHUD(ctx) {
        // Energy Bar
        const p = this.player;
        const barX = 10;
        const barY = 520;
        const barW = 150;
        const barH = 10;
        
        ctx.fillStyle = '#333';
        ctx.fillRect(barX, barY, barW, barH);
        
        const energyRatio = p.energy / p.maxEnergy;
        ctx.fillStyle = p.energy < 20 ? '#f00' : '#0ff';
        ctx.fillRect(barX, barY, barW * energyRatio, barH);
        
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.strokeRect(barX, barY, barW, barH);
        
        ctx.fillStyle = '#fff';
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText('ENERGY', barX, barY - 5);

        // Score
        this.uiManager.drawScore(this.score, 10, 25);

        // Stage Info
        ctx.fillStyle = '#fff';
        ctx.font = '14px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`STAGE ${this.currentStage}: ${this.currentStageData.name}`, 350, 25);
    }
}

// Start Game
window.addEventListener('load', () => {
    const game = new CyberTank();
    game.startGame();
});
