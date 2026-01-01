# Error Analysis Guide for Programmers

When you receive a test report with failures, follow this structured approach to understand and fix the errors.

## Phase 1: Understand the Error Report

### Step 1: Read the Error Summary
Start by reading the `error_summary` section of test_report.json:

```json
"error_summary": {
  "total_errors": 2,
  "by_severity": {
    "critical": 1,
    "warning": 1
  },
  "by_category": {
    "initialization": 1,
    "null_reference": 1,
    "logic": 0
  }
}
```

**What this tells you:**
- How many problems to fix
- Which are most important (critical first)
- What type of issues they are (initialization, null reference, logic, etc.)

### Step 2: Categorize Errors

Errors fall into these main categories:

#### **Category A: Initialization Errors**
"Variables/objects not initialized before use"
- Symptoms: "Cannot read property X of undefined", "X is not defined"
- Root cause: Missing initialization statement
- Fix strategy: Add initialization before use
- Example fixes:
  ```javascript
  // WRONG
  if (this.controller.isPressed) { ... }

  // RIGHT - Initialize first
  this.controller = new Controller();
  if (this.controller && this.controller.isPressed) { ... }
  ```

#### **Category B: Null Reference Errors**
"Accessing properties on null/undefined objects"
- Symptoms: "Cannot read property X of null/undefined"
- Root cause: Missing null check before property access
- Fix strategy: Add defensive null checks
- Example fixes:
  ```javascript
  // WRONG
  if (this.object.property) { ... }  // What if object is null?

  // RIGHT - Check object exists first
  if (this.object && this.object.property) { ... }
  ```

#### **Category C: Scope/Reference Errors**
"Variables not accessible in current scope"
- Symptoms: "X is not defined", "this.X is not defined"
- Root cause: Wrong scope, missing declaration, or naming mismatch
- Fix strategy: Check variable naming and scope
- Example fixes:
  ```javascript
  // WRONG - 'width' not defined
  const mySize = width * 2;

  // RIGHT - Use this.width or define width
  const mySize = this.width * 2;
  ```

#### **Category D: Syntax Errors**
"Invalid JavaScript syntax"
- Symptoms: "Unexpected token", "Missing )"
- Root cause: Typos, missing brackets, malformed code
- Fix strategy: Check syntax at reported line
- Example fixes:
  ```javascript
  // WRONG - Missing closing bracket
  const x = { a: 1, b: 2

  // RIGHT
  const x = { a: 1, b: 2 };
  ```

#### **Category E: Logic Errors**
"Game doesn't respond to input or behaves incorrectly"
- Symptoms: "No screen changes", "Controls don't work"
- Root cause: Event handlers not working, state transitions broken
- Fix strategy: Debug event handling and state flow
- Example fixes:
  ```javascript
  // WRONG - Event never triggers state change
  canvas.addEventListener('click', () => {
    console.log('clicked');  // Only logs, doesn't change game
  });

  // RIGHT - Event updates game state
  canvas.addEventListener('click', () => {
    this.gameState = 'playing';
    this.update();
  });
  ```

## Phase 2: Analyze Root Cause

For each error, follow this analysis process:

### Question 1: Where is the error?
- **Location**: Line number from error report
- **Context**: Read the surrounding code (before and after)
- **Question to ask**: "What code is executing at this line?"

### Question 2: Why does it fail?
- **Root cause hypothesis**: Read from test_report.json `root_cause` section
- **Variable status**: What's the state of variables at that point?
- **Question to ask**: "What conditions must be true for this code to work?"

### Question 3: What must change?
- **Fix recommendation**: From test_report.json `fix_recommendations`
- **Primary action**: The most important fix
- **Secondary actions**: Additional improvements
- **Question to ask**: "What's the minimal change that fixes this?"

## Phase 3: Understand the Error Pattern

Use this decision table to match your error to a pattern:

| Error Type | Pattern | Root Cause | Fix |
|-----------|---------|-----------|-----|
| "Cannot read property 'X' of undefined" | Object property access | Object not initialized | Add initialization |
| "Cannot read property 'X' of null" | Object property access | Object null check missing | Add null check |
| "X is not defined" | Variable reference | Variable not in scope | Check scope/naming |
| "Unexpected token" | Syntax error | Invalid syntax | Check brackets/quotes |
| "No screen changes" | Logic error | Event handler doesn't update state | Debug event → state flow |

## Phase 4: Plan Your Fix

### Step 1: Verify the Error Understanding

```
✓ I understand the error message
✓ I see the problematic line
✓ I understand why it fails
✓ I know what category it is
✓ I've identified the root cause
```

