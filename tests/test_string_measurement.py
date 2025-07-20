#!/usr/bin/env python3
"""
Unit tests for string-based text measurement system.

This module tests the character classification, text wrapping accuracy,
and mixed script support in the text measurement system.
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


class TestCharacterClassification(unittest.TestCase):
    """Test character type classification and width estimation."""
    
    def setUp(self):
        """Ensure we start with default functions."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_narrow_vs_wide_characters(self):
        """Test that narrow and wide characters have appropriate relative widths."""
        narrow_text = "iiiiiiiiiii"  # 11 narrow characters
        wide_text = "WWWWWWWWWWW"  # 11 wide characters
        
        narrow_width = window_layout.measure_text_width(narrow_text, "Arial")
        wide_width = window_layout.measure_text_width(wide_text, "Arial")
        
        self.assertGreater(wide_width, narrow_width)
        
        # Wide characters should be significantly wider than narrow ones
        ratio = wide_width / narrow_width
        self.assertGreater(ratio, 2.0, "Wide characters should be much wider than narrow")
        self.assertLess(ratio, 10.0, "Ratio should not be extreme")
    
    def test_mixed_character_types(self):
        """Test measurement of text with mixed character types."""
        test_cases = [
            ("Hello World", "Basic English"),
            ("i" * 10, "Only narrow characters"),
            ("W" * 5, "Only wide characters"),
            ("..." * 5, "Punctuation"),
            ("Hello 世界", "Mixed English + CJK"),
        ]
        
        for text, description in test_cases:
            with self.subTest(text=text, description=description):
                width = window_layout.measure_text_width(text, "Arial")
                self.assertIsInstance(width, int)
                self.assertGreater(width, 0, f"Width should be positive for: {description}")
    
    def test_empty_and_whitespace(self):
        """Test measurement of empty and whitespace-only text."""
        self.assertEqual(window_layout.measure_text_width("", "Arial"), 0)
        
        # Spaces should have some width
        space_width = window_layout.measure_text_width(" ", "Arial")
        self.assertGreater(space_width, 0)
        
        # Multiple spaces should scale
        multiple_spaces = window_layout.measure_text_width("   ", "Arial")
        self.assertGreater(multiple_spaces, space_width)
    
    def test_special_characters(self):
        """Test measurement of special characters and symbols."""
        special_cases = [
            ("©™®", "Copyright symbols"),
            ("←→↑↓", "Arrow symbols"),
            ("αβγδε", "Greek letters"),
            ("café", "Accented characters"),
        ]
        
        for text, description in special_cases:
            with self.subTest(text=text, description=description):
                width = window_layout.measure_text_width(text, "Arial")
                self.assertGreater(width, 0, f"Special characters should have width: {description}")


