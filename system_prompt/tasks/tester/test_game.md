# Task: Test Game

Test the game in Firefox headless browser and report results.

## Input

- `/public/index.html`: Game HTML file
- `/public/game.js`: Game implementation

## Output

- `/work/test/{NNN}/test_report.json`: Test results and verdict (where NNN is 001, 002, 003, etc.)
- `/work/test/{NNN}/test_result.json`: Raw test output from test_game tool

## Test Directory Structure

Each test run is saved in a numbered directory to preserve test history:
```
/work/test/
├── 001/  # First test
│   ├── test_result.json
│   └── test_report.json
├── 002/  # Second test (after fixes)
│   ├── test_result.json
│   └── test_report.json
└── 003/  # Third test
    ├── test_result.json
    └── test_report.json
```

**Benefits:**
- No backup file management needed
- Complete test history preserved
- Programmer can see progression of fixes

## Workflow

### Step 1: Run Test

The `test_game` tool automatically creates a numbered test directory and saves screenshots there.

```
result = test_game(
  "/public/index.html",
  mode="verification",
  control_keys=["SPACE", "UP", "DOWN", "LEFT", "RIGHT"]
)
```

The result includes:
- `test_directory`: The auto-created directory (e.g., "/work/test/001")
- `success`: Whether the test passed
- Screenshots are saved to the test directory

### Step 2: Parse Test Result

The test result is returned directly from `test_game()`. Parse the JSON to get:
- `test_directory`: Where files are saved (e.g., "/work/test/001")
- `success`: true/false
- `errors`: List of JavaScript errors
- `screenshot_comparisons`: Visual change detection results

### Step 3: Analyze Results

Check:
- ✅ `success`: true/false
- ✅ `errors`: empty array = good, any errors = fail
- ✅ Canvas found
- ✅ Screenshots show changes

### Step 4: Create Report

Write `test_report.json` to the same test directory (use the `test_directory` from the result).

**IMPORTANT: Visual Change Detection Thresholds**

There are **TWO different thresholds** for visual change detection:

1. **Title → Game Started**: Must be **≥2%** different
   - The title screen and game screen should show visible differences
   - This ensures the game actually started and is rendering content

2. **Game Started → Game Playing**: Must be **≥0.02%** different
   - This verifies the game responds to controls

```json
{
  "verdict": "PASS" or "FAIL",
  "timestamp": "2024-01-15T10:30:00",
  "errors": [],
  "checks": {
    "initialization": true/false,
    "canvas_found": true/false,
    "no_js_errors": true/false,
    "responds_to_tap": true/false,
    "responds_to_controls": true/false
  },
  "screenshots": {
    "title_screen": "captured",
    "game_started": "captured, X.XX% different from title (PASS if ≥2%, FAIL if <2%)",
    "game_playing": "captured, X.XX% different from started (PASS if ≥0.02%, FAIL if <0.02%)"
  },
  "message": "Summary of test results"
}
```

**Visual Change Threshold Examples:**
- Title → Game Started:
  - 45.2% diff → responds_to_tap = true (PASS, ≥2%)
  - 5.0% diff → responds_to_tap = true (PASS, ≥2%)
  - 1.5% diff → responds_to_tap = false (FAIL, <2%)
- Game Started → Game Playing:
  - 4.82% diff → responds_to_controls = true (PASS, ≥0.02%)
  - 0.53% diff → responds_to_controls = true (PASS, ≥0.02%)
  - 0.01% diff → responds_to_controls = false (FAIL, <0.02%)

## Creating Rich Error Reports (For Better Programmer Understanding)

When creating test_report.json, **enhance error objects with code context and analysis**.

### How to Enhance JavaScript Errors

**For each JavaScript error reported by the browser:**

1. **Extract error details from browser console:**
   ```
   Message: "Cannot read property 'isPressed' of undefined"
   Location: game.js:42:15
   Severity: "critical" (crashes game) or "warning" (non-fatal)
   ```

2. **Find the error location in game.js and read surrounding code:**
   ```
   40: gameState.update();
   41: if (this.controller) {
   42: if (this.controller.isPressed('SPACE')) {
   43:   this.jump();
   44: }
   ```

3. **Analyze root cause and categorize:**
   - **Initialization error**: "Variable not initialized before use"
   - **Null reference**: "Accessing property on null/undefined"
   - **Scope error**: "Variable not in scope"
   - **Syntax error**: "Invalid JavaScript syntax"
   - **Logic error**: "Game behavior incorrect"

4. **Suggest fixes based on error type:**
   - For `undefined` errors: Add null check or initialize variable
   - For `null` errors: Add null check before access
   - For scope errors: Check variable naming and scope
   - For syntax errors: Fix at reported line
   - For logic errors: Debug event handlers and state flow

### Error Report Structure (Enhanced)

