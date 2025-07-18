#!/usr/bin/env python3
"""
Test script for the notification system.
This can be run independently to test toast notifications.
"""

import sys
import os

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifications import show_corruption_notification, install_notification_dependencies

def main():
	print("Testing FullThumbs notification system...")
	
	# Test showing a corruption notification
	print("\nShowing corruption notification...")
	success = show_corruption_notification()
	
	if success:
		print("✅ Toast notification shown successfully!")
	else:
		print("❌ Toast notification failed, fell back to console message")
		
		# Offer to install dependencies
		install_deps = input("\nWould you like to install notification dependencies? (y/N): ").lower().strip()
		if install_deps == 'y':
			if install_notification_dependencies():
				print("\nTrying notification again...")
				success = show_corruption_notification()
				if success:
					print("✅ Toast notification now works!")
				else:
					print("❌ Still not working - using PowerShell fallback")
	
	print("\nTest complete!")

if __name__ == "__main__":
	main()
