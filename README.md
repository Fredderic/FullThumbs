# FullThumbs - Picture-in-Picture Window for Windows

A Python utility that creates a Picture-in-Picture (PiP) window showing a live thumbnail of another application window using Windows DWM (Desktop Window Manager) thumbnails.

## Features

- Live thumbnail view of target application windows
- Resizable and movable PiP window
- Click-through functionality to bring source app to front
- Context menu with various options
- Persistent window position and style settings
- Automatic window detection and re-attachment
- Borderless mode for minimal distraction

## Requirements

- Windows 10/11 (requires DWM support)
- Python 3.x
- Required Python packages:
  - `pywin32` - Windows API bindings

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```
   pip install pywin32
   ```

## Usage

Run the script:
```
python full-thumbs.py
```

The application will:
1. Search for the target application window (currently configured for "Sky" application)
2. Create a PiP window showing a live thumbnail
3. Allow interaction through left-click (bring to front) and right-click (context menu)

## Configuration

- Window position and style are automatically saved to `full-thumbs.json`
- Target application can be modified by changing the `g_target_app_match` configuration in the script

## Controls

- **Left-click on thumbnail**: Bring source application to front
- **Right-click**: Open context menu
- **Drag window**: Move PiP window around
- **Resize window**: Adjust PiP window size

## Development

The script includes auto-restart functionality when running in debug mode (with debugpy).

## License

This project is provided as-is for educational and personal use.
