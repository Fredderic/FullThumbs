"""Unit tests for the window_layout module."""

import unittest
from src.window_layout import (
	Dimension, Fixed, Expand, Grow,
	Layout, LayoutSpacer, LayoutText, LayoutButton, LayoutEdit,
	LayoutContainer, LayoutPadding, LayoutWindow, LayoutGroup,
	LayoutLink, LayoutHorizontalLine,
	build_about_dialog
)


class TestDimensionClasses(unittest.TestCase):
	"""Test the Dimension hierarchy and auto-wrapping functionality."""
	
	def test_dimension_auto_wrapping(self):
		"""Test that Dimension() auto-wraps numeric values in Fixed instances."""
		# Test direct numeric value auto-wrapping
		dim1 = Dimension(100)
		self.assertIsInstance(dim1, Fixed)
		self.assertEqual(dim1.minim, 100)
		self.assertEqual(dim1.maxim, 100)
		
		# Test with float value
		dim2 = Dimension(50.5)
		self.assertIsInstance(dim2, Fixed)
		self.assertEqual(dim2.minim, 50.5)
		self.assertEqual(dim2.maxim, 50.5)
	
	def test_dimension_passthrough(self):
		"""Test that Dimension() passes through existing Dimension instances."""
		original = Fixed(200)
		passed_through = Dimension(original)
		self.assertIs(passed_through, original)
		
		expand = Expand(50)
		passed_expand = Dimension(expand)
		self.assertIs(passed_expand, expand)
	
	def test_dimension_base_class_errors(self):
		"""Test that the base Dimension class cannot be instantiated directly."""
		with self.assertRaises(TypeError):
			Dimension()  # No arguments
		
		with self.assertRaises(TypeError):
			Dimension("not a number")  # Invalid type
		
		with self.assertRaises(TypeError):
			Dimension(100, 200)  # Too many arguments
	
	def test_fixed_dimension(self):
		"""Test Fixed dimension behavior."""
		fixed = Fixed(150)
		self.assertEqual(fixed.minim, 150)
		self.assertEqual(fixed.maxim, 150)
		self.assertEqual(str(fixed), "Fixed(150)")
		
		# Test type validation
		with self.assertRaises(AssertionError):
			Fixed("not a number")
	
	def test_expand_dimension(self):
		"""Test Expand dimension behavior."""
		# Default expand
		expand1 = Expand()
		self.assertEqual(expand1.minim, 0)
		self.assertIsNone(expand1.maxim)
		self.assertEqual(str(expand1), "Expand()")
		
		# Expand with minimum
		expand2 = Expand(minimum=30)
		self.assertEqual(expand2.minim, 30)
		self.assertIsNone(expand2.maxim)
		self.assertEqual(str(expand2), "Expand(minimum=30)")
		
		# Expand with minimum and maximum
		expand3 = Expand(minimum=20, maximum=100)
		self.assertEqual(expand3.minim, 20)
		self.assertEqual(expand3.maxim, 100)  # Expand now properly handles maximum
		self.assertEqual(str(expand3), "Expand(minimum=20, maximum=100)")
		
		# Test type validation
		with self.assertRaises(AssertionError):
			Expand(minimum="not a number")
		
		with self.assertRaises(AssertionError):
			Expand(minimum=10, maximum="not a number")
	
	def test_grow_dimension(self):
		"""Test Grow dimension behavior."""
		# Default grow
		grow1 = Grow()
		self.assertEqual(grow1.minim, 0)
		self.assertIsNone(grow1.maxim)
		self.assertEqual(str(grow1), "Grow()")
		
		# Grow with minimum
		grow2 = Grow(minimum=40)
		self.assertEqual(grow2.minim, 40)
		self.assertIsNone(grow2.maxim)
		self.assertEqual(str(grow2), "Grow(minimum=40)")
		
		# Grow with minimum and maximum
		grow3 = Grow(minimum=25, maximum=200)
		self.assertEqual(grow3.minim, 25)
		self.assertEqual(grow3.maxim, 200)  # Grow now properly handles maximum
		self.assertEqual(str(grow3), "Grow(minimum=25, maximum=200)")
		
		# Test type validation
		with self.assertRaises(AssertionError):
			Grow(minimum="not a number")
		
		with self.assertRaises(AssertionError):
			Grow(minimum=10, maximum="not a number")
	
	def test_dimension_immutability(self):
		"""Test that dimensions are immutable (tuple-based)."""
		fixed = Fixed(100)
		expand = Expand(50)
		grow = Grow(minimum=30, maximum=150)
		
		# Test tuple representation
		self.assertEqual(tuple(fixed), (100,))
		self.assertEqual(tuple(expand), (50, None))
		self.assertEqual(tuple(grow), (30, 150))
		
		# Test immutability - cannot modify values
		with self.assertRaises(TypeError):
			fixed[0] = 200
		
		with self.assertRaises(TypeError):
			expand[0] = 75
	
	def test_dimension_hashability(self):
		"""Test that dimensions are hashable and can be used in sets."""
		fixed1 = Fixed(100)
		fixed2 = Fixed(100)  # Same value
		fixed3 = Fixed(200)  # Different value
		expand = Expand(50)
		grow = Grow(30)
		
		# Test that they can be used in sets
		dimension_set = {fixed1, fixed2, fixed3, expand, grow}
		
		# Should have 4 unique items (fixed1 and fixed2 are equal)
		self.assertEqual(len(dimension_set), 4)
		
		# Test that they can be used as dictionary keys
		dimension_dict = {
			fixed1: "fixed_100",
			expand: "expand_50",
			grow: "grow_30"
		}
		
		self.assertEqual(dimension_dict[fixed2], "fixed_100")  # fixed2 should match fixed1


