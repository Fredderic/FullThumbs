"""
Handles the main window creation and management for the FullThumbs application.
"""

import win32gui, win32con, win32api

from .constants import PIP_PADDING, WINDOW_MODE_MINIMAL, WINDOW_MODE_MINIMAL_TEXT, WINDOW_MODE_NORMAL, WINDOW_MODE_NORMAL_TEXT, WINDOW_MODE_TOPMOST, WINDOW_MODE_TOPMOST_TEXT
from .win_api import Timer, split_lparam_pos, get_inner_client_rect
from .window_styles import get_window_style_flags
from .settings import save_window_placement

# Global flag to track if git update check is running
_git_update_checking = False

def check_for_git_updates():
	"""Check if git updates are available and exit with code 2 if they are.
	Uses background thread to avoid blocking the UI.
	"""
	import threading
	from . import main
	
	global _git_update_checking
	
	# Check if an update check is already running
	if _git_update_checking:
		print("Git update check already in progress, skipping...")
		return
	
	def _background_update_check():
		"""Background function to perform git operations."""
		import subprocess
		import os
		
		global _git_update_checking
		
		try:
			_git_update_checking = True
			repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
			
			print("Checking for git updates (background)...")
			
			# Use timeout for git operations (10 seconds max each)
			timeout_seconds = 10
			
			# Check if we're behind the remote
			subprocess.run(['git', 'fetch'], cwd=repo_dir, check=True, 
						  capture_output=True, timeout=timeout_seconds)
			
			result = subprocess.run(
				['git', 'rev-list', '--count', 'HEAD..@{u}'],
				cwd=repo_dir,
				capture_output=True,
				text=True,
				check=True,
				timeout=timeout_seconds
			)
			
			commits_behind = int(result.stdout.strip())
			if commits_behind > 0:
				print(f"Found {commits_behind} new commit(s). Requesting restart for update...")
				main.g_exit_code = 2  # Signal update restart needed
				win32gui.PostQuitMessage(2)
			else:
				print("Application is up to date.")
				
		except subprocess.TimeoutExpired:
			print("Git update check timed out (network might be slow). Skipping this check.")
		except subprocess.CalledProcessError as e:
			print(f"Git operation failed: {e}")
		except Exception as e:
			print(f"Error checking for git updates: {e}")
		finally:
			_git_update_checking = False
	
	# Start the background check
	thread = threading.Thread(target=_background_update_check, daemon=True)
	thread.start()

# -------

def get_default_window_area():
	"""Get default window area for PiP."""
	screen_width = GetSystemMetrics(win32con.SM_CXSCREEN)
	screen_height = GetSystemMetrics(win32con.SM_CYSCREEN)
	print(f"Screen dimensions: {screen_width}x{screen_height}")
	pip_width = 300
	pip_height = 200
	pip_x = screen_width - pip_width - 20 # 20px from right edge
	pip_y = screen_height - pip_height - 20 # 20px from bottom edge
	return pip_x, pip_y, pip_width, pip_height

# -------

# Menu IDs
MENU_ID_EXIT = 1001
MENU_ID_ABOUT = 1002
MENU_ID_APP_TO_FRONT = 1003
MENU_ID_WINDOW_MODE_NORMAL = 1004
MENU_ID_WINDOW_MODE_TOPMOST = 1005
MENU_ID_WINDOW_MODE_MINIMAL = 1006

TIMER_CHECK_SOURCE = Timer(id=2001, ms=200)  # Check source window every 200 ms
TIMER_SAVE_WIN_POS = Timer(id=2002, ms=1000) # Save window position every second
TIMER_UPDATE_CHECK = Timer(id=2003, ms=None) # Update check timer with configurable interval

def present_context_menu(hwnd, screen_x, screen_y):
	"""Present context menu at specified screen coordinates."""

	from src.main import g_current_window_mode, g_source_hwnd

	hmenu = win32gui.CreatePopupMenu()

	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_APP_TO_FRONT, "Bring Source App to Front")
	win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")
	
	# Add window mode options with current selection checked
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_NORMAL, WINDOW_MODE_NORMAL_TEXT)
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_TOPMOST, WINDOW_MODE_TOPMOST_TEXT)
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_MINIMAL, WINDOW_MODE_MINIMAL_TEXT)
	
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

