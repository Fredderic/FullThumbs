"""
Settings management for FullThumbs application.
"""

import json
import win32gui
import win32con
from win32api import GetSystemMetrics

from .constants import SETTINGS_FILE, WINDOW_MODE_NORMAL

# -------

saved_settings_data = None

def save_window_placement(hwnd):
	"""Save window placement and mode to settings file."""
	global saved_settings_data

	from .main import g_current_window_mode
	
	rect = win32gui.GetWindowRect(hwnd)
	settings = {
		"left": rect[0], 
		"top": rect[1], 
		"right": rect[2], 
		"bottom": rect[3],
		"window_mode": g_current_window_mode
	}
	
	if saved_settings_data != settings:
		print(f"Saving window placement: {settings}")
		with open(SETTINGS_FILE, "wt") as f:
			json.dump(settings, f)
		saved_settings_data = settings

def load_window_placement(settings_file=SETTINGS_FILE):
	"""Load window placement and mode from settings file."""
	global saved_settings_data
	try:
		with open(settings_file, "rt") as f:
			return (saved_settings_data := json.load(f))
	except (FileNotFoundError, json.JSONDecodeError):
		saved_settings_data = None
		return None

def get_default_window_settings():
	"""Get default window settings if no saved settings exist."""
	screen_width = GetSystemMetrics(win32con.SM_CXSCREEN)
	screen_height = GetSystemMetrics(win32con.SM_CYSCREEN)
	
	pip_width = 300
	pip_height = 200
	pip_x = screen_width - pip_width - 20   # 20px from right edge
	pip_y = screen_height - pip_height - 20 # 20px from bottom edge
	
	return {
		"left": pip_x,
		"top": pip_y,
		"right": pip_x + pip_width,
		"bottom": pip_y + pip_height,
		"window_mode": WINDOW_MODE_NORMAL
	}