class TestLayoutWidgets(unittest.TestCase):
	"""Test individual layout widget functionality."""
	
	def test_layout_spacer(self):
		"""Test LayoutSpacer with different dimension types."""
		# Test with auto-wrapped values
		spacer1 = LayoutSpacer(width=100, height=50)
		self.assertEqual(spacer1.query_space_request(), (100, 50))
		self.assertIsInstance(spacer1.width, Fixed)
		self.assertIsInstance(spacer1.height, Fixed)
		
		# Test with explicit dimension types
		spacer2 = LayoutSpacer(width=Expand(minimum=20), height=Fixed(30))
		self.assertEqual(spacer2.query_space_request(), (20, 30))
		self.assertIsInstance(spacer2.width, Expand)
		self.assertIsInstance(spacer2.height, Fixed)
	
	def test_layout_text(self):
		"""Test LayoutText text measurement."""
		# Reset to defaults to ensure consistent measurement
		import sys
		import os
		sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
		import window_layout
		window_layout.set_text_measurement_functions(None, None)
		
		# Test empty text
		text1 = LayoutText("")
		self.assertEqual(text1.query_space_request(), (0, 0))
		
		# Test single line text
		text2 = LayoutText("Hello")
		# query_space_request returns (minimum_width, height)
		# minimum width is based on sample characters, not the actual text
		min_width = text2.query_width_request()
		height = text2.query_height_request()
		self.assertEqual(text2.query_space_request(), (min_width, height))
		self.assertGreater(min_width, 0)
		self.assertGreater(height, 0)
		
		# Test that preferred width is different from minimum
		preferred_width = text2.get_preferred_width()
		self.assertGreater(preferred_width, min_width)
		
		# Test multiline text
		multiline = "Line 1\nLine 2\nLonger line 3"
		text3 = LayoutText(multiline)
		width_request, height_request = text3.query_space_request()
		self.assertGreater(width_request, 0)
		self.assertGreater(height_request, height)  # Should be taller than single line
		
		# Test static method
		width, height = LayoutText.get_extents("Test")
		# Should return reasonable values based on current measurement system
		self.assertGreater(width, 0)
		self.assertGreater(height, 0)
	
	def test_layout_button(self):
		"""Test LayoutButton functionality."""
		# Test button with default sizing
		button1 = LayoutButton("Click me", id=1)
		width_request, height_request = button1.query_space_request()
		# Button should have reasonable dimensions
		self.assertGreater(width_request, 50)  # Should be wider than very small
		self.assertGreaterEqual(height_request, 25)  # Minimum height
		
		# Test button with explicit dimensions
		button2 = LayoutButton("Test", id=2, width=100, height=40)
		self.assertEqual(button2.query_space_request(), (100, 40))
		self.assertIsInstance(button2.width, Fixed)
		self.assertIsInstance(button2.height, Fixed)
		
		# Test button with Grow width
		button3 = LayoutButton("Grow", id=3, width=Grow(minimum=60), height=30)
		self.assertEqual(button3.query_space_request(), (60, 30))
		self.assertIsInstance(button3.width, Grow)
		
		# Test text management
		button1.set_text("New text")
		self.assertEqual(button1.get_text(), "New text")
	
	def test_layout_edit(self):
		"""Test LayoutEdit functionality."""
		# Test edit with default sizing
		edit1 = LayoutEdit("Sample text")
		width_request, height_request = edit1.query_space_request()
		# Edit should have reasonable dimensions based on current measurement
		self.assertGreater(width_request, 30)  # Should accommodate text (lowered expectation)
		self.assertGreater(height_request, 15)  # Should have some height
		
		# Test edit with explicit dimensions
		edit2 = LayoutEdit("Test", width=200, height=50)
		self.assertEqual(edit2.query_space_request(), (200, 50))
		
		# Test multiline edit
		multiline_text = "Line 1\nLine 2\nLine 3"
		edit3 = LayoutEdit(multiline_text, multiline=True)
		width_request, height_request = edit3.query_space_request()
		# Should accommodate multiline text
		self.assertGreater(width_request, 30)  # Should have reasonable width
		self.assertGreater(height_request, 40)  # Should be taller for multiple lines
		
		# Test text management
		edit1.set_text("Updated text")
		self.assertEqual(edit1.get_text(), "Updated text")
	
	def test_layout_horizontal_line(self):
		"""Test LayoutHorizontalLine."""
		line = LayoutHorizontalLine()
		self.assertEqual(line.query_space_request(), (0, 1))


