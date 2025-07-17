"""
Constants and configuration values for FullThumbs application.
"""

import win32con
import sys
import os

# Window style modes
WINDOW_MODE_NORMAL = 0		# Normal window with borders, not always on top
WINDOW_MODE_TOPMOST = 1		# Normal window with borders, always on top
WINDOW_MODE_MINIMAL = 2		# Borderless window, always on top

WINDOW_MODE_NORMAL_TEXT  = "Normal Window"			# "Normal"
WINDOW_MODE_TOPMOST_TEXT = "Always on Top"			# "Normal (Always on Top)"
WINDOW_MODE_MINIMAL_TEXT = "Minimal (Borderless)"	# "Minimal (Borderless, Always on Top)"

# Application settings
SETTINGS_FILE = os.path.splitext(sys.argv[0])[0] + '.json'
DEBUG_PY = 'debugpy' in sys.modules # or: any('debugpy' in m for m in sys.modules)
PIP_PADDING = 10

# Auto-update settings
MIN_UPDATE_INTERVAL_MS = 60_000					# 60 seconds minimum
DEFAULT_UPDATE_INTERVAL_MS = 4 * 60 * 60_000	# 4 hours default
