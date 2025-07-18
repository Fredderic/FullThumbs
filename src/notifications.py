"""
Windows toast notification system for FullThumbs.

This module provides a simple interface for showing Windows 10/11 toast notifications
with per-session tracking to avoid notification spam.
"""

import os
import sys
import time
import threading
import subprocess
from typing import Optional, Dict, Any

# Global notification state tracking
_corruption_notification_shown = False

def can_show_notification(notification_type: str) -> bool:
	"""Check if we can show a notification of the given type without spamming."""
	if notification_type == 'corruption':
		global _corruption_notification_shown
		return not _corruption_notification_shown
	
	return True

def show_corruption_notification() -> bool:
	"""Show a toast notification about installation corruption."""
	if not can_show_notification('corruption'):
		return False
	
	try:
		# Try to use Windows 10/11 toast notifications
		if _show_toast_notification():
			global _corruption_notification_shown
			_corruption_notification_shown = True
			return True
		else:
			# Fallback to console message
			print("⚠️  Installation corruption detected - use 'python full-thumbs.py force-reinstall' to recover")
			return False
	except Exception as e:
		print(f"Failed to show notification: {e}")
		return False

def _show_toast_notification() -> bool:
	"""Show a Windows toast notification using the best available method."""
	try:
		# Try using plyer (cross-platform notification library)
		return _show_toast_with_plyer()
	except ImportError:
		try:
			# Try using win10toast (Windows-specific)
			return _show_toast_with_win10toast()
		except ImportError:
			try:
				# Try using Windows PowerShell as fallback
				return _show_toast_with_powershell()
			except Exception:
				return False

def _show_toast_with_plyer() -> bool:
	"""Show notification using plyer library."""
	try:
		from plyer import notification  # type: ignore
		
		notification.notify(
			title="FullThumbs - Installation Corrupted",
			message="Automatic updates failed due to corrupted installation. Run 'python full-thumbs.py force-reinstall' to recover.",
			app_name="FullThumbs",
			timeout=10
		)
		return True
	except ImportError:
		raise ImportError("plyer not available")
	except Exception as e:
		print(f"Plyer notification failed: {e}")
		return False

def _show_toast_with_win10toast() -> bool:
	"""Show notification using win10toast library."""
	try:
		from win10toast import ToastNotifier  # type: ignore
		
		toaster = ToastNotifier()
		toaster.show_toast(
			"FullThumbs - Installation Corrupted",
			"Automatic updates failed due to corrupted installation. Run 'python full-thumbs.py force-reinstall' to recover.",
			duration=10,
			threaded=True
		)
		return True
	except ImportError:
		raise ImportError("win10toast not available")
	except Exception as e:
		print(f"Win10toast notification failed: {e}")
		return False

def _show_toast_with_powershell() -> bool:
	"""Show notification using PowerShell (Windows 10/11 built-in)."""
	try:
		import subprocess
		
		# PowerShell command to show toast notification
		powershell_script = """
		[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
		[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
		[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
		
		$template = @"
		<toast>
			<visual>
				<binding template="ToastGeneric">
					<text>FullThumbs - Installation Corrupted</text>
					<text>Automatic updates failed due to corrupted installation. Run 'python full-thumbs.py force-reinstall' to recover.</text>
				</binding>
			</visual>
		</toast>
"@
		
		$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
		$xml.LoadXml($template)
		$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
		[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FullThumbs").Show($toast)
		"""
		
		# Run PowerShell in the background
		def run_powershell():
			subprocess.run([
				'powershell.exe', 
				'-WindowStyle', 'Hidden',
				'-ExecutionPolicy', 'Bypass',
				'-Command', powershell_script
			], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
		
		# Run in thread to avoid blocking
		thread = threading.Thread(target=run_powershell, daemon=True)
		thread.start()
		
		return True
	except Exception as e:
		print(f"PowerShell notification failed: {e}")
		return False

def install_notification_dependencies():
	"""Install optional notification dependencies."""
	try:
		# Try to install plyer (lightweight and cross-platform)
		print("Installing notification dependencies...")
		subprocess.run([sys.executable, '-m', 'pip', 'install', 'plyer'], 
					  capture_output=True, check=True)
		print("Notification dependencies installed successfully.")
		return True
	except subprocess.CalledProcessError:
		print("Failed to install notification dependencies. Toast notifications will use PowerShell fallback.")
		return False
	except Exception as e:
		print(f"Error installing notification dependencies: {e}")
		return False
