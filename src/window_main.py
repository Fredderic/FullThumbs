"""
Handles the main window creation and management for the FullThumbs application.
"""

from types import SimpleNamespace
from typing import Literal

import win32gui, win32con, win32api

from .constants import ( PIP_MIN_CLIENT_SIZE, PIP_PADDING, WINDOW_MODE_MINIMAL,
        WINDOW_MODE_MINIMAL_TEXT, WINDOW_MODE_NORMAL, WINDOW_MODE_NORMAL_TEXT,
        WINDOW_MODE_TOPMOST, WINDOW_MODE_TOPMOST_TEXT )
from .win_api import Timer, split_lparam_pos, get_inner_client_rect, track_mouse_leave
from .window_styles import get_window_style_flags
from .settings import save_window_placement

# Global flag to track if git update check is running
_git_update_checking = False
_last_update_check_found = None # None = never checked, True/False = result of the last check

def check_for_git_updates():
	"""Check if git updates are available (background thread). Only records the result for
	display -- does not restart. Use request_restart() to actually act on a found update.
	"""
	import threading
	
	global _git_update_checking, _last_update_check_found
	
	# Check if an update check is already running
	if _git_update_checking:
		print("Git update check already in progress, skipping...")
		return
	
	def _background_update_check():
		"""Background function to perform git operations."""
		import subprocess
		import os
		
		global _git_update_checking, _last_update_check_found
		
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
			_last_update_check_found = commits_behind > 0
			if commits_behind > 0:
				print(f"Found {commits_behind} new commit(s). Use 'Restart Thumbnail' from the context menu to install.")
			else:
				print("Application is up to date.")
				
		except subprocess.TimeoutExpired:
			print("Git update check timed out (network might be slow). Skipping this check.")
		except subprocess.CalledProcessError as e:
			print(f"Git operation failed: {e}")
		except Exception as e:
			print(f"Error checking for updates: {e}")
		finally:
			_git_update_checking = False
	
	# Start the background check
	thread = threading.Thread(target=_background_update_check, daemon=True)
	thread.start()

def request_restart(hwnd):
	"""Ask the supervising full-thumbs.py loop to restart (and apply any pending update).

	Restarts are never automatic -- this must be explicitly invoked. Always quits the app;
	if nothing is supervising us (e.g. running main.py directly, or via the debugger without
	--debug-loop), that just means nothing relaunches it afterwards.
	"""
	from . import main
	if not main.g_supervised:
		print("No supervisor is watching for a restart request -- quitting without a relaunch.")
	print("Requesting restart...")
	main.g_exit_code = 2  # Signal update restart needed
	win32gui.PostQuitMessage(2)

# -------

def get_default_window_area():
	"""Get default window area for PiP."""
	screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
	screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
	print(f"Screen dimensions: {screen_width}x{screen_height}")
	pip_width = 300
	pip_height = 200
	pip_x = screen_width - pip_width - 2*PIP_PADDING
	pip_y = screen_height - pip_height - 2*PIP_PADDING
	return pip_x, pip_y, pip_width, pip_height

# -------

COLORS = SimpleNamespace(
	RED			= win32api.RGB(255, 0, 0),
	BLUE		= win32api.RGB(0, 0, 255),
	WHITE		= win32api.RGB(255, 255, 255),
	DARK_GREY	= win32api.RGB(60, 60, 60),
	BLACK		= win32api.RGB(0, 0, 0)
)

THEME = SimpleNamespace(
	BACKGROUND	= COLORS.DARK_GREY,
	TEXT		= COLORS.WHITE,
	LINK		= COLORS.BLUE,
	TMB_MARKER	= COLORS.BLACK,
	TMB_HOVER	= COLORS.RED,
	TMB_ON_TOP	= COLORS.BLUE,
)

# -------

# Menu IDs
MENU_ID_EXIT = 1001
MENU_ID_ABOUT = 1002
MENU_ID_APP_TO_FRONT = 1003
MENU_ID_WINDOW_MODE_NORMAL = 1004
MENU_ID_WINDOW_MODE_TOPMOST = 1005
MENU_ID_WINDOW_MODE_MINIMAL = 1006
MENU_ID_CHECK_UPDATES = 1007
MENU_ID_RESTART_THUMBNAIL = 1008

TIMER_CHECK_SOURCE = Timer(id=2001, ms=200)  # Check source window every 200 ms
TIMER_SAVE_WIN_POS = Timer(id=2002, ms=1000) # Save window position every second
TIMER_UPDATE_CHECK = Timer(id=2003, ms=None) # Update check timer with configurable interval

_timer_handlers = dict()
def set_timer_handler(timer):
	def wrapper(func):
		_timer_handlers[timer.id] = func
		return func
	return wrapper

@set_timer_handler(TIMER_SAVE_WIN_POS)
def save_window_placement_handler(hwnd):
	# Wraps save_window_placement() to also stop the timer afterward.
	save_window_placement(hwnd)
	TIMER_SAVE_WIN_POS.stop() # One-shot: only restarted by WM_MOVE/WM_SIZE