```json
{
  "type": "JavaScript Error",
  "message": "Error message from browser console",
  "location": "game.js:42:15",
  "severity": "critical",

  "context": {
    "code_snippet": "Single line of code with error (for quick reference)",
    "surrounding_lines": {
      "before": ["line 40", "line 41"],
      "error_line": "line 42 with error",
      "after": ["line 43", "line 44"]
    }
  },

  "root_cause": {
    "hypothesis": "Brief explanation of what went wrong",
    "likely_reason": "Why this went wrong",
    "error_category": "initialization|null_reference|scope|syntax|logic"
  },

  "fix_recommendations": [
    {
      "priority": "primary",
      "action": "Most important fix",
      "example": "Code example showing the fix"
    },
    {
      "priority": "secondary",
      "action": "Additional improvement",
      "example": "Code example if applicable"
    }
  ]
}
```

### Error Categories & Analysis

| Category | Symptom | Root Cause | Example Fix |
|----------|---------|-----------|-------------|
| **Initialization** | "Cannot read property X of undefined" | Variable not initialized | `this.obj = new Object(); // before use` |
| **Null Reference** | "Cannot read property X of null" | Missing null check | `if (obj && obj.property) { ... }` |
| **Scope** | "X is not defined" | Wrong scope or naming | `this.variable` or move declaration earlier |
| **Syntax** | "Unexpected token" | Invalid JavaScript syntax | Fix brackets, quotes, commas |
| **Logic** | "No screen changes" | Event handler doesn't work | Check event listener and state updates |

### error_summary (Required)

