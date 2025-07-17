# FullThumbs - Picture-in-Picture Window for Windows

FullThumbs is a Picture-in-Picture (PiP) thumbnail viewer for Windows that provides a live, 
resizable preview of any target application window. The application features three window 
modes (normal, always-on-top, and minimal borderless), automatic git-based updates, 
and comprehensive command-line options.

## Features

- Live DWM thumbnail rendering of target applications
- Three window display modes with context menu switching
- Automatic git-based updates with configurable intervals
- Flexible command-line argument parsing
- Persistent window position and mode settings
- Debug mode with auto-reload functionality
- Click-through functionality to bring source app to front
- Context menu with various options
- Automatic window detection and re-attachment

## Requirements

- Windows 10/11 (requires DWM support)
- Python 3.x
- Required Python packages:
  - `pywin32` - Windows API bindings

## Installation

1. **Download the repository:**
   ```bash
   # Clone with git
   git clone https://github.com/Fredderic/FullThumbs.git
   cd FullThumbs
   
   # Or download ZIP from GitHub and extract
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

For detailed usage information, run:
```
python full-thumbs.py --help
```

Basic examples:
```bash
# Run with default settings (auto-update every 4 hours)
python full-thumbs.py

# Disable auto-updates
python full-thumbs.py --no-auto-update

# Check for updates every 2 hours
python full-thumbs.py --auto-update=2h

# Check for updates every 30 minutes
python full-thumbs.py --auto-update=30m

# Run directly without auto-update loop (internal use)
python full-thumbs.py run
```

### Command Structure

The application uses a subcommand structure:
- **Main command**: Handles auto-update configuration and runs the application with update checking
- **`run` subcommand**: Runs the application directly without the auto-update loop (primarily for internal use)
  - `--update-interval SECONDS`: Sets auto-update check interval in seconds (0 to disable)

## Auto-Update System

FullThumbs includes an intelligent auto-update system that:
- **Fetches updates**: Automatically checks git repository for new commits
- **Safe updates**: Only updates if working directory is clean (no uncommitted changes)
- **Configurable intervals**: Set custom check intervals (e.g., `4h`, `30m`, `2d`)
- **Time-based checking**: Uses actual time intervals, not restart counters
- **Graceful restart**: Automatically restarts application after successful updates

### Auto-Update Examples
```bash
# Default 4-hour interval
python full-thumbs.py --auto-update

# Custom intervals
python full-thumbs.py --auto-update=2h    # Every 2 hours
python full-thumbs.py --auto-update=30m   # Every 30 minutes  
python full-thumbs.py --auto-update=1d    # Daily

# Disable auto-updates
python full-thumbs.py --no-auto-update
```

## Configuration

- Window position and mode are automatically saved to `full-thumbs.json`
- Target application can be modified by changing the `g_target_app_match` configuration in the script
- Auto-update behavior is configurable via command-line arguments

## Controls

- **Left-click on thumbnail**: Bring source application to front
- **Right-click**: Open context menu with window mode options
- **Drag window**: Move PiP window around
- **Resize window**: Adjust PiP window size

## Window Modes

- **Normal**: Standard window with borders, not always on top
- **Always on Top**: Normal window with borders, stays on top of other windows
- **Minimal**: Borderless window, always on top for minimal distraction

## Development

### Architecture
- **Modular design**: Core functionality organized in `src/` directory
- **Entry point**: `full-thumbs.py` handles CLI parsing, auto-updates, and application lifecycle
- **Main application**: `src/main.py` contains the PiP window logic
- **Supporting modules**: Constants, structures, window management, settings, and version tracking

### Development Features
- **Auto-restart**: Automatic script reload when files change (debug mode)
- **Comprehensive testing**: Full test suite with unittest framework
- **Git integration**: Version tracking and automatic updates via git
- **Pre-commit hooks**: Ensures tests pass before commits
- **CLI subcommands**: Clean separation between user options and internal operations

### Debug Mode
When `DEBUG_PY = True` in `src/constants.py`:
- Auto-updates are disabled
- Direct execution without auto-update loop

## Testing

Run the test suite:
```bash
python run_tests.py
```

## License

This project is provided as-is for educational and personal use.