@set_timer_handler(TIMER_UPDATE_CHECK)
def update_check_handler(hwnd):
	# Check for git updates if enabled
	from . import main
	if getattr(main, 'g_debug_simulate_update', False):
		# Debug mode: simulate finding updates and immediately request the restart
		# (this deliberately bypasses the normal "never automatic" rule, since it's
		# only used to test full-thumbs.py's own supervised restart loop)
		print("🐛 Debug: Simulating 'updates found' - requesting restart...")
		request_restart(hwnd)
	else:
		check_for_git_updates()


_context_menu_target_hwnd = None # Source hwnd of the thumbnail under the cursor at last right-click

def present_context_menu(hwnd, screen_x, screen_y):
	"""Present context menu at specified screen coordinates."""
	global _context_menu_target_hwnd

	from . import main

	client_x, client_y = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
	target_thumb = find_thumbnail_at(main.g_thumbnail_slots, client_x, client_y)
	_context_menu_target_hwnd = target_thumb.source_hwnd if target_thumb else None
	# NOTE: not using set_hovered_thumb() here -- the popup can cause a spurious WM_MOUSELEAVE,
	# so the border colour check in WM_PAINT also checks _context_menu_target_hwnd directly.
	if target_thumb and target_thumb is not _hovered_thumb and target_thumb.current_thumb_rect:
		left, top, right, bottom = target_thumb.current_thumb_rect
		win32gui.InvalidateRect(hwnd, (left-2, top-2, right+2, bottom+2), False)

	hmenu = win32gui.CreatePopupMenu()

	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_APP_TO_FRONT, "Bring Source App to Front")
	win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")
	
	# Add window mode options with current selection checked
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_NORMAL, WINDOW_MODE_NORMAL_TEXT)
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_TOPMOST, WINDOW_MODE_TOPMOST_TEXT)
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_WINDOW_MODE_MINIMAL, WINDOW_MODE_MINIMAL_TEXT)
	
	# Check the current window mode
	if main.g_current_window_mode == WINDOW_MODE_NORMAL:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_NORMAL, win32con.MF_CHECKED)
	elif main.g_current_window_mode == WINDOW_MODE_TOPMOST:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_TOPMOST, win32con.MF_CHECKED)
	elif main.g_current_window_mode == WINDOW_MODE_MINIMAL:
		win32gui.CheckMenuItem(hmenu, MENU_ID_WINDOW_MODE_MINIMAL, win32con.MF_CHECKED)
	
	win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")
	
	# "Check for Updates" is always available (it's just a read-only fetch); label reflects the last check
	if _last_update_check_found:
		update_menu_text = "Update Found - Restart to Install"
	elif _last_update_check_found is False:
		update_menu_text = "Check for Updates (up to date)"
	else:
		update_menu_text = "Check for Updates"
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_CHECK_UPDATES, update_menu_text)

	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_RESTART_THUMBNAIL,
		"Restart Thumbnail" if main.g_supervised else "Restart Thumbnail (unsupervised)")
	
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_ABOUT, "About...")
	win32gui.AppendMenu(hmenu, win32con.MF_STRING, MENU_ID_EXIT, "Exit PiP")

	# Disable "Bring Source App to Front" if no thumbnail was under the cursor
	if _context_menu_target_hwnd is None:
		win32gui.EnableMenuItem(hmenu, MENU_ID_APP_TO_FRONT, win32con.MF_GRAYED)

	# Use TPM_RETURNCMD so the selection is available synchronously here -- without it,
	# TrackPopupMenu *posts* WM_COMMAND, which would arrive after we clear the target below.
	cmd_id = win32gui.TrackPopupMenu(hmenu,
		win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
		screen_x, screen_y, 0, hwnd, None
	)
	print(f"Context menu command selected: {cmd_id}")
	win32gui.DestroyMenu(hmenu) # Clean up the menu after use

	if cmd_id:
		win32gui.SendMessage(hwnd, win32con.WM_COMMAND, win32api.MAKELONG(cmd_id, 0), 0)

	_context_menu_target_hwnd = None
	if target_thumb and target_thumb is not _hovered_thumb and target_thumb.current_thumb_rect:
		# Clear the sticky highlight (no-op if the mouse is now genuinely hovering it)
		left, top, right, bottom = target_thumb.current_thumb_rect
		win32gui.InvalidateRect(hwnd, (left-2, top-2, right+2, bottom+2), False)

	# The menu blocked the message loop; refresh hover now the mouse may have moved on
	cursor_x, cursor_y = win32gui.ScreenToClient(hwnd, win32gui.GetCursorPos())
	set_hovered_thumb(hwnd, find_thumbnail_at(g_thumbnail_slots, cursor_x, cursor_y))

	return True # Indicate the menu was presented

# -------

