"""
WAV File Writer for Python Synthesizer
"""
import numpy as np
import wave
import struct
from pathlib import Path


class WavWriter:
    """Write audio data to WAV files"""

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize WAV writer

        Args:
            sample_rate: Audio sample rate (default: 44100 Hz)
        """
        self.sample_rate = sample_rate

    def write(self, filename: str, audio_data: np.ndarray, normalize: bool = True):
        """
        Write audio data to WAV file

        Args:
            filename: Output filename
            audio_data: Audio samples as numpy array (mono, float -1.0 to 1.0)
            normalize: Whether to normalize audio to prevent clipping
        """
        # Ensure output directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize if requested
        if normalize:
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = audio_data / max_val * 0.95  # Leave some headroom

        # Convert to 16-bit PCM
        audio_data = np.clip(audio_data, -1.0, 1.0)
        pcm_data = (audio_data * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(str(output_path), 'w') as wav_file:
            # Set parameters: nchannels, sampwidth, framerate, nframes, comptype, compname
            wav_file.setparams((1, 2, self.sample_rate, len(pcm_data), 'NONE', 'not compressed'))

            # Write audio data
            wav_file.writeframes(pcm_data.tobytes())

    def write_stereo(self, filename: str, left_channel: np.ndarray,
                    right_channel: np.ndarray, normalize: bool = True):
        """
        Write stereo audio data to WAV file

        Args:
            filename: Output filename
            left_channel: Left channel audio samples
            right_channel: Right channel audio samples
            normalize: Whether to normalize audio
        """
        # Ensure same length
        min_length = min(len(left_channel), len(right_channel))
        left_channel = left_channel[:min_length]
        right_channel = right_channel[:min_length]

        # Normalize if requested
        if normalize:
            max_val = max(np.abs(left_channel).max(), np.abs(right_channel).max())
            if max_val > 0:
                left_channel = left_channel / max_val * 0.95
                right_channel = right_channel / max_val * 0.95

        # Convert to 16-bit PCM
        left_channel = np.clip(left_channel, -1.0, 1.0)
        right_channel = np.clip(right_channel, -1.0, 1.0)
        left_pcm = (left_channel * 32767).astype(np.int16)
        right_pcm = (right_channel * 32767).astype(np.int16)

        # Interleave channels
        stereo_data = np.empty((len(left_pcm) * 2,), dtype=np.int16)
        stereo_data[0::2] = left_pcm
        stereo_data[1::2] = right_pcm

        # Ensure output directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write WAV file
        with wave.open(str(output_path), 'w') as wav_file:
            wav_file.setparams((2, 2, self.sample_rate, len(left_pcm), 'NONE', 'not compressed'))
            wav_file.writeframes(stereo_data.tobytes())
