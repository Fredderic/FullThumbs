import win32gui
from win32api import GetSystemMetrics

from .constants import DEBUG_PY, SETTINGS_FILE, WINDOW_MODE_NORMAL
from .settings import load_window_placement, save_window_placement
from .win_api import Timer, get_inner_client_rect
from .window_main import ( TIMER_CHECK_SOURCE, TIMER_UPDATE_CHECK, create_pip_window,
			get_default_window_area, handle_source_window_status, layout_thumbnails )
from .window_finder import window_finder_by_regex

# -------

# g_user32 = ctypes.windll.user32			# user32 library handle
# g_dwmapi_lib = ctypes.windll.dwmapi		# dwmapi library handle

g_exit_code = 0 # Global exit code for the application
g_target_app_matches = [] # Ordered list of finder functions; first non-topmost match is shown
g_current_window_mode = WINDOW_MODE_NORMAL # Current window mode

g_pip_hwnd = None # Global handle for the PiP window
g_thumbnail_slots = {} # finder-index -> ThumbnailManager, for each currently matched window
g_update_interval = 0  # Auto-update check interval
g_debug_simulate_update = False  # Debug flag to simulate update restart
g_supervised = False  # True if run_loop() spawned us as 'run' and will catch an exit-code-2 restart request


def setup(update_interval_ms=0, debug_simulate_update=False, supervised=False):
	global g_target_app_matches, g_pip_hwnd, g_current_thumb_rect_in_pip
	global g_current_window_mode, g_update_interval, g_debug_simulate_update, g_supervised
	
	g_update_interval = update_interval_ms
	g_debug_simulate_update = debug_simulate_update
	g_supervised = supervised

	# List of windows to watch; each gets its own thumbnail slot, shown simultaneously.
	g_target_app_matches = [	# TODO -- this needs to be in configuration
		window_finder_by_regex(r'^Sky$', 'TgcMainWindow'),
		window_finder_by_regex(r'^Mabinogi$', 'Mabinogi'),
	]
	if DEBUG_PY:
		g_target_app_matches.append(window_finder_by_regex(r'\*?IDLE Shell', 'TkTopLevel'))

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
		pip_x, pip_y, pip_width, pip_height = get_default_window_area()
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

	print(f"Attempting to find application(s)...")
	handle_source_window_status(g_pip_hwnd) # Populate/layout initial thumbnail slot(s), if any are found
	if not g_thumbnail_slots:	# If no thumbnails were found, layout the empty PiP window
		layout_thumbnails(g_pip_hwnd)

	print("Click a thumbnail to bring its source app to front.")
	print("Right-click to close the PiP window and clean up.")

	# Set a timer to periodically check the source window(s)
	TIMER_CHECK_SOURCE.start(g_pip_hwnd) # Start the timer
	# g_window_test_marker.start(g_pip_hwnd) # TEMP TEST: disabled now the border colour conveys on-top state
	
	# Set update check timer if auto-updates are enabled
	if g_update_interval > 0:
		print(f"Auto-update enabled: checking for updates every {g_update_interval/(3600*1000):.1f} hours.")
		TIMER_UPDATE_CHECK.start(g_pip_hwnd, g_update_interval)

def run():
	try:
		# Use the standard Windows message pump
		# KeyboardInterrupt will be handled in the window procedure
		win32gui.PumpMessages()
	except KeyboardInterrupt:
		# This may not be reached due to PumpMessages blocking,
		# but the window procedure should handle Ctrl+C
		print("KeyboardInterrupt received in main thread. Exiting cleanly...")
		return 0  # Exit normally when Ctrl+C is pressed
	except Exception as e:
		print(f"Error in message loop: {e}")
		return 1  # Exit with error code for unexpected exceptions
	finally:
		print("Cleaning up...")
		for thumb in g_thumbnail_slots.values():
			thumb.cleanup_thumbnail()
		g_thumbnail_slots.clear()
		if g_pip_hwnd: # Stop the timer
			Timer.stop_all(g_pip_hwnd) # Stop all timers
			save_window_placement(g_pip_hwnd) # Save the current position
			win32gui.DestroyWindow(g_pip_hwnd) # Clean up PiP window
		print("Cleanup complete.")
	
	return g_exit_code  # Return exit code instead of calling exit()