def show_about_dialog(parent_hwnd, about_text):
	"""Show an about dialog with selectable text and clickable GitHub link."""
	import webbrowser
	
	# Dialog dimensions and control IDs
	DLG_WIDTH = 400
	MARGIN = 10
	BUTTON_HEIGHT = 25
	BUTTON_WIDTH = 75
	LINK_HEIGHT = 20
	TITLE_BAR_HEIGHT = 30  # Approximate space for title bar and frame
	
	EDIT_CONTROL_ID = 1001
	OK_BUTTON_ID = 1002
	COPY_BUTTON_ID = 1003
	GITHUB_LINK_ID = 1004

	def calculate_text_extents(texts):
		# Get a device context to measure text
		desktop_dc = win32gui.GetDC(0)
		
		# Create the font we'll use in the dialog
		dialog_font = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT
		old_font = None
		if dialog_font:
			old_font = win32gui.SelectObject(desktop_dc, dialog_font)
		
		extents = []

		for text in texts:
			# Actually measure the text using GetTextExtentPoint32 for each line
			total_height = maximum_width = 0
			for line in text.split('\n'):
				text_size = win32gui.GetTextExtentPoint32(desktop_dc, line.strip() or ' ')
				maximum_width = max(maximum_width, text_size[0])
				total_height += text_size[1]
			extents.append( (maximum_width, total_height) )
		
		# Clean up
		if old_font:
			win32gui.SelectObject(desktop_dc, old_font)
		win32gui.ReleaseDC(0, desktop_dc)
		
		return extents
	
	# Calculate text extents for both about text and link text
	link_text = "Visit GitHub Repository"
	text_extents = calculate_text_extents([about_text, link_text])
	about_text_width, about_text_height = text_extents[0]
	link_text_width, link_text_height = text_extents[1]
	
	# Add padding for edit widget's border and internal padding
	about_text_height += 10  # Add padding for readability and widget borders
	
	# Calculate minimum required dialog height
	min_content_height = about_text_height + 4*MARGIN + BUTTON_HEIGHT + link_text_height
	min_dialog_height = min_content_height + TITLE_BAR_HEIGHT + 10
	
	# Use calculated height, but ensure a reasonable minimum
	DLG_HEIGHT = max(min_dialog_height, 200)  # At least 200px tall
	
	# Calculate dialog position (center on parent)
	if parent_hwnd:
		parent_rect = win32gui.GetWindowRect(parent_hwnd)
		parent_center_x = (parent_rect[0] + parent_rect[2]) // 2
		parent_center_y = (parent_rect[1] + parent_rect[3]) // 2
		
		# Find which monitor the parent window is on
		monitor_info = win32api.MonitorFromWindow(parent_hwnd, win32con.MONITOR_DEFAULTTONEAREST)
		monitor_info_ex = win32api.GetMonitorInfo(monitor_info)
		monitor_rect = monitor_info_ex['Monitor']  # (left, top, right, bottom)
		
		# Use the monitor bounds for clipping
		monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_rect
	else:
		# No parent window - use primary monitor center
		parent_center_x = win32api.GetSystemMetrics(win32con.SM_CXSCREEN) // 2
		parent_center_y = win32api.GetSystemMetrics(win32con.SM_CYSCREEN) // 2
		
		# Use primary monitor bounds
		monitor_left = 0
		monitor_top = 0
		monitor_right = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
		monitor_bottom = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
	
	dialog_x = parent_center_x - DLG_WIDTH // 2
	dialog_y = parent_center_y - DLG_HEIGHT // 2
	
	# Ensure dialog stays on the specific monitor
	dialog_x = max(monitor_left, min(dialog_x, monitor_right - DLG_WIDTH))
	dialog_y = max(monitor_top, min(dialog_y, monitor_bottom - DLG_HEIGHT))
	
	# Global variables for dialog controls
	dialog_hwnd = None
	edit_hwnd = None
	link_hwnd = None
	dialog_font = None
	underlined_font = None
	mouse_over_link = False
	
	def dialog_wnd_proc(hwnd, msg, wparam, lparam):
		nonlocal dialog_hwnd, edit_hwnd, link_hwnd, dialog_font, underlined_font, mouse_over_link
		
		if msg == win32con.WM_CTLCOLORSTATIC:
			# Color the GitHub link blue
			if lparam == link_hwnd:
				hdc = wparam
				win32gui.SetTextColor(hdc, THEME.LINK)
				win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
				# Return the dialog background brush
				return win32gui.GetSysColorBrush(win32con.COLOR_BTNFACE)
				
		elif msg == win32con.WM_SETCURSOR:
			# Change cursor to hand when over the link and handle hover
			cursor_pos = win32gui.GetCursorPos()
			window_at_cursor = win32gui.WindowFromPoint(cursor_pos)
			if window_at_cursor == link_hwnd:
				win32gui.SetCursor(win32gui.LoadCursor(0, win32con.IDC_HAND))
				# Mouse is over link - switch to underlined font if not already
				if not mouse_over_link:
					mouse_over_link = True
					if underlined_font and link_hwnd:
						win32gui.SendMessage(link_hwnd, win32con.WM_SETFONT, underlined_font, True)
						win32gui.InvalidateRect(link_hwnd, None, True)
						win32gui.UpdateWindow(link_hwnd)
				return True
			else:
				# Mouse is not over link - switch back to normal font if needed
				if mouse_over_link:
					mouse_over_link = False
					if dialog_font and link_hwnd:
						win32gui.SendMessage(link_hwnd, win32con.WM_SETFONT, dialog_font, True)
						win32gui.InvalidateRect(link_hwnd, None, True)
						win32gui.UpdateWindow(link_hwnd)
				
		elif msg == win32con.WM_COMMAND:
			cmd_id = win32api.LOWORD(wparam)
			notify_code = win32api.HIWORD(wparam)
			
			if cmd_id == OK_BUTTON_ID and notify_code == win32con.BN_CLICKED:
				win32gui.DestroyWindow(hwnd)
				return 0
			elif cmd_id == COPY_BUTTON_ID and notify_code == win32con.BN_CLICKED:
				# Select all text and copy to clipboard
				if edit_hwnd:
					win32gui.SendMessage(edit_hwnd, win32con.EM_SETSEL, 0, -1)
					win32gui.SendMessage(edit_hwnd, win32con.WM_COPY, 0, 0)
				return 0
			elif cmd_id == GITHUB_LINK_ID and notify_code == win32con.STN_CLICKED:
				# Handle link click
				try:
					webbrowser.open("https://github.com/Fredderic/FullThumbs")
				except:
					pass  # Failed to open browser
				return 0
				
		elif msg == win32con.WM_CLOSE:
			win32gui.DestroyWindow(hwnd)
			return 0
		elif msg == win32con.WM_DESTROY:
			# Clean up created font before destroying dialog
			if underlined_font and underlined_font != dialog_font:
				try:
					win32gui.DeleteObject(underlined_font)
				except:
					pass
			# Re-enable parent window
			if parent_hwnd:
				win32gui.EnableWindow(parent_hwnd, True)
				win32gui.SetForegroundWindow(parent_hwnd)
			return 0
		
		return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
	
	# Register dialog window class
	try:
		wc = win32gui.WNDCLASS()
		wc.lpfnWndProc = dialog_wnd_proc
		wc.lpszClassName = "AboutDialogClass"
		wc.hInstance = win32api.GetModuleHandle(None)
		wc.hbrBackground = win32con.COLOR_BTNFACE + 1
		wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
		
		try:
			win32gui.RegisterClass(wc)
		except win32gui.error as e:
			if e.winerror != 1410:  # Class already exists
				raise
		
		# Create the dialog window
		dialog_hwnd = win32gui.CreateWindowEx(
			win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_TOPMOST,
			"AboutDialogClass",
			"About FullThumbs",
			win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_VISIBLE,
			dialog_x, dialog_y, DLG_WIDTH, DLG_HEIGHT,
			parent_hwnd, 0, win32api.GetModuleHandle(None), None
		)
		
		# Create edit control for text display (multiline, read-only, with scrollbar)
		# Calculate client area dimensions (excluding title bar and frame)
		client_width = DLG_WIDTH - 20  # Account for frame
		client_height = DLG_HEIGHT - TITLE_BAR_HEIGHT - 10  # Account for title bar and frame
		edit_height = client_height - 4*MARGIN - BUTTON_HEIGHT - link_text_height  # Use measured link height
		
		edit_hwnd = win32gui.CreateWindow(
			"EDIT",
			about_text,
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.ES_MULTILINE | 
			win32con.ES_READONLY | win32con.WS_VSCROLL | win32con.ES_AUTOVSCROLL |
			win32con.WS_BORDER,
			MARGIN, MARGIN, 
			client_width - 2*MARGIN, edit_height,
			dialog_hwnd, EDIT_CONTROL_ID, win32api.GetModuleHandle(None), None
		)
		
		# Set a better font for the edit control (standard Windows dialog font)
		dialog_font = None
		underlined_font = None
		try:
			# Get the default GUI font (standard Windows dialog font)
			dialog_font = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT constant value
			if dialog_font:
				win32gui.SendMessage(edit_hwnd, win32con.WM_SETFONT, dialog_font, True)
			
			# Create an underlined version of the font for hover effect
			try:
				import ctypes
				from ctypes import wintypes
				
				# Create underlined font using CreateFontW
				underlined_font = ctypes.windll.gdi32.CreateFontW(
					-11,           # Height (negative for character height)
					0,             # Width (0 = default)
					0,             # Escapement
					0,             # Orientation
					400,           # Weight (400 = normal)
					0,             # Italic (0 = not italic)
					1,             # Underline (1 = underlined)
					0,             # StrikeOut (0 = not struck out)
					1,             # CharSet (1 = DEFAULT_CHARSET)
					0,             # OutPrecision
					0,             # ClipPrecision
					0,             # Quality
					0,             # PitchAndFamily
					"MS Shell Dlg" # FaceName
				)
			except:
				# If creating underlined font fails, fall back to dialog font
				underlined_font = dialog_font
		except:
			pass  # If font creation fails, use default
		
		# Create GitHub link as a static control
		link_y = MARGIN + edit_height + MARGIN
		link_hwnd = win32gui.CreateWindow(
			"STATIC", 
			link_text,
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT | win32con.SS_NOTIFY,
			MARGIN, link_y, link_text_width + 5, link_text_height,  # Use measured dimensions
			dialog_hwnd, GITHUB_LINK_ID, win32api.GetModuleHandle(None), None
		)
		
		# Set the same font for the link
		try:
			win32gui.SendMessage(link_hwnd, win32con.WM_SETFONT, dialog_font, True)
		except:
			pass
		
		# Create Copy button - moved up by about 1/3 of button height
		button_y = link_y + link_text_height + MARGIN//2  # Use measured link height
		copy_button = win32gui.CreateWindow(
			"BUTTON",
			"Copy",
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
			client_width - 2*MARGIN - 2*BUTTON_WIDTH - 5, button_y,
			BUTTON_WIDTH, BUTTON_HEIGHT,
			dialog_hwnd, COPY_BUTTON_ID, win32api.GetModuleHandle(None), None
		)
		
		# Set font for copy button
		try:
			win32gui.SendMessage(copy_button, win32con.WM_SETFONT, dialog_font, True)
		except:
			pass
		
		# Create OK button
		ok_button = win32gui.CreateWindow(
			"BUTTON",
			"OK",
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_DEFPUSHBUTTON,
			client_width - MARGIN - BUTTON_WIDTH, button_y,
			BUTTON_WIDTH, BUTTON_HEIGHT,
			dialog_hwnd, OK_BUTTON_ID, win32api.GetModuleHandle(None), None
		)
		
		# Set font for OK button
		try:
			win32gui.SendMessage(ok_button, win32con.WM_SETFONT, dialog_font, True)
		except:
			pass
		
		# # TEMPORARY TEST: Create two test labels to verify fonts work
		# test_normal = win32gui.CreateWindow(
		# 	"STATIC", 
		# 	"Normal Font Test",
		# 	win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT,
		# 	50, link_y+20, 120, 20,
		# 	dialog_hwnd, 9999, win32api.GetModuleHandle(None), None
		# )
		# test_underlined = win32gui.CreateWindow(
		# 	"STATIC", 
		# 	"Underlined Font Test",
		# 	win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT,
		# 	50, link_y+40, 120, 20,
		# 	dialog_hwnd, 9998, win32api.GetModuleHandle(None), None
		# )
		# try:
		# 	win32gui.SendMessage(test_normal, win32con.WM_SETFONT, dialog_font, True)
		# 	win32gui.SendMessage(test_underlined, win32con.WM_SETFONT, underlined_font, True)
		# except:
		# 	pass
		
		# Select all text in the edit control and set focus
		# win32gui.SendMessage(edit_hwnd, win32con.EM_SETSEL, 0, -1)  # Removed pre-selection
		win32gui.SetFocus(edit_hwnd)
		
		# Disable parent window to make this modal
		if parent_hwnd:
			win32gui.EnableWindow(parent_hwnd, False)
		
		# Bring dialog to front
		# win32gui.SetForegroundWindow(dialog_hwnd)
		win32gui.SetActiveWindow(dialog_hwnd)
		
	except Exception as e:
		print(f"Error creating about dialog: {e}")
		# Fallback to simple message box
		win32gui.MessageBox(parent_hwnd, about_text.replace('\r\n', '\n'),
					  "About FullThumbs", win32con.MB_OK)

