"""
Test script demonstrating the Win32 plugin system for layout widgets.

This shows how the plugin system ensures that when Win32Edit creates an internal
LayoutText widget, it actually gets a Win32Text widget instead.
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from window_layout import *
from win32_widgets import *

def test_plugin_system():
	"""Test that the plugin system works correctly for inter-widget dependencies."""
	
	print("=== Testing Simplified Plugin System ===")
	print()
	
	# Import the global context
	from window_layout import _layout_context
	
	# First, test with default context (should use LayoutText)
	print("1. Using default context:")
	print(f"   Current context type: {type(_layout_context).__name__ if _layout_context else 'None'}")
	
	# Create an edit widget (this will create an internal text widget)
	edit1 = LayoutEdit("Test text", multiline=True)
	print(f"   Created LayoutEdit with internal text widget: {type(edit1._text_layout).__name__}")
	print()
	
	# Now setup Win32 context and test again
	print("2. After setting up Win32 context:")
	win32_context = setup_win32_layout_context()
	print(f"   Win32 context type: {type(win32_context).__name__}")
	
	# Create a new edit widget (should use Win32Text for internal widget)
	edit2 = LayoutEdit("Win32 test text", multiline=True)
	print(f"   Created LayoutEdit with internal text widget: {type(edit2._text_layout).__name__}")
	print()
	
	# Test that the measurement functions are properly accessible
	print("3. Testing measurement function consistency:")
	print(f"   Context measure_text_width available: {hasattr(_layout_context, 'measure_text_width')}")
	print(f"   Context get_font_metrics available: {hasattr(_layout_context, 'get_font_metrics')}")
	
	# Test actual measurement
	test_text = "Hello World"
	width = _layout_context.measure_text_width(test_text)
	metrics = _layout_context.get_font_metrics()
	print(f"   Measured '{test_text}' width: {width}")
	print(f"   Font metrics: {metrics}")
	print()
	
	# Test widget creation through context
	print("4. Testing widget creation through context:")
	text_widget = _layout_context.create_text("Context-created text")
	print(f"   Text widget type: {type(text_widget).__name__}")
	print(f"   Text content: '{text_widget.text}'")
	print()
	
	print("=== Simplified Plugin System Test Complete ===")

if __name__ == "__main__":
	test_plugin_system()
