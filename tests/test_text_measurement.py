#!/usr/bin/env python3
"""
Unit tests for the pluggable text measurement interface.

This module tests the global text measurement functions and their pluggable
interface in window_layout.py.
"""

import unittest
import sys
import os

# Add the project root to the path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import window_layout
from window_layout import LayoutText


class TestDefaultTextMeasurement(unittest.TestCase):
    """Test the default text measurement functions."""
    
    def setUp(self):
        """Ensure we start with default functions."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_basic_text_measurement(self):
        """Test basic text width measurement."""
        width = window_layout.measure_text_width("Hello World", "Arial")
        self.assertIsInstance(width, int)
        self.assertGreater(width, 0)
    
    def test_character_type_classification(self):
        """Test that character classification produces realistic ratios."""
        narrow_width = window_layout.measure_text_width("iii", "Arial")
        wide_width = window_layout.measure_text_width("WWW", "Arial")
        
        self.assertGreater(wide_width, narrow_width, 
                          "Wide characters should be wider than narrow ones")
        
        # The ratio should be reasonable (not extreme)
        ratio = wide_width / narrow_width
        self.assertGreater(ratio, 1.5, "Wide/narrow ratio should be substantial")
        self.assertLess(ratio, 10.0, "Wide/narrow ratio should not be extreme")
    
    def test_font_metrics(self):
        """Test that font metrics are returned with required keys."""
        metrics = window_layout.get_font_metrics("Arial")
        self.assertIsInstance(metrics, dict)
        self.assertIn('height', metrics)
        self.assertGreater(metrics['height'], 0)
    
    def test_empty_text(self):
        """Test measurement of empty text."""
        width = window_layout.measure_text_width("", "Arial")
        self.assertEqual(width, 0)
    
    def test_single_character(self):
        """Test measurement of single characters."""
        width_i = window_layout.measure_text_width("i", "Arial")
        width_W = window_layout.measure_text_width("W", "Arial")
        
        self.assertGreater(width_i, 0)
        self.assertGreater(width_W, 0)
        self.assertGreater(width_W, width_i)


class TestPluggableInterface(unittest.TestCase):
    """Test the pluggable text measurement interface."""
    
    def setUp(self):
        """Reset to defaults before each test."""
        window_layout.set_text_measurement_functions(None, None)
    
    def tearDown(self):
        """Restore defaults after each test."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_custom_width_function(self):
        """Test replacing the width measurement function."""
        def custom_measure_text(text, font):
            return len(text) * 10  # Simple fixed-width estimation
        
        # Set custom function
        window_layout.set_text_measurement_functions(custom_measure_text, None)
        
        # Test that custom function is being used
        width = window_layout.measure_text_width("Hello", "Arial")
        self.assertEqual(width, 50)  # 5 characters * 10
    
    def test_custom_metrics_function(self):
        """Test replacing the font metrics function."""
        def custom_font_metrics(font):
            return {"height": 100, "ascent": 75, "descent": 25}
        
        # Set custom function
        window_layout.set_text_measurement_functions(None, custom_font_metrics)
        
        # Test that custom function is being used
        metrics = window_layout.get_font_metrics("Arial")
        self.assertEqual(metrics["height"], 100)
        self.assertEqual(metrics["ascent"], 75)
        self.assertEqual(metrics["descent"], 25)
    
    def test_both_custom_functions(self):
        """Test replacing both functions simultaneously."""
        def custom_width(text, font):
            return len(text) * 20
        
        def custom_metrics(font):
            return {"height": 200}
        
        # Set both functions
        window_layout.set_text_measurement_functions(custom_width, custom_metrics)
        
        # Test both are working
        width = window_layout.measure_text_width("Hi", "Arial")
        metrics = window_layout.get_font_metrics("Arial")
        
        self.assertEqual(width, 40)  # 2 characters * 20
        self.assertEqual(metrics["height"], 200)
    
    def test_restore_defaults(self):
        """Test restoring default functions."""
        # Set custom functions first
        window_layout.set_text_measurement_functions(
            lambda t, f: 999, 
            lambda f: {"height": 999}
        )
        
        # Verify custom functions are active
        self.assertEqual(window_layout.measure_text_width("test", "Arial"), 999)
        self.assertEqual(window_layout.get_font_metrics("Arial")["height"], 999)
        
        # Restore defaults
        window_layout.set_text_measurement_functions(None, None)
        
        # Verify defaults are restored
        width = window_layout.measure_text_width("test", "Arial")
        metrics = window_layout.get_font_metrics("Arial")
        
        self.assertNotEqual(width, 999)
        self.assertNotEqual(metrics["height"], 999)
        self.assertGreater(width, 0)
        self.assertGreater(metrics["height"], 0)


class TestLayoutTextIntegration(unittest.TestCase):
    """Test that LayoutText works with the pluggable interface."""
    
    def setUp(self):
        """Reset to defaults before each test."""
        window_layout.set_text_measurement_functions(None, None)
    
    def tearDown(self):
        """Restore defaults after each test."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_layout_text_with_defaults(self):
        """Test LayoutText with default measurement functions."""
        text_widget = LayoutText("The quick brown fox jumps", font="Arial")
        
        # Test width request
        width_request = text_widget.query_width_request()
        self.assertIsInstance(width_request, int)
        self.assertGreater(width_request, 0)
        
        # Test text wrapping
        wrapped_width = text_widget.try_shrink_width(100)
        self.assertIsInstance(wrapped_width, int)
        self.assertGreater(wrapped_width, 0)
        
        # Test get_extents
        extents = text_widget.get_extents(text_widget.text)
        self.assertIsInstance(extents, tuple)
        self.assertEqual(len(extents), 2)
        self.assertGreater(extents[0], 0)  # width
        self.assertGreater(extents[1], 0)  # height
    
    def test_layout_text_with_custom_functions(self):
        """Test LayoutText with custom measurement functions."""
        # Set simple custom functions
        window_layout.set_text_measurement_functions(
            lambda t, f: len(t) * 8,  # 8 pixels per character
            lambda f: {"height": 16}
        )
        
        text_widget = LayoutText("Hello", font="Arial")
        
        # Test that custom functions are being used in preferred width
        preferred_width = text_widget.get_preferred_width()
        self.assertEqual(preferred_width, 40)  # 5 characters * 8
        
        extents = text_widget.get_extents("Hello")
        self.assertEqual(extents, (40, 16))
    
    def test_text_wrapping_with_custom_functions(self):
        """Test intelligent text wrapping with custom measurement."""
        # Set predictable custom measurement
        window_layout.set_text_measurement_functions(
            lambda t, f: len(t) * 10,  # 10 pixels per character
            lambda f: {"height": 16}
        )
        
        text_widget = LayoutText("Hello World", font="Arial")
        
        # Original text is "Hello World" = 11 characters = 110 pixels
        # Try to shrink to 60 pixels - should wrap to two lines
        # "Hello" = 50 pixels, "World" = 50 pixels
        wrapped_width = text_widget.try_shrink_width(60)
        
        # Should return the width of the longer line
        self.assertEqual(wrapped_width, 50)  # "Hello" or "World" = 5 chars * 10


if __name__ == '__main__':
    unittest.main()