# -------

def pip_window_proc(hwnd, msg, wparam, lparam):
	"""Window procedure for the PiP window."""
	from . import main

	try:
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
			if main.g_thumbnail_slots and default_result == win32con.HTCLIENT:
				screen_x, screen_y = win32gui.ScreenToClient(hwnd, split_lparam_pos(lparam))
				
				# If mouse is over a thumbnail's area, pass through clicks
				if find_thumbnail_at(main.g_thumbnail_slots, screen_x, screen_y):
					return win32con.HTCLIENT
				
				# If mouse is in the gap area around the thumbnails, enable dragging
				return win32con.HTCAPTION
			
			# For all other areas (title bar, etc.), use default behavior
			return default_result

		elif msg == win32con.WM_SETCURSOR:
			if win32api.LOWORD(lparam) == win32con.HTCLIENT:
				# Set the cursor to a hand icon when hovering over the PiP window
				win32gui.SetCursor(win32gui.LoadCursor(0, win32con.IDC_HAND))
				return 0	# indicate we handled the message
				# NOTE: fallthrough would set default cursor

		elif msg == win32con.WM_MOUSEMOVE:
			track_mouse_leave(hwnd) # Re-arm WM_MOUSELEAVE; it's one-shot
			mouse_x, mouse_y = split_lparam_pos(lparam)
			set_hovered_thumb(hwnd, find_thumbnail_at(main.g_thumbnail_slots, mouse_x, mouse_y))
			# NOTE: fall through for default processing

		elif msg == win32con.WM_MOUSELEAVE:
			set_hovered_thumb(hwnd, None)
			return 0

		elif msg == win32con.WM_TIMER:
			if (handler := _timer_handlers.get(wparam)):
				handler(hwnd)
				return 0 # indicate we handled the message
			# NOTE: do not call DefWindowProc for handled commands

		elif msg == win32con.WM_PAINT:
			# Handle paint messages if needed (e.g., custom drawing)
			# ps = win32gui.PAINTSTRUCT()
			hdc, ps = win32gui.BeginPaint(hwnd) # Get DC for painting

			# 1. Draw the background of the PiP window
			background_color = THEME.BACKGROUND
			client_rect = win32gui.GetClientRect(hwnd)
			fill_brush = win32gui.CreateSolidBrush(background_color) # Dark gray background
			win32gui.FillRect(hdc, client_rect, fill_brush)
			win32gui.DeleteObject(fill_brush)

			if main.g_thumbnail_slots:
				null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
				old_brush = win32gui.SelectObject(hdc, null_brush)

				# Draw a box (and cross, if invalid) for each active thumbnail slot
				for thumb in main.g_thumbnail_slots.values():
					if not thumb.current_thumb_rect:
						continue # Registration failed before a rect could be computed (e.g. fullscreen source)
					box_left, box_top, box_right, box_bottom = thumb.current_thumb_rect

					# Hover/menu highlight takes precedence over the on-top indicator
					if thumb is _hovered_thumb or thumb.source_hwnd == _context_menu_target_hwnd:
						border_color = THEME.TMB_HOVER
					elif is_window_on_top(thumb.source_hwnd):
						border_color = THEME.TMB_ON_TOP
					else:
						border_color = THEME.TMB_MARKER

					marker_pen = win32gui.CreatePen(win32con.PS_SOLID, 2, border_color)
					old_pen = win32gui.SelectObject(hdc, marker_pen)

					win32gui.Rectangle(hdc, box_left-1, box_top-1, box_right+2, box_bottom+2)

					if not thumb.is_valid:
						win32gui.MoveToEx(hdc, box_left, box_top)
						win32gui.LineTo(hdc, box_right, box_bottom)
						win32gui.MoveToEx(hdc, box_left, box_bottom)
						win32gui.LineTo(hdc, box_right, box_top)

					win32gui.SelectObject(hdc, old_pen)
					win32gui.DeleteObject(marker_pen)

			else:
				# No thumbnail yet - use default area
				box_left, box_top, width, height = get_default_window_area()
				box_right = box_left + width
				box_bottom = box_top + height

				# Create red pen and null brush for drawing
				marker_pen = win32gui.CreatePen(win32con.PS_SOLID, 2, THEME.TMB_MARKER)
				old_pen = win32gui.SelectObject(hdc, marker_pen)
				null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
				old_brush = win32gui.SelectObject(hdc, null_brush)

				# Draw rectangle and cross
				win32gui.Rectangle(hdc, box_left-1, box_top-1, box_right+2, box_bottom+2)
				win32gui.MoveToEx(hdc, box_left, box_top)
				win32gui.LineTo(hdc, box_right, box_bottom)
				win32gui.MoveToEx(hdc, box_left, box_bottom)
				win32gui.LineTo(hdc, box_right, box_top)

				win32gui.SelectObject(hdc, old_pen)
				win32gui.DeleteObject(marker_pen)

			# 	message = "Not Found"		-- TODO
			# 	text_color = THEME.TEXT
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
			win32gui.SelectObject(hdc, old_brush) # NULL_BRUSH doesn't need deleting

			# g_window_test_marker.draw(hdc) # TEMP TEST: disabled now the border colour conveys on-top state

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

			if main.g_thumbnail_slots:
				layout_thumbnails(hwnd)

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
			target_thumb = find_thumbnail_at(main.g_thumbnail_slots, click_x, click_y)
			if target_thumb:
				# Left-click to bring that thumbnail's source app to front
				bring_window_to_front(target_thumb.source_hwnd)
			# NOTE: fall through for default processing

		elif msg == win32con.WM_RBUTTONDOWN:
			# Just let this fall through to DefWindowProc, which raises WM_CONTEXTMENU on button-up
			# (handling it here too would show the popup menu twice for a single right-click)
			pass

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
				# Show an about dialog with selectable text
				from .version import get_version_info
				from .constants import DEBUG_PY
				info = get_version_info()
				about_text = (
					f"FullThumbs PiP Viewer\r\n"
					f"Version: {info['version']}\r\n"
					f"Commit: {info['commit_hash_short']}\r\n"
					f"Branch: {info['branch']}\r\n"
					f"Built: {info['commit_date'][:10]}"  # Just the date part
				)
				if DEBUG_PY:
					about_text += "\r\n\r\n🐛 Debug Mode Active"
				show_about_dialog(hwnd, about_text)
				
				# Old simple message box implementation (retained for comparison):
				# win32gui.MessageBox(hwnd, about_text, "About FullThumbs", win32con.MB_OK)
				return 0
			elif cmd_id == MENU_ID_CHECK_UPDATES:
				# Check for updates immediately
				check_for_git_updates()
				return 0
			elif cmd_id == MENU_ID_APP_TO_FRONT:
				# Bring the thumbnail's source application (under the cursor at right-click) to the front
				if _context_menu_target_hwnd:
					bring_window_to_front(_context_menu_target_hwnd)
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
			elif cmd_id == MENU_ID_RESTART_THUMBNAIL:
				request_restart(hwnd)
				return 0
			else:
				print(f"Unhandled command ID: {cmd_id}")
			# NOTE: do not call DefWindowProc for handled commands

		elif msg == win32con.WM_CLOSE:
			# Handle close message
			save_window_placement_handler(hwnd)	# also stops the timer
			win32gui.DestroyWindow(hwnd)
			# return 0
		elif msg == win32con.WM_DESTROY:
			Timer.stop_all(hwnd)
			win32gui.PostQuitMessage(0)
			main.g_pip_hwnd = None
			# return 0

		return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

	except KeyboardInterrupt:
		# Handle Ctrl+C gracefully in the window procedure
		print("KeyboardInterrupt in window procedure. Closing application...")
		main.g_exit_code = 0  # Set exit code to normal exit
		win32gui.PostQuitMessage(0)  # Close the message loop
		return 0
	except Exception as e:
		print(f"Error in window procedure: {e}")
		return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# -------

