"""
Tests for thumbnail invalidation behavior using actual Win32 windows.
These tests require a Windows environment with DWM (Desktop Window Manager).
"""

import os
import sys
import unittest
import win32gui
import win32con
import win32api
import time

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.thumbnail import ThumbnailManager

class TestWindow:
    """Helper class to create and manage a test window."""
    def __init__(self, window_class="TestWindowClass", window_title="Test Window"):
        self.window_class = window_class
        self.window_title = window_title
        self.hwnd = None
        self._register_class()
        self._create_window()

    def _register_class(self):
        """Register the window class."""
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._window_proc
        wc.lpszClassName = self.window_class
        wc.hInstance = win32api.GetModuleHandle(None)
        win32gui.RegisterClass(wc)

    def _create_window(self):
        """Create the actual window."""
        self.hwnd = win32gui.CreateWindow(
            self.window_class,
            self.window_title,
            win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
            100, 100,  # x, y
            400, 300,  # width, height
            0, 0,      # parent, menu
            win32api.GetModuleHandle(None),
            None
        )

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """Basic window procedure."""
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        """Show the window."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def hide(self):
        """Hide the window."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def destroy(self):
        """Destroy the window."""
        if self.hwnd:
            win32gui.DestroyWindow(self.hwnd)
            self.hwnd = None

    def process_messages(self, timeout=0.1):
        """Process window messages for a short time."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            if win32gui.PumpWaitingMessages() == 1:  # WM_QUIT received
                break

class TestThumbnailInvalidation(unittest.TestCase):
    """Test the thumbnail invalidation behavior using actual Win32 windows."""

    def setUp(self):
        """Set up test windows."""
        self.source_window = TestWindow(window_class="SourceWindowClass", window_title="Source Window")
        self.target_window = TestWindow(window_class="TargetWindowClass", window_title="Target Window")
        
        # Give windows time to be created and shown
        self.source_window.process_messages()
        self.target_window.process_messages()

    def tearDown(self):
        """Clean up test windows."""
        self.source_window.destroy()
        self.target_window.destroy()
        # Process any remaining messages
        self.source_window.process_messages()
        self.target_window.process_messages()

    def test_thumbnail_invalidation(self):
        """Test that thumbnail becomes invalid when source window is hidden."""
        # Create thumbnail from source to target window
        target_rect = win32gui.GetClientRect(self.target_window.hwnd)
        thumbnail = ThumbnailManager(
            self.target_window.hwnd,
            target_rect,
            self.source_window.hwnd
        )

        # Initially the thumbnail should be valid
        self.assertTrue(thumbnail.is_valid)
        self.assertIsNotNone(thumbnail.current_thumb_rect)

        # Hide the source window
        self.source_window.hide()
        self.source_window.process_messages()

        # Handle source window status (simulating what the main app would do)
        if not win32gui.IsWindowVisible(self.source_window.hwnd):
            thumbnail.cleanup_thumbnail()

        # Thumbnail should be invalid but retain its rect
        self.assertFalse(thumbnail.is_valid)
        self.assertIsNotNone(thumbnail.current_thumb_rect)

        # Show the source window again
        self.source_window.show()
        self.source_window.process_messages()

        # Create new thumbnail (simulating what the main app would do)
        new_thumbnail = ThumbnailManager(
            self.target_window.hwnd,
            target_rect,
            self.source_window.hwnd
        )

        # New thumbnail should be valid
        self.assertTrue(new_thumbnail.is_valid)
        self.assertIsNotNone(new_thumbnail.current_thumb_rect)

if __name__ == '__main__':
    unittest.main()