Include a summary at the end of test_report.json:

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
    "logic": 0,
    "syntax": 0
  }
}
```

This helps Programmer prioritize fixes (critical first) and recognize patterns.

---

## Success Criteria (COMPLETION REQUIREMENT)

These criteria determine if the game is **complete and working**:

**CRITICAL: TWO different visual change thresholds apply:**

1. **Title → Game Started**: Must be **≥2%** different
   - The title screen and game screen should show visible differences
   - This confirms the game actually started and is rendering content

2. **Game Started → Game Playing**: Must be **≥0.02%** different
   - Any visible change confirms the game responds to input

**PASS** requires ALL of:
- [ ] ✅ No JavaScript errors on startup
- [ ] ✅ Canvas element found
- [ ] ✅ Game title displays (screenshot 1)
- [ ] ✅ Game starts after tap/click (≥2% screen change from title)
- [ ] ✅ Game responds to controls (≥0.02% screen change from started)

**FAIL** if ANY of:
- [ ] ❌ JavaScript error in console
- [ ] ❌ Canvas not found
- [ ] ❌ No screen changes after tap (<2% difference from title)
- [ ] ❌ No screen changes after controls (<0.02% difference from started)
- [ ] ❌ Test crashes or times out

**IMPORTANT - READ CAREFULLY**:
- Title → Game Started threshold is **2%** (two percent)
  - 45.2% difference = PASS (much higher than 2%)
  - 5.0% difference = PASS (higher than 2%)
  - 1.5% difference = FAIL (less than 2% - game not rendering properly)
- Game Started → Game Playing threshold is **0.02%** (zero point zero two percent)
  - 4.82% difference = PASS (game is responding)
  - 0.53% difference = PASS (game is responding)
  - 0.01% difference = FAIL (game is NOT responding)
- PASS verdict means the game meets completion criteria
- FAIL verdict triggers automatic bug fix workflow (programmer fixes → re-test)
- Maximum 3 fix attempts before workflow stops
- **You MUST use `write_file()` to create test_report.json** - do NOT edit workflow.json

## Example Reports

### PASS Report (with proper visual changes)
```json
{
  "verdict": "PASS",
  "errors": [],
  "checks": {
    "initialization": true,
    "canvas_found": true,
    "no_js_errors": true,
    "responds_to_tap": true,
    "responds_to_controls": true
  },
  "screenshots": {
    "title_screen": "captured",
    "game_started": "captured, 45.2% different from title (PASS: ≥2%)",
    "game_playing": "captured, 0.53% different from started (PASS: ≥0.02%)"
  },
  "message": "All tests passed. Title→Game: 45.2% (≥2%), Game→Controls: 0.53% (≥0.02%)."
}
```

### FAIL Report (JavaScript error) - ENHANCED VERSION

```json
{
  "verdict": "FAIL",
  "errors": [
    {
      "type": "JavaScript Error",
      "message": "Cannot read property 'x' of undefined",
      "location": "game.js:42:15",
      "severity": "critical",

      "context": {
        "code_snippet": "if (this.controller.isPressed('SPACE'))",
        "surrounding_lines": {
          "before": [
            "40: gameState.update();",
            "41: if (this.controller) {"
          ],
          "error_line": "42: if (this.controller.isPressed('SPACE')) {",
          "after": [
            "43: this.jump();",
            "44: }"
          ]
        }
      },

      "root_cause": {
        "hypothesis": "this.controller is not initialized",
        "likely_reason": "Controller object not created before this line",
        "error_category": "initialization"
      },

      "fix_recommendations": [
        {
          "priority": "primary",
          "action": "Add null check before accessing controller",
          "example": "if (this.controller && this.controller.isPressed('SPACE')) {"
        },
        {
          "priority": "secondary",
          "action": "Ensure controller is initialized in constructor",
          "example": "this.controller = new Controller(); // Move to constructor if not there"
        }
      ]
    }
  ],

  "error_summary": {
    "total_errors": 1,
    "by_severity": {
      "critical": 1,
      "warning": 0
    },
    "by_category": {
      "initialization": 1,
      "null_reference": 0,
      "logic": 0,
      "syntax": 0
    }
  },

  "checks": {
    "initialization": true,
    "canvas_found": true,
    "no_js_errors": false,
    "responds_to_tap": false
  },
  "message": "Game has 1 critical JavaScript error. Programmer should analyze using error_analysis_guide.md."
}
```

**Key additions for Programmer:**
- `context`: Surrounding code lines (programmer can see what was happening)
- `root_cause`: Analysis of why error occurred
- `fix_recommendations`: Specific fix suggestions with examples
- `error_summary`: Categorization of all errors (helps prioritize)
- `by_category`: Error types for pattern matching

### FAIL Report (insufficient visual change from title, <2%)
```json
{
  "verdict": "FAIL",
  "errors": [],
  "checks": {
    "initialization": true,
    "canvas_found": true,
    "no_js_errors": true,
    "responds_to_tap": false,
    "responds_to_controls": false
  },
  "screenshots": {
    "title_screen": "captured",
    "game_started": "captured, 1.2% different from title (FAIL: <2% - game not rendering properly)",
    "game_playing": "captured, 0.53% different from started (PASS: ≥0.02%)"
  },
  "message": "Title→Game difference too small (1.2% < 2%). Game may not be rendering content properly after tap. Programmer should check if game state is updating correctly."
}
```

### FAIL Report (no visual changes during gameplay, <0.03%)
```json
{
  "verdict": "FAIL",
  "errors": [],
  "checks": {
    "initialization": true,
    "canvas_found": true,
    "no_js_errors": true,
    "responds_to_tap": true,
    "responds_to_controls": false
  },
  "screenshots": {
    "title_screen": "captured",
    "game_started": "captured, 42.5% different from title (PASS: ≥2%)",
    "game_playing": "captured, 0.01% different from started (FAIL: <0.02%)"
  },
  "message": "Game started correctly but does not respond to controls. Game→Controls: 0.01% < 0.02%."
}
```

## Common Test Failures and Fixes

### Canvas not found
**Quick Fix (YOU CAN DO THIS):**
```
1. Read index.html
2. Add <canvas id="game-canvas"></canvas> to <body>
3. Re-run test immediately
```

**When to use quick fix:**
- Missing canvas element
- Missing element IDs
- Simple HTML structure issues

### JavaScript error
**Report to Programmer (FAIL verdict):**
- Run `check_syntax()` if needed
- Create FAIL report with error details
- Programmer will fix in next phase

### No screen changes
**Report to Programmer (FAIL verdict):**
- This is a JavaScript logic issue
- Report in test_report.json
- Programmer will fix event handling

## Steps

1. **Run test_game()** - it automatically creates a numbered test directory:
   ```python
   result = test_game(
       "/public/index.html",
       mode="verification",
       control_keys=["SPACE", "UP", "DOWN", "LEFT", "RIGHT"]
   )
   ```

2. **Parse test result** to get the test directory:
   ```python
   # result contains:
   # - test_directory: "/work/test/001" (auto-created)
   # - success: true/false
   # - errors: []
   # - screenshot_comparisons: [...]
   test_dir = result["test_directory"]  # e.g., "/work/test/001"
   ```

3. **Analyze results** and determine verdict (PASS/FAIL)

4. **Save test report** to the SAME test directory:
   ```python
   # Save test report to the auto-created directory
   write_file(f"{test_dir}/test_report.json", report_json)
   ```

5. Done - System automatically triggers fix_bugs if FAIL

**CRITICAL**:
- `test_game()` automatically creates the test directory (e.g., /work/test/001)
- Save `test_report.json` to the SAME directory that was auto-created
- Do NOT use `edit_json_item()` on workflow.json
- Each test run gets its own directory (no overwriting)

Example workflow:
```python
# Run test - auto-creates /work/test/001/ with screenshots and test_result.json
result = test_game("/public/index.html", mode="verification", ...)
test_dir = result["test_directory"]  # "/work/test/001"

# Analyze and create report
report = {"verdict": "PASS" if result["success"] else "FAIL", ...}

# Save to SAME directory
write_file(f"{test_dir}/test_report.json", json.dumps(report))
```

## Validation

- [ ] Test executed successfully via `test_game()`
- [ ] Parsed `test_directory` from result (e.g., "/work/test/001")
- [ ] Results analyzed
- [ ] Clear verdict (PASS or FAIL)
- [ ] Specific error details if FAIL
- [ ] **Report saved to `{test_directory}/test_report.json` using write_file()**
- [ ] Screenshots automatically saved by `test_game()` to same directory
- [ ] ❌ Did NOT edit workflow.json
