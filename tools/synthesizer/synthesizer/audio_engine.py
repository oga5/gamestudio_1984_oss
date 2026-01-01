"""
Audio Engine for Python Synthesizer
Implements various sound generation methods: drums, oscillators, PCM samples, and FM synthesis.
Supports full chromatic scale from C2 to C6, including sharps and flats (e.g., C2, C#2, Db2... B5, C6).
"""
import numpy as np
from typing import Dict, Tuple


# Note frequencies (Hz)
NOTE_FREQUENCIES = {
    # Octave 2
    'C2': 65.41, 'C#2': 69.30, 'Db2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'Eb2': 77.78,
    'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'Gb2': 92.50, 'G2': 98.00, 'G#2': 103.83, 'Ab2': 103.83,
    'A2': 110.00, 'A#2': 116.54, 'Bb2': 116.54, 'B2': 123.47,

    # Octave 3
    'C3': 130.81, 'C#3': 138.59, 'Db3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'Eb3': 155.56,
    'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'Gb3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'Ab3': 207.65,
    'A3': 220.00, 'A#3': 233.08, 'Bb3': 233.08, 'B3': 246.94,

    # Octave 4
    'C4': 261.63, 'C#4': 277.18, 'Db4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'Eb4': 311.13,
    'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'Gb4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'Ab4': 415.30,
    'A4': 440.00, 'A#4': 466.16, 'Bb4': 466.16, 'B4': 493.88,

    # Octave 5
    'C5': 523.25, 'C#5': 554.37, 'Db5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'Eb5': 622.25,
    'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'Gb5': 739.99, 'G5': 783.99, 'G#5': 830.61, 'Ab5': 830.61,
    'A5': 880.00, 'A#5': 932.33, 'Bb5': 932.33, 'B5': 987.77,

    # Octave 6
    'C6': 1046.50
}

# Chord definitions
CHORD_TYPES = {
    'C': ['C3', 'E3', 'G3'],
    'Dm': ['D3', 'F3', 'A3'],
    'Em': ['E3', 'G3', 'B3'],
    'F': ['F3', 'A3', 'C4'],
    'G': ['G3', 'B3', 'D4'],
    'Am': ['A3', 'C4', 'E4'],
    'Bdim': ['B3', 'D4', 'F4'],
    'C7': ['C3', 'E3', 'G3', 'Bb3']
}


