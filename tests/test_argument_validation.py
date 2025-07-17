#!/usr/bin/env python3
"""
Test suite for argument validation in full-thumbs.py

This module tests the command-line argument parsing and validation logic,
including update interval validation and time interval parsing.
"""

import unittest
import sys
import os
import argparse
from unittest.mock import patch
from io import StringIO

# Add the project root to the path so we can import from utilities.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the functions we want to test
from utilities import parse_time_interval, validate_auto_update_interval

# Still need full-thumbs module for parse_arguments function
import importlib.util
full_thumbs_path = os.path.join(project_root, "full-thumbs.py")
spec = importlib.util.spec_from_file_location("full_thumbs", full_thumbs_path)
if spec and spec.loader:
	full_thumbs = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(full_thumbs)
else:
	raise ImportError("Could not load full-thumbs.py module")

class TestArgumentValidation(unittest.TestCase):
	"""Test the argument parsing validation functions."""
	
	def test_update_interval_ms_validation_valid(self):
		"""Test that valid millisecond intervals are accepted."""
		# Test valid values
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '0']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.update_interval, 0)
		
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '1000']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.update_interval, 1000)
		
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '60000']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.update_interval, 60000)
	
	def test_update_interval_ms_validation_negative(self):
		"""Test that negative millisecond intervals are rejected."""
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '-1']):
			with self.assertRaises(SystemExit):  # argparse raises SystemExit on error
				with patch('sys.stderr', new_callable=StringIO):  # Suppress error output
					full_thumbs.parse_arguments()
	
	def test_auto_update_minimum_interval_integration(self):
		"""Test that auto-update intervals are validated for minimum time in integration context."""
		interval_ms = parse_time_interval("1m")
		self.assertEqual(validate_auto_update_interval(interval_ms), 60_000)
		
		interval_ms = parse_time_interval("60s")
		self.assertEqual(validate_auto_update_interval(interval_ms), 60_000)
		
		interval_ms = parse_time_interval("2h")
		self.assertEqual(validate_auto_update_interval(interval_ms), 7_200_000)
		
		# Invalid intervals (< 60 seconds) should return None after validation
		interval_ms = parse_time_interval("30s")
		self.assertIsNone(validate_auto_update_interval(interval_ms))
		
		interval_ms = parse_time_interval("59s")
		self.assertIsNone(validate_auto_update_interval(interval_ms))

	def test_multiple_unit_parsing_integration(self):
		"""Test that the new multiple unit functionality works in integration context."""
		# Test complex multi-unit expressions
		interval_ms = parse_time_interval("1h30m15s")
		self.assertEqual(interval_ms, 5_415_000)  # 1.5 hours + 15 seconds
		validated = validate_auto_update_interval(interval_ms)
		self.assertEqual(validated, 5_415_000)  # Should pass validation (> 60s)
		
		# Test with milliseconds
		interval_ms = parse_time_interval("2h30m500ms")
		self.assertEqual(interval_ms, 9_000_500)  # 2.5 hours + 500ms
		validated = validate_auto_update_interval(interval_ms)
		self.assertEqual(validated, 9_000_500)
		
		# Test order independence
		interval_ms1 = parse_time_interval("30m2h")
		interval_ms2 = parse_time_interval("2h30m")
		self.assertEqual(interval_ms1, interval_ms2)
		self.assertEqual(interval_ms1, 9_000_000)  # 2.5 hours
		
		# Test that short multi-unit intervals are rejected by validation
		interval_ms = parse_time_interval("30s500ms")
		self.assertEqual(interval_ms, 30_500)  # 30.5 seconds
		validated = validate_auto_update_interval(interval_ms)
		self.assertIsNone(validated)  # Should fail validation (< 60s)

