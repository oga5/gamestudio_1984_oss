"""
Image Generator
Generates pixel art images from dot pattern data
"""
import numpy as np
from typing import List, Tuple, Dict


# Character to index mapping for compact pattern format
# Unified color mapping: A-Za-f for indices 0-31 (32 colors total)
#
# Mode 1 (Legacy/Character Mapping): Colors only
#   A-Z = 0-25, a-f = 26-31 (32 colors total)
#   No run-length encoding
#
# Mode 2 (RLE): Numbers as repeat count
#   A-Z = 0-25, a-f = 26-31 (32 colors total)
#   0-9 = repeat count for previous color
#   Example: "A10" = A repeated 10 times

# Unified color mapping (A-Za-f as colors)
CHAR_TO_INDEX_COLORS = {}
for i in range(26):
    CHAR_TO_INDEX_COLORS[chr(ord('A') + i)] = i  # A-Z = 0-25
for i in range(6):
    CHAR_TO_INDEX_COLORS[chr(ord('a') + i)] = 26 + i  # a-f = 26-31

# Legacy mode mapping (same as RLE color mapping, but 0-9 not used as repeat counts)
CHAR_TO_INDEX_LEGACY = CHAR_TO_INDEX_COLORS.copy()

# RLE mode mapping (A-Z, a-f as colors, 0-9 as repeat)
CHAR_TO_INDEX_RLE = CHAR_TO_INDEX_COLORS.copy()

# Backwards compatibility alias
CHAR_TO_INDEX = CHAR_TO_INDEX_LEGACY


