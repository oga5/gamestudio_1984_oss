# Task: Improve Game

Enhance an existing game with new features, improvements, or refinements based on user requests.

## Purpose

This task is for continuous development - adding new features or improving existing gameplay without requiring full redesign or new assets (unless specifically requested).

## Input

- User request describing desired improvements
- `/public/game.js`: Current game implementation
- `/work/design.json`: Current game design (for reference)
- Optional: `/public/assets/*`: Existing assets (if additions needed)

## Output

- Updated `/public/game.js`: Improved game code
- Optional: Updated `/work/design.json`: If design changes significantly

## Types of Improvements

### Gameplay Enhancements

**Add new game mechanics**:
- New enemy types or behaviors
- Power-ups or collectibles
- New player abilities
- Difficulty progression

**Adjust game balance**:
- Speed adjustments
- Score values
- Difficulty tuning
- Timing changes

### Feature Additions

**UI improvements**:
- Score display enhancements
- Better visual feedback
- Instructions screen
- High score tracking

**Quality of life**:
- Pause functionality
- Settings menu
- Sound on/off toggle
- Better controls

### Polish

**Visual polish**:
- Animations
- Particle effects
- Screen shake
- Visual transitions

**Audio polish**:
- More sound effects
- Background music
- Audio feedback for actions

## Workflow

1. **Understand request**: Read the user's improvement request carefully
2. **Read current code**: `read_file("/public/game.js")`
3. **Read current design**: `read_file("/work/design.json")`
4. **Check assets**: `list_directory("/public/assets/images")` and `list_directory("/public/assets/sounds")`
5. **Plan improvements**: Determine what code changes are needed
6. **Implement changes**: Update game.js with enhancements
7. **Verify syntax**: `check_syntax("/public/game.js")`
8. **Update design if needed**: If game concept changed significantly
9. **Done**: Improvements implemented

## Implementation Strategy

### For New Features

1. Identify where new feature fits in game loop
2. Add necessary state variables
3. Implement update logic
4. Implement rendering
5. Add event handlers if needed
6. Integrate with existing game states

### For Balance Changes

1. Locate relevant constants/variables
2. Adjust values based on request
3. Ensure changes don't break game logic
4. Consider cascading effects

### For Polish

1. Identify where polish enhances experience
2. Add visual/audio effects
3. Ensure effects don't hurt performance
4. Keep effects consistent with game style

## Asset Considerations

**If improvements need NEW assets**:
- DO NOT create assets yourself
- Document what new assets are needed
- Suggest that user run a new workflow with asset creation tasks

**If improvements use EXISTING assets**:
- **FIRST**: Use `list_directory()` to check ALL available assets
- **USE all existing assets** - artists created them for your game
- Only reference assets that exist
- Reuse existing assets creatively

## Steps

1. Read user's improvement request in detail
2. Read current game.js and design.json
3. Check available assets (if needed for improvements)
4. Plan all improvements and changes
5. Edit game.js with improvements
6. Run `check_syntax("/public/game.js")`
7. If design.json needs updating, update it
8. If syntax OK, done. If not, fix and re-check.

## Best Practices

- Maintain code style and structure
- Don't break existing functionality
- Keep improvements focused on user request
- Add comments for complex new logic
- Preserve game's original character
- Test mental edge cases

## Validation

- [ ] User request understood and addressed
- [ ] Current code and design reviewed
- [ ] Improvements implemented
- [ ] `check_syntax("/public/game.js")` returns "OK"
- [ ] Existing features still work
- [ ] Only existing assets referenced

## Common Mistakes

❌ Adding improvements user didn't request
❌ Breaking existing gameplay
❌ Referencing non-existent assets
❌ **Ignoring available assets in /public/assets/**
❌ Over-complicating the code
❌ Not checking syntax

✅ Focus on requested improvements
✅ Preserve existing functionality
✅ **USE ALL available assets from /public/assets/**
✅ Keep code clean and simple
✅ Verify syntax is clean

## Quality Reference

Reference `/templates/game_template_advanced/game.js` for code structure.
