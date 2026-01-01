# Task: Fix Error

Fix specific errors or issues in the game code based on user-reported problems.

## Purpose

This task is for continuous development - fixing errors reported by users or found during manual testing, without requiring a formal test report.

## Input

- User request describing the error or issue
- `/public/game.js`: Current game implementation
- Optional: `/work/design.json` for reference

## Output

- Updated `/public/game.js`: Fixed game code

## Workflow

1. **Understand the issue**: Read the user's error description
2. **Read current code**: `read_file("/public/game.js")`
3. **Identify root cause**: Analyze the code to find the error
4. **Plan the fix**: Determine the minimal change needed
5. **Fix the issue**: Update game.js to resolve the error
6. **Verify syntax**: `check_syntax("/public/game.js")`
7. **Done**: Error should be resolved

## Common Error Scenarios

### Runtime Errors

**"Game crashes when..."**:
- Check the specific code path that triggers the crash
- Add null checks or initialize variables properly
- Verify object properties exist before access

**"Feature X doesn't work"**:
- Locate the code for feature X
- Check event listeners and state transitions
- Verify logic flow and conditions

### Logic Errors

**"Game behavior is incorrect"**:
- Review game state management
- Check update loop logic
- Verify calculations and conditions

**"Controls don't respond"**:
- Check event listeners (click, keydown)
- Verify event handlers are properly bound
- Check game state allows input

### Visual Issues

**"Graphics don't display correctly"**:
- Check asset loading
- Verify draw functions
- Check canvas context state

## Fix Strategy

1. **Reproduce understanding**: Make sure you understand the exact issue
2. **Locate the code**: Find the relevant section in game.js
3. **Minimal fix**: Make the smallest change that fixes the issue
4. **Verify syntax**: Always check syntax after editing
5. **Document if needed**: Add comment explaining non-obvious fixes

## Steps

1. Read user's error description carefully
2. Read current game.js to understand the code
3. Identify the problematic code section
4. Plan the fix (what needs to change)
5. Edit game.js with the fix
6. Run `check_syntax("/public/game.js")`
7. If syntax OK, done. If not, fix syntax errors and re-check.

## Best Practices

- Keep changes minimal and focused
- Don't refactor unrelated code
- Preserve existing functionality
- Test edge cases mentally
- Add comments for complex fixes

## Validation

- [ ] Error description understood
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] `check_syntax("/public/game.js")` returns "OK"
- [ ] No new issues introduced

## Common Mistakes

❌ Making large refactoring changes
❌ Fixing symptoms instead of root cause
❌ Not checking syntax after edit
❌ Breaking other features while fixing one issue
❌ **Removing or ignoring available assets** while fixing

✅ Minimal, focused fix
✅ Address root cause
✅ Verify syntax is clean
✅ Preserve other functionality
✅ **Continue using all existing assets from /public/assets/**

## Reference

See `/templates/game_template_advanced/game.js` for code structure reference if needed.
