# type: ignore

"""
full-thumbs.py - FullThumbs application main entry point

FullThumbs is a Picture-in-Picture (PiP) thumbnail viewer for Windows that provides a live, 
resizable preview of any target application window. The application features three window 
modes (normal, always-on-top, and minimal borderless), automatic git-based updates, 
and comprehensive command-line options.

Features:
- Live DWM thumbnail rendering of target applications
- Three window display modes with context menu switching
- Automatic git-based updates with configurable intervals
- Flexible command-line argument parsing
- Persistent window position and mode settings
- Debug mode with auto-reload functionality

This script serves as the main entry point and handles argument parsing, auto-updates,
and application lifecycle management. The core PiP functionality is implemented in
the src/ module.
"""

import sys, os, re, argparse, subprocess

from src import main, constants
from utilities import parse_time_interval, validate_auto_update_interval

# --- Core Functions ---

def parse_arguments():
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(
		description='FullThumbs - Picture-in-Picture thumbnail viewer',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Auto-update examples:
  --auto-update        Default 4 hour interval
  --auto-update=2h     Check every 2 hours
  --auto-update=30m    Check every 30 minutes (minimum 1 minute)
  --auto-update=1d     Check every day
  --no-auto-update     Disable auto-updates
Note: Auto-update intervals must be at least 60 seconds (1 minute).
		""".strip()
	)
	
	# Create subparsers for commands
	subparsers = parser.add_subparsers(dest='command', help='Available commands')
	
	# Internal run command (no arguments)
	run_parser = subparsers.add_parser(
		'run',
		help='Run the application directly (internal use only)'
	)
	def validate_update_interval_ms(value):
		"""Validate that update interval is a non-negative integer (milliseconds)."""
		value = int(value)
		if value < 0:
			raise argparse.ArgumentTypeError("Update interval must be non-negative")
		return value
	run_parser.add_argument('--update-interval', type=validate_update_interval_ms, default=0,
							help='Auto-update check interval in milliseconds (0 to disable)')
	
	# Auto-update arguments for main command (when no subcommand is used)
	auto_group = parser.add_mutually_exclusive_group()
	auto_group.add_argument('--auto-update', nargs='?', const='4h', metavar='INTERVAL',
							help='Enable auto-updates with optional interval (default: 4h)')
	auto_group.add_argument('--no-auto-update', action='store_true',
							help='Disable auto-updates completely')
	
	return parser.parse_args()

# --- Main Logic ---

def check_for_updates():
	"""Check for git updates and pull if available."""
	try:
		repo_dir = os.path.dirname(os.path.abspath(__file__))
		
		# Fetch latest changes from remote
		print("Checking for updates...")
		subprocess.run(['git', 'fetch'], cwd=repo_dir, check=True, capture_output=True)
		
		# Check if we're behind the remote
		result = subprocess.run(
			['git', 'rev-list', '--count', 'HEAD..@{u}'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		
		commits_behind = int(result.stdout.strip())
		if commits_behind > 0:
			print(f"Found {commits_behind} new commit(s). Updating...")
			
			# Check if working directory is clean
			status_result = subprocess.run(
				['git', 'status', '--porcelain'],
				cwd=repo_dir,
				capture_output=True,
				text=True,
				check=True
			)
			
			if status_result.stdout.strip():
				print("WARNING: Working directory has uncommitted changes. Skipping update.")
				return False
			
			# Pull the latest changes
			subprocess.run(['git', 'pull'], cwd=repo_dir, check=True)
			print("Update complete! Restarting application...")
			return True
		else:
			print("Application is up to date.")
			return False
			
	except subprocess.CalledProcessError as e:
		print(f"Git operation failed: {e}")
		return False
	except Exception as e:
		print(f"Error checking for updates: {e}")
		return False

def run_loop(args):
	import time
	
	# Determine auto-update settings
	if getattr(args, 'no_auto_update', False) or constants.DEBUG_PY:
		ENABLE_AUTO_UPDATE = False
		UPDATE_CHECK_INTERVAL = 0
	elif getattr(args, 'auto_update', None):
		ENABLE_AUTO_UPDATE = True
		interval_ms = parse_time_interval(args.auto_update)
		UPDATE_CHECK_INTERVAL = validate_auto_update_interval(interval_ms)
		if UPDATE_CHECK_INTERVAL is None:
			print(f"Error: Invalid time interval '{args.auto_update}'. Intervals must be at least 60 seconds (1 minute). Using default 4h.")
			UPDATE_CHECK_INTERVAL = 4 * 60 * 60_000  # 4 hours
	else:
		# Default behavior (no auto-update args provided)
		ENABLE_AUTO_UPDATE = not constants.DEBUG_PY
		UPDATE_CHECK_INTERVAL = 4 * 60 * 60_000  # Default 4 hours
	
	result = 1
	last_update_check = 0  # Reset on each application start
	
	while result:
		try:
			current_time = time.time()
			
			# Check for updates periodically (only if enabled)
			update_check_interval_seconds = UPDATE_CHECK_INTERVAL / 1000 if ENABLE_AUTO_UPDATE else 0
			if ENABLE_AUTO_UPDATE and (current_time - last_update_check) >= update_check_interval_seconds:
				if check_for_updates():
					# Updates were applied, restart immediately
					continue
				last_update_check = current_time
			
			print("Running in production mode. Press Ctrl+C to exit.")
			if ENABLE_AUTO_UPDATE and last_update_check == 0:
				hours = update_check_interval_seconds / 3600
				print(f"Auto-update enabled: checking for updates every {hours:.1f} hours.")
			elif ENABLE_AUTO_UPDATE:
				next_check = last_update_check + update_check_interval_seconds
				time_until_next = next_check - current_time
				if time_until_next > 0:
					hours_until_next = time_until_next / 3600
					print(f"Next update check in {hours_until_next:.1f} hours.")
			else:
				print("Auto-updates disabled.")
			
			# Pass the update interval to the run command
			run_cmd = [sys.executable, __file__, 'run', '--update-interval', str(UPDATE_CHECK_INTERVAL if ENABLE_AUTO_UPDATE else 0)]
			result = subprocess.run(run_cmd).returncode
			
			# Handle exit code 2 (update restart request)
			if result == 2:
				print("Application requested update restart...")
				if check_for_updates():
					# Updates were applied, restart immediately
					continue
				else:
					print("No updates found despite restart request.")
		except KeyboardInterrupt:
			print("Exiting due to keyboard interrupt.")
			break
		except Exception as e:
			print(f"An error occurred: {e}")
			print("Exiting...")
			break
		time.sleep(1)

if __name__ == "__main__":
	args = parse_arguments()
	
	if constants.DEBUG_PY or args.command == 'run':
		# Don't use the loop if running in debug mode or with run command
		print("Starting...")
		update_interval = 0
		if args.command == 'run' and hasattr(args, 'update_interval'):
			update_interval = args.update_interval
		main.setup(update_interval)
		exit_code = main.run()
		if exit_code == 2:
			sys.exit(2)  # Signal update restart needed
		assert False, "The script should not reach this point."
	else:
		# Default behavior - start with auto-update loop
		run_loop(args)