class TestArgumentParsing(unittest.TestCase):
	"""Test various argument parsing scenarios."""
	
	def test_run_command_default(self):
		"""Test run command with default arguments."""
		with patch('sys.argv', ['full-thumbs.py', 'run']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.command, 'run')
			self.assertEqual(args.update_interval, 0)
	
	def test_auto_update_default(self):
		"""Test auto-update with default interval."""
		with patch('sys.argv', ['full-thumbs.py', '--auto-update']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.auto_update, 'default')
	
	def test_no_arguments_default_behavior(self):
		"""Test default behavior when no auto-update arguments are specified."""
		with patch('sys.argv', ['full-thumbs.py']):
			args = full_thumbs.parse_arguments()
			self.assertIsNone(args.auto_update)
			self.assertFalse(args.no_auto_update)
	
	def test_auto_update_custom_interval(self):
		"""Test auto-update with custom interval."""
		with patch('sys.argv', ['full-thumbs.py', '--auto-update=2h']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.auto_update, '2h')
	
	def test_no_auto_update(self):
		"""Test disabling auto-update."""
		with patch('sys.argv', ['full-thumbs.py', '--no-auto-update']):
			args = full_thumbs.parse_arguments()
			self.assertTrue(args.no_auto_update)
	
	def test_mutually_exclusive_auto_update(self):
		"""Test that auto-update arguments are mutually exclusive."""
		with patch('sys.argv', ['full-thumbs.py', '--auto-update', '--no-auto-update']):
			with self.assertRaises(SystemExit):  # argparse raises SystemExit on error
				with patch('sys.stderr', new_callable=StringIO):  # Suppress error output
					full_thumbs.parse_arguments()

class TestIntegrationScenarios(unittest.TestCase):
	"""Test integration scenarios combining multiple features."""
	
	def test_run_with_1_second_interval(self):
		"""Test that run command accepts 1 second (1000ms) interval."""
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '1000']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.update_interval, 1000)
	
	def test_run_with_very_high_interval(self):
		"""Test that run command accepts very high intervals."""
		with patch('sys.argv', ['full-thumbs.py', 'run', '--update-interval', '3600000']):
			args = full_thumbs.parse_arguments()
			self.assertEqual(args.update_interval, 3_600_000)
	
	def test_auto_update_time_parsing_integration(self):
		"""Test that auto-update rejects intervals shorter than 1 minute in context."""
		interval_ms = parse_time_interval("30s")
		self.assertIsNone(validate_auto_update_interval(interval_ms))
		
		interval_ms = parse_time_interval("59s")
		self.assertIsNone(validate_auto_update_interval(interval_ms))
		
		interval_ms = parse_time_interval("0.5m")
		self.assertIsNone(validate_auto_update_interval(interval_ms))
	
	def test_time_conversion_to_milliseconds(self):
		"""Test that time interval parsing and millisecond handling works correctly."""
		# Test basic conversion
		milliseconds = parse_time_interval("2h")
		self.assertEqual(milliseconds, 7_200_000)
		
		# Test with minutes
		milliseconds = parse_time_interval("5m")
		self.assertEqual(milliseconds, 300_000)
		
		# Test with exact 1 minute minimum for validation
		milliseconds = parse_time_interval("1m")
		self.assertEqual(milliseconds, 60_000)
		validated = validate_auto_update_interval(milliseconds)
		self.assertEqual(validated, 60_000)
		
		# Test fractional seconds preservation
		milliseconds = parse_time_interval("1.5s")
		self.assertEqual(milliseconds, 1500)
	
	def test_complete_auto_update_workflow(self):
		"""Test the complete workflow from auto-update parsing to run command generation."""
		auto_update_arg = "2h"
		
		# Step 1: Parse the time interval
		interval_ms = parse_time_interval(auto_update_arg)
		self.assertEqual(interval_ms, 7_200_000)
		
		# Step 2: Validate for auto-update use
		update_check_interval_ms = validate_auto_update_interval(interval_ms)
		self.assertEqual(update_check_interval_ms, 7_200_000)
		
		# Step 3: Simulate what happens in main when run command is processed
		self.assertEqual(update_check_interval_ms, 7_200_000)
		
		# Verify the workflow is consistent
		self.assertEqual(interval_ms, update_check_interval_ms)

if __name__ == '__main__':
	# Set up the test suite
	unittest.main(verbosity=2)