class ImageGenerator:
    """Generates pixel art images from dot pattern JSON data"""

    def __init__(self, lenient: bool = True):
        """
        Initialize the image generator
        
        Args:
            lenient: If True, auto-fix pattern length mismatches (pad with 0 or truncate)
        """
        self.width = 0
        self.height = 0
        self.colors = []
        self.pattern = []
        self.lenient = lenient
        self.warnings = []

    def parse_size(self, size_str: str) -> Tuple[int, int]:
        """
        Parse size string like "32x32" into width and height

        Args:
            size_str: Size string in format "WxH"

        Returns:
            Tuple of (width, height)

        Raises:
            ValueError: If size string is invalid
        """
        try:
            parts = size_str.lower().split('x')
            if len(parts) != 2:
                raise ValueError(f"Invalid size format: {size_str}. Expected format: WxH (e.g., 32x32)")

            width = int(parts[0])
            height = int(parts[1])

            if width <= 0 or height <= 0:
                raise ValueError(f"Width and height must be positive: {size_str}")

            return width, height
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid size format: {size_str}. Expected format: WxH (e.g., 32x32)") from e

    def parse_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """
        Parse color string into RGBA tuple

        Args:
            color_str: Color string (e.g., "#FF0000", "#F00", "transparent")

        Returns:
            RGBA tuple (0-255 for each channel)

        Raises:
            ValueError: If color string is invalid
        """
        # Handle transparent color
        if color_str.lower() == "transparent":
            return (0, 0, 0, 0)

        # Remove # if present
        if color_str.startswith('#'):
            color_str = color_str[1:]

        # Handle 3-character hex (#F00 -> #FF0000)
        if len(color_str) == 3:
            color_str = ''.join([c*2 for c in color_str])

        # Parse 6-character hex
        if len(color_str) == 6:
            try:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                return (r, g, b, 255)
            except ValueError as e:
                raise ValueError(f"Invalid hex color: #{color_str}") from e

        raise ValueError(f"Invalid color format: {color_str}. Expected #RGB, #RRGGBB, or 'transparent'")

    def load_pattern(self, pattern_data: Dict) -> None:
        """
        Load pattern data from JSON

        Args:
            pattern_data: Dictionary containing size, colors, and pattern

        Raises:
            ValueError: If pattern data is invalid
        """
        # Parse size
        if 'size' not in pattern_data:
            raise ValueError("Pattern data missing 'size' field")

        self.width, self.height = self.parse_size(pattern_data['size'])

        # Parse colors (32 colors: 0=transparent, 1-31=custom)
        if 'colors' not in pattern_data:
            raise ValueError("Pattern data missing 'colors' field")

        colors_data = pattern_data['colors']
        if not isinstance(colors_data, list):
            raise ValueError("'colors' must be a list")

        if len(colors_data) > 32:
            raise ValueError(f"Too many colors: {len(colors_data)}. Maximum is 32.")

        # Parse each color
        self.colors = []
        for i, color_str in enumerate(colors_data):
            try:
                rgba = self.parse_color(color_str)
                self.colors.append(rgba)
            except ValueError as e:
                raise ValueError(f"Invalid color at index {i}: {e}") from e

        # Ensure we have at least color 0 (transparent)
        if len(self.colors) == 0:
            self.colors.append((0, 0, 0, 0))

        # Parse pattern
        if 'pattern' not in pattern_data:
            raise ValueError("Pattern data missing 'pattern' field")

        raw_pattern = pattern_data['pattern']
        
        # Check for RLE mode flag
        self.rle_mode = pattern_data.get('rle', False)

        # Auto-detect RLE if not specified
        if 'rle' not in pattern_data and isinstance(raw_pattern, str):
            # Heuristic: Check for RLE-specific features
            # 1. Row repetition syntax (*N)
            if '*' in raw_pattern:
                self.rle_mode = True
            # 2. Extended characters (W-Z, a-f) which are not in Legacy (0-9, A-V)
            elif any(c in 'WXYZabcdef' for c in raw_pattern):
                self.rle_mode = True
            # 3. Letter followed by digit (e.g., A10) - likely RLE
            else:
                import re
                if re.search(r'[A-Za-z]\d+', raw_pattern):
                    self.rle_mode = True
        
        # Handle both list format and compact string format
        if isinstance(raw_pattern, str):
            self.pattern = self._parse_string_pattern(raw_pattern)
        elif isinstance(raw_pattern, list):
            self.pattern = raw_pattern
        else:
            raise ValueError("'pattern' must be a list or string")

        # Verify/fix pattern length
        expected_length = self.width * self.height
        actual_length = len(self.pattern)
        
        if actual_length != expected_length:
            if self.lenient:
                if actual_length < expected_length:
                    # Pad with 0 (transparent/first color)
                    padding = expected_length - actual_length
                    self.pattern.extend([0] * padding)
                    self.warnings.append(
                        f"Pattern too short: padded {padding} pixels with color 0 "
                        f"(expected {expected_length}, got {actual_length})"
                    )
                else:
                    # Truncate
                    excess = actual_length - expected_length
                    self.pattern = self.pattern[:expected_length]
                    self.warnings.append(
                        f"Pattern too long: truncated {excess} pixels "
                        f"(expected {expected_length}, got {actual_length})"
                    )
            else:
                raise ValueError(
                    f"Pattern length mismatch: expected {expected_length} "
                    f"({self.width}x{self.height}), got {actual_length}"
                )

        # Verify all color indices are valid (with lenient handling)
        max_color_idx = len(self.colors) - 1
        for i, color_idx in enumerate(self.pattern):
            if not isinstance(color_idx, int):
                raise ValueError(f"Pattern value at index {i} is not an integer: {color_idx}")

            if color_idx < 0 or color_idx > max_color_idx:
                if self.lenient:
                    # Clamp to valid range
                    self.pattern[i] = 0
                    if len(self.warnings) < 10:  # Limit warnings
                        self.warnings.append(
                            f"Color index {color_idx} at pixel {i} out of range, using 0"
                        )
                else:
                    raise ValueError(
                        f"Pattern value at index {i} is out of range: {color_idx}. "
                        f"Valid range: 0-{max_color_idx}"
                    )

    def generate_image(self) -> np.ndarray:
        """
        Generate image array from loaded pattern

        Returns:
            numpy array of shape (height, width, 4) with RGBA values

        Raises:
            RuntimeError: If pattern not loaded
        """
        if not self.pattern or not self.colors:
            raise RuntimeError("Pattern not loaded. Call load_pattern() first.")

        # Create image array
        image = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Fill in pixels
        for i, color_idx in enumerate(self.pattern):
            y = i // self.width
            x = i % self.width
            image[y, x] = self.colors[color_idx]

        return image

    def _parse_string_pattern(self, pattern_str: str) -> List[int]:
        """
        Parse compact string pattern format

        Format: Each character represents a color index
        - 'A'-'Z' = indices 0-25
        - 'a'-'f' = indices 26-31
        - ':' = row delimiter (enables per-row length validation/fixing)
        - Whitespace and newlines are ignored

        Example without row delimiter:
            "AAABBBAABBCCB"

        Example with row delimiter (recommended):
            "AAABBBaa:AAbCCBA:AAaaBBCC:AAbCCBaa"

        When ':' is used, each row is padded/truncated to match width.

        Args:
            pattern_str: Compact pattern string

        Returns:
            List of color indices
        """
        # Check if row delimiter is used OR row repetition is used
        if ':' in pattern_str or '*' in pattern_str:
            return self._parse_string_pattern_with_rows(pattern_str)
        
        # Choose parsing mode
        if self.rle_mode:
            return self._parse_rle_string(pattern_str)
        
        # Legacy format without row delimiter
        result = []
        for char in pattern_str:
            if char in CHAR_TO_INDEX_LEGACY:
                result.append(CHAR_TO_INDEX_LEGACY[char])
            elif char.isspace():
                continue  # Skip whitespace
            else:
                if self.lenient:
                    result.append(0)  # Unknown char -> 0
                    if len(self.warnings) < 10:
                        self.warnings.append(f"Unknown pattern character '{char}', using 0")
                else:
                    raise ValueError(f"Invalid pattern character: '{char}'")
        return result

    def _parse_rle_string(self, pattern_str: str) -> List[int]:
        """
        Parse RLE (Run-Length Encoded) pattern string
        
        Format:
        - A-Z = color indices 0-25
        - a-f = color indices 26-31
        - 0-9 = repeat count for previous color
        
        Example: "A10BC3" = A×10 + B×1 + C×3 = AAAAAAAAAABCCC
        
        Args:
            pattern_str: RLE encoded pattern string
            
        Returns:
            List of color indices
        """
        result = []
        i = 0
        last_color = 0
        
        while i < len(pattern_str):
            char = pattern_str[i]
            
            if char.isspace():
                i += 1
                continue
            
            if char in CHAR_TO_INDEX_RLE:
                # It's a color character
                last_color = CHAR_TO_INDEX_RLE[char]
                
                # Check if followed by a number (repeat count)
                repeat_str = ""
                j = i + 1
                while j < len(pattern_str) and pattern_str[j].isdigit():
                    repeat_str += pattern_str[j]
                    j += 1
                
                if repeat_str:
                    repeat = int(repeat_str)
                    result.extend([last_color] * repeat)
                    i = j
                else:
                    # No repeat count, just one pixel
                    result.append(last_color)
                    i += 1
            elif char.isdigit():
                # Digit without preceding color - treat as repeat of last color
                repeat_str = char
                j = i + 1
                while j < len(pattern_str) and pattern_str[j].isdigit():
                    repeat_str += pattern_str[j]
                    j += 1
                repeat = int(repeat_str)
                result.extend([last_color] * repeat)
                i = j
            else:
                if self.lenient:
                    result.append(0)
                    if len(self.warnings) < 10:
                        self.warnings.append(f"Unknown RLE character '{char}', using color 0")
                    i += 1
                else:
                    raise ValueError(f"Invalid RLE character: '{char}'")
        
        return result

    def _parse_row_pixels(self, row_str: str, row_idx: int) -> List[int]:
        """
        Parse a single row of pixels (supports both legacy and RLE mode)
        
        Args:
            row_str: Row string to parse
            row_idx: Row index for error messages
            
        Returns:
            List of color indices for this row
        """
        if self.rle_mode:
            return self._parse_rle_string(row_str)
        
        # Legacy mode
        row_pixels = []
        for char in row_str:
            if char in CHAR_TO_INDEX_LEGACY:
                row_pixels.append(CHAR_TO_INDEX_LEGACY[char])
            elif char.isspace():
                continue
            else:
                if self.lenient:
                    row_pixels.append(0)
                    if len(self.warnings) < 10:
                        self.warnings.append(
                            f"Unknown character '{char}' in row {row_idx + 1}, using 0"
                        )
                else:
                    raise ValueError(f"Invalid pattern character: '{char}'")
        return row_pixels

    def _parse_string_pattern_with_rows(self, pattern_str: str) -> List[int]:
        """
        Parse compact string pattern with row delimiters ':'
        
        Each row is validated/fixed independently:
        - Too short: padded with 0
        - Too long: truncated
        - Missing rows: filled with 0
        
        Supports both legacy and RLE modes.
        
        Args:
            pattern_str: Pattern string with ':' row delimiters
            
        Returns:
            List of color indices
        """
        result = []
        
        # Split by ':' and filter empty parts
        raw_rows = [r.strip() for r in pattern_str.split(':')]
        raw_rows = [r for r in raw_rows if r]  # Remove empty rows
        
        rows = []
        for r in raw_rows:
            # Handle row repetition *N
            if '*' in r:
                parts = r.split('*')
                if len(parts) == 2 and parts[1].isdigit():
                    base_row = parts[0]
                    count = int(parts[1])
                    rows.extend([base_row] * count)
                else:
                    rows.append(r)
            else:
                rows.append(r)
        
        for row_idx, row_str in enumerate(rows):
            if row_idx >= self.height:
                # Extra rows beyond height
                if self.lenient:
                    if len(self.warnings) < 10:
                        self.warnings.append(
                            f"Extra row {row_idx + 1} ignored (height is {self.height})"
                        )
                    break
                else:
                    raise ValueError(f"Too many rows: got {len(rows)}, expected {self.height}")
            
            # Parse this row (uses appropriate mode)
            row_pixels = self._parse_row_pixels(row_str, row_idx)
            
            # Fix row length
            row_len = len(row_pixels)
            if row_len < self.width:
                # Pad row
                padding = self.width - row_len
                row_pixels.extend([0] * padding)
                if self.lenient and len(self.warnings) < 10:
                    self.warnings.append(
                        f"Row {row_idx + 1}: padded {padding} pixels (got {row_len}, need {self.width})"
                    )
            elif row_len > self.width:
                # Truncate row
                excess = row_len - self.width
                row_pixels = row_pixels[:self.width]
                if self.lenient and len(self.warnings) < 10:
                    self.warnings.append(
                        f"Row {row_idx + 1}: truncated {excess} pixels (got {row_len}, need {self.width})"
                    )
            
            result.extend(row_pixels)
        
        # Handle missing rows
        rows_parsed = min(len(rows), self.height)
        if rows_parsed < self.height:
            missing_rows = self.height - rows_parsed
            missing_pixels = missing_rows * self.width
            result.extend([0] * missing_pixels)
            if self.lenient and len(self.warnings) < 10:
                self.warnings.append(
                    f"Missing {missing_rows} rows: filled with color 0"
                )
        
        return result

    def get_pattern_info(self) -> Dict:
        """
        Get information about the loaded pattern

        Returns:
            Dictionary with pattern information
        """
        return {
            'width': self.width,
            'height': self.height,
            'total_pixels': self.width * self.height,
            'num_colors': len(self.colors),
            'has_transparency': any(c[3] == 0 for c in self.colors),
            'warnings': self.warnings
        }
