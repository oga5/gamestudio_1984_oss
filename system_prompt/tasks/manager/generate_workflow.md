# Task: Generate Workflow

Create a workflow JSON to develop the requested game.

## Output

- `/work/workflow.json`: Complete workflow specification

## Available Roles and Tasks for Workflow

**IMPORTANT**: These are TASK NAMES to use in workflow.json.
**Each task is executed by its assigned agent role, NOT by you.**

### Designer
- Task name: `create_game_concept` - Create `/work/design.json` with game specification
- Task name: `create_asset_list` - Create `/work/image_asset.json` and `/work/sound_asset.json` with detailed asset requirements

### Graphic Artist
- Task name: `generate_sprites` - Create all images in `/public/assets/images/` from image_asset.json

### Sound Artist
- Task name: `generate_sounds` - Create all sounds in `/public/assets/sounds/` from sound_asset.json

### Programmer
- Task name: `implement_game` - Write complete `/public/game.js` implementation (NEW GAME)
- Task name: `fix_bugs` - Fix issues identified in test report (after testing)
- Task name: `fix_error` - Fix specific errors based on user report (continuous development)
- Task name: `improve_game` - Add features or improvements to existing game (continuous development)

### Tester
- Task name: `test_game` - Run Firefox test, create `/work/test_report.json`

## CRITICAL: Workflow Order

See manager.md for complete workflow details.

**MANDATORY SEQUENCE** (brief version):
1. Design → Asset Specs
2. Create Images + Sounds
3. Validate Assets
4. Implement Game
5. Test Game
6. (If FAIL) System auto-adds fix phase (max 3 attempts)

**IMPORTANT**:
- ❌ DO NOT add fix_bugs in initial workflow - system handles this automatically
- ✅ System will auto-add fix phases if test verdict is FAIL
- ✅ Workflow ends at first test_game task
- ✅ Asset validation MUST happen before programming

## Workflow JSON Format

```json
{
  "workflow": {
    "name": "Game Development: [Game Title]",
    "description": "Workflow for developing [game type]",
    "phases": [
      {
        "id": "phase_design",
        "name": "Design Phase",
        "description": "Create game concept and asset specifications",
        "tasks": [
          {
            "id": "task_1",
            "agent": "Designer",
            "task": "create_game_concept",
            "description": "Create game design specification",
            "output": "/work/design.json",
            "status": "pending"
          },
          {
            "id": "task_2",
            "agent": "Designer",
            "task": "create_asset_list",
            "description": "Create detailed asset specifications",
            "output": "/work/image_asset.json, /work/sound_asset.json",
            "dependencies": ["task_1"],
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_assets",
        "name": "Asset Creation Phase",
        "description": "Create all game assets",
        "tasks": [
          {
            "id": "task_3",
            "agent": "Graphic Artist",
            "task": "generate_sprites",
            "description": "Create all sprite images",
            "output": "/public/assets/images/*.png",
            "dependencies": ["task_2"],
            "status": "pending"
          },
          {
            "id": "task_4",
            "agent": "Sound Artist",
            "task": "generate_sounds",
            "description": "Create all sound effects",
            "output": "/public/assets/sounds/*.wav",
            "dependencies": ["task_2"],
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_implementation",
        "name": "Implementation Phase",
        "description": "Implement game code",
        "tasks": [
          {
            "id": "task_5",
            "agent": "Programmer",
            "task": "implement_game",
            "description": "Write complete game implementation",
            "output": "/public/game.js",
            "dependencies": ["task_3", "task_4"],
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_testing",
        "name": "Testing Phase",
        "description": "Test game functionality",
        "tasks": [
          {
            "id": "task_6",
            "agent": "Tester",
            "task": "test_game",
            "description": "Run automated game test",
            "output": "/work/test_report.json",
            "dependencies": ["task_5"],
            "status": "pending"
          }
        ]
      }
    ]
  }
}
```

## Workflow Validation Rules

When creating workflow, ensure:

1. **Design First**: Designer tasks always come first
2. **Assets Before Code**: Both Graphic Artist AND Sound Artist complete before Programmer
3. **Test After Code**: Tester runs after Programmer
4. **Dependencies**: Each task lists which tasks must complete first
5. **Asset Validation**: Add validation step between assets and implementation

## Workflow Creation Steps

### Step 1: Detect Project Type

**Check if this is an existing project**:
1. Use `file_exists("/public/game.js")` to check if game already exists
2. If game.js exists: This is **continuous development** (improvement/fix)
3. If game.js doesn't exist: This is **new game development**

### Step 2: Determine Workflow Type

