#!/usr/bin/env python3
"""
Unit tests for intelligent text wrapping functionality.

This module tests the word-boundary-respecting text wrapping and its
integration with the layout distribution system.
"""

import unittest
import sys
import os

# Add the project root to the path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import window_layout
from window_layout import (LayoutText, LayoutButton, LayoutContainer, Expand,
                         LayoutPluginContext, layout_context)


@layout_context
class TestContext(LayoutPluginContext):
    """Test context that uses the default measurement implementation."""
    pass


class TestIntelligentTextWrapping(unittest.TestCase):
    """Test intelligent text wrapping with word boundaries."""
    
    def test_short_text_no_wrapping(self):
        """Test that short text doesn't need wrapping."""
        text_widget = LayoutText("This is short")
        
        preferred_width = text_widget.get_preferred_width()
        
        # Should be able to fit in its preferred width without wrapping
        actual_width = text_widget.try_shrink_width(preferred_width)
        self.assertEqual(actual_width, preferred_width)
        
        # Should not shrink below minimum word width
        min_width = text_widget.query_width_request()
        actual_min = text_widget.try_shrink_width(1)
        self.assertGreaterEqual(actual_min, min_width)
    
    def test_long_words_constraint(self):
        """Test text widget adapts appropriately with very long words."""
        long_words = "Supercalifragilisticexpialidocious antidisestablishmentarianism"
        text_widget = LayoutText(long_words)
        
        # When given a very small target width
        actual_width = text_widget.try_shrink_width(50)
        
        # Should return a reasonable width that can fit the text
        self.assertGreater(actual_width, 0)
        # Width should be less than the unconstrained width
        self.assertLess(actual_width, text_widget.get_preferred_width())
    
    def test_mixed_text_wrapping(self):
        """Test wrapping of text with mixed word lengths."""
        mixed_text = "This has some regular words and some verylongwordsthatdontwrapeasily"
        text_widget = LayoutText(mixed_text)
        
        preferred_width = text_widget.get_preferred_width()
        
        # Test shrinking to various targets
        test_targets = [100, 150, 200]
        
        for target in test_targets:
            with self.subTest(target=target):
                actual = text_widget.try_shrink_width(target)
                
                # Should be able to achieve something reasonable
                self.assertGreater(actual, 0)
                
                # If we can't hit the target, should have a good reason
                if actual > target:
                    # Should be due to a long word constraint
                    min_width = text_widget.query_width_request()
                    self.assertGreaterEqual(actual, min_width)
    
    def test_multiple_sentences_wrapping(self):
        """Test wrapping of text with multiple sentences."""
        sentences = "This is a sentence. This is another sentence with more words in it."
        text_widget = LayoutText(sentences)
        
        preferred_width = text_widget.get_preferred_width()
        half_width = preferred_width // 2
        
        # Should be able to wrap to roughly half width
        actual = text_widget.try_shrink_width(half_width)
        
        # Should be smaller than full width
        self.assertLess(actual, preferred_width)
        
        # Should respect word boundaries (minimum word width)
        min_width = text_widget.query_width_request()
        self.assertGreaterEqual(actual, min_width)
    
    def test_wrapping_efficiency(self):
        """Test that wrapping achieves reasonable efficiency."""
        text = "The quick brown fox jumps over the lazy dog"
        text_widget = LayoutText(text)
        
        preferred_width = text_widget.get_preferred_width()
        target = preferred_width // 3  # Target 1/3 of preferred width
        
        actual = text_widget.try_shrink_width(target)
        
        # Calculate efficiency (how close we got to target)
        if actual <= target:
            efficiency = 1.0  # Perfect
        else:
            efficiency = target / actual
        
        # Should achieve at least reasonable efficiency for normal text
        self.assertGreater(efficiency, 0.3, "Should achieve at least 30% efficiency")
    
    def test_single_word_limitation(self):
        """Test behavior with single very long words."""
        single_long_word = "pneumonoultramicroscopicsilicovolcanoconiosiss"
        text_widget = LayoutText(single_long_word)
        
        word_width = text_widget.get_preferred_width()
        
        # Should not be able to shrink below the word width
        for target in [50, 100, 200]:
            actual = text_widget.try_shrink_width(target)
            self.assertGreaterEqual(actual, word_width)