def create_pip_window(x, y, width, height, window_mode, title="PiP View"):
	"""Creates a PiP window with the specified window mode."""
	
	# Add debug indicator to title when running under debugger
	from .constants import DEBUG_PY
	if DEBUG_PY:
		title += " (Debug)"

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

def is_window_on_top(hwnd):
	"""Check if hwnd is the active foreground window and not minimized."""
	return bool(hwnd) and win32gui.GetForegroundWindow() == hwnd and not win32gui.IsIconic(hwnd)

def find_thumbnail_at(slots, x, y):
	"""Return the ThumbnailManager (from a slot dict) whose rect contains (x, y), or None."""
	for thumb in slots.values():
		if thumb.check_within_thumbnail_rect(x, y):
			return thumb
	return None

_hovered_thumb = None # Thumbnail currently highlighted for mouseover/context-menu, if any

def set_hovered_thumb(hwnd, thumb):
	"""Update which thumbnail is mouseover-highlighted, repainting only what changed."""
	global _hovered_thumb
	if thumb is _hovered_thumb:
		return
	for changed_thumb in (_hovered_thumb, thumb):
		if changed_thumb and changed_thumb.current_thumb_rect:
			left, top, right, bottom = changed_thumb.current_thumb_rect
			win32gui.InvalidateRect(hwnd, (left-2, top-2, right+2, bottom+2), False)
	_hovered_thumb = thumb

