#!/usr/bin/env python3
"""
SFX Generator - Preset-based sound effect generator for 1984-era arcade games
Simple API for generating common game sound effects without complex JSON configuration.
"""
import numpy as np
import os
import struct
import wave
from typing import Optional, Dict, Any


class SFXGenerator:
    """
    Preset-based sound effect generator.

    Designed for 1984-era arcade game sounds with simple parameter control.
    """

    VALID_TYPES = [
        'explosion', 'laser', 'hit', 'powerup', 'coin', 'jump',
        'gameover', 'victory', 'damage', 'select', 'blip'
    ]

    VALID_INTENSITIES = ['low', 'medium', 'high']
    VALID_PITCHES = ['low', 'mid', 'high']

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize SFX generator.

        Args:
            sample_rate: Audio sample rate (default: 44100 Hz)
        """
        self.sample_rate = sample_rate

    def generate(self, sfx_type: str, intensity: str = 'medium',
                 pitch: str = 'mid', duration: Optional[float] = None) -> np.ndarray:
        """
        Generate a sound effect.

        Args:
            sfx_type: Type of sound effect (explosion, laser, hit, etc.)
            intensity: Intensity level (low, medium, high)
            pitch: Pitch level (low, mid, high)
            duration: Optional duration override in seconds

        Returns:
            Audio samples as numpy array
        """
        sfx_type = sfx_type.lower()
        intensity = intensity.lower()
        pitch = pitch.lower()

        if sfx_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid sfx_type: {sfx_type}. Valid types: {self.VALID_TYPES}")
        if intensity not in self.VALID_INTENSITIES:
            raise ValueError(f"Invalid intensity: {intensity}. Valid: {self.VALID_INTENSITIES}")
        if pitch not in self.VALID_PITCHES:
            raise ValueError(f"Invalid pitch: {pitch}. Valid: {self.VALID_PITCHES}")

        # Dispatch to specific generator
        generator_map = {
            'explosion': self._explosion,
            'laser': self._laser,
            'hit': self._hit,
            'powerup': self._powerup,
            'coin': self._coin,
            'jump': self._jump,
            'gameover': self._gameover,
            'victory': self._victory,
            'damage': self._damage,
            'select': self._select,
            'blip': self._blip,
        }

        return generator_map[sfx_type](intensity, pitch, duration)

    def _get_pitch_multiplier(self, pitch: str) -> float:
        """Get frequency multiplier based on pitch setting."""
        return {'low': 0.7, 'mid': 1.0, 'high': 1.4}[pitch]

    def _get_intensity_multiplier(self, intensity: str) -> float:
        """Get volume/duration multiplier based on intensity setting."""
        return {'low': 0.6, 'medium': 1.0, 'high': 1.4}[intensity]

    def _make_envelope(self, length: int, attack: float = 0.01,
                       decay: float = 0.1, sustain: float = 0.5,
                       release: float = 0.3) -> np.ndarray:
        """Create ADSR envelope."""
        total = attack + decay + release
        t = np.linspace(0, 1, length)

        envelope = np.zeros(length)
        attack_end = int(attack / total * length)
        decay_end = int((attack + decay) / total * length)

        # Attack
        if attack_end > 0:
            envelope[:attack_end] = np.linspace(0, 1, attack_end)
        # Decay
        if decay_end > attack_end:
            envelope[attack_end:decay_end] = np.linspace(1, sustain, decay_end - attack_end)
        # Release
        envelope[decay_end:] = np.linspace(sustain, 0, length - decay_end)

        return envelope

    def _noise(self, length: int, color: str = 'white') -> np.ndarray:
        """Generate noise."""
        white = np.random.uniform(-1, 1, length)

        if color == 'white':
            return white
        elif color == 'pink':
            # Simple pink noise approximation
            b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
            a = [1, -2.494956002, 2.017265875, -0.522189400]
            from scipy.signal import lfilter
            return lfilter(b, a, white)
        elif color == 'brown':
            # Brown noise (integrated white noise)
            brown = np.cumsum(white)
            return brown / np.max(np.abs(brown))
        return white

    def _explosion(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate explosion sound.

        Combines:
        - Low frequency rumble (pitch-swept sine)
        - Noise burst (filtered white/brown noise)
        - Sub-bass impact
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.3 + 0.4 * int_mult)
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        # Sub-bass impact (pitch sweep down)
        base_freq = 80 * pitch_mult
        freq_sweep = base_freq * np.exp(-t * 8)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate
        sub_bass = np.sin(phase) * np.exp(-t * 6)

        # Noise burst
        noise = np.random.uniform(-1, 1, samples)
        noise_env = np.exp(-t * (8 / int_mult))
        noise_component = noise * noise_env * 0.6

        # Mid rumble
        rumble_freq = 40 * pitch_mult
        rumble = np.sin(2 * np.pi * rumble_freq * t) * np.exp(-t * 4)

        # Combine
        sound = sub_bass * 0.5 + noise_component * 0.4 + rumble * 0.3
        sound = sound * int_mult * 0.7

        return np.clip(sound, -1, 1)

    def _laser(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate laser/shoot sound.

        Classic arcade laser: high-to-low pitch sweep with sine or square wave.
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.1 + 0.1 * int_mult)
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        # Pitch sweep from high to low
        start_freq = 1200 * pitch_mult
        end_freq = 200 * pitch_mult
        freq_sweep = start_freq * np.exp(-t * np.log(start_freq / end_freq) / dur)

        # Generate waveform
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate

        if intensity == 'high':
            # Square wave for aggressive laser
            sound = np.sign(np.sin(phase))
        else:
            # Sine wave for cleaner laser
            sound = np.sin(phase)

        # Envelope
        envelope = np.exp(-t * (10 / int_mult))
        sound = sound * envelope * 0.6 * int_mult

        return np.clip(sound, -1, 1)

    def _hit(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate hit/impact sound.

        Short, punchy sound with noise and tone.
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.08 + 0.07 * int_mult)
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        # Tone component
        freq = 300 * pitch_mult
        tone = np.sin(2 * np.pi * freq * t) * np.exp(-t * 30)

        # Noise component
        noise = np.random.uniform(-1, 1, samples) * np.exp(-t * 40)

        # Combine
        sound = tone * 0.6 + noise * 0.4
        sound = sound * int_mult * 0.7

        return np.clip(sound, -1, 1)

    def _powerup(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate power-up sound.

        Ascending arpeggio with bright waveform.
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.4 + 0.2 * int_mult)
        samples = int(self.sample_rate * dur)

        # Ascending notes (C-E-G-C arpeggio)
        base_freq = 262 * pitch_mult  # C4
        ratios = [1, 1.26, 1.5, 2]  # Major arpeggio

        note_samples = samples // len(ratios)
        sound = np.zeros(samples)

        for i, ratio in enumerate(ratios):
            start = i * note_samples
            end = start + note_samples
            t = np.linspace(0, dur / len(ratios), note_samples)

            freq = base_freq * ratio
            # Square wave for 8-bit feel
            note = np.sign(np.sin(2 * np.pi * freq * t))
            envelope = np.exp(-t * 8)

            sound[start:end] = note * envelope

        sound = sound * 0.5 * int_mult
        return np.clip(sound, -1, 1)

    def _coin(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate coin/collect sound.

        Two-note chime (classic coin sound).
        """
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or 0.15
        samples = int(self.sample_rate * dur)
        half = samples // 2

        sound = np.zeros(samples)
        t1 = np.linspace(0, dur / 2, half)
        t2 = np.linspace(0, dur / 2, samples - half)

        # First note (lower)
        freq1 = 988 * pitch_mult  # B5
        note1 = np.sin(2 * np.pi * freq1 * t1) * np.exp(-t1 * 15)

        # Second note (higher)
        freq2 = 1319 * pitch_mult  # E6
        note2 = np.sin(2 * np.pi * freq2 * t2) * np.exp(-t2 * 15)

        sound[:half] = note1
        sound[half:] = note2

        return sound * 0.6

    def _jump(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate jump sound.

        Quick ascending pitch sweep.
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.1 + 0.05 * int_mult)
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        # Ascending pitch sweep
        start_freq = 150 * pitch_mult
        end_freq = 400 * pitch_mult

        freq_sweep = start_freq + (end_freq - start_freq) * (t / dur)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate

        # Square wave
        sound = np.sign(np.sin(phase))
        envelope = np.exp(-t * 15)

        return sound * envelope * 0.5

    def _gameover(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate game over sound.

        Descending sad melody.
        """
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or 1.5
        samples = int(self.sample_rate * dur)

        # Descending notes (minor feel)
        base_freq = 330 * pitch_mult  # E4
        ratios = [1, 0.89, 0.75, 0.67]  # Descending pattern

        note_samples = samples // len(ratios)
        sound = np.zeros(samples)

        for i, ratio in enumerate(ratios):
            start = i * note_samples
            end = start + note_samples
            t = np.linspace(0, dur / len(ratios), note_samples)

            freq = base_freq * ratio
            # Triangle wave for sad tone
            note = 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
            envelope = np.exp(-t * 3)

            sound[start:end] = note * envelope

        return sound * 0.5

    def _victory(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate victory fanfare.

        Triumphant ascending melody.
        """
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or 1.2
        samples = int(self.sample_rate * dur)

        # Victory arpeggio (C major)
        base_freq = 262 * pitch_mult
        ratios = [1, 1.26, 1.5, 2, 2.52]  # C-E-G-C-E

        note_samples = samples // len(ratios)
        sound = np.zeros(samples)

        for i, ratio in enumerate(ratios):
            start = i * note_samples
            end = min(start + note_samples, samples)
            length = end - start
            t = np.linspace(0, dur / len(ratios), length)

            freq = base_freq * ratio
            # Square wave for classic feel
            note = np.sign(np.sin(2 * np.pi * freq * t))
            envelope = np.exp(-t * 4)

            sound[start:end] = note * envelope

        return sound * 0.5

    def _damage(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate damage/hurt sound.

        Quick descending buzz.
        """
        int_mult = self._get_intensity_multiplier(intensity)
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or (0.15 + 0.1 * int_mult)
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        # Descending pitch
        start_freq = 400 * pitch_mult
        end_freq = 100 * pitch_mult
        freq_sweep = start_freq * np.exp(-t * np.log(start_freq / end_freq) / dur)

        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate
        # Sawtooth for harsh sound
        sound = 2 * (phase / (2 * np.pi) - np.floor(0.5 + phase / (2 * np.pi)))

        envelope = np.exp(-t * 10)
        return sound * envelope * 0.6 * int_mult

    def _select(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate menu select sound.

        Quick pleasant blip.
        """
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or 0.08
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        freq = 800 * pitch_mult
        sound = np.sin(2 * np.pi * freq * t)
        envelope = np.exp(-t * 30)

        return sound * envelope * 0.5

    def _blip(self, intensity: str, pitch: str, duration: Optional[float]) -> np.ndarray:
        """
        Generate simple blip sound.

        Very short, simple tone.
        """
        pitch_mult = self._get_pitch_multiplier(pitch)

        dur = duration or 0.05
        samples = int(self.sample_rate * dur)
        t = np.linspace(0, dur, samples)

        freq = 1000 * pitch_mult
        sound = np.sin(2 * np.pi * freq * t)
        envelope = np.exp(-t * 50)

        return sound * envelope * 0.4


class SFXWriter:
    """Write audio data to WAV files."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def write(self, filename: str, audio_data: np.ndarray, normalize: bool = True) -> None:
        """
        Write audio data to WAV file.

        Args:
            filename: Output filename
            audio_data: Audio samples as numpy array
            normalize: Whether to normalize audio (default: True)
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)

        # Normalize if requested
        if normalize and len(audio_data) > 0:
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val * 0.9

        # Convert to 16-bit PCM
        audio_int = (audio_data * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int.tobytes())


def generate_sfx(output_path: str, sfx_type: str, intensity: str = 'medium',
                 pitch: str = 'mid', duration: float = None,
                 root_dir: str = None) -> dict:
    """
    Generate a sound effect and save to WAV file.

    Args:
        output_path: Output file path (relative or absolute)
        sfx_type: Type of sound effect:
            - explosion: Explosion/boom sound
            - laser: Laser/shoot sound
            - hit: Impact/hit sound
            - powerup: Power-up collection sound
            - coin: Coin/item collection sound
            - jump: Jump sound
            - gameover: Game over jingle
            - victory: Victory fanfare
            - damage: Damage/hurt sound
            - select: Menu select sound
            - blip: Simple blip sound
        intensity: Intensity level (low, medium, high)
        pitch: Pitch level (low, mid, high)
        duration: Optional duration override in seconds
        root_dir: Optional root directory to prepend to output path

    Returns:
        dict with status, path, and duration
    """
    try:
        # Build full path
        if root_dir:
            full_path = os.path.join(root_dir, output_path)
        else:
            full_path = output_path

        # Generate sound
        generator = SFXGenerator()
        audio_data = generator.generate(sfx_type, intensity, pitch, duration)

        # Write to file
        writer = SFXWriter()
        writer.write(full_path, audio_data)

        # Calculate duration
        actual_duration = len(audio_data) / generator.sample_rate

        return {
            'status': 'success',
            'path': full_path,
            'duration': actual_duration,
            'type': sfx_type,
            'intensity': intensity,
            'pitch': pitch
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='SFX Generator - Generate 1984-era arcade sound effects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sfx_generator.py explosion -o boom.wav
  python sfx_generator.py laser --intensity high --pitch high -o laser.wav
  python sfx_generator.py powerup -o powerup.wav

Available types: explosion, laser, hit, powerup, coin, jump, gameover, victory, damage, select, blip
        """
    )

    parser.add_argument('type', choices=SFXGenerator.VALID_TYPES,
                        help='Type of sound effect')
    parser.add_argument('-o', '--output', default='output.wav',
                        help='Output WAV filename')
    parser.add_argument('--intensity', choices=['low', 'medium', 'high'],
                        default='medium', help='Intensity level')
    parser.add_argument('--pitch', choices=['low', 'mid', 'high'],
                        default='mid', help='Pitch level')
    parser.add_argument('--duration', type=float, default=None,
                        help='Duration override in seconds')
    parser.add_argument('--root_dir', help='Root directory for output')

    args = parser.parse_args()

    result = generate_sfx(
        args.output, args.type, args.intensity, args.pitch,
        args.duration, args.root_dir
    )

    if result['status'] == 'success':
        print(f"SUCCESS: {result['path']} ({result['duration']:.2f}s)")
        print(f"  Type: {result['type']}, Intensity: {result['intensity']}, Pitch: {result['pitch']}")
    else:
        print(f"ERROR: {result['error']}")