### Step 2: Choose Your Fix Strategy

For **Initialization Errors**:
```
1. Find where variable should be initialized
2. Add initialization statement
3. Verify it happens before first use
4. Test: Check if error disappears
```

For **Null Reference Errors**:
```
1. Find the property access
2. Add defensive check: `if (object && object.property)`
3. Make sure check happens before access
4. Test: Check if error disappears
```

For **Scope Errors**:
```
1. Check variable naming (typos?)
2. Check if variable is in scope
3. Use `this.variable` if it's an object property
4. Test: Check if error disappears
```

For **Syntax Errors**:
```
1. Go to the reported line
2. Look for unmatched brackets, quotes, commas
3. Fix the syntax
4. Run check_syntax() - must show "OK"
5. Test: Check if error disappears
```

For **Logic Errors**:
```
1. Find the event listener or state update
2. Check if event is properly bound
3. Check if event triggers state change
4. Check if update() is called after state change
5. Test: Check if game responds
```

### Step 3: Implement the Fix

Choose the right file editing tool:
```
✓ Use file_edit() for single, exact matches
✓ Use sed_edit() for pattern replacements
✓ Use replace_file() for major rewrites
```

### Step 4: Verify the Fix

```javascript
// After making changes:
1. Run check_syntax("/public/game.js")
2. Confirm: "OK" status returned
3. Tester will re-run test automatically
4. Check next test report for remaining errors
```

## Common Error Sequences

### Sequence 1: Missing Initialization
```
Error 1: "this.controller is not defined"
Error 2: "Cannot read property 'isPressed' of undefined"
Error 3: "Game doesn't respond to input"

Analysis:
1. Controller object never created
2. Code tries to use undefined controller
3. Input handling doesn't work

Fix:
1. Add: this.controller = new Controller();
2. Place in constructor or setup()
3. Verify before first use
```

### Sequence 2: Missing Null Checks
```
Error 1: "Cannot read property 'x' of null"
Error 2: "Game crashes on specific input"

Analysis:
1. Object initialized but becomes null
2. Code accesses properties without checking

Fix:
1. Add null check: if (object && object.property)
2. Provide fallback value
3. Log warning if unexpected null
```

### Sequence 3: Logic Errors After Fixes
```
After Errors 1-2 fixed:
Error 3: "No screen changes after click"

Analysis:
1. Previous syntax/null errors fixed
2. Event listener exists
3. But state doesn't update

Fix:
1. Check event listener is bound
2. Check event triggers handler
3. Check state updates in handler
4. Check update() called after state change
```

## Tips for Success

### ✅ DO THIS
- Read the error summary first (get overview)
- Check code context from test report
- Match error pattern to category
- Follow the analysis questions
- Use the decision table
- Implement minimal fix
- Verify syntax after edit
- Trust the Tester's error analysis

### ❌ DON'T DO THIS
- Fix multiple different errors at once (fix one category at a time)
- Skip null checks "because it should be initialized"
- Refactor code while fixing errors
- Remove or modify working code
- Assume you know better than the Tester's analysis
- Make changes without understanding why

## Example: Complete Error Fix

### Error Report Received:
```json
{
  "type": "JavaScript Error",
  "message": "Cannot read property 'isPressed' of undefined",
  "location": "game.js:42",
  "severity": "critical",
  "context": {
    "error_line": "if (this.controller.isPressed('SPACE')) {",
    "surrounding_lines": {
      "before": ["40: updateGame();", "41: if (this.controller) {"],
      "after": ["43: this.jump();"]
    }
  },
  "root_cause": {
    "hypothesis": "this.controller not initialized",
    "likely_reason": "Missing initialization in constructor"
  },
  "fix_recommendations": [
    {
      "priority": "primary",
      "action": "Initialize controller in constructor",
      "example": "this.controller = new Controller();"
    }
  ]
}
```

### Analysis Process:
```
Q1: Where? → Line 42, accessing this.controller.isPressed
Q2: Why? → this.controller is undefined (not initialized)
Q3: What? → Need to initialize controller earlier
Pattern? → Initialization error
Root cause? → Missing initialization statement
```

### Fix Plan:
```
1. Find constructor function
2. Add: this.controller = new Controller();
3. Place before any code that uses this.controller
4. Run check_syntax() → verify "OK"
5. Wait for Tester to re-run test
```

### After Fix:
```
Test Report Result: PASS ✓
OR
Test Report Result: FAIL (different error)
→ Analyze next error and repeat
```

---

## Reference

- See `fix_bugs.md` for the overall workflow
- See test_report.json `error_summary` for categorization
- See test_report.json `fix_recommendations` for suggested approaches
