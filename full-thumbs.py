# type: ignore

import re, json, sys, os, subprocess
from typing import NamedTuple
import ctypes, pywintypes, win32gui, win32con, win32api
import win32ui	# NOTE: required, causes an error if not imported
from ctypes import byref, create_string_buffer, c_int
from win32api import GetSystemMetrics

# Define DWM_THUMBNAIL_PROPERTIES structure and constants
class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
	_fields_ = [
		("dwFlags", ctypes.c_uint),
		("rcDestination", ctypes.c_long * 4),	# RECT
		("rcSource", ctypes.c_long * 4),		# RECT
		("opacity", ctypes.c_ubyte),
		("fVisible", ctypes.c_bool),
		("fSourceClientAreaOnly", ctypes.c_bool),
	]
DWM_TNP_RECTDESTINATION = 0x00000001
DWM_TNP_RECTSOURCE = 0x00000002
DWM_TNP_OPACITY = 0x00000004
DWM_TNP_VISIBLE = 0x00000008
DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010

# Window style modes
WINDOW_MODE_NORMAL = 0		# Normal window with borders, not always on top
WINDOW_MODE_TOPMOST = 1		# Normal window with borders, always on top
WINDOW_MODE_MINIMAL = 2		# Borderless window, always on top

g_user32 = ctypes.windll.user32			# user32 library handle
g_dwmapi_lib = ctypes.windll.dwmapi		# dwmapi library handle
g_exit_code = 0 # Global exit code for the application

g_target_app_match = None # Function to find the target application window
g_source_hwnd = None
g_pip_hwnd = None # Global handle for the PiP window
g_thumb_handle = None
g_pip_padding = 10 # Define your desired padding for the thumbnail within the PiP window
g_current_thumb_rect_in_pip = None # Store the current thumbnail rectangle in the PiP window
g_normal_window_style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE # Normal style for PiP window
g_normal_window_ex_style = 0 # Normal extended style for PiP window (no special flags)
g_minimal_window_style = win32con.WS_POPUP | win32con.WS_VISIBLE # Minimal style for PiP window
g_minimal_window_ex_style = win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST # Minimal extended style for PiP window
g_topmost_window_ex_style = win32con.WS_EX_TOPMOST # Normal style but always on top
g_current_window_mode = WINDOW_MODE_NORMAL # Current window mode

SETTINGS_FILE = os.path.splitext(sys.argv[0])[0] + '.json'
DEBUG_PY = 'debugpy' in sys.modules # or: any('debugpy' in m for m in sys.modules)

# --- Core Functions ---

def _run_find_window(enum_windows_callback):
	try:
		win32gui.EnumWindows(enum_windows_callback, None)
	except pywintypes.error as e:
		# Error 18: "There are no more files."
		# This typically means the enumeration completed successfully (or was stopped).
		# We can safely ignore it if a window was found.
		if e.winerror == 18 and found_hwnd is not None:
			pass # Successfully found and stopped, no actual error
		else:
			# If it's a different error, or error 18 but no window was found, re-raise
			raise e
	except Exception as e:
		# Catch any other unexpected errors during enumeration
		print(f"An unexpected error occurred during EnumWindows: {e}")
		raise

def window_finder_by_title(title_substring):
	"""
	Finds a window by a partial match of its title using EnumWindows.
	Returns the HWND of; 1) the first exact matching window found,
			2) the last partial match found, or 3) None if not found.
	"""
	def window_finder():
		title_substring_l = title_substring.lower() # Normalize to lowercase for case-insensitive comparison
		found_hwnd = None
		def enum_windows_callback(hwnd, lParam):
			nonlocal found_hwnd
			window_title = win32gui.GetWindowText(hwnd)
			# Check if the window is visible and has a title (to filter out hidden/system windows)
			if win32gui.IsWindowVisible(hwnd) and window_title:
				window_title_l = window_title.lower() # Normalize to lowercase for case-insensitive comparison
				if title_substring_l == window_title_l:
					found_hwnd = hwnd
					# class_name = win32gui.GetClassName(found_hwnd)
					# print(f"\t{found_hwnd!r} -> {window_title!r} (Class: {class_name!r})")
					return False # Stop enumeration by returning False
				elif title_substring_l in window_title_l:
					found_hwnd = hwnd
			return True # Continue enumeration
		_run_find_window(enum_windows_callback)
		return found_hwnd
	return window_finder