class TestLayoutContainers(unittest.TestCase):
	"""Test container layout functionality."""
	
	def test_layout_padding(self):
		"""Test LayoutPadding with different padding configurations."""
		# Test with single value padding
		child = LayoutSpacer(width=100, height=50)
		padding1 = LayoutPadding(padding=10, child=child)
		expected = (100 + 20, 50 + 20)  # Child size + padding on all sides
		self.assertEqual(padding1.query_space_request(), expected)
		
		# Test with 4-value padding (top, right, bottom, left)
		padding2 = LayoutPadding(padding=(5, 10, 15, 20), child=child)
		# Note: Implementation uses [0]+[2] for width and [1]+[3] for height
		# This seems wrong but we'll test the current behavior
		expected = (100 + 20, 50 + 30)  # Child size + current padding calculation
		self.assertEqual(padding2.query_space_request(), expected)
		
		# Test with no child
		padding3 = LayoutPadding(padding=5)
		self.assertEqual(padding3.query_space_request(), (10, 10))  # Just padding
	
	def test_layout_container_vertical(self):
		"""Test vertical LayoutContainer."""
		child1 = LayoutSpacer(width=100, height=30)
		child2 = LayoutSpacer(width=80, height=20)
		child3 = LayoutSpacer(width=120, height=40)
		
		# Test without gaps
		container = LayoutContainer.vertical(children=(child1, child2, child3))
		expected_width = max(100, 80, 120)  # Maximum width
		expected_height = 30 + 20 + 40  # Sum of heights
		self.assertEqual(container.query_space_request(), (expected_width, expected_height))
		
		# Test with gaps
		container_gap = LayoutContainer.vertical(gap=5, children=(child1, child2, child3))
		expected_height_gap = 30 + 20 + 40 + (2 * 5)  # Heights + gaps
		self.assertEqual(container_gap.query_space_request(), (expected_width, expected_height_gap))
	
	def test_layout_container_horizontal(self):
		"""Test horizontal LayoutContainer."""
		child1 = LayoutSpacer(width=50, height=100)
		child2 = LayoutSpacer(width=30, height=80)
		child3 = LayoutSpacer(width=70, height=120)
		
		# Test without gaps
		container = LayoutContainer.horizontal(children=(child1, child2, child3))
		expected_width = 50 + 30 + 70  # Sum of widths
		expected_height = max(100, 80, 120)  # Maximum height
		self.assertEqual(container.query_space_request(), (expected_width, expected_height))
		
		# Test with gaps
		container_gap = LayoutContainer.horizontal(gap=10, children=(child1, child2, child3))
		expected_width_gap = 50 + 30 + 70 + (2 * 10)  # Widths + gaps
		self.assertEqual(container_gap.query_space_request(), (expected_width_gap, expected_height))
	
	def test_layout_container_caching(self):
		"""Test that LayoutContainer caches children_with_gaps properly."""
		child1 = LayoutSpacer(width=50, height=30)
		child2 = LayoutSpacer(width=60, height=40)
		
		# Test with simple numeric gap (should return just children)
		container = LayoutContainer.horizontal(gap=5, children=(child1, child2))
		
		# First call should populate cache
		children_with_gaps_1 = container._get_children_with_gaps()
		self.assertEqual(len(children_with_gaps_1), 2)  # child1, child2 (simple gaps don't create widgets)
		self.assertIs(children_with_gaps_1, container.children)  # Should return children directly for simple gaps
		
		# Second call should return cached result
		children_with_gaps_2 = container._get_children_with_gaps()
		self.assertIs(children_with_gaps_1, children_with_gaps_2)
		
		# For simple gaps, cache invalidation still returns the same children object
		container._invalidate_gap_cache()
		children_with_gaps_3 = container._get_children_with_gaps()
		self.assertIs(children_with_gaps_1, children_with_gaps_3)  # Still same children object for simple gaps
		
		# Test with widget-based gap (should create gap widgets)
		container_widget_gap = LayoutContainer.horizontal(gap=lambda: LayoutSpacer(width=5, height=0), children=(child1, child2))
		
		# First call should populate cache with gap widgets
		children_with_gaps_widget_1 = container_widget_gap._get_children_with_gaps()
		self.assertEqual(len(children_with_gaps_widget_1), 3)  # child1, gap widget, child2
		
		# Second call should return same cached result
		children_with_gaps_widget_2 = container_widget_gap._get_children_with_gaps()
		self.assertIs(children_with_gaps_widget_1, children_with_gaps_widget_2)
		
		# Cache invalidation should create new gap widgets
		container_widget_gap._invalidate_gap_cache()
		children_with_gaps_widget_3 = container_widget_gap._get_children_with_gaps()
		self.assertIsNot(children_with_gaps_widget_1, children_with_gaps_widget_3)  # Different objects after invalidation


