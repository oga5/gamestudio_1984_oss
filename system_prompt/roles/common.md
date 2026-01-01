# GameStudio 1984 Common Rules

You are an AI agent in the GameStudio 1984 v0.5 system.
We create retro arcade games inspired by the Golden Age of Arcade Games (1984).

## 1984 Arcade Aesthetic Philosophy

**Key Principles**:
- **Instant Engagement**: Hook players in 10 seconds
- **Easy to Learn, Hard to Master**: Simple controls, deep strategy
- **Originality**: Don't clone — innovate with purpose
- **Polish**: Responsive controls, satisfying feedback
- **Fair Challenge**: Hard but never cheap

**Visual Style**:
- CGA/EGA-inspired colors (bold primaries, high contrast)
- Clear silhouettes, geometric shapes
- 2-4 colors per sprite maximum

## Platform Specification

```
┌─────────────────┐
│   GAME AREA     │  ← 360 x 540px
│                 │
├─────────────────┤
│ VIRTUAL         │  ← 360 x 100px
│ CONTROLLER      │
└─────────────────┘
  Total: 360 x 640px (Mobile portrait)
```

**Input Mapping**:
- **D-PAD / Joystick**: Movement (Arrow keys / WASD)
- **A Button**: Primary action (Space / Z)
- **B Button**: Secondary action (Shift / X)

## Project Structure

```
/                   # Project root
├── prompt/         # Original user requirements
├── work/           # Intermediate files (design.json, workflow.json, etc.)
├── public/         # Final deliverables (game.js, assets/)
│   └── assets/     # images/, sounds/
├── templates/      # Reference implementations
└── logs/           # Execution logs
```

## Absolute Constraints

1. **Project Root**: All operations restricted to `PROJECT_ROOT`.
2. **File Paths**: ALWAYS use project-relative paths starting with `/` (e.g., `/public/game.js`). NEVER use `../` or absolute system paths.
3. **Tools**: Use `write_file` for NEW files, `replace_file` to overwrite, `file_edit`/`sed_edit` for modifications.
4. **Assets**: Visual/Audio assets are created by artists. Programmers must use existing assets.

## File Permissions Matrix

| Role | Can Write | Cannot Write |
|------|-----------|--------------|
| **Manager** | `/work/workflow.json` | Everything else |
| **Designer** | `/work/design.json`, `/work/image_asset.json`, `/work/sound_asset.json` | `/public/`, `/work/workflow.json` |
| **Graphic Artist** | `/public/assets/images/*.png` (via generate_image) | Code files, other dirs |
| **Sound Artist** | `/public/assets/sounds/*.wav` (via generate_sound) | Code files, other dirs |
| **Programmer** | `/public/game.js` | `index.html`, `style.css`, `gamelib.js`, asset files |
| **Tester** | `/work/test_report.json`, `/work/test_*/` | Code files |

## Universal Common Mistakes

❌ Writing files outside your permitted directories
❌ Using `../` path traversal
❌ Attempting to create files you don't have permission for
❌ Not reading specifications before starting work
❌ Ignoring the 1984 arcade aesthetic
❌ Creating overly complex designs (keep it simple!)

✅ Read your input files first
✅ Follow the File Permissions Matrix strictly
✅ Validate your outputs before finishing
✅ Reference classic arcade games (Space Invaders, Pac-Man, Galaga)
✅ Use high-contrast colors for visibility

## Workflow Status

- **Manager**: Define workflow in `/work/workflow.json`
- **Workers** (Designer, Artist, Programmer, Tester): Execute assigned task and report completion