def window_finder_by_regex(title_match, class_match=None):
	"""
	Finds a window by a regex match of its title and optionally class name using EnumWindows.
	Returns the HWND of; the first matching window found, or None if not found.
	"""
	if isinstance(title_match, str):
		# If title_match is a string, convert it to a regex pattern
		title_match = re.compile(title_match)
	def window_finder():
		found_hwnd = window_title = window_class = None
		def enum_windows_callback(hwnd, lParam):
			nonlocal found_hwnd, window_title, window_class
			window_title = win32gui.GetWindowText(hwnd)
			window_class = win32gui.GetClassName(hwnd)
			# Check if the window is visible and has a title (to filter out hidden/system windows)
			if win32gui.IsWindowVisible(hwnd) and window_title:
				if title_match.match(window_title) and (
						class_match == window_class or not class_match ):
					found_hwnd = hwnd
					return False # Stop enumeration by returning False
			return True # Continue enumeration
		_run_find_window(enum_windows_callback)
		if class_match is None and found_hwnd is not None:
			print(f"Found window: {found_hwnd!r} with title: {window_title!r} and class: {window_class!r}")
		return found_hwnd
	return window_finder


saved_settings_data = None

def save_window_placement(hwnd):
	global saved_settings_data
	# Save the current position of the PiP window to a JSON file
	rect = win32gui.GetWindowRect(hwnd)
	
	settings = {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3],
			 "window_mode": g_current_window_mode }
	if saved_settings_data != settings:
		print(f"Saving window placement: {settings}")
		with open(SETTINGS_FILE, "wt") as f:
			json.dump(settings, f)
		saved_settings_data = settings

def load_window_placement(settings_file=SETTINGS_FILE):
	global saved_settings_data
	try:
		with open(settings_file, "rt") as f:
			return (saved_settings_data := json.load(f))
	except (FileNotFoundError, json.JSONDecodeError):
		# If the file doesn't exist or is invalid, return None
		saved_settings_data = None
		return None


def create_pip_window(x, y, width, height, window_mode, title="PiP View"):
	"""Creates a PiP window with the specified window mode."""

	# Register window class
	wc = win32gui.WNDCLASS()
	wc.lpfnWndProc = pip_window_proc
	wc.lpszClassName = "PiPWindowClass"
	wc.hInstance = win32api.GetModuleHandle(None)
	try:
		win32gui.RegisterClass(wc)
	except win32gui.error as e:
		if e.winerror == 1410: # Class already exists
			pass
		else:
			raise

	# Get the correct style flags for the window mode
	style, ex_style, _, mode_name = get_window_style_flags(window_mode)
	print(f"Creating window with style: {mode_name}")

	hwnd = win32gui.CreateWindowEx(
		ex_style,
		"PiPWindowClass",
		title,
		style,
		x, y, width, height,
		0, 0, win32api.GetModuleHandle(None), None
	)

	return hwnd

# --- Thumbnail Functions ---

def get_inner_client_rect(g_pip_hwnd):
	dest_left, dest_top, dest_right, dest_bottom = win32gui.GetClientRect(g_pip_hwnd)
	return (dest_left+g_pip_padding, dest_top+g_pip_padding,
			dest_right-g_pip_padding, dest_bottom-g_pip_padding)

def calculate_aspect_fit_rect(target_rect, source_width, source_height):
	"""
	Calculates the dimensions of a rectangle that maintains the source aspect ratio
	and fits within a target bounding box. Returns (x_offset, y_offset, width, height).
	The offsets are relative to the top-left of the target_box.
	"""

	target_left, target_top, target_right, target_bottom = target_rect
	target_width = target_right - target_left
	target_height = target_bottom - target_top

	# Calculate scaling factors for both dimensions
	scale_w = target_width / source_width
	scale_h = target_height / source_height

	# Use the minimum scale factor to ensure it fits in both dimensions
	scale = min(scale_w, scale_h)

	# Calculate new scaled dimensions
	new_width = int(source_width * scale)
	new_height = int(source_height * scale)

	# Calculate offsets to center the scaled content within the target bounding box
	x_offset = (target_width - new_width) // 2
	y_offset = (target_height - new_height) // 2

	return (
			target_left+x_offset, target_top+y_offset,
			target_left+x_offset+new_width, target_top+y_offset+new_height
		)