**For NEW GAME (game.js doesn't exist)**:
- Full workflow: Design → Assets → Implementation → Testing
- Include all phases as shown in template below

**For CONTINUOUS DEVELOPMENT (game.js exists)**:
- Check if user request needs new assets:
  - If request mentions "new sprites", "new images", "new sounds", "add graphics", etc.: Include asset phases
  - If request is about bugs, improvements, features using existing assets: Skip asset phases
- Simplified workflow based on request type:
  - **Error fix**: Programmer (fix_error) → Tester (test_game)
  - **Improvement**: Programmer (improve_game) → Tester (test_game)
  - **With new assets**: Designer (create_asset_list) → Artists (generate_sprites/sounds) → Programmer (improve_game) → Tester

### Step 3: Read Existing State (for continuous development)

If game.js exists:
1. Use `read_file("/public/game.js")` to understand current implementation
2. Use `read_file("/work/design.json")` if it exists to understand current design
3. Include this information in workflow description for context

### Step 4: Create Appropriate Workflow

Based on project type and needs:
- **New game**: Use full workflow template
- **Fix error (no new assets)**: Minimal workflow with fix_error + test
- **Improve game (no new assets)**: Minimal workflow with improve_game + test
- **Add assets + improvements**: Include asset creation phases before programmer

### Step 5: Write Workflow

Write the appropriate workflow to `/work/workflow.json`

## Validation Checklist

- [ ] Design phase first
- [ ] Asset phase second (both artists)
- [ ] Implementation phase third (after assets)
- [ ] Testing phase fourth (after implementation)
- [ ] Dependencies correctly specified
- [ ] All task IDs unique
- [ ] All agent names match available roles

## Workflow Examples

### Example 1: New Game Development (Full Workflow)

Use the template shown above with all phases.

### Example 2: Fix Error (Continuous Development - No Assets)

```json
{
  "workflow": {
    "name": "Fix Error: [Error Description]",
    "description": "Fix error in existing game",
    "phases": [
      {
        "id": "phase_fix",
        "name": "Error Fix Phase",
        "description": "Fix reported error",
        "tasks": [
          {
            "id": "task_1",
            "agent": "Programmer",
            "task": "fix_error",
            "description": "Fix the reported error",
            "output": "/public/game.js",
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_testing",
        "name": "Testing Phase",
        "description": "Verify fix works",
        "tasks": [
          {
            "id": "task_2",
            "agent": "Tester",
            "task": "test_game",
            "description": "Test the game after fix",
            "output": "/work/test_report.json",
            "dependencies": ["task_1"],
            "status": "pending"
          }
        ]
      }
    ]
  }
}
```

### Example 3: Improve Game (Continuous Development - No Assets)

```json
{
  "workflow": {
    "name": "Improve Game: [Improvement Description]",
    "description": "Add improvements to existing game",
    "phases": [
      {
        "id": "phase_improvement",
        "name": "Improvement Phase",
        "description": "Implement requested improvements",
        "tasks": [
          {
            "id": "task_1",
            "agent": "Programmer",
            "task": "improve_game",
            "description": "Implement game improvements",
            "output": "/public/game.js",
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_testing",
        "name": "Testing Phase",
        "description": "Verify improvements work",
        "tasks": [
          {
            "id": "task_2",
            "agent": "Tester",
            "task": "test_game",
            "description": "Test the improved game",
            "output": "/work/test_report.json",
            "dependencies": ["task_1"],
            "status": "pending"
          }
        ]
      }
    ]
  }
}
```

### Example 4: Improve with New Assets (Continuous Development - With Assets)

```json
{
  "workflow": {
    "name": "Improve Game with New Assets",
    "description": "Add new assets and improvements",
    "phases": [
      {
        "id": "phase_design",
        "name": "Asset Design Phase",
        "description": "Define new assets needed",
        "tasks": [
          {
            "id": "task_1",
            "agent": "Designer",
            "task": "create_asset_list",
            "description": "Define new asset requirements",
            "output": "/work/image_asset.json, /work/sound_asset.json",
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_assets",
        "name": "Asset Creation Phase",
        "description": "Create new assets",
        "tasks": [
          {
            "id": "task_2",
            "agent": "Graphic Artist",
            "task": "generate_sprites",
            "description": "Create new sprite images",
            "output": "/public/assets/images/*.png",
            "dependencies": ["task_1"],
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_improvement",
        "name": "Improvement Phase",
        "description": "Implement improvements with new assets",
        "tasks": [
          {
            "id": "task_3",
            "agent": "Programmer",
            "task": "improve_game",
            "description": "Implement improvements using new assets",
            "output": "/public/game.js",
            "dependencies": ["task_2"],
            "status": "pending"
          }
        ]
      },
      {
        "id": "phase_testing",
        "name": "Testing Phase",
        "description": "Test improvements",
        "tasks": [
          {
            "id": "task_4",
            "agent": "Tester",
            "task": "test_game",
            "description": "Test the improved game",
            "output": "/work/test_report.json",
            "dependencies": ["task_3"],
            "status": "pending"
          }
        ]
      }
    ]
  }
}
```

## Common Mistakes

❌ Not checking if game.js exists (missing project type detection)
❌ Including full design phase for simple fixes
❌ Including asset phases when no new assets needed
❌ Programmer before Graphic Artist (violates asset-first rule)
❌ Programmer before Sound Artist (violates asset-first rule)
❌ Missing dependencies
❌ Wrong agent/task names

✅ Check project type first (new vs existing)
✅ Use minimal workflow for fixes/improvements
✅ Skip asset phases when not needed
✅ Correct phase ordering (Design → Assets → Code → Test)
✅ Proper dependencies
✅ Asset-first rule enforced when assets are needed
✅ Validation between assets and code
