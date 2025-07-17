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
	- Special values: 'default', 'minimum'
	- Single units: '4h', '30m', '2d', '3600s', '500ms'
	- Multiple units: '2h15m', '1d2h30m', '1h30m45s500ms'
	- Numbers without units default to hours: '4' -> 4 hours
	- Order doesn't matter: '15m2h' same as '2h15m'
	
	Returns None if parsing fails.
	"""
	if not time_str:
		return None
	
	# Handle special values
	if time_str.lower() == 'default':
		from src import constants
		return constants.DEFAULT_UPDATE_INTERVAL_MS
	elif time_str.lower() == 'minimum':
		from src import constants
		return constants.MIN_UPDATE_INTERVAL_MS
	
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
	if ''.join(f"{value}{unit}" for value, unit in matches) != time_str:
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


def _get_time_interval_parts(milliseconds):
	"""
	Internal function to break down milliseconds into time unit parts.
	
	Returns a list of (count, unit_name) tuples.
	Example: 3661000 -> [(1, 'h'), (1, 'm'), (1, 's')]
	"""
	if milliseconds == 0:
		return []
	
	# Define units in descending order (largest first)
	units = [
		('d', 24 * 3600_000),  # days
		('h', 3600_000),       # hours  
		('m', 60_000),         # minutes
		('s', 1000),           # seconds
		('ms', 1)              # milliseconds
	]
	
	parts = []
	remaining = milliseconds
	
	for unit_name, unit_value in units:
		if remaining >= unit_value:
			count = remaining // unit_value
			remaining = remaining % unit_value
			parts.append((count, unit_name))
	
	return parts


def format_time_interval(milliseconds):
	"""
	Convert milliseconds back to human-readable format.
	
	Examples:
	- 3600000 -> "1h"
	- 60000 -> "1m" 
	- 14400000 -> "4h"
	- 9000000 -> "2h30m"
	- 90000 -> "1m30s"
	
	Returns the most compact representation using appropriate units.
	"""
	if milliseconds == 0:
		return "0"
	
	parts = _get_time_interval_parts(milliseconds)
	return ''.join(f"{count}{unit}" for count, unit in parts) if parts else "0ms"


def format_time_interval_words(milliseconds):
	"""
	Convert milliseconds to human-readable format using whole words.
	
	If the interval consists of only one time unit, uses full words like
	"30 minutes" or "10 seconds". For compound intervals, falls back to
	the compact format like "2h30m".
	
	Examples:
	- 3600000 -> "1 hour"
	- 60000 -> "1 minute"
	- 30000 -> "30 seconds"
	- 9000000 -> "2h30m" (compound, falls back)
	- 90000 -> "1m30s" (compound, falls back)
	"""
	if milliseconds == 0:
		return "0"
	
	parts = _get_time_interval_parts(milliseconds)
	
	if not parts:
		return "0 milliseconds"
	
	# If only one part, use whole words
	if len(parts) == 1:
		count, unit = parts[0]
		
		# Define singular and plural forms
		unit_words = {
			'ms': ('millisecond', 'milliseconds'),
			's': ('second', 'seconds'),
			'm': ('minute', 'minutes'),
			'h': ('hour', 'hours'),
			'd': ('day', 'days')
		}
		
		singular, plural = unit_words[unit]
		word = singular if count == 1 else plural
		return f"{count} {word}"
	
	# Multiple parts - fall back to compact format
	return format_time_interval(milliseconds)


def validate_auto_update_interval(milliseconds):
	"""
	Validate that auto-update interval meets minimum requirements.
	Returns the interval in milliseconds if valid, None if invalid.
	"""
	if milliseconds is None:
		return None
	
	from src import constants
	
	# Enforce minimum interval for auto-updates
	if milliseconds > 0 and milliseconds < constants.MIN_UPDATE_INTERVAL_MS:
		return None
	
	return milliseconds
