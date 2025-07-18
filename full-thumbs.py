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

import sys, os, argparse, subprocess

from src import main, constants
from utilities import parse_time_interval, validate_auto_update_interval, format_time_interval_words

# --- Core Functions ---

def parse_arguments():
	"""Parse command line arguments."""
	# Get dynamic values for help text
	default_interval = format_time_interval_words(constants.DEFAULT_UPDATE_INTERVAL_MS)
	minimum_interval = format_time_interval_words(constants.MIN_UPDATE_INTERVAL_MS)
	
	parser = argparse.ArgumentParser(
		description='FullThumbs - Picture-in-Picture thumbnail viewer',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog=f"""
Auto-update examples:
  --auto-update        Default {default_interval} interval
  --auto-update=2h     Check every 2 hours
  --auto-update=30m    Check every 30 minutes (minimum {minimum_interval})
  --auto-update=1d     Check every day
  --auto-update=default   Use configured default interval ({default_interval})
  --auto-update=minimum   Use configured minimum interval ({minimum_interval})
  --no-auto-update     Disable auto-updates
Note: Auto-update intervals must be at least {minimum_interval}.
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
	run_parser.add_argument('--debug-simulate-update', action='store_true',
							help='Debug mode: simulate finding updates and request restart')
	
	# Force reinstall subcommand
	reinstall_parser = subparsers.add_parser(
		'force-reinstall',
		help='Force re-install from git repository (DESTRUCTIVE: resets source files, preserves settings and venv)'
	)
	reinstall_parser.add_argument('--yes', action='store_true',
								  help='Confirm the destructive operation without prompting')
	
	# Auto-update arguments for main command (when no subcommand is used)
	auto_group = parser.add_mutually_exclusive_group()
	auto_group.add_argument('--auto-update', nargs='?', const='default', metavar='INTERVAL',
			help=f'Enable auto-updates with optional interval (default: {default_interval},'
				f' special values: "default", "minimum")')
	auto_group.add_argument('--no-auto-update', action='store_true',
			help='Disable auto-updates completely')
	
	# Debug override option
	parser.add_argument('--debug-loop', action='store_true',
			help='Debug the production restart loop with git updates disabled')
	
	return parser.parse_args()

# --- Main Logic ---

def check_for_updates():
	"""Check for git updates and pull if available."""
	try:
		repo_dir = os.path.dirname(os.path.abspath(__file__))
		
		# Get the current commit hash to detect manual updates
		current_commit = subprocess.run(
			['git', 'rev-parse', 'HEAD'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		).stdout.strip()
		
		# Check if the commit has changed since last check (indicating manual update)
		last_commit = getattr(check_for_updates, '_last_commit', None)
		if last_commit and last_commit != current_commit:
			print("Installation appears to have been updated manually - triggering restart to refresh application...")
			check_for_updates._last_commit = current_commit
			return True  # Trigger restart/update cycle
		
		# Store the current commit for next check
		check_for_updates._last_commit = current_commit
		
		# Check working directory status
		status_result = subprocess.run(
			['git', 'status', '--porcelain'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		
		has_uncommitted_changes = bool(status_result.stdout.strip())
		
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
			
			if has_uncommitted_changes:
				print("WARNING: Working directory has uncommitted changes. Skipping update.")
				# This indicates potential corruption - show notification
				try:
					from src.notifications import show_corruption_notification
					show_corruption_notification()
				except ImportError:
					print("⚠️  Installation corruption detected - use 'python full-thumbs.py force-reinstall' to recover")
				return False
			
			# Pull the latest changes
			subprocess.run(['git', 'pull'], cwd=repo_dir, check=True)
			print("Update complete! Restarting application...")
			# Update our stored commit hash since we just pulled
			check_for_updates._last_commit = subprocess.run(
				['git', 'rev-parse', 'HEAD'],
				cwd=repo_dir,
				capture_output=True,
				text=True,
				check=True
			).stdout.strip()
			return True
		else:
			print("Application is up to date.")
			return False
			
	except subprocess.CalledProcessError as e:
		print(f"Git operation failed: {e}")
		# Git operation failure might indicate corruption
		try:
			from src.notifications import show_corruption_notification
			show_corruption_notification()
		except ImportError:
			print("⚠️  Installation corruption detected - use 'python full-thumbs.py force-reinstall' to recover")
		return False
	except Exception as e:
		print(f"Error checking for updates: {e}")
		return False

def reinstall_from_git(confirmed=False):
	"""Re-install from git repository, resetting source files while preserving settings and venv."""
	try:
		repo_dir = os.path.dirname(os.path.abspath(__file__))
		
		# First, check what would be affected
		print("Checking repository status...")
		status_result = subprocess.run(
			['git', 'status', '--porcelain'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		
		if not confirmed:
			if status_result.stdout.strip():
				print("\n⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️")
				print("This will permanently reset ALL source files to the git repository state.")
				print("The following will be PRESERVED:")
				print("  • Settings files (*.json)")
				print("  • Virtual environment (.venv/, venv/)")
				print("  • User data and configurations")
				
				print("\nThe following files will be LOST:")
				for line in status_result.stdout.strip().split('\n'):
					status_code = line[:2]
					file_path = line[3:] if len(line) > 3 else line
					if status_code.strip():
						print(f"  • {file_path}")
				
				print("\nTo proceed with this destructive operation, run:")
				print("  python full-thumbs.py force-reinstall --yes")
				return False
			else:
				print("No modified files detected - proceeding with reinstall...")
				# No changes to lose, so we can proceed without confirmation
		
		print("Re-installing from git repository...")
		print("This will reset all source files to the repository state.")
		print("Settings files and virtual environment will be preserved.")
		
		# Fetch latest changes from remote
		print("\n1. Fetching latest changes...")
		subprocess.run(['git', 'fetch'], cwd=repo_dir, check=True, capture_output=True)
		
		# Reset all tracked files to HEAD
		print("\n2. Resetting source files to repository state...")
		subprocess.run(['git', 'reset', '--hard', 'HEAD'], cwd=repo_dir, check=True)
		
		# Clean untracked files (but preserve important ones)
		print("\n3. Cleaning untracked files (preserving settings and venv)...")
		# Remove untracked files except for settings and venv
		subprocess.run(['git', 'clean', '-fd', '--exclude=*.json', '--exclude=.venv/', '--exclude=venv/'], 
					  cwd=repo_dir, check=True)
		
		# Pull latest changes
		print("\n4. Pulling latest changes...")
		subprocess.run(['git', 'pull'], cwd=repo_dir, check=True)
		
		print("\n✅ Re-installation complete!")
		print("Source files have been reset to the repository state.")
		print("Settings files and virtual environment have been preserved.")
		return True
		
	except subprocess.CalledProcessError as e:
		print(f"❌ Git operation failed: {e}")
		return False
	except Exception as e:
		print(f"❌ Error during re-installation: {e}")
		return False

def run_loop(args):
	import time
	
	# Check if we're in debug loop mode
	is_debug_loop = getattr(args, 'debug_loop', False)
	
	# Determine auto-update settings
	if getattr(args, 'no_auto_update', False) or (constants.DEBUG_PY and not is_debug_loop):
		ENABLE_AUTO_UPDATE = False
		UPDATE_CHECK_INTERVAL = 0
	elif args.auto_update is None:
		# Neither --auto-update nor --no-auto-update specified, use default behavior
		ENABLE_AUTO_UPDATE = True
		interval_ms = parse_time_interval('default')  # Use default interval
		UPDATE_CHECK_INTERVAL = validate_auto_update_interval(interval_ms)
	else:
		# --auto-update was specified with a value
		ENABLE_AUTO_UPDATE = True
		interval_ms = parse_time_interval(args.auto_update)
		UPDATE_CHECK_INTERVAL = validate_auto_update_interval(interval_ms)
		if UPDATE_CHECK_INTERVAL is None:
			minimum_interval = format_time_interval_words(constants.MIN_UPDATE_INTERVAL_MS)
			print(f"Error: Invalid time interval '{args.auto_update}'. Intervals must be at least {minimum_interval}.")
			sys.exit(1)
	
	# If in debug loop mode, disable git operations but keep the timing logic
	if is_debug_loop:
		print("🐛 Debug loop mode: Git updates disabled, but timing logic active")
		ENABLE_GIT_OPERATIONS = False
	else:
		ENABLE_GIT_OPERATIONS = ENABLE_AUTO_UPDATE
	
	result = 1
	last_update_check = 0  # Reset on each application start
	
	while result:
		try:
			current_time = time.time()
			
			# Check for updates periodically (only if enabled)
			update_check_interval_seconds = UPDATE_CHECK_INTERVAL / 1000 if ENABLE_AUTO_UPDATE else 0
			if ENABLE_AUTO_UPDATE and (current_time - last_update_check) >= update_check_interval_seconds:
				if ENABLE_GIT_OPERATIONS:
					if check_for_updates():
						# Updates were applied, restart immediately
						continue
					last_update_check = current_time
				else:
					# Debug mode: simulate update check and finding updates
					print("🐛 Debug: Simulating update check (no git operations)")
					print("🐛 Debug: Simulating 'updates found' - will trigger restart cycle")
					last_update_check = current_time
					# In debug mode, simulate finding updates by triggering a restart request
					# This will test the full restart loop logic without actual git operations
			
			if is_debug_loop:
				print("🐛 Running in debug loop mode. Press Ctrl+C to exit.")
			else:
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
			if is_debug_loop:
				# In debug mode, pass a special flag to simulate update restart
				run_cmd.append('--debug-simulate-update')
			result = subprocess.run(run_cmd).returncode
			
			# Handle different exit codes
			if result == 0:
				# Normal exit, break the loop
				print("Application exited normally.")
				break
			elif result == 1:
				# Fatal error (e.g., Python import errors, argument errors, etc.)
				print("Application encountered a fatal error and cannot continue.")
				break
			elif result == 2:
				# Update restart request
				print("Application requested update restart...")
				if ENABLE_GIT_OPERATIONS and check_for_updates():
					# Updates were applied, restart immediately
					continue
				elif is_debug_loop:
					print("🐛 Debug: Update restart requested but git operations disabled")
				else:
					print("No updates found despite restart request.")
			else:
				# Other unexpected exit codes
				print(f"Application exited with unexpected code {result}. Stopping.")
				break
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
	
	# Handle force reinstall subcommand
	if args.command == 'force-reinstall':
		# Prevent reinstall in debug mode to protect development environment
		if constants.DEBUG_PY:
			print("❌ Force reinstall is disabled in debug mode to protect the development environment.")
			print("To reinstall, run the application outside of the debugger.")
			sys.exit(1)
		
		confirmed = getattr(args, 'yes', False)
		success = reinstall_from_git(confirmed)
		if success:
			print("\nApplication has been re-installed successfully.")
			print("You can now run the application normally.")
		sys.exit(0 if success else 1)
	
	# Check if we should enable debug loop mode
	debug_loop = getattr(args, 'debug_loop', False)
	is_debug_mode = constants.DEBUG_PY and not debug_loop
	
	if is_debug_mode or args.command == 'run':
		# Don't use the loop if running in debug mode or with run command
		print("Starting...")

		update_interval = getattr(args, 'update_interval', 0) if args.command == 'run' else 0
		simulate_update = getattr(args, 'debug_simulate_update', False)
		main.setup(update_interval, simulate_update)
		
		if simulate_update:
			# In debug mode, the application will exit with code 2 when timer fires
			print("🐛 Debug: Application will simulate finding updates on timer event...")

		exit_code = main.run()
		sys.exit(exit_code)
		assert False, "The script should not reach this point."
	else:
		# Default behavior - start with auto-update loop
		# This includes --debug-loop which will run the loop but disable git
		run_loop(args)
