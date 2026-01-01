# Doteditor - Comprehensive Guide

For basic usage, see [README.md](./README.md). This guide covers detailed JSON format, pattern optimization techniques, and practical examples.

---

## JSON Format Details

### Format A: Number Array (Traditional)

Specify color indices as an array. Simple but verbose for large patterns.

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

**Advantages:**
- Simple and easy to understand
- Good for small sprites

**Disadvantages:**
- Large file size
- Hard to read
- Not ideal for LLM generation

---

### Format B: Compact String (Recommended)

Represent color indices as characters. Use `:` to delimit rows.

```json
{
  "size": "8x8",
  "colors": ["transparent", "#FFFF00", "#FFAA00"],
  "pattern": "AAABBBAAA:AABccBAAA:ABcccBcAA:BcccccBc:BcccccBc:ABcccBcAA:AABccBAAA:AAABBBAAA"
}
```

**Features:**
- `A-Z` = indices 0-25
- `a-f` = indices 26-31
- `:` = row delimiter (important!)
- Whitespace is ignored

**Advantages:**
- Compact (small file size)
- Human-readable
- Optimal for LLM generation
- Per-row validation

**Example:**
```json
{
  "size": "4x4",
  "colors": ["transparent", "#FF0000", "#00FF00", "#0000FF"],
  "pattern": "AABB:ABBA:BBAA:BBAA"
}
```

---

### Format C: RLE (Run-Length Encoding)

Compress consecutive identical colors. Enable with `"rle": true`.

```json
{
  "size": "8x8",
  "rle": true,
  "colors": ["transparent", "#FFFF00", "#FFAA00"],
  "pattern": "A3B2A3:A2BC2BA2:ABC4BA:B6C:B6C:ABC4BA:A2BC2BA2:A3B2A3"
}
```

**RLE Notation:**
- `A-Z` = color indices 0-25
- `a-f` = color indices 26-31
- `0-9` = repeat count for preceding color
- `:` = row delimiter

**RLE Expansion Examples:**
| RLE | Expands To | Meaning |
|-----|------------|---------|
| `A3` | `AAA` | Color 0 × 3 |
| `B5C2` | `BBBBBCC` | Color 1 × 5 + Color 2 × 2 |
| `ABC` | `ABC` | Color 0, 1, 2 (one each) |
| `A10B5A10` | `AAAAAAAAAABBBBBBBBBBAAAAAAAAAA` | 10 + 5 + 10 = 25 pixels |

**Advantages:**
- Very compact
- Excellent for repetitive patterns
- Most memory efficient

**Disadvantages:**
- Hard to write manually
- Ineffective for random patterns

**Recommended Use Cases:**
- Gradients (A10B10C10...)
- Background patterns
- Regular textures

---

## Character Mapping (Legacy/Compact Mode)

Color-to-character mapping for Compact String format (non-RLE):

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

---

## RLE Character Mapping

Color-to-character mapping for RLE mode (`"rle": true`):

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

---

## Row Delimiter (`:` Usage)

Using row delimiters enables per-row validation and auto-correction.

### Auto-Fix Features

```json
{
  "size": "8x4",
  "pattern": "AAABBBAAA:AABcCA:ABccccBAAA:BcccccBB"
}
```

| Row | Length | Operation |
|-----|--------|-----------|
| Row 1 | 8 chars | ✓ OK (matches width) |
| Row 2 | 6 chars | **Pad**: `AABccAAA` |
| Row 3 | 10 chars | **Truncate**: `ABccccBcAA` |
| Row 4 | 8 chars | ✓ OK |

**Advantages:**
- Per-row auto-correction
- Easy error identification
- No manual length adjustment needed

---

## Practical Examples

### Example 1: 8×8 Bullet Sprite (RLE)

```json
{
  "size": "8x8",
  "rle": true,
  "colors": ["transparent", "#FFFF00", "#FFAA00"],
  "pattern": "A3B2A3:A2BC2BA2:ABC4BA:B6C:B6C:ABC4BA:A2BC2BA2:A3B2A3"
}
```

**Expansion:**
```
A3B2A3    →  AAABBAA
A2BC2BA2  →  AABCCBAA
ABC4BA    →  ABCCCCBA
B6C       →  BBBBBBBB
B6C       →  BBBBBBBB
ABC4BA    →  ABCCCCBA
A2BC2BA2  →  AABCCBAA
A3B2A3    →  AAABBAA
```

---

### Example 2: 32×32 Player Sprite

```json
{
  "size": "32x32",
  "rle": true,
  "colors": ["transparent", "#00FF00", "#00CC00", "#FFFFFF"],
  "pattern": "A12B4C4D4A8:A11B6C4D4A7:A10B8C4D4A6:A9B10C4D4A5:A8B12C4D4A4:A7B14C4D4A3:A6B16C4D4A2:A5B18C4D4A:A4B20C4D:A3B22C4D:A2B24C4D:AB26C4D:B28C4D:AB26C4D:A2B24C4D:A3B22C4D:A4B20C4D:A5B18C4D4A:A6B16C4D4A2:A7B14C4D4A3:A8B12C4D4A4:A9B10C4D4A5:A10B8C4D4A6:A11B6C4D4A7:A12B4C4D4A8"
}
```

---

### Example 3: 16×16 Character Sprite (Compact String)

