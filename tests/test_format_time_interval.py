"""
Unit tests for the format_time_interval function.

This module tests the format_time_interval function from utilities.py.
The function converts milliseconds back to human-readable format.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilities import format_time_interval, format_time_interval_words


class TestFormatTimeInterval(unittest.TestCase):
	"""Test cases for format_time_interval function."""

	def test_zero_milliseconds(self):
		"""Test formatting zero milliseconds."""
		self.assertEqual(format_time_interval(0), "0")

	def test_simple_milliseconds(self):
		"""Test formatting simple millisecond values."""
		self.assertEqual(format_time_interval(1), "1ms")
		self.assertEqual(format_time_interval(500), "500ms")
		self.assertEqual(format_time_interval(999), "999ms")

	def test_simple_seconds(self):
		"""Test formatting simple second values."""
		self.assertEqual(format_time_interval(1000), "1s")
		self.assertEqual(format_time_interval(2000), "2s")
		self.assertEqual(format_time_interval(30000), "30s")
		self.assertEqual(format_time_interval(59000), "59s")

	def test_simple_minutes(self):
		"""Test formatting simple minute values."""
		self.assertEqual(format_time_interval(60_000), "1m")
		self.assertEqual(format_time_interval(120_000), "2m")
		self.assertEqual(format_time_interval(300_000), "5m")
		self.assertEqual(format_time_interval(1800_000), "30m")

	def test_simple_hours(self):
		"""Test formatting simple hour values."""
		self.assertEqual(format_time_interval(3600_000), "1h")
		self.assertEqual(format_time_interval(7200_000), "2h")
		self.assertEqual(format_time_interval(14400_000), "4h")
		self.assertEqual(format_time_interval(18000_000), "5h")

	def test_simple_days(self):
		"""Test formatting simple day values."""
		self.assertEqual(format_time_interval(86400_000), "1d")
		self.assertEqual(format_time_interval(172800_000), "2d")
		self.assertEqual(format_time_interval(259200_000), "3d")

	def test_compound_hours_minutes(self):
		"""Test formatting compound hour and minute values."""
		self.assertEqual(format_time_interval(3660_000), "1h1m")  # 1h + 1m
		self.assertEqual(format_time_interval(5400_000), "1h30m")  # 1h + 30m
		self.assertEqual(format_time_interval(9000_000), "2h30m")  # 2h + 30m
		self.assertEqual(format_time_interval(12600_000), "3h30m")  # 3h + 30m

	def test_compound_minutes_seconds(self):
		"""Test formatting compound minute and second values."""
		self.assertEqual(format_time_interval(61_000), "1m1s")  # 1m + 1s
		self.assertEqual(format_time_interval(90_000), "1m30s")  # 1m + 30s
		self.assertEqual(format_time_interval(150_000), "2m30s")  # 2m + 30s

	def test_compound_seconds_milliseconds(self):
		"""Test formatting compound second and millisecond values."""
		self.assertEqual(format_time_interval(1001), "1s1ms")  # 1s + 1ms
		self.assertEqual(format_time_interval(1500), "1s500ms")  # 1s + 500ms
		self.assertEqual(format_time_interval(2750), "2s750ms")  # 2s + 750ms

	def test_compound_hours_minutes_seconds(self):
		"""Test formatting compound hour, minute, and second values."""
		self.assertEqual(format_time_interval(3661_000), "1h1m1s")  # 1h + 1m + 1s
		self.assertEqual(format_time_interval(5445_000), "1h30m45s")  # 1h + 30m + 45s
		self.assertEqual(format_time_interval(9075_000), "2h31m15s")  # 2h + 31m + 15s

	def test_compound_all_units(self):
		"""Test formatting with all time units."""
		# 1d + 2h + 30m + 45s + 500ms = 95,445,500ms
		self.assertEqual(format_time_interval(95_445_500), "1d2h30m45s500ms")
		
		# 2d + 1h + 15m + 30s + 250ms = 177,330,250ms
		self.assertEqual(format_time_interval(177_330_250), "2d1h15m30s250ms")

	def test_default_update_interval(self):
		"""Test formatting the default update interval (4 hours)."""
		self.assertEqual(format_time_interval(14_400_000), "4h")

	def test_minimum_update_interval(self):
		"""Test formatting the minimum update interval (1 minute)."""
		self.assertEqual(format_time_interval(60_000), "1m")

	def test_common_intervals(self):
		"""Test formatting common time intervals used in applications."""
		# 5 minutes
		self.assertEqual(format_time_interval(300_000), "5m")
		
		# 15 minutes
		self.assertEqual(format_time_interval(900_000), "15m")
		
		# 30 minutes
		self.assertEqual(format_time_interval(1_800_000), "30m")
		
		# 1.5 hours (90 minutes)
		self.assertEqual(format_time_interval(5_400_000), "1h30m")
		
		# 12 hours
		self.assertEqual(format_time_interval(43_200_000), "12h")
		
		# 24 hours (1 day)
		self.assertEqual(format_time_interval(86_400_000), "1d")

	def test_edge_cases(self):
		"""Test edge cases and boundary values."""
		# Just under 1 second
		self.assertEqual(format_time_interval(999), "999ms")
		
		# Just under 1 minute
		self.assertEqual(format_time_interval(59_999), "59s999ms")
		
		# Just under 1 hour
		self.assertEqual(format_time_interval(3_599_999), "59m59s999ms")
		
		# Just under 1 day
		self.assertEqual(format_time_interval(86_399_999), "23h59m59s999ms")

	def test_large_values(self):
		"""Test formatting very large time values."""
		# 7 days
		self.assertEqual(format_time_interval(604_800_000), "7d")
		
		# 30 days
		self.assertEqual(format_time_interval(2_592_000_000), "30d")
		
		# 1 year (365 days)
		self.assertEqual(format_time_interval(31_536_000_000), "365d")

	def test_reverse_parse_compatibility(self):
		"""Test that format_time_interval output can be parsed by parse_time_interval."""
		from utilities import parse_time_interval
		
		test_values = [
			60_000,      # 1m
			3600_000,    # 1h
			5400_000,    # 1h30m
			90_000,      # 1m30s
			3661_000,    # 1h1m1s
			86_400_000,  # 1d
		]
		
		for milliseconds in test_values:
			formatted = format_time_interval(milliseconds)
			parsed_back = parse_time_interval(formatted)
			self.assertEqual(parsed_back, milliseconds, 
				f"Round-trip failed: {milliseconds} -> '{formatted}' -> {parsed_back}")


class TestFormatTimeIntervalWords(unittest.TestCase):
	"""Test cases for format_time_interval_words function."""

	def test_zero_milliseconds(self):
		"""Test formatting zero milliseconds."""
		self.assertEqual(format_time_interval_words(0), "0")

	def test_single_unit_singular(self):
		"""Test formatting single units with count of 1 (singular forms)."""
		self.assertEqual(format_time_interval_words(1), "1 millisecond")
		self.assertEqual(format_time_interval_words(1000), "1 second")
		self.assertEqual(format_time_interval_words(60_000), "1 minute")
		self.assertEqual(format_time_interval_words(3600_000), "1 hour")
		self.assertEqual(format_time_interval_words(86400_000), "1 day")

	def test_single_unit_plural(self):
		"""Test formatting single units with count > 1 (plural forms)."""
		self.assertEqual(format_time_interval_words(500), "500 milliseconds")
		self.assertEqual(format_time_interval_words(30000), "30 seconds")
		self.assertEqual(format_time_interval_words(300_000), "5 minutes")
		self.assertEqual(format_time_interval_words(7200_000), "2 hours")
		self.assertEqual(format_time_interval_words(172800_000), "2 days")

	def test_single_unit_common_values(self):
		"""Test formatting common single-unit time values."""
		# Common second values
		self.assertEqual(format_time_interval_words(2000), "2 seconds")
		self.assertEqual(format_time_interval_words(15000), "15 seconds")
		self.assertEqual(format_time_interval_words(30000), "30 seconds")
		
		# Common minute values
		self.assertEqual(format_time_interval_words(180_000), "3 minutes")
		self.assertEqual(format_time_interval_words(600_000), "10 minutes")
		self.assertEqual(format_time_interval_words(1800_000), "30 minutes")
		
		# Common hour values
		self.assertEqual(format_time_interval_words(14400_000), "4 hours")
		self.assertEqual(format_time_interval_words(18000_000), "5 hours")
		self.assertEqual(format_time_interval_words(43200_000), "12 hours")

	def test_compound_intervals_fallback(self):
		"""Test that compound intervals fall back to compact format."""
		# Hour + minute combinations
		self.assertEqual(format_time_interval_words(3660_000), "1h1m")
		self.assertEqual(format_time_interval_words(5400_000), "1h30m")
		self.assertEqual(format_time_interval_words(9000_000), "2h30m")
		
		# Minute + second combinations
		self.assertEqual(format_time_interval_words(90_000), "1m30s")
		self.assertEqual(format_time_interval_words(150_000), "2m30s")
		
		# Complex combinations
		self.assertEqual(format_time_interval_words(3661_000), "1h1m1s")
		self.assertEqual(format_time_interval_words(95_445_500), "1d2h30m45s500ms")

	def test_default_and_minimum_intervals(self):
		"""Test formatting the application's default and minimum intervals."""
		# Default update interval (4 hours)
		self.assertEqual(format_time_interval_words(14_400_000), "4 hours")
		
		# Minimum update interval (1 minute)
		self.assertEqual(format_time_interval_words(60_000), "1 minute")

	def test_edge_cases_single_units(self):
		"""Test edge cases that result in single units."""
		# Large single units
		self.assertEqual(format_time_interval_words(259200_000), "3 days")  # 3 days exactly
		self.assertEqual(format_time_interval_words(604800_000), "7 days")  # 1 week
		
		# Small single units
		self.assertEqual(format_time_interval_words(999), "999 milliseconds")
		self.assertEqual(format_time_interval_words(59000), "59 seconds")

	def test_consistency_with_compact_format(self):
		"""Test that compound intervals match the compact format exactly."""
		test_values = [
			3661_000,    # 1h1m1s
			5445_000,    # 1h30m45s
			90_000,      # 1m30s
			1500,        # 1s500ms
			95_445_500,  # 1d2h30m45s500ms
		]
		
		for milliseconds in test_values:
			words_result = format_time_interval_words(milliseconds)
			compact_result = format_time_interval(milliseconds)
			self.assertEqual(words_result, compact_result,
				f"Compound interval mismatch: {milliseconds}ms -> words: '{words_result}', compact: '{compact_result}'")

	def test_boundary_values(self):
		"""Test values at unit boundaries."""
		# Exactly at boundaries (single units)
		self.assertEqual(format_time_interval_words(1000), "1 second")
		self.assertEqual(format_time_interval_words(60_000), "1 minute")
		self.assertEqual(format_time_interval_words(3600_000), "1 hour")
		self.assertEqual(format_time_interval_words(86400_000), "1 day")
		
		# Just over boundaries (compound, fallback)
		self.assertEqual(format_time_interval_words(1001), "1s1ms")
		self.assertEqual(format_time_interval_words(60_001), "1m1ms")
		self.assertEqual(format_time_interval_words(3600_001), "1h1ms")


if __name__ == '__main__':
	unittest.main()
