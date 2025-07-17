"""
Window style management for FullThumbs application.
"""

import win32gui
import win32con
from .constants import (
	WINDOW_MODE_NORMAL,  WINDOW_MODE_NORMAL_TEXT,
	WINDOW_MODE_MINIMAL, WINDOW_MODE_MINIMAL_TEXT,
	WINDOW_MODE_TOPMOST, WINDOW_MODE_TOPMOST_TEXT,
)

# Window styles
NORMAL_WINDOW_STYLE = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
NORMAL_WINDOW_EX_STYLE = 0
MINIMAL_WINDOW_STYLE = win32con.WS_POPUP | win32con.WS_VISIBLE
MINIMAL_WINDOW_EX_STYLE = win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST
TOPMOST_WINDOW_EX_STYLE = win32con.WS_EX_TOPMOST

# -------

def get_window_style_flags(window_mode):
	"""Returns the style flags for a given window mode."""
	if window_mode == WINDOW_MODE_MINIMAL:
		return (
			MINIMAL_WINDOW_STYLE,	MINIMAL_WINDOW_EX_STYLE, 
			win32con.HWND_TOPMOST,	WINDOW_MODE_MINIMAL_TEXT
		)
	elif window_mode == WINDOW_MODE_TOPMOST:
		return (
			NORMAL_WINDOW_STYLE,	TOPMOST_WINDOW_EX_STYLE, 
			win32con.HWND_TOPMOST,	WINDOW_MODE_TOPMOST_TEXT
		)
	else:  # WINDOW_MODE_NORMAL
		return (
			NORMAL_WINDOW_STYLE,	NORMAL_WINDOW_EX_STYLE, 
			win32con.HWND_NOTOPMOST, WINDOW_MODE_NORMAL_TEXT
		)

def set_window_style(hwnd, window_mode, current_mode):
	"""Set window style for the given mode."""
	if window_mode == current_mode:
		return current_mode
	
	target_style, target_ex_style, insert_after, mode_name = get_window_style_flags(window_mode)
	window_flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED
	
	print(f"Setting window style to: {mode_name}")
	win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, target_style)
	win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, target_ex_style)
	win32gui.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, window_flags)
	
	return window_mode
