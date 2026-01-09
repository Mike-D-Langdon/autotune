# Autotune Audio Processor

A web-based autotune application with a NiceGUI interface for applying pitch correction to audio files.

## Features

- Upload audio files (WAV, MP3, FLAC, OGG)
- Select target musical scale (root note + major/minor)
- Apply pitch correction (autotune effect)
- Download processed audio

## Installation

Using the pyproject.toml:

```bash
pip install .
```

## Usage

Run the application:

```bash
python main.py
```

Then open your browser to `http://localhost:8080`

## How It Works

1. **Upload**: Select an audio file to process
2. **Configure Scale**: Choose the scale root (C, D, E, etc.) and type (Major/Minor)
3. **Process**: Click "Apply Autotune" to process the audio
4. **Download**: Download the pitch-corrected result

## Technical Details

The autotune effect works in three stages:

1. **Pitch Detection**: Uses librosa's pYIN algorithm to track the fundamental frequency
2. **Pitch Correction**: Snaps detected pitches to the nearest note in the selected scale
3. **Pitch Shifting**: Uses PSOLA (Pitch Synchronous Overlap and Add) to shift the audio

## Project Structure

```
autotune/
├── main.py                 # NiceGUI web interface
├── autotune_processor.py   # Core audio processing functions
├── uploads/                # Directory for uploaded/processed files
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Dependencies

- librosa: Audio analysis and pitch detection
- soundfile: Audio file I/O
- psola: Pitch shifting algorithm
- numpy: Numerical operations
- scipy: Signal processing (median filter)
- flask: Web framework for file serving
- nicegui: Web-based GUI framework