def update_thumbnail_properties(dest_rect):
	"""Updates the properties of the DWM thumbnail."""
	global g_current_thumb_rect_in_pip

	# Adjust to maintain aspect ratio
	source_left, source_top, source_right, source_bottom = win32gui.GetClientRect(g_source_hwnd)
	if source_left >= source_right or source_top >= source_bottom:
		print("Source window dimensions are invalid. Cannot update thumbnail properties.")
		return False
	g_current_thumb_rect_in_pip = dest_rect = calculate_aspect_fit_rect(dest_rect,
			source_right - source_left, source_bottom - source_top)

	# Set thumbnail properties
	props = DWM_THUMBNAIL_PROPERTIES()
	props.dwFlags = DWM_TNP_RECTDESTINATION | DWM_TNP_VISIBLE | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY 
	props.rcDestination = dest_rect
	props.fVisible = True
	props.opacity = 255 # Full opacity

	# props.fSourceClientAreaOnly = False # Show the entire source window, not just the client area (testing)

	result = g_dwmapi_lib.DwmUpdateThumbnailProperties(g_thumb_handle, byref(props))
	if result != 0:
		print(f"Failed to update thumbnail properties: HRESULT {result}")
		return False # Return False for failure
	else:
		win32gui.InvalidateRect(g_pip_hwnd, None, True)

	return True # Return True for success

def set_pip_thumbnail(dest_hwnd, dest_rect):
	"""
	Attempts to set up a DWM thumbnail relationship.
	This function relies on ctypes for DWM functions as pywin32's DWM coverage can vary.
	"""

	global g_thumb_handle, g_dwmapi_lib

	try:
		g_thumb_handle = ctypes.c_void_p() # HTHUMBNAIL handle

		# DwmRegisterThumbnail function signature
		# HRESULT WINAPI DwmRegisterThumbnail(HWND hwndDestination, HWND hwndSource, PTHUMBNAILID pThumbnailId);
		g_dwmapi_lib.DwmRegisterThumbnail.argtypes = [
			ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
		]
		g_dwmapi_lib.DwmRegisterThumbnail.restype = ctypes.c_long

		# DwmUpdateThumbnailProperties function signature
		# HRESULT WINAPI DwmUpdateThumbnailProperties(HTHUMBNAIL hThumbnailId, const DWM_THUMBNAIL_PROPERTIES* ptnProperties);
		g_dwmapi_lib.DwmUpdateThumbnailProperties.argtypes = [
			ctypes.c_void_p, ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES)
		]
		g_dwmapi_lib.DwmUpdateThumbnailProperties.restype = ctypes.c_long

		# Register the thumbnail
		result = g_dwmapi_lib.DwmRegisterThumbnail(dest_hwnd, g_source_hwnd, byref(g_thumb_handle))
		if result != 0: # S_OK is 0
			print(f"Failed to register thumbnail: HRESULT {result}")
			return False # Return False for failure

		if not update_thumbnail_properties(dest_rect):
			g_dwmapi_lib.DwmUnregisterThumbnail(g_thumb_handle) # Clean up
			return False # Return False for failure

		return True # Return True for success

	except Exception as e:
		print(f"Error with DWM thumbnail: {e}")
		print("Note: DWM thumbnails often don't work for true exclusive fullscreen apps.")
		return False # Return False for failure

def bring_window_to_front(hwnd):
	"""Brings a window to the foreground."""
	win32gui.SetForegroundWindow(hwnd)
	# Restore if minimized (optional, sometimes helpful)
	if win32gui.IsIconic(hwnd):
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

def cleanup_thumbnail():
	"""Unregisters a DWM thumbnail."""
	global g_thumb_handle
	if g_thumb_handle:
		g_dwmapi_lib.DwmUnregisterThumbnail(g_thumb_handle)
		g_thumb_handle = None

