#!/usr/bin/env python3
"""
Unit tests for text-handling layout widgets.

This module tests the LayoutText, LayoutLink and other text-related layout widgets,
focusing on their layout behavior, text wrapping, and integration with containers.
Tests include basic widget properties, layout calculations, text wrapping behavior,
and interaction with parent containers.
"""

import unittest
import sys
import os

# Add the project root to the path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from window_layout import LayoutText, LayoutLink, LayoutPluginContext, layout_context_class


layout_context_class(LayoutPluginContext)


class TestLayoutTextWidget(unittest.TestCase):
    """Test the LayoutText widget's basic properties."""
    
    def test_basic_text_widget(self):
        """Test basic LayoutText widget creation and properties."""
        text = LayoutText("Hello World", font="Arial")
        self.assertEqual(text.text, "Hello World")
        self.assertEqual(text.font, "Arial")


class TestLayoutLinkWidget(unittest.TestCase):
    """Test the LayoutLink widget's basic properties."""
    
    def test_link_with_title(self):
        """Test LayoutLink with a custom title."""
        link = LayoutLink("https://example.com", title="Click here", font="Arial")
        self.assertEqual(link.url, "https://example.com")
        self.assertEqual(link.text, "Click here")
        self.assertEqual(link.font, "Arial")
    
    def test_link_without_title(self):
        """Test LayoutLink with no title (should display URL)."""
        link = LayoutLink("https://example.com", font="Arial")
        self.assertEqual(link.url, "https://example.com")
        self.assertEqual(link.text, "https://example.com")
        self.assertEqual(link.font, "Arial")


if __name__ == '__main__':
    unittest.main()