class AudioEngine:
    """Main audio engine for generating sounds"""
    
    # Class-level reference to module constants for backward compatibility
    NOTE_FREQUENCIES = NOTE_FREQUENCIES
    CHORD_TYPES = CHORD_TYPES

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize audio engine

        Args:
            sample_rate: Audio sample rate (default: 44100 Hz)
        """
        self.sample_rate = sample_rate
        self.pcm_samples = self._generate_pcm_samples()

    def _generate_pcm_samples(self) -> Dict[str, np.ndarray]:
        """Generate PCM samples for different instruments"""
        samples = {}
        duration = 1.0  # 1 second samples
        t = np.linspace(0, duration, int(self.sample_rate * duration))

        # Piano (with harmonics and decay)
        envelope = np.exp(-3 * t)
        samples['piano'] = envelope * (
            np.sin(2 * np.pi * 440 * t) * 0.5 +
            np.sin(2 * np.pi * 880 * t) * 0.3 +
            np.sin(2 * np.pi * 1320 * t) * 0.2
        )

        # Electric Piano
        envelope = np.exp(-2 * t)
        samples['epiano'] = envelope * (
            np.sin(2 * np.pi * 440 * t) * 0.6 +
            np.sin(2 * np.pi * 880 * t) * 0.4
        )

        # Organ (sustained)
        envelope = np.where(t < 0.05, t / 0.05, np.where(t > 0.9, (1 - t) / 0.1, 1))
        samples['organ'] = envelope * (
            np.sin(2 * np.pi * 440 * t) * 0.4 +
            np.sin(2 * np.pi * 880 * t) * 0.3 +
            np.sin(2 * np.pi * 1320 * t) * 0.2 +
            np.sin(2 * np.pi * 1760 * t) * 0.1
        )

        # Strings (slow attack, sustained)
        envelope = np.where(t < 0.3, t / 0.3, np.where(t > 0.8, (1 - t) / 0.2, 1))
        samples['strings'] = envelope * (
            np.sin(2 * np.pi * 440 * t) * 0.3 +
            np.sin(2 * np.pi * 880 * t) * 0.25 +
            np.sin(2 * np.pi * 1320 * t) * 0.2 +
            np.sin(2 * np.pi * 220 * t) * 0.25
        )

        return samples

    def generate_drum(self, drum_type: str, volume: float = 1.0) -> np.ndarray:
        """
        Generate drum sound

        Args:
            drum_type: Type of drum ('Kick', 'Snare', 'Hi-Hat', 'Clap')
            volume: Volume multiplier (0.0 to 1.0)

        Returns:
            Audio samples as numpy array
        """
        drum_configs = {
            'Kick': {'freq': 60, 'decay': 0.5, 'noise': False},
            'Snare': {'freq': 200, 'decay': 0.15, 'noise': True},
            'Hi-Hat': {'freq': 8000, 'decay': 0.05, 'noise': True},
            'Clap': {'freq': 1000, 'decay': 0.1, 'noise': True}
        }

        if drum_type not in drum_configs:
            return np.array([])

        config = drum_configs[drum_type]
        duration = config['decay']
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)

        if config['noise']:
            # Noise-based drum (snare, hi-hat, clap)
            noise = np.random.uniform(-1, 1, samples)
            envelope = np.exp(-t / duration * 10)
            sound = noise * envelope

            # Simple bandpass filter simulation
            freq = config['freq']
            if freq > 1000:  # High-pass for hi-hat
                sound = np.diff(sound, prepend=sound[0])
        else:
            # Oscillator-based drum (kick)
            freq_envelope = config['freq'] * (1 - 0.7 * (1 - np.exp(-t / duration * 5)))
            phase = 2 * np.pi * np.cumsum(freq_envelope) / self.sample_rate
            sound = np.sin(phase)
            envelope = np.exp(-t / duration * 5)
            sound = sound * envelope

        return sound * volume * 0.5

    def generate_oscillator(self, frequency: float, duration: float,
                          waveform: str = 'sine', volume: float = 1.0) -> np.ndarray:
        """
        Generate oscillator sound

        Args:
            frequency: Frequency in Hz
            duration: Duration in seconds
            waveform: Waveform type ('sine', 'sawtooth', 'triangle', 'square')
            volume: Volume multiplier (0.0 to 1.0)

        Returns:
            Audio samples as numpy array
        """
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)

        if waveform == 'sine':
            sound = np.sin(2 * np.pi * frequency * t)
        elif waveform == 'sawtooth':
            sound = 2 * (t * frequency - np.floor(0.5 + t * frequency))
        elif waveform == 'triangle':
            sound = 2 * np.abs(2 * (t * frequency - np.floor(0.5 + t * frequency))) - 1
        elif waveform == 'square':
            sound = np.sign(np.sin(2 * np.pi * frequency * t))
        else:
            sound = np.sin(2 * np.pi * frequency * t)

        # Envelope (ADSR-like)
        envelope = np.exp(-t / duration * 5)
        return sound * envelope * volume * 0.3

    def generate_pcm(self, note: str, sound_type: str = 'piano',
                    volume: float = 1.0) -> np.ndarray:
        """
        Generate PCM sound

        Args:
            note: Note name (e.g., 'C4', 'A3')
            sound_type: PCM sound type ('piano', 'epiano', 'organ', 'strings')
            volume: Volume multiplier (0.0 to 1.0)

        Returns:
            Audio samples as numpy array
        """
        if note not in NOTE_FREQUENCIES:
            return np.array([])

        freq = NOTE_FREQUENCIES[note]
        sample = self.pcm_samples.get(sound_type, self.pcm_samples['piano'])

        # Resample to match the note frequency
        # Base frequency is A4 (440 Hz)
        playback_rate = freq / 440.0

        # Simple resampling
        duration = 0.5  # seconds
        new_length = int(len(sample) / playback_rate * (duration / 1.0))
        indices = np.linspace(0, len(sample) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(sample)), sample)

        return resampled[:int(self.sample_rate * duration)] * volume * 0.4

    def generate_fm(self, frequency: float, duration: float,
                   ratio: float = 2.0, depth: float = 500.0,
                   volume: float = 1.0) -> np.ndarray:
        """
        Generate FM synthesis sound

        Args:
            frequency: Carrier frequency in Hz
            duration: Duration in seconds
            ratio: Modulator/carrier frequency ratio
            depth: Modulation depth
            volume: Volume multiplier (0.0 to 1.0)

        Returns:
            Audio samples as numpy array
        """
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)

        # FM synthesis: modulator modulates carrier frequency
        modulator_freq = frequency * ratio
        modulator = np.sin(2 * np.pi * modulator_freq * t)

        # Carrier with modulated frequency
        phase = 2 * np.pi * frequency * t + depth * modulator
        carrier = np.sin(phase)

        # Envelope
        envelope = np.exp(-t / duration * 5)

        return carrier * envelope * volume * 0.3

    def generate_note(self, note: str, duration: float, waveform: str = 'sine',
                     volume: float = 1.0) -> np.ndarray:
        """
        Generate a note with specified waveform

        Args:
            note: Note name (e.g., 'C4', 'A3')
            duration: Duration in seconds
            waveform: Waveform type
            volume: Volume multiplier

        Returns:
            Audio samples as numpy array
        """
        if note not in NOTE_FREQUENCIES:
            return np.array([])

        freq = NOTE_FREQUENCIES[note]
        return self.generate_oscillator(freq, duration, waveform, volume)

    def generate_chord(self, chord_name: str, duration: float,
                      waveform: str = 'triangle', volume: float = 1.0) -> np.ndarray:
        """
        Generate a chord

        Args:
            chord_name: Chord name (e.g., 'C', 'Am', 'G')
            duration: Duration in seconds
            waveform: Waveform type
            volume: Volume multiplier

        Returns:
            Audio samples as numpy array (mixed chord notes)
        """
        if chord_name not in CHORD_TYPES:
            return np.array([])

        notes = CHORD_TYPES[chord_name]
        chord_sound = None

        for note in notes:
            note_sound = self.generate_note(note, duration, waveform, volume)
            if chord_sound is None:
                chord_sound = note_sound
            else:
                # Mix notes together
                min_len = min(len(chord_sound), len(note_sound))
                chord_sound[:min_len] += note_sound[:min_len]

        return chord_sound