def check_within_pip_rect(x, y):
	"""Checks if the given coordinates (x, y) are within the PiP window's rectangle."""
	if g_current_thumb_rect_in_pip:
		left, top, right, bottom = g_current_thumb_rect_in_pip
		return left < x < right and top < y < bottom
	return False # If no thumbnail rectangle is set, return False


script_modified_time = None

def check_restart_required():
	#DOC# if DEBUG_PY, then restart the script if the source file changes
	global script_modified_time, g_exit_code
	try:
		current_modified_time = os.path.getmtime(__file__)
		if script_modified_time is None:
			script_modified_time = current_modified_time
		elif current_modified_time != script_modified_time:
			print("Script file has been modified. Restarting...")
			# script_modified_time = current_modified_time	-- FIXME: this is not needed, we just want to restart
			g_exit_code = 2 # Set exit code to indicate restart
			# win32gui.PostQuitMessage(2) # Exit the message loop to restart	-- FIXME
			win32gui.SendMessage(g_pip_hwnd, win32con.WM_CLOSE, 0, 0)
	except Exception as e:
		print(f"Error checking script modification time: {e}")

# --- Main Window Procedure ---

class Timer(NamedTuple):
	"""Simple structure to hold timer information."""
	id: int
	ms: int
	
	_timers = set()

	def start(self):
		"""Sets a timer using the user32 library."""
		g_user32.SetTimer(g_pip_hwnd, self.id, self.ms, None)
		Timer._timers.add(self) # Keep track of active timers
		return self

	def stop(self):
		"""Kills a timer using the user32 library."""
		g_user32.KillTimer(g_pip_hwnd, self.id)
		Timer._timers.discard(self) # Remove from active timers
		return self
	__del__ = stop

	def stop_all():
		"""Stops all active timers."""
		for timer in tuple(Timer._timers):
			timer.stop()
		assert not Timer._timers

MENU_ID_EXIT = 1001
MENU_ID_ABOUT = 1002
MENU_ID_APP_TO_FRONT = 1003
MENU_ID_WINDOW_MODE_NORMAL = 1004
MENU_ID_WINDOW_MODE_TOPMOST = 1005
MENU_ID_WINDOW_MODE_MINIMAL = 1006

TIMER_CHECK_SOURCE = Timer(id=2001, ms=200)  # Check source window every 200 ms
TIMER_SAVE_WIN_POS = Timer(id=2002, ms=1000) # Save window position every second
TIMER_RESTART_CHEK = Timer(id=2003, ms=5000) # Check for script restarts every 5 seconds

def present_context_menu(hwnd, screen_x, screen_y):
	"""Present context menu at specified screen coordinates."""

	hmenu = win32gui.CreatePopupMenu()

	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_APP_TO_FRONT, "Bring Source App to Front")
	win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")
	
	# Add window mode options with current selection checked
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_NORMAL, "Normal Window")
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_TOPMOST, "Always on Top")
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_MINIMAL, "Minimal (Borderless)")
	
	# Check the current window mode
	if g_current_window_mode == WINDOW_MODE_NORMAL:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_NORMAL, win32con.MF_CHECKED)
	elif g_current_window_mode == WINDOW_MODE_TOPMOST:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_TOPMOST, win32con.MF_CHECKED)
	elif g_current_window_mode == WINDOW_MODE_MINIMAL:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_MINIMAL, win32con.MF_CHECKED)
	
	win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_ABOUT, "About...")
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_EXIT, "Exit PiP")

	# Disable "Bring Source App to Front" if no source window is available
	if g_source_hwnd is None:
		win32gui.EnableMenuItem(hmenu, MENU_ID_APP_TO_FRONT, win32con.MF_GRAYED)

	# Display the context menu
	result = win32gui.TrackPopupMenu(hmenu,
		win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
		screen_x, screen_y, 0, hwnd, None
	)
	print(f"Context menu command selected: {result}")
	win32gui.DestroyMenu(hmenu) # Clean up the menu after use
	return True # Indicate the menu was presented

