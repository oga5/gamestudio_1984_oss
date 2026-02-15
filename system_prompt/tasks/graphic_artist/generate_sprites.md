# Task: Generate Sprite

Generate a SINGLE image asset (PNG or SVG) based on the specification provided in your task prompt.

## CRITICAL: Single Asset Processing

**You will receive ONE asset specification in your task prompt.** The system handles multiple assets by calling you separately for each one. Your job is to:

1. Generate ONLY the single image specified in your task prompt
2. **SVG FIRST**: If the size is 32x32 or smaller, ALWAYS use `generate_svg()` and save as `.svg`.
3. Do NOT read `/work/image_asset.json` - the specification is already in your prompt
4. Do NOT try to process multiple assets - focus on the ONE you were given
5. Complete your task when that single image is generated and validated

## Input

- **Asset specification**: Provided directly in your task prompt (NOT from a file)
- **Background color check**: Read `/work/design.json` to verify color contrast

## Output

- ONE file in `/public/assets/images/` matching the specification
  - **32x32 or larger**: ALWAYS use `generate_svg()`. Note: This tool renders SVG to PNG for game engine compatibility.
  - **16x16 or smaller**: Use `generate_image()` with pixel patterns.

## CRITICAL: You MUST Use Tools

**IMPORTANT**: This task requires you to call the `generate_image()` or `generate_svg()` tool. You cannot complete this task without executing tools. If you describe what you would do without actually calling the tools, the task will fail.

Before finishing:
- Verify you have called a generation tool at least once
- Verify you have called `validate_asset()` to check the generated file
- If you complete without calling these tools, the task has FAILED

## Workflow

1. Read `/work/design.json` to check backgroundColor for contrast verification
2. Study the asset specification from your task prompt (name, size, description, visual_details)
3. Choose format based on size:
   - **32x32 or larger**: ALWAYS use **SVG** (`generate_svg`) - BEST for complex geometric shapes, neon/vector styles.
   - **16x16 or smaller**: Use **Pixel Pattern** (`generate_image`) - Best for very small pixel art.
4. Visualize the sprite as if designing for a 1984 arcade cabinet
5. Design the graphic with 1984 arcade aesthetic
6. **EXECUTE**: Call `generate_svg(output_path, svg_content)` OR `generate_image(output_path, pattern_json)`
7. **EXECUTE**: Call `validate_asset(output_path)` to confirm validity
8. **DONE** - Task complete when this single image is validated. Do NOT attempt to regenerate.

## SVG Creation Guidelines (Preferred for 32x32 and larger)

- Use simple `<rect>`, `<circle>`, `<polygon>`, or `<path>` elements.
- Use **EXACT** hex colors from `visual_details.colors`.
- Keep the design clean, geometric, and bold.
- **`generate_svg` converts your XML to PNG automatically.**

**Example SVG (32x32 Neon Triangle)**:
```xml
<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <!-- Outer Glow/Stroke -->
  <polygon points="16,2 30,28 2,28" fill="none" stroke="#00FFFF" stroke-width="2" />
  <!-- Core -->
  <polygon points="16,6 26,26 6,26" fill="#FFFFFF" />
</svg>
```

## PNG Creation Guidelines (For 16x16 or smaller)

- Use `generate_image` with RLE pattern.
- Follow 1984 Arcade Aesthetic Philosophy.

### RLE Pattern Reference
- A-Z = color indices 0-25, a-f = indices 26-31
- Numbers = repeat count, : = row, *N = repeat row

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
