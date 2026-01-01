#!/usr/bin/env python3
"""
Python Synthesizer CLI
Command-line interface for generating audio from JSON pattern files
"""
import argparse
import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from synthesizer import Sequencer, WavWriter


# Module-level logger
_logger = None


def setup_logger(root_dir: str = None) -> logging.Logger:
    """Setup debug logger to project_root/logs/synthesizer.log"""
    global _logger
    if _logger is not None:
        return _logger
    
    logger = logging.getLogger('synthesizer')
    logger.setLevel(logging.DEBUG)
    
    # Determine log file path
    if root_dir:
        log_dir = Path(root_dir) / 'logs'
    else:
        log_dir = Path.cwd() / 'logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'synthesizer.log'
    
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
        Output WAV filename
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
    default_name = f"{input_path.stem}_{timestamp}.wav"

    # Apply root_dir if specified
    if root_dir:
        return os.path.join(root_dir, default_name)
    return default_name


def print_pattern_info(pattern: dict):
    """Print pattern information"""
    print("=" * 60)
    print("Pattern Information:")
    print("=" * 60)
    print(f"BPM: {pattern.get('bpm', 120)}")
    print(f"Pattern Length: {pattern.get('patternLength', 16)} steps")
    print(f"Master Volume: {pattern.get('masterVolume', 0.7):.2f}")

    tracks = pattern.get('tracks', {})
    print(f"\nActive Tracks: {len([t for t in tracks.values() if not t.get('muted', False)])}")

    for track_name, track_data in tracks.items():
        if track_data.get('muted', False):
            continue

        data = track_data.get('data', {})
        active_notes = sum(
            sum(1 for v in pattern if v)
            for pattern in data.values()
        )

        print(f"  - {track_name.upper()}: {active_notes} active notes")
        if 'waveform' in track_data:
            print(f"    Waveform: {track_data['waveform']}")
        if 'sound' in track_data:
            print(f"    Sound: {track_data['sound']}")
        if 'ratio' in track_data:
            print(f"    FM Ratio: {track_data['ratio']}, Depth: {track_data['depth']}")

    print("=" * 60)


def main():
    """Main CLI function"""
    # Check for --help-full / -H to show README
    if len(sys.argv) > 1 and sys.argv[1] in ('--help-full', '-H'):
        show_readme()
        return 0
    
    parser = argparse.ArgumentParser(
        description='Python Synthesizer - Generate WAV files from JSON patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate WAV from pattern file
  python synth.py pattern.json

  # Specify output filename
  python synth.py pattern.json -o output.wav

  # Quiet mode (no info output)
  python synth.py pattern.json -q

  # Show full documentation (README.md)
  python synth.py -H

For full documentation, run: python synth.py -H
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
        help='Output WAV filename (default: auto-generated)'
    )

    parser.add_argument(
        '--root_dir',
        help='Root directory to prepend to output path'
    )

    parser.add_argument(
        '-r', '--sample-rate',
        type=int,
        default=44100,
        help='Sample rate in Hz (default: 44100)'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (no info output)'
    )

    parser.add_argument(
        '--info-only',
        action='store_true',
        help='Show pattern info only, do not generate audio'
    )

    parser.add_argument(
        '--no-normalize',
        action='store_true',
        help='Do not normalize output audio'
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
    logger.info('SYNTHESIZER STARTED')
    logger.info(f'Input: {args.input}')
    logger.info(f'Output: {args.output}')
    logger.info(f'Root dir: {args.root_dir}')
    logger.info(f'Sample rate: {args.sample_rate}')
    logger.info(f'Quiet: {args.quiet}')
    logger.info(f'Command: {" ".join(sys.argv)}')

    try:
        # Load pattern
        if not args.quiet:
            print(f"Loading pattern from: {args.input}")

        pattern = load_json_pattern(args.input)
        logger.debug(f'Pattern loaded successfully: bpm={pattern.get("bpm")}, tracks={list(pattern.get("tracks", {}).keys())}')

        # Show pattern info
        if not args.quiet:
            print_pattern_info(pattern)

        # Info only mode
        if args.info_only:
            return 0

        # Generate output filename
        output_file = generate_output_filename(args.input, args.output, args.root_dir)

        if not args.quiet:
            print(f"\nGenerating audio...")

        # Create sequencer and render
        sequencer = Sequencer(sample_rate=args.sample_rate, quiet=args.quiet)
        audio_data = sequencer.render_pattern(pattern)
        
        # Show warnings summary if any
        if sequencer.warnings:
            if not args.quiet:
                print(f"\n⚠ {len(sequencer.warnings)} warning(s) during generation (incomplete data was skipped)")
            for warning in sequencer.warnings:
                logger.warning(warning)

        # Write WAV file
        if not args.quiet:
            print(f"Writing WAV file: {output_file}")

        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(output_file, audio_data, normalize=not args.no_normalize)

        duration = len(audio_data) / args.sample_rate
        if not args.quiet:
            print(f"\n✓ Successfully generated {output_file}")
            print(f"  Duration: {duration:.2f} seconds")
            print(f"  Sample Rate: {args.sample_rate} Hz")
            print(f"  Samples: {len(audio_data)}")

        logger.info(f'SUCCESS: Generated {output_file}')
        logger.info(f'  Duration: {duration:.2f}s, Samples: {len(audio_data)}')
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
