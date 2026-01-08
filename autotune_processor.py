"""
Autotune audio processing module.

This module provides functions for pitch correction (autotune effect) on audio files.
It uses librosa for pitch detection and psola for pitch shifting.
"""

import librosa
from pathlib import Path
import soundfile as sf
import psola
import numpy as np
import scipy.signal as sig


def correct(f0: float, scale_root: str, scale_type: str) -> float:
    """
    Correct a single frequency value to the nearest note in the specified scale.
    
    Args:
        f0: The input frequency in Hz (can be NaN for unvoiced segments).
        scale_root: The root note of the scale (e.g., 'C', 'D', 'F#').
        scale_type: The type of scale, either 'maj' for major or 'min' for minor.
    
    Returns:
        The corrected frequency in Hz, snapped to the nearest note in the scale.
        Returns NaN if input is NaN.
    """
    if np.isnan(f0):
        return np.nan

    # Build the scale key string in the format expected by librosa (e.g., 'C:min')
    scale_key = f"{scale_root}:{scale_type}"
    
    # Get the scale degrees (semitone offsets) for the specified key
    scale_degrees = librosa.key_to_degrees(scale_key)
    
    # Extend scale degrees to include the octave (for wrapping calculations)
    scale_degrees = np.concatenate((scale_degrees, [scale_degrees[0] + 12]))

    # Convert frequency to MIDI note number
    midi_note = librosa.hz_to_midi(f0)
    
    # Get the degree within the octave (0-12)
    degree = midi_note % 12
    
    # Find the closest scale degree
    closest_degree_id = np.argmin(np.abs(scale_degrees - degree))

    # Calculate how far off we are from the closest scale degree
    degree_difference = degree - scale_degrees[closest_degree_id]

    # Adjust the MIDI note to snap to the scale
    midi_note -= degree_difference

    # Convert back to frequency
    return librosa.midi_to_hz(midi_note)


def correct_pitch(f0: np.ndarray, scale_root: str, scale_type: str) -> np.ndarray:
    """
    Apply pitch correction to an array of frequency values.
    
    Args:
        f0: Array of fundamental frequency values in Hz.
        scale_root: The root note of the scale (e.g., 'C', 'D', 'F#').
        scale_type: The type of scale, either 'maj' for major or 'min' for minor.
    
    Returns:
        Array of corrected frequency values, smoothed with a median filter.
    """
    # Apply correction to each frequency value
    corrected_f0 = np.zeros_like(f0)
    for i in range(f0.shape[0]):
        corrected_f0[i] = correct(f0[i], scale_root, scale_type)
    
    # Apply median filter to smooth out rapid pitch changes
    smoothed_corrected_f0 = sig.medfilt(corrected_f0, kernel_size=11)

    # Preserve NaN values from the original corrected array
    smoothed_corrected_f0[np.isnan(smoothed_corrected_f0)] = corrected_f0[
        np.isnan(smoothed_corrected_f0)
    ]

    return smoothed_corrected_f0


def autotune(y: np.ndarray, sr: int, scale_root: str, scale_type: str) -> np.ndarray:
    """
    Apply the full autotune effect to an audio signal.
    
    This function performs three main steps:
    1. Track the pitch of the input audio using pYIN algorithm
    2. Calculate the desired (corrected) pitch based on the target scale
    3. Apply pitch shifting to move the audio to the corrected pitch
    
    Args:
        y: Audio time series (mono).
        sr: Sample rate of the audio.
        scale_root: The root note of the scale (e.g., 'C', 'D', 'F#').
        scale_type: The type of scale, either 'maj' for major or 'min' for minor.
    
    Returns:
        Pitch-corrected audio time series.
    """
    # Define analysis parameters
    frame_length = 2048
    hop_length = frame_length // 4
    fmin = librosa.note_to_hz('C2')  # Minimum frequency for pitch detection
    fmax = librosa.note_to_hz('C7')  # Maximum frequency for pitch detection
    
    # Step 1: Track pitch using pYIN algorithm
    f0, _, _ = librosa.pyin(
        y,
        frame_length=frame_length,
        hop_length=hop_length,
        sr=sr,
        fmin=fmin,
        fmax=fmax
    )
    
    # Step 2: Calculate desired pitch by correcting to the scale
    corrected_f0 = correct_pitch(f0, scale_root, scale_type)
    
    # Step 3: Apply pitch shifting using PSOLA
    return psola.vocode(
        y,
        sample_rate=int(sr),
        target_pitch=corrected_f0,
        fmin=fmin,
        fmax=fmax
    )


def process_audio_file(
    input_filepath: str,
    scale_root: str,
    scale_type: str,
    output_filepath: str = None
) -> str:
    """
    Process an audio file with the autotune effect.
    
    Args:
        input_filepath: Path to the input audio file.
        scale_root: The root note of the scale (e.g., 'C', 'D', 'F#').
        scale_type: The type of scale, either 'maj' for major or 'min' for minor.
        output_filepath: Optional path for the output file. If not provided,
                        the output will be saved with '_pitch_corrected' suffix.
    
    Returns:
        Path to the output audio file.
    """
    # Load the audio file
    y, sr = librosa.load(input_filepath, sr=None, mono=False)

    # Convert to mono if stereo
    if y.ndim > 1:
        y = y[0, :]

    # Apply the autotune effect
    pitch_corrected_y = autotune(y, sr, scale_root, scale_type)

    # Generate output filepath if not provided
    if output_filepath is None:
        filepath = Path(input_filepath)
        output_filepath = str(
            filepath.parent / (filepath.stem + "_pitch_corrected.wav")
        )

    # Save the processed audio
    sf.write(output_filepath, pitch_corrected_y, sr)

    return output_filepath