```json
{
  "size": "16x16",
  "colors": ["transparent", "#FFFFFF", "#FF6600", "#CC3300", "#000000"],
  "pattern": "AAAABBBBBBAAAAA:AAAABBBBBBBBBAA:AAABBCCCCBBBBAA:AABBCCBCCBCCBBAA:AABBCCBBCCCCBBAA:ABBCCCCCCCCBBAA:BBCCCCCCCCCCBBA:BCCCCCCCCCCCCBB:BCCCCCCCCCCCCBB:ABBCCCCCCCCBBAA:ABBCCCCCCBBBAA:AABBBCCCBBBBAA:AAABBBBBBBBBBAA:AAABBBBBBBBAA:AAAAAAAAAAAAAAA:AAAAAAAAAAAAAAA"
}
```

---

## Common Errors and Solutions

### Error 1: Row Length Mismatch

**❌ WRONG:**
```json
{
  "size": "8x4",
  "pattern": "AAABBBAAA:AABcCA:ABccccBAAA:BcccccBB"
}
// Row 2: 6 chars (need 8)
// Row 3: 10 chars (need 8)
```

**✅ RIGHT:**
```json
{
  "size": "8x4",
  "pattern": "AAABBBAAA:AABccAAA:ABccccBcAA:BcccccBB"
}
```

### Error 2: Insufficient Rows

**❌ WRONG:**
```json
{
  "size": "8x8",
  "pattern": "AAABBBAAA:AABccAAA:ABccccBcAA"
}
// Only 3 rows (need 8)
```

**✅ RIGHT:**
```json
{
  "size": "8x8",
  "pattern": "AAABBBAAA:AABccAAA:ABccccBcAA:BcccccBB:BcccccBB:ABccccBcAA:AABccAAA:AAABBBAAA"
}
```

### Error 3: RLE Without Flag

**❌ WRONG:**
```json
{
  "size": "8x8",
  "pattern": "A3B2A3:A2BC2BA2"
  // Missing "rle": true!
}
```

**✅ RIGHT:**
```json
{
  "size": "8x8",
  "rle": true,
  "colors": ["transparent", "#FF0000", "#00FF00"],
  "pattern": "A3B2A3:A2BC2BA2"
}
```

### Error 4: Color Index Out of Range

**❌ WRONG:**
```json
{
  "size": "4x4",
  "colors": ["transparent", "#FF0000"],  // Only 2 colors
  "pattern": "AABB:ABBA:BBAA:BBAA"  // Using index 1 and 2
}
```

**✅ RIGHT:**
```json
{
  "size": "4x4",
  "colors": ["transparent", "#FF0000", "#00FF00"],  // 3 colors
  "pattern": "AABB:ABBA:BBAA:BBAA"
}
```

### Error 5: Mixed Case (RLE)

**❌ WRONG:**
```json
{
  "size": "8x8",
  "rle": true,
  "pattern": "a5b3:A5B3"  // Inconsistent case
}
```

**✅ RIGHT:**
```json
{
  "size": "8x8",
  "rle": true,
  "pattern": "A5B3:A5B3"  // Consistent (uppercase preferred)
}
```

---

## Pattern Design Tips

### 1. Creating Gradients

```json
{
  "size": "8x8",
  "rle": true,
  "colors": ["transparent", "#FF0000", "#FF6600", "#FFCC00", "#FFFF00"],
  "pattern": "A8:B8:C8:D8:B8:C8:D8:A8"
}
```

### 2. Using Symmetric Patterns

```json
{
  "size": "16x16",
  "rle": true,
  "colors": ["transparent", "#00FF00"],
  "pattern": "A8B8:A7B1B7:A6B2B6:A5B3B5:A4B4B4:A3B5B3:A2B6B2:AB7B:AB7B:A2B6B2:A3B5B3:A4B4B4:A5B3B5:A6B2B6:A7B1B7:A8B8"
}
```

### 3. Building Complex Shapes

Use multiple colors and adjust per row:

```json
{
  "size": "24x24",
  "rle": true,
  "colors": ["transparent", "#00FF00", "#00CC00", "#FFFFFF"],
  "pattern": "A12B4D4A4:A10B4B2D4A4:A8B4B4D4A4:..."
}
```

---

## Lenient Mode (Default)

By default, the tool runs in **lenient mode** with automatic error correction.

### Auto-Fix Example

```json
{
  "size": "8x8",
  "pattern": [0,1,2,3,4,5]  // 64 needed, only 6 provided
}
```

**Warning:**
```
⚠ Pattern too short: padded 58 pixels with color 0
```

**Result:** Image is still generated (missing pixels filled with transparent/color 0)

### Using Strict Mode

To fail on errors instead of auto-fixing:

```bash
python3 dotter.py pattern.json --strict
```

This will **fail with error** if pattern length is insufficient.

---

## Color Details Guide

### RGB Format Specification

- 3-digit: `#RGB` → `#F00` = `#FF0000`
- 6-digit: `#RRGGBB` → `#FF0000`

### 1984 Arcade Palette

```json
{
  "colors": [
    "transparent",      // Index 0
    "#00FF00",         // Player (green)
    "#FF0000",         // Enemy (red)
    "#FFFF00",         // Bullet (yellow)
    "#FF6600",         // Explosion (orange)
    "#FFFFFF",         // Highlight (white)
    "#0000FF"          // Accent (blue)
  ]
}
```

---

## Performance Tips

### 1. File Size Optimization

- **Use RLE:** 30-50% smaller than Compact String
- **Remove unused colors:** Don't define colors you don't use

### 2. Generation Speed

- Small sprites (8×8 - 32×32): Instant
- Large sprites (64×64+): Hundreds of milliseconds

### 3. Memory Usage

- Compact String: ~1KB per 100 pixels
- RLE: ~0.5KB per 100 pixels

---

## Next Steps

- [artist_guide.md](../../system_prompt/tool_guides/artist_guide.md) - Complete workflow
- [README.md](./README.md) - Basic usage
- [doteditor source code](./doteditor/) - Implementation details