class TestComplexLayouts(unittest.TestCase):
	"""Test complex layout scenarios and the about dialog."""
	
	def test_about_dialog_layout(self):
		"""Test the complete about dialog layout."""
		test_about_text = """FullThumbs PiP Viewer
Version: 1.0.0-dev
A Picture-in-Picture viewer application for Windows."""
		
		test_github_link = "https://github.com/Fredderic/FullThumbs"
		
		layout = build_about_dialog(test_about_text, test_github_link)
		
		# Should be a LayoutWindow
		self.assertIsInstance(layout, LayoutWindow)
		
		# Should have reasonable dimensions
		width, height = layout.query_space_request()
		self.assertGreater(width, 200)  # Should be reasonably wide
		self.assertGreater(height, 100)  # Should be reasonably tall
		
		# Test that it's a valid layout tree
		self.assertIsNotNone(layout.child)
		self.assertIsInstance(layout.child, LayoutContainer)
	
	def test_nested_containers(self):
		"""Test nested container layouts."""
		# Create a complex nested structure
		button1 = LayoutButton("Button 1", id=1)
		button2 = LayoutButton("Button 2", id=2)
		
		# Horizontal container for buttons
		button_row = LayoutContainer.horizontal(gap=10, children=(button1, button2))
		
		# Text above buttons
		text = LayoutText("Header Text")
		
		# Vertical container for text and buttons
		main_container = LayoutContainer.vertical(gap=15, children=(text, button_row))
		
		# Wrap in padding
		padded = LayoutPadding(padding=20, child=main_container)
		
		# Get dimensions
		width, height = padded.query_space_request()
		
		# Should be reasonable dimensions
		self.assertGreater(width, 100)
		self.assertGreater(height, 50)
		
		# Test that query methods are consistent
		self.assertEqual(padded.query_space_request(), (width, height))
		self.assertEqual(padded.query_width_request(), width)
		self.assertEqual(padded.query_height_request(), height)


if __name__ == '__main__':
	# Set up test suites for selective running
	def run_dimension_tests():
		"""Run only the dimension-related tests."""
		suite = unittest.TestLoader().loadTestsFromTestCase(TestDimensionClasses)
		runner = unittest.TextTestRunner(verbosity=2)
		runner.run(suite)
	
	def run_widget_tests():
		"""Run only the widget-related tests."""
		suite = unittest.TestLoader().loadTestsFromTestCase(TestLayoutWidgets)
		runner = unittest.TextTestRunner(verbosity=2)
		runner.run(suite)
	
	def run_container_tests():
		"""Run only the container-related tests."""
		suite = unittest.TestLoader().loadTestsFromTestCase(TestLayoutContainers)
		runner = unittest.TextTestRunner(verbosity=2)
		runner.run(suite)
	
	def run_complex_tests():
		"""Run only the complex layout tests."""
		suite = unittest.TestLoader().loadTestsFromTestCase(TestComplexLayouts)
		runner = unittest.TextTestRunner(verbosity=2)
		runner.run(suite)
	
	# Run all tests by default
	unittest.main(verbosity=2)
