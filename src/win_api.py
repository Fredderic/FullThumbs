"""
Windows API utilities and helpers for FullThumbs application.

This module contains Windows-specific functionality including coordinate
manipulation, window rectangle calculations, and timer management using
the Windows API.
"""

import ctypes, win32api, win32gui
from typing import NamedTuple

from src.constants import PIP_PADDING

# ---

def split_lparam_pos(lparam):
	"""Splits the lparam into x and y coordinates."""
	# return win32api.LOWORD(lparam), win32api.HIWORD(lparam)
	try:
		lparam &= 0xFFFFFFFF # Ensure lparam is treated as a 32-bit value
		if lparam >= 0x80000000:
			lparam = lparam - 0x100000000
		return (
				ctypes.c_short(win32api.LOWORD(lparam)).value,
				ctypes.c_short(win32api.HIWORD(lparam)).value
			)
	except Exception as e:
		print(f"Error splitting lparam: {e}")
		raise

def get_inner_client_rect(hwnd):
	"""Get the inner client rectangle with padding."""
	dest_left, dest_top, dest_right, dest_bottom = win32gui.GetClientRect(hwnd)
	return (
		dest_left  + PIP_PADDING,	dest_top    + PIP_PADDING,
		dest_right - PIP_PADDING,	dest_bottom - PIP_PADDING
	)

# --- Timer class to manage application timers

class Timer(NamedTuple):
	"""Simple structure to hold timer information."""
	id: int
	ms: int | None = None  # Can be None for timers that specify interval at start time
	
	_timers = dict()

	def start(self, hwnd, interval_ms=None):
		"""Sets a timer using the user32 library.
		
		Args:
			hwnd: Window handle to associate the timer with
			interval_ms: Optional override for the timer interval in milliseconds.
						If None, uses self.ms. Must be positive.
		"""
		# Determine the interval to use
		effective_ms = interval_ms if interval_ms is not None else self.ms
		if effective_ms is None or effective_ms <= 0:
			raise ValueError(f"Timer {self.id} requires a positive interval (got {effective_ms})")
		
		ctypes.windll.user32.SetTimer(hwnd, self.id, effective_ms, None)
		Timer._timers[self] = hwnd
		return self

	def stop(self):
		"""Kills a timer using the user32 library."""
		ctypes.windll.user32.KillTimer(Timer._timers.pop(self), self.id)
		return self

	@staticmethod
	def stop_all(hwnd=None):
		"""Stops all active timers."""
		for timer,t_hwnd in tuple(Timer._timers.items()):
			if hwnd is None or t_hwnd == hwnd:
				timer.stop()
