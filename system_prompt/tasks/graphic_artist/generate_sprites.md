# Task: Generate Sprite

Generate a SINGLE pixel art image based on the specification provided in your task prompt.

## CRITICAL: Single Asset Processing

**You will receive ONE asset specification in your task prompt.** The system handles multiple assets by calling you separately for each one. Your job is to:

1. Generate ONLY the single image specified in your task prompt
2. Do NOT read `/work/image_asset.json` - the specification is already in your prompt
3. Do NOT try to process multiple assets - focus on the ONE you were given
4. Complete your task when that single image is generated and validated

## Input

- **Asset specification**: Provided directly in your task prompt (NOT from a file)
- **Background color check**: Read `/work/design.json` to verify color contrast

## Output

- ONE PNG file in `/public/assets/images/` matching the specification

## CRITICAL: You MUST Use Tools

**IMPORTANT**: This task requires you to call the `generate_image()` tool. You cannot complete this task without executing tools. If you describe what you would do without actually calling the tools, the task will fail.

Before finishing:
- Verify you have called `generate_image()` at least once
- Verify you have called `validate_asset()` to check the generated file
- If you complete without calling these tools, the task has FAILED

## Workflow

1. Read `/work/design.json` to check backgroundColor for contrast verification
2. Study the asset specification from your task prompt (name, size, description, visual_details)
3. Visualize the sprite as if designing for a 1984 arcade cabinet
4. Design the pixel art pattern with 1984 arcade aesthetic
5. **EXECUTE**: Call `generate_image(output_path, pattern_json)`
6. **EXECUTE**: Call `inspect_image(output_path)` to visually verify
7. **EXECUTE**: Call `validate_asset(output_path)` to confirm validity
8. If invalid (.err file created), regenerate with improvements (max 3 attempts)
9. **DONE** - Task complete when this single image is validated

## Image Creation Process

### Step 1: Check Background Color
```
read_file("/work/design.json")
# Note the backgroundColor field for contrast check
```

### Step 2: Study Asset Specification (from your task prompt)

**The specification includes**:
- **name**: Output filename (e.g., "player.png")
- **size**: Dimensions (e.g., "32x32")
- **description**: Overall concept and context
- **visual_details.shape**: Form and silhouette guidance
- **visual_details.colors**: **EXACT hex colors you MUST use**
- **visual_details.style**: Artistic direction
- **visual_details.key_features**: Important details to include
- **visual_details.inspiration**: Classic arcade game references

### Step 3: Verify Color Contrast

**CRITICAL: Verify colors against backgroundColor**:
- Dark background + bright colors (yellow, cyan, white) = ✅ GOOD
- Light background + dark colors (dark blue, black) = ✅ GOOD
- Similar tones (dark bg + dark sprite) = ❌ PROBLEM → Report conflict

### Step 4: Design Pattern with 1984 Authenticity

**Design Philosophy**:
- Channel the spirit of 1984 arcade masters (Space Invaders, Galaga, Pac-Man)
- Use bold, geometric shapes with high contrast
- 2-4 vibrant colors maximum
- Make silhouette instantly recognizable
- Think: "How would this look on an arcade CRT screen?"

**Technical Approach**:
- colors[0] = "transparent" (background)
- colors[1-4] = exact colors from visual_details.colors
- Simple, geometric shapes over organic curves
- Bold pixel outlines for clarity
- RLE pattern for efficiency

### Step 5: Generate Image
```
generate_image(
  "/public/assets/images/[name from spec]",
  '{
    "size": "[size from spec]",
    "colors": ["transparent", "#color1", "#color2", ...],
    "pattern": "...",
    "rle": true
  }'
)
```

### Step 6: Inspect and Validate
```
inspect_image("/public/assets/images/[name]")
validate_asset("/public/assets/images/[name]")
# Should return: "VALID: /public/assets/images/[name]"
```

## RLE Pattern Reference

- A-Z = color indices 0-25
- a-f = color indices 26-31
- 0-9 = repeat count for previous color
- : = new row
- *N = repeat row N times

**Example (16x16 Space Invaders style enemy)**:
```json
{
  "size": "16x16",
  "colors": ["transparent", "#00FF00", "#008800"],
  "pattern": "A16:A4B8A4:A2B4C4B4A2:AB2C8B2A:BC12B:BC12B:B4C4B4:B2C8B2:A2B8A2:A4C4A4:A16*6",
  "rle": true
}
```

## Validation Checklist

For your single image:
- [ ] Generated in `/public/assets/images/`
- [ ] Validated (returns "VALID")
- [ ] Correct size from spec
- [ ] **Uses EXACT colors from visual_details.colors**
- [ ] Colors clearly visible against backgroundColor
- [ ] High contrast, bold colors
- [ ] Iconic, recognizable silhouette
- [ ] Reflects inspiration from classic arcade games
- [ ] Geometric, simple design (not overly complex)
- [ ] No .err file exists

## Common Issues

❌ **Reading image_asset.json** → Specification is in your task prompt! Don't read files
❌ **Trying to process multiple assets** → You have ONE asset, generate only that
❌ Pattern too complex → Simplify! 1984 style is bold and geometric
❌ Wrong colors → USE EXACT colors from visual_details.colors
❌ Too many colors → Limit to 2-4 colors per sprite
❌ Poor contrast → Verify against backgroundColor from design.json
❌ Invalid file (.err) → Regenerate with fixed pattern (max 3 attempts)

✅ Focus on the SINGLE asset from your task prompt
✅ Bold, iconic 1984 arcade pixel art
✅ Exact colors from specification
✅ Validate before completing