def handle_source_window_status(hwnd):
	global g_source_hwnd

	# TODO: Make sure the window title and class still match the target application.

	if ( g_source_hwnd and win32gui.IsWindow(g_source_hwnd)
				and win32gui.IsWindowVisible(g_source_hwnd) ):
		# Source window is still valid and visible
		return

	if g_source_hwnd:
		print("Source window is no longer valid or visible. Attempting to find it again...")
		g_source_hwnd = None # Reset the source window handle

		# Unregister the current thumbnail if it exists
		cleanup_thumbnail()

		win32gui.InvalidateRect(g_pip_hwnd, None, True)

	# Try to find the source window again
	g_source_hwnd = g_target_app_match()
	if not g_source_hwnd:
		# Source window not found, try again later
		return

	# Re-register the thumbnail with the new source window
	print(f"Found source window: {g_source_hwnd} ({win32gui.GetWindowText(g_source_hwnd)!r})")
	pip_rect = get_inner_client_rect(g_pip_hwnd)
	if not set_pip_thumbnail(g_pip_hwnd, pip_rect):
		print("Failed to set thumbnail for the new source window.")
	else:
		print("Thumbnail successfully updated for the new source window.")

def get_window_style_flags(window_mode):
	"""Returns the style flags for a given window mode."""
	if window_mode == WINDOW_MODE_MINIMAL:
		# Minimal style (borderless, always on top)
		return (g_minimal_window_style, g_minimal_window_ex_style, win32con.HWND_TOPMOST, "Minimal (Borderless, Always on Top)")
	elif window_mode == WINDOW_MODE_TOPMOST:
		# Normal style but always on top
		return (g_normal_window_style, g_topmost_window_ex_style, win32con.HWND_TOPMOST, "Normal (Always on Top)")
	else:  # WINDOW_MODE_NORMAL
		# Normal style, not always on top
		return (g_normal_window_style, g_normal_window_ex_style, win32con.HWND_NOTOPMOST, "Normal")

def set_pip_window_style(window_mode):
	global g_current_window_mode
	
	if window_mode is None:
		# Cycle to the next mode
		window_mode = (g_current_window_mode + 1) % 3
	elif window_mode == g_current_window_mode:
		# No change needed, return early
		return
	
	# Get the style flags for the new mode
	target_style, target_ex_style, insert_after, mode_name = get_window_style_flags(window_mode)
	window_uFlags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED
	
	print(f"Setting window style to: {mode_name}")
	win32gui.SetWindowLong(g_pip_hwnd, win32con.GWL_STYLE, target_style)
	win32gui.SetWindowLong(g_pip_hwnd, win32con.GWL_EXSTYLE, target_ex_style)
	win32gui.SetWindowPos(g_pip_hwnd, insert_after, 0, 0, 0, 0, window_uFlags)
	
	# Update the global current window mode
	g_current_window_mode = window_mode

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

