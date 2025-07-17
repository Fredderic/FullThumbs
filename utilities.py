"""
General utility functions for FullThumbs application.

This module contains utility functions that are not specific to Windows APIs
or any particular framework, providing general-purpose functionality used
throughout the application.
"""

import re


def parse_time_interval(time_str):
	"""
	Parse time interval string into milliseconds.
	
	Supports:
	- Single units: '4h', '30m', '2d', '3600s', '500ms'
	- Multiple units: '2h15m', '1d2h30m', '1h30m45s500ms'
	- Numbers without units default to hours: '4' -> 4 hours
	- Order doesn't matter: '15m2h' same as '2h15m'
	
	Returns None if parsing fails.
	"""
	if not time_str:
		return None
	
	time_str = time_str.lower()
	
	# Reject strings with spaces (before any processing)
	if ' ' in time_str:
		return None
	
	# Handle pure numbers (no units) - default to hours
	if re.match(r'^\d+(?:\.\d+)?$', time_str):
		value = float(time_str)
		if value == 0.0:
			return 0
		return round(value * 3600_000)
	
	# Define unit patterns and their millisecond multipliers
	units = {
		'ms': 1,
		's': 1000,
		'm': 60_000,
		'h': 3600_000,
		'd': 24 * 3600_000
	}
	
	# Create regex pattern that matches all units with values
	# Pattern matches: number (with optional decimal) followed by unit
	pattern = r'(\d+(?:\.\d+)?)(ms|[smhd])'
	matches = re.findall(pattern, time_str)
	
	if not matches:
		return None
	
	# Check that the entire string was consumed by our matches
	# Reconstruct what we matched and compare with original
	matched_parts = []
	for value, unit in matches:
		matched_parts.append(f"{value}{unit}")
	reconstructed = ''.join(matched_parts)
	
	if reconstructed != time_str:
		return None  # String contains invalid characters or formatting
	
	# Check for duplicate units
	used_units = [unit for _, unit in matches]
	if len(used_units) != len(set(used_units)):
		return None  # Duplicate units not allowed
	
	# Calculate total milliseconds
	total_ms = 0
	has_zero_with_unit = False
	
	for value_str, unit in matches:
		value = float(value_str)
		
		# Track zero values with explicit units
		if value == 0.0 and unit:
			has_zero_with_unit = True
		
		total_ms += round(value * units[unit])
	
	# Force non-zero inputs that round to 0 to be 1ms (let validation catch it)
	if total_ms == 0 and not has_zero_with_unit and matches:
		total_ms = 1
	
	# Warning for zero with explicit unit (only if it's the only component)
	if has_zero_with_unit and len(matches) == 1:
		print(f"Warning: Specifying '0{matches[0][1]}' is unusual - did you mean just '0'?")
	
	return total_ms


def validate_auto_update_interval(milliseconds):
	"""
	Validate that auto-update interval meets minimum requirements.
	Returns the interval in milliseconds if valid, None if invalid.
	"""
	if milliseconds is None:
		return None
	
	# Convert to seconds for validation
	seconds = milliseconds // 1000
	
	# Enforce minimum interval of 60 seconds (1 minute) for auto-updates
	if seconds > 0 and seconds < 60:
		return None
	
	return milliseconds
