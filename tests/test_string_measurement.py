#!/usr/bin/env python3
"""
Unit tests for default text measurement approximations in LayoutPluginContext.

This module tests that the default text measurement functions provide reasonable
approximations suitable for layout testing, without requiring platform-specific
implementations.
"""

import unittest
import sys
import os

# Add the project root to the path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from functools import lru_cache
from window_layout import LayoutText, LayoutPluginContext, layout_context, layout_context_class
from typing import cast

layout_context_class(LayoutPluginContext)

class TestDefaultTextMeasurement(unittest.TestCase):
    """Test the default text measurement approximations using the global context."""
    
    def setUp(self):
        """Verify the global context is available and get the current context."""
        # Only test _layout_context directly in one place since we're testing the plugin system
        self.context = layout_context()
        assert self.context is not None, "Global layout context not initialized"

    def tearDown(self):
        """Clean up after each test."""
        self.context = None
    
    def test_character_classification(self):
        """Test that different character types are classified with appropriate widths."""
        # Test basic character classifications
        tests = [
            (self.context.measure_text_width("i", None), 4, "Narrow character 'i'"),
            (self.context.measure_text_width("W", None), 14, "Wide character 'W'"),
            (self.context.measure_text_width(" ", None), 4, "Space character"),
            (self.context.measure_text_width("a", None), 8, "Average width character 'a'"),
            (self.context.measure_text_width("世", None), 16, "CJK character"),
        ]
        
        for actual, expected, msg in tests:
            with self.subTest(msg=msg):
                self.assertEqual(actual, expected, msg)
    
    def test_text_scaling(self):
        """Test that text width scales reasonably with length."""
        # Test that multiple characters scale linearly
        single_i = self.context.measure_text_width("i", None)
        multiple_i = self.context.measure_text_width("iii", None)
        self.assertEqual(multiple_i, single_i * 3, "Width should scale linearly")
        
        # Mixed text should sum individual character widths
        mixed = self.context.measure_text_width("Hi!", None)
        expected = (10 + 4 + 8)  # H=10 (capital) + i=4 (narrow) + !=8 (punctuation)
        self.assertEqual(mixed, expected, "Mixed text width should sum individual widths")
    
    def test_empty_and_whitespace(self):
        """Test measurement of empty and whitespace text."""
        self.assertEqual(self.context.measure_text_width("", None), 0, "Empty string should have zero width")
        self.assertEqual(self.context.measure_text_width(" ", None), 4, "Space should have width 4")
        self.assertEqual(self.context.measure_text_width("   ", None), 12, "Multiple spaces should scale linearly")
    
    def test_font_metrics(self):
        """Test that font metrics provide reasonable defaults."""
        metrics = self.context.get_font_metrics(None)
        self.assertEqual(metrics['height'], 16, "Default font height should be 16")


class TestTextWrapping(unittest.TestCase):
    """Test text wrapping behavior using the default measurement approximations."""
    
    def setUp(self):
        """Set up test environment."""
        self.text_layout = LayoutText("Test text")  # LayoutText uses the default LayoutPluginContext
        
    def tearDown(self):
        """Clean up after each test."""
        self.text_layout = None
    
    def test_text_length_comparison(self):
        """Test that longer text gets wider measurements."""
        text_widget = LayoutText("Sample")
        
        # Test that longer words get wider measurements
        self.assertGreater(text_widget.get_extents("World")[0], 
                          text_widget.get_extents("Hi")[0])
    
    def test_text_wrapping_with_mixed_widths(self):
        """Test wrapping behavior with mixed character widths."""
        # Text with very different character widths
        mixed_text = "iiiii WWWWW normal"
        text_widget = LayoutText(mixed_text)
        
        # Test that wide characters take more space
        narrow_part = text_widget.get_extents("iiiii")[0]
        wide_part = text_widget.get_extents("WWWWW")[0]
        self.assertGreater(wide_part, narrow_part)
    
    def test_unwrappable_text(self):
        """Test text width calculations for long words."""
        # Single long word
        long_word = "supercalifragilisticexpialidocious"
        text_widget = LayoutText(long_word)
        
        # Test that long words get proportionally longer measurements
        long_width = text_widget.get_extents(long_word)[0]
        short_width = text_widget.get_extents("short")[0]
        self.assertGreater(long_width, short_width * 3)

if __name__ == '__main__':
    unittest.main()
