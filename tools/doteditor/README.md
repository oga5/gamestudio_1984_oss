# Doteditor - Dot Pattern Image Generator

Doteditor is a Python tool that generates pixel art images (PNG format) from dot patterns defined in JSON files. Perfect for creating retro game graphics, pixel art characters, and sprites.

## Overview

This tool allows you to define pixel patterns in a simple JSON format and outputs them as PNG images. You can create precise pixel art by specifying each pixel with a color index.

## Installation

Install required packages:

```bash
pip install Pillow numpy
```

## Directory Structure

```
tools/doteditor/
├── README.md           # This file
├── dotter.py           # CLI tool (main script)
└── doteditor/          # Core module
    ├── __init__.py
    ├── image_generator.py  # Image generation logic
    └── png_writer.py       # PNG output functionality
```

## Usage

### Basic Usage

```bash
python3 tools/doteditor/dotter.py <input.json>
```

### Options

```bash
# Specify output filename
python3 tools/doteditor/dotter.py pattern.json -o output.png

# Specify scale (2x, 4x, etc.)
python3 tools/doteditor/dotter.py pattern.json -s 4

# Quiet mode (no info output)
python3 tools/doteditor/dotter.py pattern.json -q

# Show pattern info only (don't generate image)
python3 tools/doteditor/dotter.py pattern.json --info-only
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `input` | Input JSON pattern file (required) |
| `-o, --output` | Output PNG filename (auto-generated if omitted) |
| `-s, --scale` | Scale multiplier (default: 1) |
| `-q, --quiet` | Quiet mode |
| `--info-only` | Show pattern info only |
| `--strict` | Strict mode: fail on pattern errors instead of auto-fixing |

## JSON Format

### Basic Structure

```json
{
  "size": "WIDTHxHEIGHT",
  "colors": [
    "color0",
    "color1",
    ...
  ],
  "pattern": [pixel data array]
}
```

### Required Fields

#### 1. `size` (string)

Specify image size in `"WIDTHxHEIGHT"` format.

```json
"size": "32x32"
```

#### 2. `colors` (array)

Color palette (max 32 colors, indices 0-31).

- Index 0: Usually `"transparent"` (transparent)
- Indices 1-31: RGB colors in `"#RGB"` or `"#RRGGBB"` format

```json
"colors": [
  "transparent",
  "#FF0000",
  "#00FF00",
  "#0000FF"
]
```

#### 3. `pattern` (array or string)

Pixel data can be specified in two formats:

**Format A: Number Array (Traditional)**
- Array length should equal `width × height`
- Each element is a color index (0-31)
- Arranged left-to-right, top-to-bottom

```json
"pattern": [
  0,0,1,0,
  0,1,2,1,
  1,2,2,2,
  0,1,2,1
]
```

**Format B: Compact String (New! Recommended for LLM)**
- Each character represents a color index
- `A-Z` = indices 0-25
- `a-f` = indices 26-31
- `:` = row delimiter (recommended!)
- Whitespace is ignored
- Much shorter than array format!
- **NOTE: Digits 0-9 are NOT used for colors** (only in RLE mode as repeat counts)

```json
"pattern": "AAbA:AbBA:BcBB:AbBA"
```

**Row Delimiter `:` (Highly Recommended)**

Using `:` enables per-row validation and auto-fixing:
- Each row is independently padded/truncated to match width
- Missing rows are filled with color 0
- Extra rows are ignored
- Errors are localized to specific rows

```json
{
  "size": "8x4",
  "pattern": "AAABBBAAA:AABcCA:ABccccBAAA:BcccccBB"
}
// Row 1: OK (8 chars)
// Row 2: padded 2 pixels (6 → 8)
// Row 3: truncated 2 pixels (10 → 8)
// Row 4: OK (8 chars)
```

**Character Mapping (Legacy Mode - default):**
| Char | Index | Char | Index | Char | Index | Char | Index |
|------|-------|------|-------|------|-------|------|-------|
| A | 0 | J | 9 | S | 18 | a | 26 |
| B | 1 | K | 10 | T | 19 | b | 27 |
| C | 2 | L | 11 | U | 20 | c | 28 |
| D | 3 | M | 12 | V | 21 | d | 29 |
| E | 4 | N | 13 | W | 22 | e | 30 |
| F | 5 | O | 14 | X | 23 | f | 31 |
| G | 6 | P | 15 | Y | 24 | | |
| H | 7 | Q | 16 | Z | 25 | | |
| I | 8 | R | 17 | | | | |

**Format C: RLE (Run-Length Encoding) Mode**

Enable with `"rle": true` in JSON. Numbers become repeat counts instead of colors:

- `A-Z` = color indices 0-25
- `a-f` = color indices 26-31  
- `0-9` = repeat count for preceding color

```json
{
  "size": "8x8",
  "rle": true,
  "colors": ["transparent", "#FFFF00", "#FFAA00"],
  "pattern": "A3B2A3:A2BC2BA2:AB6A:B8:B8:AB6A:A2BC2BA2:A3B2A3"
}
```

**RLE Examples:**
| RLE | Expands to | Meaning |
|-----|------------|---------|
| `A10` | `AAAAAAAAAA` | Color 0 × 10 |
| `B5C3` | `BBBBBCCC` | Color 1 × 5, Color 2 × 3 |
| `ABC` | `ABC` | Color 0, 1, 2 (one each) |
| `A3BC2A3` | `AAABCCAAA` | 3+1+2+3 = 9 pixels |

**RLE Character Mapping:**
| Char | Index | Char | Index | Char | Index |
|------|-------|------|-------|------|-------|
| A | 0 | J | 9 | S | 18 | a | 26 |
| B | 1 | K | 10 | T | 19 | b | 27 |
| C | 2 | L | 11 | U | 20 | c | 28 |
| D | 3 | M | 12 | V | 21 | d | 29 |
| E | 4 | N | 13 | W | 22 | e | 30 |
| F | 5 | O | 14 | X | 23 | f | 31 |
| G | 6 | P | 15 | Y | 24 | | |
| H | 7 | Q | 16 | Z | 25 | | |
| I | 8 | R | 17 | | | | |

## Examples

### Example 1: Simple 8x8 Bullet Sprite (Array Format)

```json
{
  "size": "8x8",
  "colors": [
    "transparent",
    "#FFFF00",
    "#FFAA00"
  ],
  "pattern": [
    0,0,0,1,1,0,0,0,
    0,0,1,2,2,1,0,0,
    0,1,2,2,2,2,1,0,
    1,2,2,2,2,2,2,1,
    1,2,2,2,2,2,2,1,
    0,1,2,2,2,2,1,0,
    0,0,1,2,2,1,0,0,
    0,0,0,1,1,0,0,0
  ]
}
```

### Example 1b: Same Sprite (Compact String with Row Delimiter)

```json
{
  "size": "8x8",
  "colors": ["transparent", "#FFFF00", "#FFAA00"],
  "pattern": "AAABBAAA:AABccBAAA:ABcccBcAA:BcccccBc:BcccccBc:ABcccBcAA:AABccBAAA:AAABBAAA"
}
```

### Example 2: 16x16 Character Sprite

```json
{
  "size": "16x16",
  "colors": [
    "transparent",
    "#FFFFFF",
    "#FF6600",
    "#CC3300",
    "#000000"
  ],
  "pattern": [
    0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,
    0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
    0,0,0,1,1,2,2,2,2,2,2,1,1,0,0,0,
    0,0,1,1,2,2,3,2,2,3,2,2,1,1,0,0,
    0,0,1,2,2,3,3,2,2,3,3,2,2,1,0,0,
    0,1,1,2,2,2,2,4,4,2,2,2,2,1,1,0,
    0,1,2,2,2,2,4,4,4,4,2,2,2,2,1,0,
    1,1,2,2,2,2,2,4,4,2,2,2,2,2,1,1,
    1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,
    1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,
    0,1,2,2,2,1,1,1,1,1,1,2,2,2,1,0,
    0,1,1,2,2,1,1,1,1,1,1,2,2,1,1,0,
    0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,
    0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
  ]
}
```

### Execution Examples

```bash
# Generate example 1 at 4x scale
python3 tools/doteditor/dotter.py bullet.json -o bullet_sprite.png -s 4

