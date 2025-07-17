#!/usr/bin/env python3
"""
Unit tests for time interval parsing functionality.

This module tests the parse_time_interval function from utilities.py.
"""

import unittest
import sys
import os

# Add the project root to the path so we can import from utilities.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the functions we want to test
from utilities import parse_time_interval, validate_auto_update_interval

class TestTimeIntervalParsing(unittest.TestCase):
	"""Test the parse_time_interval function."""
	
	def test_valid_seconds(self):
		"""Test parsing second intervals."""
		self.assertEqual(parse_time_interval("60s"), 60_000)
		self.assertEqual(parse_time_interval("120s"), 120_000)
		self.assertEqual(parse_time_interval("1s"), 1000)
		self.assertEqual(parse_time_interval("0.5s"), 500)
	
	def test_valid_minutes(self):
		"""Test parsing minute intervals."""
		self.assertEqual(parse_time_interval("1m"), 60_000)
		self.assertEqual(parse_time_interval("5m"), 300_000)
		self.assertEqual(parse_time_interval("0.5m"), 30_000)
	
	def test_valid_hours(self):
		"""Test parsing hour intervals."""
		self.assertEqual(parse_time_interval("1h"), 3600_000)
		self.assertEqual(parse_time_interval("4h"), 14400_000)
		self.assertEqual(parse_time_interval("0.5h"), 1800_000)
	
	def test_valid_days(self):
		"""Test parsing day intervals."""
		self.assertEqual(parse_time_interval("1d"), 86400_000)
		self.assertEqual(parse_time_interval("0.5d"), 43200_000)
	
	def test_default_unit_hours(self):
		"""Test that numbers without units default to hours."""
		self.assertEqual(parse_time_interval("1"), 3600_000)
		self.assertEqual(parse_time_interval("4"), 14400_000)
	
	def test_decimal_values(self):
		"""Test parsing decimal values with rounding."""
		self.assertEqual(parse_time_interval("1.5h"), 5400_000)
		self.assertEqual(parse_time_interval("2.5m"), 150_000)
		
		# Test rounding behavior with fractional seconds (preserves precision)
		self.assertEqual(parse_time_interval("90.4s"), 90_400)
		self.assertEqual(parse_time_interval("90.5s"), 90_500)
		self.assertEqual(parse_time_interval("90.6s"), 90_600)
		
		# Test millisecond precision
		self.assertEqual(parse_time_interval("1.001s"), 1001)
		self.assertEqual(parse_time_interval("0.1s"), 100)
	
	def test_short_intervals_allowed(self):
		"""Test that short intervals are now allowed (no minimum enforcement)."""
		self.assertEqual(parse_time_interval("30s"), 30_000)
		self.assertEqual(parse_time_interval("1s"), 1000)
		self.assertEqual(parse_time_interval("0.5s"), 500)
		self.assertEqual(parse_time_interval("0.1s"), 100)
	
	def test_zero_with_unit_warning(self):
		"""Test that zero with explicit unit produces a warning but still works."""
		# These should work but produce warnings
		import io
		import sys
		captured_output = io.StringIO()
		old_stdout = sys.stdout
		sys.stdout = captured_output
		
		try:
			result = parse_time_interval("0s")
			self.assertEqual(result, 0)
			output = captured_output.getvalue()
			self.assertIn("Warning", output)
			self.assertIn("0s", output)
		finally:
			sys.stdout = old_stdout
	
	def test_invalid_formats(self):
		"""Test that invalid formats return None."""
		self.assertIsNone(parse_time_interval(""))
		self.assertIsNone(parse_time_interval("invalid"))
		self.assertIsNone(parse_time_interval("1x"))
		self.assertIsNone(parse_time_interval("h1"))
		self.assertIsNone(parse_time_interval("-1h"))
		
		# Invalid multiple unit patterns
		self.assertIsNone(parse_time_interval("1h2h"))  # Duplicate units
		self.assertIsNone(parse_time_interval("1.5.5h"))  # Invalid decimal format
		self.assertIsNone(parse_time_interval("1h-30m"))  # Negative values
		self.assertIsNone(parse_time_interval("1habcd2m"))  # Invalid characters between units
	
	def test_none_input(self):
		"""Test that None input returns None."""
		self.assertIsNone(parse_time_interval(None))
	
	def test_case_insensitive(self):
		"""Test that parsing is case insensitive."""
		self.assertEqual(parse_time_interval("2H"), 7200_000)
		self.assertEqual(parse_time_interval("30M"), 1800_000)
		self.assertEqual(parse_time_interval("1D"), 86400_000)
		self.assertEqual(parse_time_interval("60S"), 60_000)
	
	def test_edge_cases(self):
		"""Test edge cases and boundary conditions."""
		# Very large values
		self.assertEqual(parse_time_interval("999999s"), 999_999_000)
		
		# Very small values are preserved as milliseconds
		self.assertEqual(parse_time_interval("0.001s"), 1)
		self.assertEqual(parse_time_interval("0.01s"), 10)
		self.assertEqual(parse_time_interval("0.1s"), 100)
		
		# Leading zeros
		self.assertEqual(parse_time_interval("01h"), 3_600_000)
		self.assertEqual(parse_time_interval("000001m"), 60_000)
	
	def test_zero_values(self):
		"""Test zero values for all units."""
		# Zero without unit should be fine
		self.assertEqual(parse_time_interval("0"), 0)
		
		# Zero with units should produce warnings but still work
		# (Testing the actual warning output is done in test_zero_with_unit_warning)
	
	def test_spaces_not_allowed(self):
		"""Test that spaces in input are rejected."""
		self.assertIsNone(parse_time_interval("1 h"))
		self.assertIsNone(parse_time_interval(" 1h"))
		self.assertIsNone(parse_time_interval("1h "))
		self.assertIsNone(parse_time_interval("1 . 5 h"))
	
	def test_multiple_units_supported(self):
		"""Test that multiple units in one string are now supported."""
		# Basic multiple units
		self.assertEqual(parse_time_interval("1h30m"), 5_400_000)  # 90 minutes
		self.assertEqual(parse_time_interval("1d2h"), 93_600_000)  # 26 hours
		self.assertEqual(parse_time_interval("2h15m"), 8_100_000)  # 135 minutes
		
		# Order shouldn't matter
		self.assertEqual(parse_time_interval("30m1h"), 5_400_000)  # Same as 1h30m
		self.assertEqual(parse_time_interval("2h1d"), 93_600_000)  # Same as 1d2h
		
		# Complex combinations
		self.assertEqual(parse_time_interval("1d2h30m"), 95_400_000)  # 26.5 hours
		self.assertEqual(parse_time_interval("1h30m45s"), 5_445_000)  # 90m 45s
		
		# With milliseconds
		self.assertEqual(parse_time_interval("1h500ms"), 3_600_500)  # 1 hour + 500ms
		self.assertEqual(parse_time_interval("30s250ms"), 30_250)     # 30.25 seconds
		
		# Decimal values in combinations
		self.assertEqual(parse_time_interval("1.5h30m"), 7_200_000)  # 2 hours
		
		# Invalid: duplicate units
		self.assertIsNone(parse_time_interval("1h2h"))  # Two hour units
		self.assertIsNone(parse_time_interval("30m15m"))  # Two minute units
	
	def test_valid_milliseconds(self):
		"""Test parsing millisecond intervals."""
		self.assertEqual(parse_time_interval("1000ms"), 1000)
		self.assertEqual(parse_time_interval("500ms"), 500)
		self.assertEqual(parse_time_interval("1ms"), 1)
		self.assertEqual(parse_time_interval("0.5ms"), 1)  # Rounds to 0, forced to 1
		self.assertEqual(parse_time_interval("1.5ms"), 2)  # Rounds to 2
	
	def test_zero_rounding_edge_cases(self):
		"""Test that values that round to 0 are forced to 1ms."""
		# Single units that would round to 0
		self.assertEqual(parse_time_interval("0.5ms"), 1)
		self.assertEqual(parse_time_interval("0.4ms"), 1)
		self.assertEqual(parse_time_interval("0.0001s"), 1)  # 0.1ms rounds to 0
		
		# Multiple units where total rounds to 0 (note: this needs valid syntax)
		# We can't easily create a multi-unit case that rounds to 0 without explicit zeros
		# since the smallest non-zero unit (1ms) is already 1
		
		# Explicit zero should still be 0 (not forced to 1)
		self.assertEqual(parse_time_interval("0ms"), 0)
		self.assertEqual(parse_time_interval("0s"), 0)
		self.assertEqual(parse_time_interval("0"), 0)

class TestAutoUpdateValidation(unittest.TestCase):
	"""Test the validate_auto_update_interval function."""
	
	def test_minimum_interval_validation(self):
		"""Test that auto-update validation enforces minimum intervals."""
		# Valid intervals (>= 60 seconds)
		self.assertEqual(validate_auto_update_interval(60_000), 60_000)
		self.assertEqual(validate_auto_update_interval(120_000), 120_000)
		self.assertEqual(validate_auto_update_interval(3_600_000), 3_600_000)
		
		# Invalid intervals (< 60 seconds)
		self.assertIsNone(validate_auto_update_interval(30_000))
		self.assertIsNone(validate_auto_update_interval(59_000))
		self.assertIsNone(validate_auto_update_interval(1000))
		
		# Special case: 0 is allowed
		self.assertEqual(validate_auto_update_interval(0), 0)
		
		# None input returns None
		self.assertIsNone(validate_auto_update_interval(None))

if __name__ == "__main__":
	# Run the tests
	unittest.main(verbosity=2)