def layout_thumbnails_evenly(hwnd, thumbnails):
	"""Split the current inner client area into equal-width thumbnail columns."""
	if not thumbnails:
		return
	client_rect = get_inner_client_rect(hwnd)
	left, top, right, bottom = client_rect
	count = len(thumbnails)
	gap = PIP_PADDING if count > 1 else 0
	cell_width = (right - left - gap * (count - 1)) // count
	x = left
	for thumb in thumbnails:
		thumb.update_thumbnail_rect((x, top, x + cell_width, bottom))
		x += cell_width + gap

class LayoutThumbnailAnchorEdge:
	_EDGES = ("top", "left", "bottom", "right")

	def __init__(self, edge: Literal[0,'top', 1,'left', 2,'bottom', 3,'right']): #type: ignore
		if isinstance(edge, str):
			edge: int = self._EDGES.index(edge)
		if not isinstance(edge, int) or edge < 0 or edge >= 4:
			raise ValueError(f"Unsupported anchor edge: {edge!r}")
		# compute layout parameters based on the edge
		majorFn = self.Xmajor if edge & 1 else self.Ymajor
		anchor_end = edge & 2 > 0
		self.layout_params = (majorFn, anchor_end)

	def __call__(self, hwnd, thumbnails):
		return self.perform_layout(hwnd, thumbnails, *self.layout_params)

	class Xmajor:
		@staticmethod
		def fromRect(left, top, right, bottom) -> tuple[int, int, int, int]:
			return left, right, top, bottom

		@staticmethod
		def toRect(major_start, major_end, minor_start, minor_end) -> tuple[int, int, int, int]:
			return major_start, minor_start, major_end, minor_end

	assert Xmajor.fromRect(1, 2, 3, 4) == (1, 3, 2, 4)
	assert Xmajor.toRect  (1, 3, 2, 4) == (1, 2, 3, 4)

	class Ymajor:
		@staticmethod
		def fromRect(left, top, right, bottom) -> tuple[int, int, int, int]:
			return top, bottom, left, right

		@staticmethod
		def toRect(major_start, major_end, minor_start, minor_end) -> tuple[int, int, int, int]:
			return minor_start, major_start, minor_end, major_end

	assert Ymajor.fromRect(1, 2, 3, 4) == (2, 4, 1, 3)
	assert Ymajor.toRect  (2, 4, 1, 3) == (1, 2, 3, 4)

	def perform_layout(self, hwnd, thumbnails, major, anchor_end: bool):
		"""Keep the outer right edge and height fixed while fitting full-height thumbnails."""
		inner_major_start, _, inner_minor_start, inner_minor_end = major.fromRect(*get_inner_client_rect(hwnd))
		inner_minor_size = max(1, inner_minor_end - inner_minor_start)
		gap = PIP_PADDING if len(thumbnails) > 1 else 0

		# Calculate the size of each thumbnail cell based on the source window
		#	aspect ratios and the available inner client area.
		cell_sizes = []
		for thumb in thumbnails:
			source_major_start, source_major_end, source_minor_start, source_minor_end = \
					major.fromRect(*win32gui.GetClientRect(thumb.source_hwnd))
			source_major_size = source_major_end - source_major_start
			source_minor_size = source_minor_end - source_minor_start
			if source_major_size <= 0 or source_minor_size <= 0:
				raise ValueError("Invalid source window dimensions.")
			cell_sizes.append(max(PIP_MIN_CLIENT_SIZE,
			        round(inner_minor_size * source_major_size / source_minor_size)))
		if thumbnails:
			desired_inner_major = sum(cell_sizes) + gap * (len(thumbnails) - 1)
			desired_client_major = max(PIP_MIN_CLIENT_SIZE, desired_inner_major) + 2 * PIP_PADDING
		else:
			desired_client_major = PIP_MIN_CLIENT_SIZE

		# Adjust the PiP window size to accommodate the desired client area for thumbnails.
		window_major_start, window_major_end, window_minor_start, window_minor_end = \
				major.fromRect(*win32gui.GetWindowRect(hwnd))
		client_major_start, client_major_end, _, _ = major.fromRect(*win32gui.GetClientRect(hwnd))
		window_major_size = window_major_end - window_major_start
		frame_major_size = window_major_size - (client_major_end - client_major_start)
		desired_window_major = desired_client_major + frame_major_size

		if window_major_size != desired_window_major:
			if anchor_end:
				# recalculate the window start position based on the desired window size and anchor end
				window_major_start = window_major_end - desired_window_major
			pos_x, pos_y, size_w, size_h = major.toRect(
				window_major_start, desired_window_major,
				window_minor_start, window_minor_end - window_minor_start
			)
			win32gui.SetWindowPos( hwnd, 0, pos_x, pos_y, size_w, size_h,
					win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE )
			return

		# Position and size each thumbnail within the PiP window based on the calculated cell sizes.
		p = inner_major_start
		for thumb, cell_size in zip(thumbnails, cell_sizes):
			thumb.update_thumbnail_rect(major.toRect(p, p + cell_size, inner_minor_start, inner_minor_end))
			p += cell_size + gap

