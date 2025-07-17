import win32gui
from win32api import GetSystemMetrics

from .constants import DEBUG_PY, SETTINGS_FILE, WINDOW_MODE_NORMAL
from .settings import load_window_placement, save_window_placement
from .win_api import Timer, get_inner_client_rect
from .window_main import TIMER_CHECK_SOURCE, TIMER_UPDATE_CHECK, create_pip_window, get_default_window_area
from .window_finder import window_finder_by_regex
from .thumbnail import ThumbnailManager

# -------

# g_user32 = ctypes.windll.user32			# user32 library handle
# g_dwmapi_lib = ctypes.windll.dwmapi		# dwmapi library handle

g_exit_code = 0 # Global exit code for the application
g_target_app_match = None # Function to find the target application window
g_current_window_mode = WINDOW_MODE_NORMAL # Current window mode

g_pip_hwnd = None # Global handle for the PiP window
g_source_hwnd = None
g_thumbnail = None
g_update_interval = 0  # Auto-update check interval
g_debug_simulate_update = False  # Debug flag to simulate update restart


def setup(update_interval_ms=0, debug_simulate_update=False):
	global g_target_app_match, g_source_hwnd, g_pip_hwnd, g_current_thumb_rect_in_pip
	global g_current_window_mode, g_thumbnail, g_update_interval, g_debug_simulate_update
	
	g_update_interval = update_interval_ms
	g_debug_simulate_update = debug_simulate_update

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

	if g_source_hwnd is not None:
		try:
			g_thumbnail = ThumbnailManager(g_pip_hwnd, pip_rect, g_source_hwnd)
		except Exception as e:
			print("Failed to get DWM thumbnail. The target application might be in true exclusive fullscreen mode.")
			win32gui.DestroyWindow(g_pip_hwnd) # Clean up PiP window
			exit(1)

	print("DWM thumbnail successfully registered. The PiP window should now show the live view.")
	print("Click the PiP window to bring the source app to front.")
	print("Right-click to close the PiP window and clean up.")

	# Set a timer to periodically check the source window
	TIMER_CHECK_SOURCE.start(g_pip_hwnd) # Start the timer
	
	# Set update check timer if auto-updates are enabled
	if g_update_interval > 0:
		print(f"Auto-update enabled: checking for updates every {g_update_interval/(3600*1000):.1f} hours.")
		TIMER_UPDATE_CHECK.start(g_pip_hwnd, g_update_interval)

def run():
	try:
		# This is the main message loop
		win32gui.PumpMessages()
	except Exception as e:
		print(f"Error in message loop: {e}")
	finally:
		print("Cleaning up...")
		if g_thumbnail:
			g_thumbnail.cleanup_thumbnail()
		if g_pip_hwnd: # Stop the timer
			Timer.stop_all(g_pip_hwnd) # Stop all timers
			save_window_placement(g_pip_hwnd) # Save the current position
			win32gui.DestroyWindow(g_pip_hwnd) # Clean up PiP window
		print("Cleanup complete.")
		return g_exit_code  # Return exit code instead of calling exit()
