# Task: Evaluate Workflow Action

Evaluate whether to resume the existing workflow or create a new one based on the project state and user request.

## Context

When a project has an existing workflow with pending tasks, you need to decide:
- **Option 1: Resume** - Continue the existing workflow from where it stopped
- **Option 2: Create New** - Start a new workflow for new features/improvements

## Your Responsibility

Analyze the project state and user request, then make an intelligent decision about the best course of action.

## Output

- `/work/workflow_action.json`: Decision result in JSON format

## Decision Process

### Step 1: Load Existing Workflow

1. Read `/work/workflow.json` to understand the current workflow
2. Identify:
   - What tasks are completed
   - What tasks are pending
   - What tasks are in progress
   - What was the workflow trying to achieve

### Step 2: Analyze Project State

1. Check if `/public/game.js` exists (game implementation)
2. Check if `/work/design.json` exists (game design)
3. Check if `/work/test_report.json` exists (test results)
4. Read these files to understand current project state

### Step 3: Analyze User Request

Parse the user's request to determine intent:
- **Resume indicators**: Empty request, "resume", "continue", "finish", "complete", etc.
- **New work indicators**: Specific feature requests, bug fixes, improvements, new assets, etc.

### Step 4: Make Decision

**Choose RESUME if**:
- User request is empty or explicitly asks to resume/continue
- User request is aligned with the pending tasks in existing workflow
- No contradictions between user request and existing workflow goals

**Choose CREATE_NEW if**:
- User request asks for new features not covered by existing workflow
- User request contradicts the existing workflow's goals
- Existing workflow was for a different purpose (e.g., was testing, now wants new feature)

### Step 5: Write Decision

Create `/work/workflow_action.json` with the following format:

```json
{
  "action": "resume",
  "reason": "User request is empty and existing workflow has pending tasks. The workflow is testing the game implementation and should continue.",
  "workflow_summary": {
    "total_tasks": 6,
    "completed": 4,
    "pending": 2,
    "current_goal": "Testing game implementation"
  }
}
```

Or:

```json
{
  "action": "create_new",
  "reason": "User requested new feature 'add jumping mechanic' which is not covered by existing workflow. Existing workflow was for testing only.",
  "workflow_summary": {
    "total_tasks": 6,
    "completed": 4,
    "pending": 2,
    "current_goal": "Testing game implementation"
  }
}
```

## Decision Logic Examples

### Example 1: Empty User Request

**Workflow**: Testing phase (task 5 of 6 completed)
**User Request**: "" (empty)
**Decision**: `resume`
**Reason**: No new request means user wants to continue existing work

### Example 2: Resume Keywords

**Workflow**: Implementation phase (task 3 of 6 completed)
**User Request**: "continue development" or "resume" or "finish the game"
**Decision**: `resume`
**Reason**: Explicit request to continue

### Example 3: New Feature Request

**Workflow**: Testing phase (all tasks completed, but test failed)
**User Request**: "Add a power-up system"
**Decision**: `create_new`
**Reason**: New feature not covered by existing workflow

### Example 4: Bug Fix on Incomplete Workflow

**Workflow**: Testing phase (task 5 of 6 completed)
**User Request**: "Fix the collision bug"
**Decision**: `resume`
**Reason**: Bug fix is likely covered by the existing fix_bugs task that would be added after test failure

### Example 5: Aligned Request

**Workflow**: Asset creation phase (task 2 of 6 completed, pending: generate_sprites)
**User Request**: "Create the game sprites"
**Decision**: `resume`
**Reason**: Request aligns with pending tasks in workflow

### Example 6: Different Goal

**Workflow**: Building a "Space Shooter" game (task 3 of 6 completed)
**User Request**: "Make a platformer game instead"
**Decision**: `create_new`
**Reason**: Completely different game, need new workflow

## Output Schema

```json
{
  "action": "resume" | "create_new",
  "reason": "Detailed explanation of the decision (1-2 sentences)",
  "workflow_summary": {
    "total_tasks": <number>,
    "completed": <number>,
    "pending": <number>,
    "current_goal": "<brief description of what workflow is trying to achieve>"
  }
}
```

## Important Notes

1. **Always analyze carefully** - Don't just check keywords, understand the context
2. **Read the files** - Don't guess, actually read the workflow and project files
3. **Be conservative** - When in doubt between resume and create_new, prefer resume to avoid wasting completed work
4. **Consider progress** - If workflow is 90% complete, strongly prefer resume unless user explicitly wants something different

## Tools You Have

- `file_exists(path)`: Check if file exists
- `read_file(path)`: Read file contents
- `write_file(path, content)`: Write file (use this for `/work/workflow_action.json`)

## Common Mistakes

❌ Not reading the existing workflow before deciding
❌ Creating new workflow when user just wants to continue
❌ Resuming when user clearly wants something different
❌ Only checking keywords without understanding context
❌ Not providing detailed reason for decision

✅ Read and analyze existing workflow
✅ Read and analyze project state
✅ Understand user request intent
✅ Make informed decision with clear reasoning
✅ Write properly formatted JSON output