g_thumbnail_layout = LayoutThumbnailAnchorEdge('right')

def layout_thumbnails(hwnd):
	"""(Re)lay out all currently active thumbnail slots for the PiP window."""
	from src.main import g_thumbnail_slots	# FIXME: put this somewhere importable
	ordered = [g_thumbnail_slots[index] for index in sorted(g_thumbnail_slots)]
	g_thumbnail_layout(hwnd, ordered)
	win32gui.InvalidateRect(hwnd, None, True) # Also clears any now-vacated cells

# TEMP TEST: delete this class (and its call sites become errors) to remove the test indicator
class WindowTestMarker:
	"""Draws a small red/blue square in the PiP window reflecting (currently) is_window_on_top(source)."""
	TIMER = Timer(id=2099, ms=250)
	RECT = (0, 0, 10, 10)

	def __init__(self):
		self._last_state = None
		_timer_handlers[WindowTestMarker.TIMER.id] = self.check

	def start(self, hwnd):
		self.TIMER.start(hwnd)

	def check(self, hwnd):
		"""Call on TIMER tick; invalidates the indicator rect if the state changed."""
		from . import main
		source_hwnd = next((t.source_hwnd for t in main.g_thumbnail_slots.values()), None)
		state = is_window_on_top(source_hwnd)
		if state != self._last_state:
			self._last_state = state
			win32gui.InvalidateRect(hwnd, self.RECT, False)

	def draw(self, hdc):
		"""Call from WM_PAINT to draw the indicator."""
		from . import main
		source_hwnd = next((t.source_hwnd for t in main.g_thumbnail_slots.values()), None)
		color = THEME.TMB_ON_TOP if is_window_on_top(source_hwnd) else THEME.TMB_HOVER
		brush = win32gui.CreateSolidBrush(color)
		win32gui.FillRect(hdc, self.RECT, brush)
		win32gui.DeleteObject(brush)