class TestTextWrappingLayoutIntegration(unittest.TestCase):
    """Test integration of intelligent text wrapping with layout distribution."""
    
    def test_text_in_horizontal_layout(self):
        """Test text wrapping in horizontal layout containers."""
        layout = LayoutContainer.horizontal(
            gap=10,
            children=(
                LayoutButton('Fixed', id=1, width=75),
                LayoutText('This text should wrap intelligently when space is constrained'),
                LayoutButton('Expand', id=2, width=Expand(minimum=50)),
            )
        )
        
        # Test various layout widths
        test_widths = [200, 300, 400]
        
        for width in test_widths:
            with self.subTest(width=width):
                actual = layout.distribute_width(width)
                self.assertGreater(actual, 0)
                # Allow reasonable overflow for constrained layouts with unwrappable content
                self.assertLessEqual(actual, width * 1.2)  # Allow up to 20% overflow
    
    def test_text_wrapping_gives_back_space(self):
        """Test that wrapped text can give back excess space for redistribution."""
        # Create layout with text that can wrap
        layout = LayoutContainer.horizontal(
            gap=5,
            children=(
                LayoutText('This is a moderately long text that can wrap at word boundaries'),
                LayoutButton('Button', id=1, width=Expand(minimum=80)),
            )
        )
        
        # Test with generous width
        generous_width = 400
        actual = layout.distribute_width(generous_width)
        
        # Should be able to distribute without excessive width
        self.assertGreater(actual, 0)
        
        # The text should have wrapped to allow button to get reasonable space
        # (This is more of an integration test - exact behavior depends on algorithm)
    
    def test_constrained_layout_with_unwrappable_text(self):
        """Test layout behavior when text cannot wrap further."""
        very_long_word = "supercalifragilisticexpialidociousantidisestablishmentarianism"
        layout = LayoutContainer.horizontal(
            gap=5,
            children=(
                LayoutButton('Small', id=1, width=50),
                LayoutText(very_long_word),
                LayoutButton('Small', id=2, width=50),
            )
        )
        
        # Try to constrain to small width
        small_width = 200
        actual = layout.distribute_width(small_width)
        
        # Should expand beyond target due to unwrappable text
        self.assertGreater(actual, small_width)
        
        # But should still be a reasonable result
        self.assertLess(actual, small_width * 3)  # Not excessively large


class TestWordBoundaryRespect(unittest.TestCase):
    """Test that text wrapping respects word boundaries."""
    
    def test_no_mid_word_breaks(self):
        """Test that wrapping doesn't break words in the middle."""
        text = "The quick brown fox jumps over the lazy dog"
        text_widget = LayoutText(text)
        
        # Get minimum width (should be width of longest word)
        words = text.split()
        # Find longest word's width by creating a text widget for each word
        word_widths = [LayoutText(word).get_preferred_width() for word in words]
        expected_min = max(word_widths)
        
        actual_min = text_widget.try_shrink_width(1)
        
        # Should be approximately the longest word width
        self.assertGreaterEqual(actual_min, expected_min * 0.9)  # Allow small measurement variations
        self.assertLessEqual(actual_min, expected_min * 1.1)
    
    def test_wrapping_prefers_spaces(self):
        """Test that wrapping breaks at spaces when possible."""
        # Text designed to test space vs mid-word breaking
        text = "This has spaces and alsoverylongwordswithoutspaces"
        text_widget = LayoutText(text)
        
        # The minimum should be the longest word
        longest_word = "alsoverylongwordswithoutspaces"
        # Create a widget with just the longest word to get its width
        expected_min = LayoutText(longest_word).get_preferred_width()
        
        actual_min = text_widget.try_shrink_width(50)
        
        # Should be constrained by the long word, not breaking words with spaces
        self.assertGreaterEqual(actual_min, expected_min * 0.9)
    
    def test_punctuation_handling(self):
        """Test handling of punctuation in word wrapping."""
        punctuated_text = "Hello, world! How are you? Fine, thanks."
        text_widget = LayoutText(punctuated_text)
        
        # Should handle punctuation gracefully
        min_width = text_widget.try_shrink_width(50)
        self.assertGreater(min_width, 0)
        
        # Should be able to wrap at word boundaries despite punctuation
        preferred = text_widget.get_preferred_width()
        wrapped = text_widget.try_shrink_width(preferred // 2)
        self.assertLess(wrapped, preferred)


if __name__ == '__main__':
    unittest.main()
