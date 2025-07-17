"""
Window finding utilities for FullThumbs application.
"""

import re
import win32gui
import pywintypes

def _run_find_window(enum_windows_callback):
	"""Helper function to run window enumeration with error handling."""
	try:
		win32gui.EnumWindows(enum_windows_callback, None)
	except pywintypes.error as e:
		if e.winerror == 18:  # "There are no more files."
			pass  # Successfully found and stopped, no actual error
		elif e.winerror == 3:  # "The system cannot find the path specified."
			# This can happen if a window handle becomes invalid during enumeration
			print(f"Warning: Window enumeration encountered invalid handle (error {e.winerror}). This is usually harmless.")
			print(f"Full error details: {e}")
			pass  # Continue execution - this is often recoverable
		else:
			print(f"Windows API error during EnumWindows: {e.winerror} - {e.strerror}")
			raise e
	except Exception as e:
		print(f"An unexpected error occurred during EnumWindows: {e}")
		raise

def window_finder_by_title(title_substring):
	"""
	Finds a window by a partial match of its title using EnumWindows.
	Returns the HWND of; 1) the first exact matching window found,
			2) the last partial match found, or 3) None if not found.
	"""
	def window_finder():
		title_substring_l = title_substring.lower()
		found_hwnd = None
		
		def enum_windows_callback(hwnd, lParam):
			nonlocal found_hwnd
			try:
				# Validate window handle first
				if not hwnd or not win32gui.IsWindow(hwnd):
					return True  # Continue with next window
				
				# Check if window is visible before getting title (more efficient)
				if not win32gui.IsWindowVisible(hwnd):
					return True  # Continue with next window
				
				window_title = win32gui.GetWindowText(hwnd)
				if window_title:
					window_title_l = window_title.lower()
					if title_substring_l == window_title_l:
						found_hwnd = hwnd
						return False  # Stop enumeration
					elif title_substring_l in window_title_l:
						found_hwnd = hwnd
			except pywintypes.error as e:
				# Handle cases where window becomes invalid during enumeration
				if e.winerror in [2, 3, 6]:  # Common "invalid handle" type errors
					return True  # Continue with next window
				raise  # Re-raise unexpected errors
			except Exception as e:
				print(f"Error processing window {hwnd}: {e}")
				return True  # Continue with next window
			
			return True  # Continue enumeration
		
		_run_find_window(enum_windows_callback)
		return found_hwnd
	return window_finder

def window_finder_by_regex(title_match, class_match=None):
	"""
	Finds a window by a regex match of its title and optionally class name.
	Returns the HWND of the first matching window found, or None if not found.
	"""
	if isinstance(title_match, str):
		title_match = re.compile(title_match)
	
	def window_finder():
		found_hwnd = window_title = window_class = None
		
		def enum_windows_callback(hwnd, lParam):
			nonlocal found_hwnd, window_title, window_class
			try:
				# Validate window handle first
				if not hwnd or not win32gui.IsWindow(hwnd):
					return True  # Continue with next window
				
				# Check if window is visible before getting title (more efficient)
				if not win32gui.IsWindowVisible(hwnd):
					return True  # Continue with next window
				
				window_title = win32gui.GetWindowText(hwnd)
				if window_title:
					window_class = win32gui.GetClassName(hwnd)
					
					if title_match.match(window_title) and (
							class_match == window_class or not class_match):
						found_hwnd = hwnd
						return False  # Stop enumeration
			except pywintypes.error as e:
				# Handle cases where window becomes invalid during enumeration
				if e.winerror in [2, 3, 6]:  # Common "invalid handle" type errors
					return True  # Continue with next window
				raise  # Re-raise unexpected errors
			except Exception as e:
				print(f"Error processing window {hwnd}: {e}")
				return True  # Continue with next window
			
			return True  # Continue enumeration
		
		_run_find_window(enum_windows_callback)
		if class_match is None and found_hwnd is not None:
			print(f"Found window: {found_hwnd!r} with title: {window_title!r} and class: {window_class!r}")
		return found_hwnd
	return window_finder
