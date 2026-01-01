"""
Sequencer for Python Synthesizer
Manages pattern sequencing and timing
"""
import numpy as np
from typing import Dict, List, Any
from .audio_engine import AudioEngine


class Sequencer:
    """Pattern sequencer for generating audio from sequence data"""

    def __init__(self, sample_rate: int = 44100, quiet: bool = False):
        """
        Initialize sequencer

        Args:
            sample_rate: Audio sample rate (default: 44100 Hz)
        """
        self.sample_rate = sample_rate
        self.engine = AudioEngine(sample_rate)
        self.quiet = quiet
        self.warnings = []  # Collect warnings for incomplete data

    def render_pattern(self, settings: Dict[str, Any]) -> np.ndarray:
        """
        Render a complete pattern to audio

        Args:
            settings: Pattern settings dictionary containing:
                - bpm: Beats per minute
                - patternLength: Number of steps (default: 16). No hard limit; use 64+ for long BGM.
                - masterVolume: Master volume (0.0 to 1.0)
                - tracks: Dictionary of track configurations

        Returns:
            Audio samples as numpy array
        """
        bpm = settings.get('bpm', 120)
        steps = settings.get('patternLength', 16)
        master_volume = settings.get('masterVolume', 0.7)

        # Calculate timing
        duration_per_step = (60.0 / bpm) / 4  # 16th notes
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)

        # Initialize output buffer
        output = np.zeros(total_samples)

        # Get track settings
        tracks = settings.get('tracks', {})

        # Render each track
        for track_name in ['drum', 'bass', 'chord', 'melody', 'pcm', 'fm', 'fm2']:
            if track_name not in tracks:
                continue

            track = tracks[track_name]
            if track.get('muted', False):
                continue

            try:
                track_audio = self._render_track(
                    track_name,
                    track,
                    steps,
                    duration_per_step
                )

                # Mix into output
                mix_length = min(len(output), len(track_audio))
                output[:mix_length] += track_audio[:mix_length]
            except Exception as e:
                self._warn(f"Skipping track '{track_name}': {e}")

        # Apply master volume
        output *= master_volume

        # Normalize to prevent clipping
        max_val = np.abs(output).max()
        if max_val > 1.0:
            output /= max_val

        return output

    def _render_track(self, track_name: str, track_config: Dict[str, Any],
                     steps: int, duration_per_step: float) -> np.ndarray:
        """
        Render a single track

        Args:
            track_name: Name of the track
            track_config: Track configuration dictionary
            steps: Number of steps in the pattern
            duration_per_step: Duration of each step in seconds

        Returns:
            Audio samples as numpy array
        """
        volume = track_config.get('volume', 0.7)
        data = track_config.get('data', {})

        # Calculate total samples needed
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        if track_name == 'drum':
            output = self._render_drum_track(data, steps, duration_per_step, volume)
        elif track_name == 'bass':
            waveform = track_config.get('waveform', 'sawtooth')
            output = self._render_note_track(data, steps, duration_per_step,
                                            waveform, volume, 0.2)
        elif track_name == 'chord':
            waveform = track_config.get('waveform', 'triangle')
            output = self._render_chord_track(data, steps, duration_per_step,
                                             waveform, volume)
        elif track_name == 'melody':
            waveform = track_config.get('waveform', 'sine')
            output = self._render_note_track(data, steps, duration_per_step,
                                            waveform, volume, 0.3)
        elif track_name == 'pcm':
            sound_type = track_config.get('sound', 'piano')
            output = self._render_pcm_track(data, steps, duration_per_step,
                                           sound_type, volume)
        elif track_name in ['fm', 'fm2']:
            ratio = track_config.get('ratio', 2.0)
            depth = track_config.get('depth', 500.0)
            output = self._render_fm_track(data, steps, duration_per_step,
                                          ratio, depth, volume)

        return output

    def _warn(self, message: str):
        """Log a warning message"""
        self.warnings.append(message)
        if not self.quiet:
            print(f"  [Warning] {message}")

    def _render_drum_track(self, data: Dict[str, List[bool]], steps: int,
                          duration_per_step: float, volume: float) -> np.ndarray:
        """Render drum track"""
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        drum_types = ['Kick', 'Snare', 'Hi-Hat', 'Clap']

        for drum_type in drum_types:
            if drum_type not in data:
                continue

            pattern = data[drum_type]
            if not isinstance(pattern, list):
                self._warn(f"Invalid drum pattern for '{drum_type}': expected list")
                continue

            for step, active in enumerate(pattern):
                if not active or step >= steps:
                    continue

                try:
                    # Generate drum sound
                    drum_sound = self.engine.generate_drum(drum_type, volume)

                    # Calculate start position
                    start_sample = int(step * duration_per_step * self.sample_rate)
                    end_sample = start_sample + len(drum_sound)

                    # Mix into output
                    if end_sample <= total_samples:
                        output[start_sample:end_sample] += drum_sound
                    else:
                        # Truncate if sound extends beyond pattern length
                        available = total_samples - start_sample
                        output[start_sample:] += drum_sound[:available]
                except Exception as e:
                    self._warn(f"Failed to generate drum '{drum_type}' at step {step}: {e}")

        return output

    def _render_note_track(self, data: Dict[str, List[bool]], steps: int,
                          duration_per_step: float, waveform: str,
                          volume: float, note_duration: float) -> np.ndarray:
        """Render note track (bass or melody)"""
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        for note_name, pattern in data.items():
            if not isinstance(pattern, list):
                self._warn(f"Invalid note pattern for '{note_name}': expected list")
                continue

            for step, active in enumerate(pattern):
                if not active or step >= steps:
                    continue

                try:
                    # Generate note
                    note_sound = self.engine.generate_note(
                        note_name, note_duration, waveform, volume
                    )

                    if len(note_sound) == 0:
                        self._warn(f"Unknown note '{note_name}', skipping")
                        break  # Skip this note entirely

                    # Calculate start position
                    start_sample = int(step * duration_per_step * self.sample_rate)
                    end_sample = start_sample + len(note_sound)

                    # Mix into output
                    if end_sample <= total_samples:
                        output[start_sample:end_sample] += note_sound
                    else:
                        available = total_samples - start_sample
                        output[start_sample:] += note_sound[:available]
                except Exception as e:
                    self._warn(f"Failed to generate note '{note_name}' at step {step}: {e}")

        return output

    def _render_chord_track(self, data: Dict[str, List[bool]], steps: int,
                           duration_per_step: float, waveform: str,
                           volume: float) -> np.ndarray:
        """Render chord track"""
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        for chord_name, pattern in data.items():
            if not isinstance(pattern, list):
                self._warn(f"Invalid chord pattern for '{chord_name}': expected list")
                continue

            for step, active in enumerate(pattern):
                if not active or step >= steps:
                    continue

                try:
                    # Generate chord
                    chord_sound = self.engine.generate_chord(
                        chord_name, 0.4, waveform, volume
                    )

                    if len(chord_sound) == 0:
                        self._warn(f"Unknown chord '{chord_name}', skipping")
                        break

                    # Calculate start position
                    start_sample = int(step * duration_per_step * self.sample_rate)
                    end_sample = start_sample + len(chord_sound)

                    # Mix into output
                    if end_sample <= total_samples:
                        output[start_sample:end_sample] += chord_sound
                    else:
                        available = total_samples - start_sample
                        output[start_sample:] += chord_sound[:available]
                except Exception as e:
                    self._warn(f"Failed to generate chord '{chord_name}' at step {step}: {e}")

        return output

    def _render_pcm_track(self, data: Dict[str, List[bool]], steps: int,
                         duration_per_step: float, sound_type: str,
                         volume: float) -> np.ndarray:
        """Render PCM track"""
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        for note_name, pattern in data.items():
            if not isinstance(pattern, list):
                self._warn(f"Invalid PCM pattern for '{note_name}': expected list")
                continue

            for step, active in enumerate(pattern):
                if not active or step >= steps:
                    continue

                try:
                    # Generate PCM sound
                    pcm_sound = self.engine.generate_pcm(
                        note_name, sound_type, volume
                    )

                    if len(pcm_sound) == 0:
                        self._warn(f"Unknown note '{note_name}' for PCM, skipping")
                        break

                    # Calculate start position
                    start_sample = int(step * duration_per_step * self.sample_rate)
                    end_sample = start_sample + len(pcm_sound)

                    # Mix into output
                    if end_sample <= total_samples:
                        output[start_sample:end_sample] += pcm_sound
                    else:
                        available = total_samples - start_sample
                        output[start_sample:] += pcm_sound[:available]
                except Exception as e:
                    self._warn(f"Failed to generate PCM '{note_name}' at step {step}: {e}")

        return output

    def _render_fm_track(self, data: Dict[str, List[bool]], steps: int,
                        duration_per_step: float, ratio: float,
                        depth: float, volume: float) -> np.ndarray:
        """Render FM synthesis track"""
        total_duration = duration_per_step * steps
        total_samples = int(self.sample_rate * total_duration)
        output = np.zeros(total_samples)

        for note_name, pattern in data.items():
            if not isinstance(pattern, list):
                self._warn(f"Invalid FM pattern for '{note_name}': expected list")
                continue

            if note_name not in self.engine.NOTE_FREQUENCIES:
                self._warn(f"Unknown note '{note_name}' for FM track, skipping")
                continue

            freq = self.engine.NOTE_FREQUENCIES[note_name]

            for step, active in enumerate(pattern):
                if not active or step >= steps:
                    continue

                try:
                    # Generate FM sound
                    fm_sound = self.engine.generate_fm(
                        freq, 0.3, ratio, depth, volume
                    )

                    # Calculate start position
                    start_sample = int(step * duration_per_step * self.sample_rate)
                    end_sample = start_sample + len(fm_sound)

                    # Mix into output
                    if end_sample <= total_samples:
                        output[start_sample:end_sample] += fm_sound
                    else:
                        available = total_samples - start_sample
                        output[start_sample:] += fm_sound[:available]
                except Exception as e:
                    self._warn(f"Failed to generate FM note '{note_name}' at step {step}: {e}")

        return output
