#!/usr/bin/env python3
"""
Dotter - Dot Pattern Image Generator CLI
Command-line interface for generating pixel art images from JSON pattern files
"""
import argparse
import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from doteditor import ImageGenerator, PNGWriter


# Module-level logger
_logger = None


def setup_logger(root_dir: str = None) -> logging.Logger:
    """Setup debug logger to project_root/logs/doteditor.log"""
    global _logger
    if _logger is not None:
        return _logger
    
    logger = logging.getLogger('doteditor')
    logger.setLevel(logging.DEBUG)
    
    # Determine log file path
    if root_dir:
        log_dir = Path(root_dir) / 'logs'
    else:
        log_dir = Path.cwd() / 'logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'doteditor.log'
    
    # File handler with detailed format
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    logger.addHandler(file_handler)
    _logger = logger
    return logger


def get_readme_path() -> Path:
    """Get path to README.md relative to this script"""
    return Path(__file__).parent / "README.md"


def show_readme():
    """Display README.md contents"""
    readme_path = get_readme_path()
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print(f"README.md not found at {readme_path}", file=sys.stderr)


def load_json_pattern(filename: str) -> dict:
    """
    Load pattern from JSON file

    Args:
        filename: Path to JSON file

    Returns:
        Pattern dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Pattern file not found: {filename}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_output_filename(input_file: str, output_file: str = None, root_dir: str = None) -> str:
    """
    Generate output filename

    Args:
        input_file: Input JSON filename
        output_file: Optional output filename
        root_dir: Optional root directory to prepend to output path

    Returns:
        Output PNG filename
    """
    if output_file:
        # If root_dir is specified, join it with output_file
        if root_dir:
            return os.path.join(root_dir, output_file)
        # Otherwise use output_file as-is (can be relative or absolute)
        return output_file

    # Generate default filename
    input_path = Path(input_file)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_name = f"{input_path.stem}_{timestamp}.png"

    # Apply root_dir if specified
    if root_dir:
        return os.path.join(root_dir, default_name)
    return default_name


def print_pattern_info(pattern: dict, generator: ImageGenerator):
    """Print pattern information"""
    print("=" * 60)
    print("Dot Pattern Information:")
    print("=" * 60)
    print(f"Size: {pattern.get('size', 'N/A')}")

    colors = pattern.get('colors', [])
    print(f"Colors defined: {len(colors)}")

    # Print color palette
    if colors:
        print("\nColor Palette:")
        for i, color in enumerate(colors[:10]):  # Show first 10 colors
            print(f"  [{i:2d}] {color}")
        if len(colors) > 10:
            print(f"  ... and {len(colors) - 10} more colors")

    info = generator.get_pattern_info()
    print(f"\nTotal pixels: {info['total_pixels']}")
    print(f"Has transparency: {'Yes' if info['has_transparency'] else 'No'}")

    print("=" * 60)


def main():
    """Main CLI function"""
    # Check for --help-full / -H to show README
    if len(sys.argv) > 1 and sys.argv[1] in ('--help-full', '-H'):
        show_readme()
        return 0
    
    parser = argparse.ArgumentParser(
        description='Dotter - Generate PNG images from JSON dot patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate PNG from pattern file
  python dotter.py character.json

  # Specify output filename
  python dotter.py character.json -o sprite.png

  # Scale up the output (2x, 4x, etc.)
  python dotter.py character.json -s 4

  # Show full documentation (README.md)
  python dotter.py -H

Pattern Formats:
  1. Array format:     "pattern": [0,0,1,2,2,...]
  2. String format:    "pattern": "AABCCBAA:ABccccBA:..."  (A-Z, a-f for colors, with row delimiter ':')
  3. RLE format:       "pattern": "A3B2A3:..." with "rle": true (letters=colors, digits=repeat count)

For full documentation, run: python dotter.py -H
        """
    )

    parser.add_argument(
        'input',
        nargs='?',
        help='Input JSON pattern file'
    )
    
    parser.add_argument(
        '-H', '--help-full',
        action='store_true',
        help='Show full documentation (README.md)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output PNG filename (default: auto-generated)'
    )

    parser.add_argument(
        '--root_dir',
        help='Root directory to prepend to output path'
    )

    parser.add_argument(
        '-s', '--scale',
        type=int,
        default=1,
        help='Scale factor for output (default: 1)'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (no info output)'
    )

    parser.add_argument(
        '--info-only',
        action='store_true',
        help='Show pattern info only, do not generate image'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode: fail on pattern length mismatch instead of auto-fixing'
    )

    args = parser.parse_args()
    
    # Handle --help-full after parsing (in case it wasn't first arg)
    if args.help_full:
        show_readme()
        return 0
    
    # Check if input is provided
    if not args.input:
        parser.print_help()
        return 1

    # Setup logger
    logger = setup_logger(args.root_dir)
    logger.info('=' * 60)
    logger.info('DOTEDITOR STARTED')
    logger.info(f'Input: {args.input}')
    logger.info(f'Output: {args.output}')
    logger.info(f'Root dir: {args.root_dir}')
    logger.info(f'Scale: {args.scale}')
    logger.info(f'Quiet: {args.quiet}')
    logger.info(f'Strict: {args.strict}')
    logger.info(f'Command: {" ".join(sys.argv)}')

    try:
        # Load pattern
        if not args.quiet:
            print(f"Loading pattern from: {args.input}")

        pattern = load_json_pattern(args.input)
        logger.debug(f'Pattern loaded: size={pattern.get("size")}, colors={len(pattern.get("colors", []))}')

        # Create generator and load pattern
        generator = ImageGenerator(lenient=not args.strict)
        generator.load_pattern(pattern)

        # Show warnings if any
        if generator.warnings:
            if not args.quiet:
                print("\n⚠ Warnings:")
                for warning in generator.warnings:
                    print(f"  - {warning}")
            for warning in generator.warnings:
                logger.warning(warning)

        # Show pattern info
        if not args.quiet:
            print_pattern_info(pattern, generator)

        # Info only mode
        if args.info_only:
            return 0

        # Generate output filename
        output_file = generate_output_filename(args.input, args.output, args.root_dir)

        if not args.quiet:
            print(f"\nGenerating image...")

        # Generate image
        image_array = generator.generate_image()

        # Write PNG file
        if not args.quiet:
            print(f"Writing PNG file: {output_file}")

        writer = PNGWriter()
        file_info = writer.write_with_info(
            output_file,
            image_array,
            scale=args.scale,
            quiet=args.quiet
        )

        if not args.quiet:
            print(f"\n✓ Successfully generated {output_file}")

        logger.info(f'SUCCESS: Generated {output_file}')
        logger.info(f'  Size: {pattern.get("size")}, Scale: {args.scale}')
        return 0

    except FileNotFoundError as e:
        logger.error(f'FileNotFoundError: {e}')
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except json.JSONDecodeError as e:
        logger.error(f'JSONDecodeError in {args.input}: {e}')
        logger.error(f'  Line {e.lineno}, Column {e.colno}: {e.msg}')
        print(f"Error: Invalid JSON in {args.input}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        logger.error(f'ValueError: {e}')
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except ImportError as e:
        logger.error(f'ImportError: {e}')
        print(f"Error: {e}", file=sys.stderr)
        print("  Please install required packages: pip install Pillow numpy", file=sys.stderr)
        return 1

    except Exception as e:
        import traceback
        logger.error(f'Exception: {e}')
        logger.error(traceback.format_exc())
        print(f"Error: {e}", file=sys.stderr)
        if not args.quiet:
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
