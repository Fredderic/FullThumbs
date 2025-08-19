"""Test cases for separator line layout behavior."""

import unittest
import sys
import os

# Add the project root to the path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from window_layout import (
    Layout,
    LayoutGroup,
    LayoutContainer,
    LayoutPluginContext,
    LayoutSeparatorLine,
    Fixed,
    Grow,
    layout_context_class,
)

class SeparatorLineTests(unittest.TestCase):
    def setUp(self):
        """Set up the layout context for testing."""
        layout_context_class(LayoutPluginContext)
    
    def test_separator_line_thickness(self):
        """Test the thickness property and dimensional behavior of separator lines."""
        # Test horizontal line thickness
        # Check default thickness first
        line = LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL)
        default_thickness = line.thickness
        self.assertEqual(line.query_height_request(), default_thickness)
        self.assertEqual(line.query_width_request(), 0)  # Width should be 0 to allow expansion
        
        # Test explicit thickness setting
        line.thickness = 3
        self.assertEqual(line.thickness, 3)
        self.assertEqual(line.query_height_request(), 3)
        self.assertEqual(line.query_width_request(), 0)  # Width should stay 0
        
        # Test vertical line thickness
        line = LayoutSeparatorLine(axis=LayoutGroup.VERTICAL)
        self.assertEqual(line.thickness, default_thickness)
        self.assertEqual(line.query_width_request(), default_thickness)
        self.assertEqual(line.query_height_request(), 0)  # Height should be 0 to allow expansion
        
        # Test explicit thickness setting
        line.thickness = 5
        self.assertEqual(line.thickness, 5)
        self.assertEqual(line.query_width_request(), 5)
        self.assertEqual(line.query_height_request(), 0)  # Height should stay 0
    
    def test_separator_line_expansion(self):
        """Test that separator lines expand properly in their primary direction."""
        # Horizontal line
        line = LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL)
        # Record initial thickness
        thickness = line.query_height_request()
        
        # Should take full available width
        width = line.distribute_width(100)
        self.assertEqual(width, 100)
        # Height should stay at thickness
        height = line.distribute_height(50)
        self.assertEqual(height, thickness)
        
        # Vertical line
        line = LayoutSeparatorLine(axis=LayoutGroup.VERTICAL)
        # Record initial thickness
        thickness = line.query_width_request()
        
        # Should take full available height
        height = line.distribute_height(100)
        self.assertEqual(height, 100)
        # Width should stay at thickness
        width = line.distribute_width(50)
        self.assertEqual(width, thickness)
    
    def test_lines_in_containers(self):
        """Test that separator lines pack and expand correctly in containers."""
        # Test horizontal container with 3 equal vertical lines
        h_container = LayoutContainer.horizontal(
            gap=10,  # Fixed gap between lines
            children=(
                LayoutSeparatorLine(axis=LayoutGroup.VERTICAL),
                LayoutSeparatorLine(axis=LayoutGroup.VERTICAL),
                LayoutSeparatorLine(axis=LayoutGroup.VERTICAL),
            )
        )
        
        # Get thickness for calculations
        line_thickness = h_container.children[0].query_width_request()
        
        # Test minimum width request (3 lines at thickness + 2 gaps at 10px)
        expected_width = (line_thickness * 3) + (10 * 2)
        self.assertEqual(h_container.query_width_request(), expected_width)
        # Height should be 0 to allow growth
        self.assertEqual(h_container.query_height_request(), 0)
        
        # Layout with specific size - lines should share height
        h_container.layout(0, 0, 200, 100)
        for child in h_container.children:
            # Each line should be at full container height
            self.assertEqual(child._computed_size[1], 100)
            # Each line should maintain its thickness
            self.assertEqual(child._computed_size[0], line_thickness)
        
        # Test vertical container with 3 equal horizontal lines
        v_container = LayoutContainer.vertical(
            gap=10,  # Fixed gap between lines
            children=(
                LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL),
                LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL),
                LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL),
            )
        )
        
        # Get thickness for calculations
        line_thickness = v_container.children[0].query_height_request()
        
        # Test minimum height request (3 lines at thickness + 2 gaps at 10px)
        expected_height = (line_thickness * 3) + (10 * 2)
        self.assertEqual(v_container.query_height_request(), expected_height)
        # Width should be 0 to allow growth
        self.assertEqual(v_container.query_width_request(), 0)
        
        # Layout with specific size - lines should share width
        v_container.layout(0, 0, 100, 200)
        for child in v_container.children:
            # Each line should be at full container width
            self.assertEqual(child._computed_size[0], 100)
            # Each line should maintain its thickness
            self.assertEqual(child._computed_size[1], line_thickness)
    
    def test_constrained_separator_line(self):
        """Test separator lines with fixed size constraints."""
        # Test horizontal line with fixed width
        h_line = LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL, width=Fixed(100))
        self.assertEqual(h_line.query_width_request(), 100)  # Should respect fixed width
        self.assertEqual(h_line.query_height_request(), 2)   # Default thickness

        # Test vertical line with fixed height
        v_line = LayoutSeparatorLine(axis=LayoutGroup.VERTICAL, height=Fixed(100))
        self.assertEqual(v_line.query_width_request(), 2)    # Default thickness
        self.assertEqual(v_line.query_height_request(), 100) # Should respect fixed height
        
        # Test layout respects constraints
        h_line.layout(0, 0, 200, 50)  # Give more space than requested
        self.assertEqual(h_line._computed_size[0], 100)  # Should stay at fixed width
        self.assertEqual(h_line._computed_size[1], h_line.query_height_request())  # Should keep thickness
        
        v_line.layout(0, 0, 50, 200)  # Give more space than requested
        self.assertEqual(v_line._computed_size[0], v_line.query_width_request())  # Should keep thickness
        self.assertEqual(v_line._computed_size[1], 100)  # Should stay at fixed height
    
    def test_constrained_separator_limited_by_container(self):
        """Test that separator lines with fixed sizes still respect available space."""
        # Test horizontal line with fixed width larger than container
        h_line = LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL, width=Fixed(200))
        
        # Give less space than requested
        h_line.layout(0, 0, 150, 50)
        # Should limit to container width
        self.assertEqual(h_line._computed_size[0], 150)
        # But keep thickness
        self.assertEqual(h_line._computed_size[1], h_line.query_height_request())
        
        # Test vertical line with fixed height larger than container
        v_line = LayoutSeparatorLine(axis=LayoutGroup.VERTICAL, height=Fixed(200))
        
        # Give less space than requested
        v_line.layout(0, 0, 50, 150)
        # Should keep thickness
        self.assertEqual(v_line._computed_size[0], v_line.query_width_request())
        # Should limit to container height
        self.assertEqual(v_line._computed_size[1], 150)
        
        # Test in containers to ensure behavior is consistent
        h_container = LayoutContainer.horizontal(
            gap=10,
            children=(LayoutSeparatorLine(axis=LayoutGroup.HORIZONTAL, width=Fixed(200)),)
        )
        
        # Give container less space than child requests
        h_container.layout(0, 0, 150, 50)
        # Child should limit to available space
        self.assertEqual(h_container.children[0]._computed_size[0], 150)

if __name__ == '__main__':
    unittest.main()
