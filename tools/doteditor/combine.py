#!/usr/bin/env python3
"""
Combine multiple PNG images into a single image.

Usage:
    python combine.py -o output.png input1.png input2.png input3.png input4.png --layout 2x2
    python combine.py -o output.png input1.png input2.png --layout 2x1
    python combine.py -o output.png input1.png input2.png input3.png input4.png --layout 1x4
"""

import argparse
import sys
import os

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow library is required. Install with: pip install Pillow")
    sys.exit(1)


def combine_images(input_files: list, output_file: str, layout: str, root_dir: str = None) -> str:
    """
    Combine multiple images into a single image.
    
    Args:
        input_files: List of input PNG file paths
        output_file: Output PNG file path
        layout: Layout format like "2x2", "1x4", "4x1"
        root_dir: Optional root directory for relative paths
    
    Returns:
        Success message or error string
    """
    # Parse layout
    try:
        cols, rows = map(int, layout.lower().split('x'))
    except ValueError:
        return f"Error: Invalid layout format '{layout}'. Use format like '2x2', '1x4', etc."
    
    expected_count = cols * rows
    if len(input_files) != expected_count:
        return f"Error: Layout {layout} requires {expected_count} images, but got {len(input_files)}"
    
    # Resolve paths
    if root_dir:
        input_files = [
            os.path.join(root_dir, f.lstrip('/')) if not os.path.isabs(f) or f.startswith('/')
            else f for f in input_files
        ]
        if output_file.startswith('/'):
            output_file = os.path.join(root_dir, output_file.lstrip('/'))
    
    # Load all images
    images = []
    for f in input_files:
        if not os.path.exists(f):
            return f"Error: File not found: {f}"
        try:
            img = Image.open(f)
            images.append(img)
        except Exception as e:
            return f"Error loading {f}: {e}"
    
    # Check all images have the same size
    first_size = images[0].size
    for i, img in enumerate(images):
        if img.size != first_size:
            return f"Error: Image size mismatch. {input_files[0]} is {first_size}, but {input_files[i]} is {img.size}"
    
    tile_width, tile_height = first_size
    
    # Create output image
    output_width = tile_width * cols
    output_height = tile_height * rows
    
    # Use RGBA mode to preserve transparency
    result = Image.new('RGBA', (output_width, output_height), (0, 0, 0, 0))
    
    # Paste images in grid
    for idx, img in enumerate(images):
        col = idx % cols
        row = idx // cols
        x = col * tile_width
        y = row * tile_height
        
        # Convert to RGBA if necessary
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        result.paste(img, (x, y))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    # Save result
    try:
        result.save(output_file, 'PNG')
    except Exception as e:
        return f"Error saving {output_file}: {e}"
    
    return f"Combined {len(images)} images into {output_file} ({output_width}x{output_height})"


def main():
    parser = argparse.ArgumentParser(
        description='Combine multiple PNG images into a single image',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combine 4 images into 2x2 grid (for 64x64 boss from 4x 32x32 tiles)
  python combine.py -o boss.png topleft.png topright.png bottomleft.png bottomright.png --layout 2x2
  
  # Combine 4 images into horizontal strip (sprite sheet)
  python combine.py -o spritesheet.png frame1.png frame2.png frame3.png frame4.png --layout 4x1
  
  # Combine 2 images vertically
  python combine.py -o combined.png top.png bottom.png --layout 1x2

Layout format:
  COLSxROWS - e.g., "2x2" means 2 columns, 2 rows
  Images are placed left-to-right, top-to-bottom
"""
    )
    
    parser.add_argument('input_files', nargs='+', help='Input PNG files')
    parser.add_argument('-o', '--output', required=True, help='Output PNG file')
    parser.add_argument('--layout', required=True, help='Layout format (e.g., 2x2, 4x1, 1x4)')
    parser.add_argument('--root_dir', help='Root directory for relative paths')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress output')
    
    args = parser.parse_args()
    
    result = combine_images(
        input_files=args.input_files,
        output_file=args.output,
        layout=args.layout,
        root_dir=args.root_dir
    )
    
    if not args.quiet:
        print(result)
    
    if result.startswith("Error"):
        sys.exit(1)


if __name__ == '__main__':
    main()