# g_window_test_marker = WindowTestMarker() # TEMP TEST: disabled now the border colour conveys on-top state


_last_on_top_state = set() # thumbs currently "on top"; only the symmetric difference needs invalidating each tick

@set_timer_handler(TIMER_CHECK_SOURCE)
def handle_source_window_status(hwnd):
	"""Poll each configured finder and keep its thumbnail slot in sync with what it currently matches."""
	from . import main
	from .thumbnail import ThumbnailManager

	slots = main.g_thumbnail_slots
	changed = False

	for index, finder in enumerate(main.g_target_app_matches):
		thumb = slots.get(index)

		# Drop the slot if its window is no longer valid/visible
		if thumb and not (win32gui.IsWindow(thumb.source_hwnd) and win32gui.IsWindowVisible(thumb.source_hwnd)):
			print(f"Slot {index}: window is no longer valid or visible.")
			thumb.cleanup_thumbnail()
			del slots[index]
			thumb = None
			changed = True

		found_hwnd = finder()
		if not found_hwnd:
			continue

		if thumb is None:
			print(f"Slot {index}: found window {found_hwnd} ({win32gui.GetWindowText(found_hwnd)!r})")
			# Placeholder rect; layout_thumbnails() below assigns the real cell once the slot count is final
			slots[index] = ThumbnailManager(hwnd, get_inner_client_rect(hwnd), found_hwnd)
			changed = True
		elif thumb.source_hwnd != found_hwnd:
			print(f"Slot {index}: switching to window {found_hwnd} ({win32gui.GetWindowText(found_hwnd)!r})")
			thumb.switch_source(found_hwnd)

	if changed:
		layout_thumbnails(hwnd)

	# Invalidate rectangle of thumbnails whose on-top state changed since the last check.

	global _last_on_top_state
	new_on_top_state = {thumb for thumb in main.g_thumbnail_slots.values() if is_window_on_top(thumb.source_hwnd)}
	for thumb in _last_on_top_state ^ new_on_top_state:
		# Hover/menu highlight already overrides the colour, so skip the repaint while active
		if thumb is not _hovered_thumb and thumb.source_hwnd != _context_menu_target_hwnd and thumb.current_thumb_rect:
			left, top, right, bottom = thumb.current_thumb_rect
			win32gui.InvalidateRect(hwnd, (left-2, top-2, right+2, bottom+2), False)
	_last_on_top_state = new_on_top_state


WINDOW_U_FLAGS = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED

def set_pip_window_style(window_mode):
	from . import main
	
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

