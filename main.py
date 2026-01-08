"""
Autotune Application with NiceGUI Interface.

This module provides a web-based GUI for the autotune audio processor.
Users can upload audio files, select scale parameters, and process
audio with pitch correction.
"""

import os
import shutil
from pathlib import Path

from nicegui import ui, app, run
from flask import Flask, send_from_directory

from autotune_processor import process_audio_file

# Directory for storing uploaded and processed files
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Flask app for serving static files (processed audio downloads)
flask_app = Flask(__name__)


@flask_app.route('/downloads/<path:filename>')
def download_file(filename: str):
    """
    Flask route to serve processed audio files for download.
    
    Args:
        filename: Name of the file to download.
    
    Returns:
        The file as an attachment for download.
    """
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


# Available musical note options for the scale root selector
NOTE_OPTIONS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Scale type options (major or minor)
SCALE_TYPE_OPTIONS = {'Major': 'maj', 'Minor': 'min'}


class AutotuneApp:
    """
    Main application class for the Autotune GUI.
    
    This class manages the state and UI components of the autotune
    application, including file upload, parameter selection, and
    audio processing.
    """
    
    def __init__(self):
        """Initialize the application state variables."""
        # Currently uploaded file path
        self.uploaded_file_path: str = None
        # Original filename for display
        self.uploaded_filename: str = None
        # Path to the processed output file
        self.output_file_path: str = None
        # Selected scale root note (default: C)
        self.scale_root: str = 'C'
        # Selected scale type display name (default: Minor)
        self.scale_type_display: str = 'Minor'
        # Processing status message
        self.status_message: str = ''
        # Flag indicating if processing is in progress
        self.is_processing: bool = False
    
    @property
    def scale_type(self) -> str:
        """
        Get the scale type code for librosa.
        
        Returns:
            'maj' for Major or 'min' for Minor.
        """
        return SCALE_TYPE_OPTIONS[self.scale_type_display]
    
    async def handle_upload(self, e):
        """
        Handle file upload events from the UI.
        
        Args:
            e: Upload event containing the file data (UploadEventArguments).
               The file is accessed via e.file which has name, content_type,
               and methods like read(), save(), etc.
        """
        # Reset previous output
        self.output_file_path = None
        self.status_message = ''
        
        # Extract file info from the upload event
        uploaded_file = e.file
        self.uploaded_filename = uploaded_file.name
        self.uploaded_file_path = str(UPLOAD_DIR / uploaded_file.name)
        
        # Save uploaded file to the uploads directory using the async save method
        await uploaded_file.save(self.uploaded_file_path)
        
        self.status_message = f'File "{uploaded_file.name}" uploaded successfully.'
        self.status_label.set_text(self.status_message)
        self.status_label.classes(remove='text-red-500', add='text-green-500')
        
        # Enable the process button
        self.process_button.enable()
    
    async def process_audio(self):
        """
        Process the uploaded audio file with autotune effect.
        
        This method applies pitch correction to the uploaded audio
        using the selected scale parameters.
        """
        if not self.uploaded_file_path:
            self.status_message = 'Please upload an audio file first.'
            self.status_label.set_text(self.status_message)
            self.status_label.classes(remove='text-green-500', add='text-red-500')
            return
        
        # Update UI to show processing state
        self.is_processing = True
        self.process_button.disable()
        self.status_message = 'Processing audio... This may take a moment.'
        self.status_label.set_text(self.status_message)
        self.status_label.classes(remove='text-red-500 text-green-500', add='text-blue-500')
        self.spinner.set_visibility(True)
        
        try:
            # Generate output filename
            input_path = Path(self.uploaded_file_path)
            output_filename = f"{input_path.stem}_pitch_corrected.wav"
            output_path = str(UPLOAD_DIR / output_filename)
            
            # Process the audio file with selected parameters
            # Using run.cpu_bound to execute in a separate process (non-blocking)
            self.output_file_path = await run.cpu_bound(
                process_audio_file,
                self.uploaded_file_path,
                self.scale_root,
                self.scale_type,
                output_path
            )
            
            # Update status on success
            self.status_message = f'Processing complete! Output: {output_filename}'
            self.status_label.set_text(self.status_message)
            self.status_label.classes(remove='text-blue-500 text-red-500', add='text-green-500')
            
            # Enable download button
            self.download_button.enable()
            
        except Exception as ex:
            # Handle processing errors
            self.status_message = f'Error processing audio: {str(ex)}'
            self.status_label.set_text(self.status_message)
            self.status_label.classes(remove='text-green-500 text-blue-500', add='text-red-500')
        
        finally:
            # Reset processing state
            self.is_processing = False
            self.process_button.enable()
            self.spinner.set_visibility(False)
    
    def download_output(self):
        """
        Trigger download of the processed audio file.
        """
        if self.output_file_path:
            filename = Path(self.output_file_path).name
            ui.download(f'/downloads/{filename}')
    
    def build_ui(self):
        """
        Build the NiceGUI user interface.
        
        Creates all UI components including file upload, parameter
        selectors, and action buttons.
        """
        # Add Flask app routes to NiceGUI for file downloads
        app.add_static_files('/downloads', str(UPLOAD_DIR))
        
        # Main container with centered content
        with ui.column().classes('w-full max-w-2xl mx-auto p-8'):
            # Application title
            ui.label('🎤 Autotune Audio Processor').classes(
                'text-3xl font-bold text-center mb-8'
            )
            
            # Description text
            ui.label(
                'Upload an audio file and select scale parameters to apply '
                'pitch correction (autotune effect).'
            ).classes('text-gray-600 text-center mb-6')
            
            # File upload section
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('1. Upload Audio File').classes('text-lg font-semibold mb-2')
                
                # File upload component
                ui.upload(
                    label='Select WAV file',
                    on_upload=self.handle_upload,
                    auto_upload=True
                ).classes('w-full').props('accept=".wav,.mp3,.flac,.ogg"')
            
            # Scale parameters section
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('2. Select Scale Parameters').classes('text-lg font-semibold mb-4')
                
                with ui.row().classes('w-full gap-4'):
                    # Scale root note selector
                    with ui.column().classes('flex-1'):
                        ui.label('Scale Root').classes('text-sm text-gray-600 mb-1')
                        ui.select(
                            options=NOTE_OPTIONS,
                            value=self.scale_root,
                            on_change=lambda e: setattr(self, 'scale_root', e.value)
                        ).classes('w-full')
                    
                    # Major/Minor selector
                    with ui.column().classes('flex-1'):
                        ui.label('Major or Minor').classes('text-sm text-gray-600 mb-1')
                        ui.select(
                            options=list(SCALE_TYPE_OPTIONS.keys()),
                            value=self.scale_type_display,
                            on_change=lambda e: setattr(self, 'scale_type_display', e.value)
                        ).classes('w-full')
            
            # Action buttons section
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('3. Process Audio').classes('text-lg font-semibold mb-4')
                
                with ui.row().classes('w-full gap-4 justify-center'):
                    # Process button - starts the autotune processing
                    self.process_button = ui.button(
                        'Apply Autotune',
                        on_click=self.process_audio
                    ).classes('bg-blue-500').props('icon=auto_fix_high')
                    self.process_button.disable()
                    
                    # Download button - downloads the processed file
                    self.download_button = ui.button(
                        'Download Result',
                        on_click=self.download_output
                    ).classes('bg-green-500').props('icon=download')
                    self.download_button.disable()
                
                # Processing spinner (hidden by default)
                with ui.row().classes('w-full justify-center mt-4'):
                    self.spinner = ui.spinner('dots', size='lg')
                    self.spinner.set_visibility(False)
            
            # Status message display
            with ui.card().classes('w-full p-4'):
                ui.label('Status').classes('text-lg font-semibold mb-2')
                self.status_label = ui.label('Ready. Please upload an audio file.').classes(
                    'text-gray-600'
                )


def main():
    """
    Main entry point for the Autotune application.
    
    Initializes the application and starts the NiceGUI server.
    """
    # Create application instance and build the UI
    autotune_app = AutotuneApp()
    autotune_app.build_ui()
    
    # Start the NiceGUI server
    ui.run(title='Autotune Processor', port=8080, reload=False)


if __name__ == '__main__':
    main()