def pip_window_proc(hwnd, msg, wparam, lparam):
	"""Window procedure for the PiP window."""

	if msg == win32con.WM_NCHITTEST:
		# Handle non-client area hit testing
		
		# First get the default hit test result to preserve normal window behaviour
		default_result = win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
		
		# If it's a border or corner for resizing, allow normal behavior
		if default_result in (win32con.HTLEFT, win32con.HTRIGHT, win32con.HTTOP, win32con.HTBOTTOM,
							  win32con.HTTOPLEFT, win32con.HTTOPRIGHT, win32con.HTBOTTOMLEFT, 
							  win32con.HTBOTTOMRIGHT):
			return default_result
		
		# For client area, check if we should customize behavior
		if default_result == win32con.HTCLIENT:
			screen_x, screen_y = win32gui.ScreenToClient(hwnd, split_lparam_pos(lparam))
			
			# If mouse is over the thumbnail area, pass through clicks
			if check_within_pip_rect(screen_x, screen_y):
				return win32con.HTCLIENT
			
			# If mouse is in the gap area around the thumbnail, enable dragging
			return win32con.HTCAPTION
		
		# For all other areas (title bar, etc.), use default behavior
		return default_result

	elif msg == win32con.WM_SETCURSOR:
		if win32api.LOWORD(lparam) == win32con.HTCLIENT:
			# Set the cursor to a hand icon when hovering over the PiP window
			win32gui.SetCursor(win32gui.LoadCursor(0, win32con.IDC_HAND))
			return 0	# indicate we handled the message
			# NOTE: fallthrough would set default cursor

	elif msg == win32con.WM_TIMER:
		# Handle periodic checks for the source window
		if wparam == TIMER_CHECK_SOURCE.id:
			handle_source_window_status(hwnd)
			return 0 # indicate we handled the message
		elif wparam == TIMER_SAVE_WIN_POS.id:
			# Save the current position of the PiP window
			save_window_placement(hwnd)
			return 0 # indicate we handled the message
		elif wparam == TIMER_RESTART_CHEK.id:
			# Check if the script file has been modified (for debugpy)
			check_restart_required()
			return 0
		# NOTE: do not call DefWindowProc for handled commands

	elif msg == win32con.WM_PAINT:
		# Handle paint messages if needed (e.g., custom drawing)
		# ps = win32gui.PAINTSTRUCT()
		hdc, ps = win32gui.BeginPaint(hwnd) # Get DC for painting

		# 1. Draw the background of the PiP window
		background_color = win32api.RGB(60, 60, 60) # Dark gray background
		client_rect = win32gui.GetClientRect(hwnd)
		fill_brush = win32gui.CreateSolidBrush(background_color) # Dark gray background
		win32gui.FillRect(hdc, client_rect, fill_brush)
		win32gui.DeleteObject(fill_brush)

		# 2. Draw the red box around the thumbnail area
		# Create a red pen (for outline)
		red_pen = win32gui.CreatePen(win32con.PS_SOLID, 2, win32api.RGB(255, 0, 0)) # 2 pixels thick
		old_pen = win32gui.SelectObject(hdc, red_pen) # Select it into the DC
		# Create a null brush (for no fill)
		null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
		old_brush = win32gui.SelectObject(hdc, null_brush) # Select it into the DC
		# Draw the rectangle
		box_left, box_top, box_right, box_bottom = g_current_thumb_rect_in_pip
		win32gui.Rectangle(hdc, box_left-1, box_top-1, box_right+2, box_bottom+2)

		if not g_source_hwnd:
			# If no source window is available, draw missing application indicator
			win32gui.MoveToEx(hdc, box_left, box_top)
			win32gui.LineTo(hdc, box_right, box_bottom)
			win32gui.MoveToEx(hdc, box_left, box_bottom)
			win32gui.LineTo(hdc, box_right, box_top)

		# 	message = "Not Found"		-- TODO
		# 	text_color = win32api.RGB(255, 255, 255)
		# 	win32gui.SetTextColor(hdc, text_color)
		# 	win32gui.SetBkMode(hdc, win32con.TRANSPARENT) # Transparent background
		# 	# Draw the text in the center of the PiP window
		# 	client_width = client_rect[2] - client_rect[0]
		# 	client_height = client_rect[3] - client_rect[1]
		# 	text_extent = win32gui.GetTextExtent(hdc, message)
		# 	text_x = (client_width - text_extent[0]) // 2
		# 	text_y = (client_height - text_extent[1]) // 2
		# 	win32gui.TextOut(hdc, text_x, text_y, message)

		# Restore original GDI objects
		win32gui.SelectObject(hdc, old_pen)
		win32gui.DeleteObject(red_pen)
		win32gui.SelectObject(hdc, old_brush) # NULL_BRUSH doesn't need deleting

		print(f"Drawing thumbnail box at: {box_left}, {box_top}, {box_right}, {box_bottom}")

		# NOTE: DWM thumbnails are rendered *on top* of anything you draw.
		# So, drawing a background or border *first* is correct.

		win32gui.EndPaint(hwnd, ps) # Release DC
		return 0 # calling DefWindowProc is not necessary

	elif msg == win32con.WM_SIZE:
		# Window has been resized.
		# wparam: Type of resizing (SIZE_MAXIMIZED, SIZE_MINIMIZED, SIZE_RESTORED, etc.)
		# lparam: LOWORD is new client width, HIWORD is new client height
		new_client_width, new_client_height = split_lparam_pos(lparam)
		print(f"PiP window resized to client dimensions: {new_client_width}x{new_client_height}")

		if g_thumb_handle:
			# Recalculate thumbnail's destination rectangle based on new client size
			thumb_draw_top = g_pip_padding
			thumb_draw_left = g_pip_padding
			thumb_draw_right = max(g_pip_padding, new_client_width - g_pip_padding)
			thumb_draw_bottom = max(g_pip_padding, new_client_height - g_pip_padding)
			thumb_draw_rect = (thumb_draw_left, thumb_draw_top, thumb_draw_right, thumb_draw_bottom)
			update_thumbnail_properties(thumb_draw_rect)

		TIMER_SAVE_WIN_POS.start() # Restart the timer to save window position
		return 0	# do not call DefWindowProc
	
	elif msg == win32con.WM_MOVE:
		# Window has been moved.
		# lparam: LOWORD is new x position, HIWORD is new y position
		new_x, new_y = split_lparam_pos(lparam)
		print(f"PiP window moved to: {new_x}, {new_y}")

		TIMER_SAVE_WIN_POS.start()
		# NOTE: fall through to run the default window procedure

	elif msg == win32con.WM_LBUTTONDOWN:
		click_x, click_y = split_lparam_pos(lparam)
		if check_within_pip_rect(click_x, click_y):
			# Left-click to bring the source app to front
			bring_window_to_front(g_source_hwnd)
		# NOTE: fall through for default processing

	elif msg == win32con.WM_RBUTTONDOWN:
		# Right-click to close the PiP window
		screen_x, screen_y = win32gui.ClientToScreen(hwnd, split_lparam_pos(lparam))
		print(f"Right-click at screen coordinates: {screen_x}, {screen_y}")
		present_context_menu(hwnd, screen_x, screen_y)
		# NOTE: fall through for default processing
	elif msg == win32con.WM_CONTEXTMENU:
		# Get mouse coordinates in screen coordinates for TrackPopupMenuEx
		if lparam == -1: # screen_x == 65535 and screen_y == 65535:
			# If lparam is -1, use the current mouse position
			screen_x, screen_y = win32api.GetCursorPos()
		else:
			screen_x, screen_y = split_lparam_pos(lparam)
		print(f"Context-menu at screen coordinates: {screen_x}, {screen_y}")
		present_context_menu(hwnd, screen_x, screen_y)
		# NOTE: fall through for default processing

	elif msg == win32con.WM_COMMAND:
		# Handle menu commands
		cmd_id = win32api.LOWORD(wparam)
		if cmd_id == MENU_ID_EXIT:
			win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
			return 0
		elif cmd_id == MENU_ID_ABOUT:
			# Show an about dialog or message box
			win32gui.MessageBox(hwnd, "PiP View Application\nVersion 1.0", "About PiP View", win32con.MB_OK)
			return 0
		elif cmd_id == MENU_ID_APP_TO_FRONT:
			# Bring the source application to the front
			if g_source_hwnd:
				bring_window_to_front(g_source_hwnd)
			else:
				win32gui.MessageBox(hwnd, "No source application found.", "Error", win32con.MB_OK | win32con.MB_ICONERROR)
			return 0
		elif cmd_id == MENU_ID_WINDOW_MODE_NORMAL:
			# Set window to normal mode
			set_pip_window_style(WINDOW_MODE_NORMAL)
			return 0
		elif cmd_id == MENU_ID_WINDOW_MODE_TOPMOST:
			# Set window to always on top mode
			set_pip_window_style(WINDOW_MODE_TOPMOST)
			return 0
		elif cmd_id == MENU_ID_WINDOW_MODE_MINIMAL:
			# Set window to minimal mode
			set_pip_window_style(WINDOW_MODE_MINIMAL)
			return 0
		else:
			print(f"Unhandled command ID: {cmd_id}")
		# NOTE: do not call DefWindowProc for handled commands

	elif msg == win32con.WM_CLOSE:
		# Handle close message
		save_window_placement(hwnd)
		win32gui.DestroyWindow(hwnd)
		# return 0
	elif msg == win32con.WM_DESTROY:
		global g_pip_hwnd
		Timer.stop_all()
		win32gui.PostQuitMessage(0)
		g_pip_hwnd = None
		# return 0

	return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# --- Main Logic ---