# Generate example 2 at 2x scale
python3 tools/doteditor/dotter.py character.json -o character_sprite.png -s 2
```

## Sprite Size Guidelines

| Sprite Type | Recommended Size | Recommended Colors |
|-------------|-----------------|-------------------|
| Small Character | 16x16 | 4-8 colors |
| Medium Character | 32x32 | 8-16 colors |
| Large Character | 48x48, 64x64 | 12-20 colors |
| Small Icon/Bullet | 8x8 | 2-4 colors |
| UI Element | 16x16～32x32 | 4-8 colors |

## Scale Setting Tips

- 8x8 or 16x16 sprites: `scale=4` or `scale=8` recommended
- 32x32 sprites: `scale=2` or `scale=4` recommended
- 64x64 sprites: `scale=1` or `scale=2` recommended

## Lenient Mode (Default)

By default, the tool runs in **lenient mode** which auto-fixes common errors:

### Pattern Too Short → Padded with 0
```json
{
  "size": "8x8",
  "pattern": [0,1,2,3,4,5,6,7,8,9]  // Only 10 elements, 64 required
}
// ⚠ Warning: Pattern too short: padded 54 pixels with color 0
// Image is still generated!
```

### Pattern Too Long → Truncated
```json
{
  "size": "4x4",
  "pattern": "AAAABBBBCCCCDDDDEEEE"  // 20 chars, only 16 needed
}
// ⚠ Warning: Pattern too long: truncated 4 pixels
// Image is still generated!
```

### Invalid Color Index → Replaced with 0
```json
{
  "size": "4x4",
  "colors": ["transparent", "#FF0000"],
  "pattern": [0,0,1,1, 0,1,9,1, ...]  // Color index 9 is undefined
}
// ⚠ Warning: Color index 9 at pixel 6 out of range, using 0
// Image is still generated!
```

### Strict Mode

Use `--strict` to fail on any error instead of auto-fixing:
```bash
python3 dotter.py pattern.json --strict
```

## Common Mistakes (Strict Mode)

### ❌ Invalid Size Format

```json
{
  "size": "32"  // Missing height! Should be "32x32"
}
```

### ✅ Correct Example

```json
{
  "size": "4x4",
  "colors": [
    "transparent",
    "#FF0000",
    "#00FF00"
  ],
  "pattern": [
    0,0,1,0,
    0,1,2,1,
    1,2,2,2,
    0,1,2,1
  ]
}
```

## Using as a Module

You can also use it as a module within Python code:

```python
from doteditor import ImageGenerator, PNGWriter
import json

# Load JSON pattern
with open('pattern.json', 'r') as f:
    pattern = json.load(f)

# Generate image
generator = ImageGenerator()
generator.load_pattern(pattern)
image_array = generator.generate_image()

# Write PNG
writer = PNGWriter()
writer.write_with_info('output.png', image_array, scale=4)
```

## Troubleshooting

### Error: "Pattern file not found"

- Check that the file path is correct
- Verify your current directory

### Error: "Invalid JSON"

- Verify JSON syntax is correct
- Check for missing/extra commas and brackets

### Error: "Pattern length mismatch"

- Ensure the `pattern` array length matches `width × height`

### Error: "Invalid color index"

- Verify all `pattern` values are within the `colors` array index range (0 to colors.length-1)

## License

This tool is part of the DeepAgents project.

## Related Files

- `prompt/dotter.md` - Prompt configuration for Dotter agent
- `chat_app.py` - Integration within DeepAgents chat application