def pip_window_proc(hwnd, msg, wparam, lparam):
	"""Window procedure for the PiP window."""

	from src import main

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
		if main.g_thumbnail and default_result == win32con.HTCLIENT:
			screen_x, screen_y = win32gui.ScreenToClient(hwnd, split_lparam_pos(lparam))
			
			# If mouse is over the thumbnail area, pass through clicks
			if main.g_thumbnail.check_within_thumbnail_rect(screen_x, screen_y):
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
		elif wparam == TIMER_UPDATE_CHECK.id:
			# Check for git updates if enabled
			check_for_git_updates()
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

		if main.g_thumbnail:
			# 2. Draw the red box around the thumbnail area
			# Create a red pen (for outline)
			red_pen = win32gui.CreatePen(win32con.PS_SOLID, 2, win32api.RGB(255, 0, 0)) # 2 pixels thick
			old_pen = win32gui.SelectObject(hdc, red_pen) # Select it into the DC
			# Create a null brush (for no fill)
			null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
			old_brush = win32gui.SelectObject(hdc, null_brush) # Select it into the DC
			# Draw the rectangle
			box_left, box_top, box_right, box_bottom = main.g_thumbnail.current_thumb_rect
			win32gui.Rectangle(hdc, box_left-1, box_top-1, box_right+2, box_bottom+2)

		else:
			box_left, box_top, width, height = get_default_window_area()
			box_right = box_left + width
			box_bottom = box_top + height
			# If no source window is available, draw missing application indicator
			win32gui.Rectangle(hdc, box_left-1, box_top-1, box_right+2, box_bottom+2)
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

		if main.g_thumbnail:
			# Recalculate thumbnail's destination rectangle based on new client size
			thumb_draw_top = PIP_PADDING
			thumb_draw_left = PIP_PADDING
			thumb_draw_right = max(PIP_PADDING, new_client_width - PIP_PADDING)
			thumb_draw_bottom = max(PIP_PADDING, new_client_height - PIP_PADDING)
			thumb_draw_rect = (thumb_draw_left, thumb_draw_top, thumb_draw_right, thumb_draw_bottom)
			main.g_thumbnail.update_thumbnail_rect(thumb_draw_rect)

		TIMER_SAVE_WIN_POS.start(hwnd) # Restart the timer to save window position
		return 0	# do not call DefWindowProc
	
	elif msg == win32con.WM_MOVE:
		# Window has been moved.
		# lparam: LOWORD is new x position, HIWORD is new y position
		new_x, new_y = split_lparam_pos(lparam)
		print(f"PiP window moved to: {new_x}, {new_y}")

		TIMER_SAVE_WIN_POS.start(hwnd)
		# NOTE: fall through to run the default window procedure

	elif msg == win32con.WM_LBUTTONDOWN:
		click_x, click_y = split_lparam_pos(lparam)
		if check_within_pip_rect(click_x, click_y):
			# Left-click to bring the source app to front
			bring_window_to_front(main.g_source_hwnd)
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
			from .version import get_version_info
			info = get_version_info()
			about_text = (
				f"FullThumbs PiP Viewer\n"
				f"Version: {info['version']}\n"
				f"Commit: {info['commit_hash_short']}\n"
				f"Branch: {info['branch']}\n"
				f"Built: {info['commit_date'][:10]}"  # Just the date part
			)
			win32gui.MessageBox(hwnd, about_text, "About FullThumbs", win32con.MB_OK)
			return 0
		elif cmd_id == MENU_ID_APP_TO_FRONT:
			# Bring the source application to the front
			if main.g_source_hwnd:
				bring_window_to_front(main.g_source_hwnd)
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
		Timer.stop_all(hwnd)
		win32gui.PostQuitMessage(0)
		main.g_pip_hwnd = None
		# return 0

	return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# -------

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

def bring_window_to_front(hwnd):
	"""Brings a window to the foreground."""
	win32gui.SetForegroundWindow(hwnd)
	# Restore if minimized (optional, sometimes helpful)
	if win32gui.IsIconic(hwnd):
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

def handle_source_window_status(hwnd):
	# global g_source_hwnd
	from src import main

	# TODO: Make sure the window title and class still match the target application.

	if ( main.g_source_hwnd and win32gui.IsWindow(main.g_source_hwnd)
				and win32gui.IsWindowVisible(main.g_source_hwnd) ):
		# Source window is still valid and visible
		return

	if main.g_source_hwnd:
		print("Source window is no longer valid or visible. Attempting to find it again...")
		main.g_source_hwnd = None # Reset the source window handle

		# Unregister the current thumbnail if it exists
		main.g_thumbnail.cleanup_thumbnail()

		win32gui.InvalidateRect(main.g_pip_hwnd, None, True)

	# Try to find the source window again
	main.g_source_hwnd = main.g_target_app_match()
	if not main.g_source_hwnd:
		# Source window not found, try again later
		return

	# Re-register the thumbnail with the new source window
	print(f"Found source window: {main.g_source_hwnd} ({win32gui.GetWindowText(main.g_source_hwnd)!r})")
	pip_rect = get_inner_client_rect(main.g_pip_hwnd)
	main.g_thumbnail.update_thumbnail_rect(pip_rect)
	# if not g_thumbnail.update_thumbnail_rect(pip_rect):
	# 	print("Failed to set thumbnail for the new source window.")
	# else:
	# 	print("Thumbnail successfully updated for the new source window.")

WINDOW_U_FLAGS = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED

def set_pip_window_style(window_mode):
	from src import main
	
	if window_mode is None:
		# Cycle to the next mode
		window_mode = (main.g_current_window_mode + 1) % 3
	elif window_mode == main.g_current_window_mode:
		# No change needed, return early
		return
	
	# Get the style flags for the new mode
	target_style, target_ex_style, insert_after, mode_name = get_window_style_flags(window_mode)
	
	print(f"Setting window style to: {mode_name}")
	win32gui.SetWindowLong(main.g_pip_hwnd, win32con.GWL_STYLE, target_style)
	win32gui.SetWindowLong(main.g_pip_hwnd, win32con.GWL_EXSTYLE, target_ex_style)
	win32gui.SetWindowPos(main.g_pip_hwnd, insert_after, 0, 0, 0, 0, WINDOW_U_FLAGS)
	
	# Update the global current window mode
	main.g_current_window_mode = window_mode