def setup():
	global g_target_app_match, g_source_hwnd, g_pip_hwnd, g_current_thumb_rect_in_pip, g_current_window_mode

	# target_app_title = "Sky"
	g_target_app_match = window_finder_by_regex(r'^Sky$', 'TgcMainWindow')

	print(f"Attempting to find application...")
	g_source_hwnd = g_target_app_match()

	if not g_source_hwnd:
		print(f"Could not find target application. Make sure it's running.")
	else:
		print(f"Found window '{win32gui.GetWindowText(g_source_hwnd)}' with HWND: {g_source_hwnd}")

	# Define PiP window size and position (e.g., bottom right of main monitor)
	if (settings := load_window_placement(SETTINGS_FILE)):
		#- Load saved position from JSON file
		pip_x = settings["left"]
		pip_y = settings["top"]
		pip_width = settings["right"] - settings["left"]
		pip_height = settings["bottom"] - settings["top"]
		window_mode = settings.get("window_mode", WINDOW_MODE_NORMAL)
	else:
		#- Default position if no saved settings
		screen_width = GetSystemMetrics(win32con.SM_CXSCREEN)
		screen_height = GetSystemMetrics(win32con.SM_CYSCREEN)
		print(f"Screen dimensions: {screen_width}x{screen_height}")
		pip_width = 300
		pip_height = 200
		pip_x = screen_width - pip_width - 20 # 20px from right edge
		pip_y = screen_height - pip_height - 20 # 20px from bottom edge
		window_mode = WINDOW_MODE_NORMAL

	# Set the initial window mode
	g_current_window_mode = window_mode

	print(f"Creating PiP window at {pip_x}x{pip_y}+{pip_width}x{pip_height}...")
	g_pip_hwnd = create_pip_window(pip_x, pip_y, pip_width, pip_height, window_mode)
	if not g_pip_hwnd:
		print("Failed to create PiP window.")
		exit(1)
	else:
		print(f"PiP window created with HWND: {g_pip_hwnd}")

	# Get the client area dimensions of the destination (PiP) window
	g_current_thumb_rect_in_pip = pip_rect = get_inner_client_rect(g_pip_hwnd)
	print(f"PiP client area: {pip_rect}")

	if g_source_hwnd and not set_pip_thumbnail(g_pip_hwnd, pip_rect):
		print("Failed to get DWM thumbnail. The target application might be in true exclusive fullscreen mode.")
		win32gui.DestroyWindow(g_pip_hwnd) # Clean up PiP window
		exit(1)

	print("DWM thumbnail successfully registered. The PiP window should now show the live view.")
	print("Click the PiP window to bring the source app to front (this feature is conceptual and needs more event handling).")
	print("Right-click to close the PiP window and clean up.")

	# Set a timer to periodically check the source window
	TIMER_CHECK_SOURCE.start() # Start the timer

	if not DEBUG_PY:
		# Set a timer to periodically check for script updates
		print("Running in production mode.")
		TIMER_RESTART_CHEK.start()

def run():
	try:
		# This is the main message loop
		win32gui.PumpMessages()
	except Exception as e:
		print(f"Error in message loop: {e}")
	finally:
		print("Cleaning up...")
		cleanup_thumbnail()
		if g_pip_hwnd: # Stop the timer
			Timer.stop_all()
			save_window_placement(g_pip_hwnd) # Save the current position
			win32gui.DestroyWindow(g_pip_hwnd) # Clean up PiP window
		print("Cleanup complete.")
		exit(g_exit_code)

def run_loop():
	import time
	result = 1
	while result:
		try:
			print("Running in production mode. Press Ctrl+C to exit.")
			result = subprocess.run([sys.executable, __file__, '--run']).returncode
		except KeyboardInterrupt:
			print("Exiting due to keyboard interrupt.")
			break
		except Exception as e:
			print(f"An error occurred: {e}")
			print("Exiting...")
			break
		time.sleep(1)

if __name__ == "__main__":
	if DEBUG_PY or len(sys.argv) > 1 and sys.argv[1] == '--run':
		# Don't use the loop if running in debug mode
		print("Running in debug mode.")
		setup()
		run()
		assert False, "The script should not reach this point."
	else:
		run_loop()
