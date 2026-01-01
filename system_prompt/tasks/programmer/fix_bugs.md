# Task: Fix Bugs

Fix issues identified in the test report.

## Input

- `/work/test/{NNN}/test_report.json`: Test results with error details (Manager will specify directory)
- `/public/game.js`: Current game implementation

## Output

- Updated `/public/game.js`: Fixed game code

## Test Directory

Manager will provide the test directory number in the task context.
Examples:
- First test: `/work/test/001/test_report.json`
- Second test: `/work/test/002/test_report.json`

**To find latest test (if not specified):**
```
list_directory("/work/test")
# Look for highest numbered directory (001, 002, 003, etc.)
# Use latest: /work/test/003/test_report.json
```

## Workflow

### Phase 1: Understand Errors
1. **Read test report**: `read_file("/work/test/{NNN}/test_report.json")`
2. **Read error summary**: Check `error_summary` section for total count and categories
3. **Analyze each error**: Use `error_analysis_guide.md` for structured analysis
4. **Understand root causes**: From `root_cause` section in test_report.json

### Phase 2: Plan Fixes
5. **Match errors to patterns**: Use error categorization table
6. **Choose fix strategy**: For each error type (see Fix Strategy section below)
7. **Read current code**: `read_file("/public/game.js")`
8. **Plan ALL fixes**: Before making any changes, plan all fixes

### Phase 3: Implement Fixes
9. **Fix issues**: Update game.js to resolve errors (fix one category at a time)
10. **Verify syntax**: `check_syntax("/public/game.js")`
11. **Done**: Tester will re-test (in next numbered directory)

## Common Error Types

### JavaScript Runtime Errors

**"Cannot read property 'x' of undefined"**:
- Cause: Accessing property on null/undefined object
- Fix: Add null checks or initialize variables

**"Cannot access property 'x' of undefined"**:
- Cause: Variable not defined before use
- Fix: Check initialization order

**"Uncaught ReferenceError: X is not defined"**:
- Cause: Variable/function used before declaration
- Fix: Move declaration earlier or check scope

### Syntax Errors

**"Unexpected token"**:
- Cause: Syntax mistake (missing bracket, etc.)
- Fix: Check syntax at reported line and surrounding lines

**"Escaped backticks detected"**:
- Cause: Template literals have `\`` instead of `` ` `` (literal backslash-backtick in the JS file)
- Fix: Replace `\`` with `` ` `` using `file_edit()` or `sed_edit()`
- **Approach 1 - file_edit (exact match)**:
  1. Read the file: `read_file("/public/game.js")`
  2. Copy EXACT text from output (with `\``)
  3. Call: `file_edit("/public/game.js", old_string="broken text", new_string="fixed text")`
- **Approach 2 - sed_edit (regex pattern)**:
  1. Use regex to find/replace: `sed_edit("/public/game.js", r'\\`', '`', global_replace=True)`
  2. This replaces all escaped backticks with proper backticks

### Logic Errors

**"No screen changes after tap"**:
- Cause: Game not responding to click/touch
- Fix: Check event listener and state transitions

**"No screen changes with controls"**:
- Cause: Keyboard controls not working
- Fix: Check keydown handler and game state updates

## Understanding Errors

**IMPORTANT**: Before fixing anything, use the error_analysis_guide.md to understand:

1. **Error Category**: What type of error is it? (initialization, null reference, logic, etc.)
2. **Root Cause**: Why does it fail? (from `root_cause` section in test_report.json)
3. **Fix Strategy**: What's the appropriate fix for this category?

See **error_analysis_guide.md** for complete analysis methodology.

## Fix Strategy by Error Category

1. **Syntax Errors**: Fix these first (blocks everything else)
   - Invalid JavaScript syntax
   - Missing brackets, quotes, semicolons
   - Procedure: Fix reported line, run check_syntax()

2. **Initialization Errors**: Fix second (variables must exist)
   - Variables not initialized before use
   - Missing object creation
   - Procedure: Add initialization, verify before first use

3. **Null Reference Errors**: Fix third (defensive programming)
   - Accessing properties on null/undefined
   - Missing null checks
   - Procedure: Add null checks before access

4. **Logic Errors**: Fix last (after other errors resolved)
   - Game doesn't respond to input
   - State transitions broken
   - Procedure: Debug event handlers and state flow

### File Editing Approach

**Choose the right tool for the job:**
- **`file_edit()`** - For exact-match replacements (single line, small block)
  - Most reliable when string appears only once
  - Fails clearly if string not found or appears multiple times

- **`sed_edit()`** - For pattern-based replacements
  - Use when replacing multiple similar patterns
  - Good for bulk changes (e.g., `var` → `const`)

- **`replace_file()`** - For major rewrites
  - When multiple fixes needed, easier to rewrite whole file
  - Most reliable when other tools fail repeatedly

## Steps

### Step 1: Understand the Errors
1. Read test report: `read_file("/work/test/{NNN}/test_report.json")`
2. Check `error_summary` to see total errors and categories
3. For each error, use **error_analysis_guide.md** to understand:
   - Error category (syntax, initialization, null reference, logic)
   - Root cause (from `root_cause` section)
   - Fix strategy (from fix_recommendations)

### Step 2: Analyze Code
4. Read current game.js: `read_file("/public/game.js")`
5. Find each error location in the code
6. Understand the context around each error

### Step 3: Plan Fixes
7. For each error, decide:
   - What's the minimal change needed?
   - Which file editing tool to use? (file_edit, sed_edit, replace_file)
   - What order to fix them? (syntax → init → null → logic)

### Step 4: Implement Fixes
8. Edit game.js with fixes (fix one category at a time)
9. Run `check_syntax("/public/game.js")`
10. If syntax OK, done. If not, fix syntax errors and re-check.

## Validation

- [ ] check_syntax returns "OK"
- [ ] All errors from test report addressed
- [ ] No new errors introduced

## Common Mistakes

❌ Fixing only first error (fix ALL errors)
❌ Not checking syntax after edit
❌ Introducing new bugs while fixing old ones
❌ **Removing or ignoring generated assets** during fixes
❌ Using `file_edit()` when string appears multiple times (use `sed_edit()` instead)
❌ Retrying `file_edit()` when it fails (switch to `sed_edit()` or `replace_file()`)

✅ Fix all reported errors
✅ Verify syntax is clean
✅ Test logic carefully
✅ **Keep using all existing assets from /public/assets/**
✅ Choose right tool: `file_edit()` for single fixes, `sed_edit()` for patterns, `replace_file()` for rewrites

## Reference

**For error analysis methodology:**
- See `error_analysis_guide.md` for structured error analysis
- Decision table for error categorization
- Fix strategy by error type
- Common error sequences and solutions

**Key files to reference:**
- `error_analysis_guide.md` - How to analyze errors
- `fix_error.md` - Fixing user-reported errors (alternative to test report)
- test_report.json - Full error details with context and recommendations