class TestTextWrappingAccuracy(unittest.TestCase):
    """Test text wrapping behavior with string-based measurement."""
    
    def setUp(self):
        """Ensure we start with default functions."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_simple_text_wrapping(self):
        """Test wrapping of simple text."""
        text_widget = LayoutText("Hello World")
        
        # Get full width
        full_width = text_widget.get_preferred_width()
        self.assertGreater(full_width, 0)
        
        # Test that we can't shrink below minimum (longest word)
        hello_width = window_layout.measure_text_width("Hello", "Arial")
        world_width = window_layout.measure_text_width("World", "Arial")
        expected_min = max(hello_width, world_width)
        
        actual_min = text_widget.try_shrink_width(1)  # Try to shrink very small
        self.assertGreaterEqual(actual_min, expected_min)
    
    def test_long_word_constraints(self):
        """Test that long words correctly set minimum width constraints."""
        long_word = "supercalifragilisticexpialidocious"
        text_widget = LayoutText(f"Short {long_word} text")
        
        # The minimum achievable width should be at least the long word's width
        long_word_width = window_layout.measure_text_width(long_word, "Arial")
        min_achievable = text_widget.try_shrink_width(10)
        
        self.assertGreaterEqual(min_achievable, long_word_width)
    
    def test_text_wrapping_with_mixed_widths(self):
        """Test wrapping behavior with mixed character widths."""
        # Text with very different character widths
        mixed_text = "iiiii WWWWW normal"
        text_widget = LayoutText(mixed_text)
        
        full_width = text_widget.get_preferred_width()
        half_width = text_widget.try_shrink_width(full_width // 2)
        
        # Should be able to wrap to something smaller than full width
        self.assertLess(half_width, full_width)
        self.assertGreater(half_width, 0)
    
    def test_unwrappable_text(self):
        """Test behavior with text that cannot be wrapped."""
        # Single long word
        long_word = "pneumonoultramicroscopicsilicovolcanoconiosiss"
        text_widget = LayoutText(long_word)
        
        word_width = window_layout.measure_text_width(long_word, "Arial")
        
        # Try to shrink to various small sizes
        for target in [10, 50, 100]:
            actual = text_widget.try_shrink_width(target)
            self.assertGreaterEqual(actual, word_width, 
                                  f"Cannot shrink below word width for target {target}")


class TestRealisticUIScenarios(unittest.TestCase):
    """Test with realistic UI text scenarios."""
    
    def setUp(self):
        """Ensure we start with default functions."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_button_labels(self):
        """Test measurement of typical button labels."""
        button_texts = ["OK", "Cancel", "Save", "Save As...", "Apply"]
        
        for text in button_texts:
            with self.subTest(text=text):
                width = window_layout.measure_text_width(text, "Arial")
                self.assertGreater(width, 0)
                self.assertLess(width, 200, "Button text should not be extremely wide")
    
    def test_error_messages(self):
        """Test measurement of error messages."""
        error_messages = [
            "File not found",
            "Error: Invalid input",
            "Warning: This action cannot be undone",
            "Error: 文件未找到 (File not found)",  # Mixed scripts
        ]
        
        for text in error_messages:
            with self.subTest(text=text):
                text_widget = LayoutText(text)
                width = text_widget.get_preferred_width()
                self.assertGreater(width, 0)
                
                # Should be able to wrap to reasonable widths
                wrapped = text_widget.try_shrink_width(200)
                self.assertGreater(wrapped, 0)
                self.assertLessEqual(wrapped, width)
    
    def test_internationalization(self):
        """Test measurement of international text."""
        international_texts = [
            ("Iñtërnâtiônàlizætiøn", "Accented Latin"),
            ("العربية", "Arabic"),
            ("हिन्दी", "Hindi"),
            ("中文", "Chinese"),
            ("русский", "Cyrillic"),
        ]
        
        for text, description in international_texts:
            with self.subTest(text=text, description=description):
                width = window_layout.measure_text_width(text, "Arial")
                self.assertGreater(width, 0, f"International text should have width: {description}")


class TestMeasurementConsistency(unittest.TestCase):
    """Test consistency and edge cases in text measurement."""
    
    def setUp(self):
        """Ensure we start with default functions."""
        window_layout.set_text_measurement_functions(None, None)
    
    def test_measurement_monotonicity(self):
        """Test that longer text generally has greater or equal width."""
        base_text = "Hello"
        base_width = window_layout.measure_text_width(base_text, "Arial")
        
        # Adding characters should generally increase width
        longer_text = base_text + " World"
        longer_width = window_layout.measure_text_width(longer_text, "Arial")
        
        self.assertGreaterEqual(longer_width, base_width)
    
    def test_measurement_repeatability(self):
        """Test that measuring the same text gives consistent results."""
        text = "Test repeatability"
        
        width1 = window_layout.measure_text_width(text, "Arial")
        width2 = window_layout.measure_text_width(text, "Arial")
        width3 = window_layout.measure_text_width(text, "Arial")
        
        self.assertEqual(width1, width2)
        self.assertEqual(width2, width3)
    
    def test_font_parameter_handling(self):
        """Test that font parameter is handled gracefully."""
        text = "Font test"
        
        # Should work with different font values
        width_arial = window_layout.measure_text_width(text, "Arial")
        width_times = window_layout.measure_text_width(text, "Times New Roman")
        width_none = window_layout.measure_text_width(text, None)
        
        # All should return valid widths
        for width in [width_arial, width_times, width_none]:
            self.assertIsInstance(width, int)
            self.assertGreater(width, 0)


if __name__ == '__main__':
    unittest.main()
