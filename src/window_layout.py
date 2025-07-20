""" NOTES and TODOs:
- WM_SIZE message handler (to handle window resizing)
- WM_GETMINMAXINFO message handler

SIZING SYSTEM: ✅ COMPLETE
	✅ FIXED		always use the same size
	✅ EXPAND		distribute space evenly among children
	✅ GROW			consume space in order from smallest to largest
	✅ Mixed sizing methods with unified grow algorithm
	✅ Maximum size constraints and limits
	✅ Intelligent text wrapping with word boundaries
	✅ String-based font measurement (ready for real APIs)
	✅ Shrink-then-grow space optimization
	✅ Bidirectional layout (width and height)
	✅ Content-aware minimum constraints

POSITIONING SYSTEM: ✅ COMPLETE
	✅ Widget position storage and retrieval
	✅ Hierarchical positioning (parent-to-child)
	✅ Alignment support (left, center, right, top, bottom)
	✅ Padding offsets and spacing
	✅ Complete layout method (size + position)

+ Fit sizing widths
+ Grow and shrink widths
+ Wrap text
+ Fit sizing heights
+ Grow and shrink heights
+ Positioning
- Draw widgets
"""

# -------
# Text Measurement Interface
# -------

def _default_measure_text_width(text, font=None):
	"""Default text width measurement implementation.
	
	This is a placeholder implementation that provides rough estimates
	based on character classification. In production, this should be
	replaced with actual font measurement using system APIs.
	
	Args:
		text: The complete text string to measure
		font: Font information (currently unused)
		
	Returns:
		int: Estimated text width in pixels
	"""
	if not text:
		return 0
	
	# TODO: Replace with actual text measurement APIs like:
	# Windows: GetTextExtentPoint32(hdc, text, len(text), &size)
	# Cross-platform: FreeType, Skia, Pango, etc.
	
	# For now, use character classification for better estimates
	# These are very rough approximations - real measurement is essential
	width = 0
	for char in text:
		if char == ' ':
			width += 4  # Spaces are narrow
		elif char in 'ij':
			width += 4  # Very narrow characters
		elif char in 'Il1':
			width += 5  # Narrow characters
		elif char in 'frt':
			width += 6  # Somewhat narrow
		elif char in 'abcdeghknopqsuvxyz':
			width += 8  # Average width
		elif char in 'ABCDEFGHIJKLMNOPQRSTUVXYZ':
			width += 10  # Capital letters are wider
		elif char in 'mw':
			width += 12  # Wide lowercase
		elif char in 'MW':
			width += 14  # Wide capitals
		elif ord(char) > 127:
			# Non-ASCII characters - could be anything!
			# CJK characters are typically much wider
			if ord(char) >= 0x4E00 and ord(char) <= 0x9FFF:  # CJK range
				width += 16  # CJK characters are typically wider
			elif ord(char) >= 0x0100:  # Extended Latin and beyond
				width += 10  # Assume similar to capitals
			else:
				width += 8  # Default assumption
		else:
			width += 8  # Punctuation and other characters
	
	return width

def _default_get_font_metrics(font=None):
	"""Default font metrics implementation.
	
	This is a placeholder that will eventually interface with the system's
	font measurement APIs to get accurate font information.
	
	Args:
		font: Font information (currently unused)
		
	Returns:
		dict: Font metrics with keys 'height'
	"""
	# TODO: Replace with actual font measurement using system APIs
	# For Windows, this would use GDI functions like GetTextMetrics
	# For cross-platform, could use libraries like FreeType
	
	font_height = 16  # Default UI font height
	
	return {
		'height': font_height,
	}

# Global text measurement function - can be replaced by applications
measure_text_width = _default_measure_text_width
get_font_metrics = _default_get_font_metrics

def set_text_measurement_functions(width_func=None, metrics_func=None):
	"""Set custom text measurement functions.
	
	This allows applications to replace the default estimation functions
	with actual font measurement implementations using system APIs.
	
	Args:
		width_func: Function(text, font) -> int that measures text width,
		           or None to restore the default function
		metrics_func: Function(font) -> dict that returns font metrics,
		            or None to restore the default function
	"""
	global measure_text_width, get_font_metrics
	
	if width_func is not None:
		measure_text_width = width_func
	else:
		measure_text_width = _default_measure_text_width
	
	if metrics_func is not None:
		get_font_metrics = metrics_func
	else:
		get_font_metrics = _default_get_font_metrics

# -------
# Layout Classes
# -------

class Dimension(tuple):
	"""Base class for dimension sizing.
	
	This class defines the interface for different sizing strategies.
	Subclasses should implement get_minimum() and get_maximum() methods.
	"""
	__slots__ = ()
	
	def __new__(cls, *args, **kwargs):
		"""Create a new Dimension instance.
		
		If called on the base Dimension class with a single numeric argument,
		automatically wrap it in a Fixed dimension. If passed a Dimension instance,
		return it unchanged. Otherwise, create the appropriate subclass instance.
		"""
		if cls is Dimension:
			# Called on base class - check if we should auto-wrap in Fixed
			if len(args) == 1 and len(kwargs) == 0:
				if isinstance(args[0], (int, float)):
					return Fixed(args[0])
				elif isinstance(args[0], Dimension):
					# Already a Dimension instance, return it unchanged
					return args[0]
			# If we get here, it's an invalid call to the base class
			raise TypeError("Dimension base class cannot be instantiated directly")
		else:
			# Called on a subclass - tuple.__new__ will handle the data
			return tuple.__new__(cls)
	
	@property
	def minim(self):
		"""The minimum size for this dimension."""
		raise NotImplementedError("Subclasses must implement minim property")
	
	@property
	def maxim(self):
		"""The maximum size for this dimension, or None for unlimited."""
		raise NotImplementedError("Subclasses must implement maxim property")

class Fixed(Dimension):
	"""
	Fixed dimension that always returns the same size.
	"""

	__slots__ = ()
	
	def __new__(cls, value):
		assert isinstance(value, (int, float)), f"Fixed value must be a number, got {type(value).__name__}: {value}"
		return tuple.__new__(cls, (value,))

	@property
	def minim(self):
		return self[0]
	
	@property
	def maxim(self):
		return self[0]
	
	def __str__(self):
		return f"Fixed({self[0]})"

class Expand(Dimension):
	"""
	Expand dimension that distributes space evenly among children.
	"""

	__slots__ = ()
	
	def __new__(cls, minimum=0, maximum=None):
		assert isinstance(minimum, (int, float)), f"Expand minimum must be a number, got {type(minimum).__name__}: {minimum}"
		assert maximum is None or isinstance(maximum, (int, float)), f"Expand maximum must be a number or None, got {type(maximum).__name__}: {maximum}"
		return tuple.__new__(cls, (minimum, maximum))

	@property
	def minim(self):
		return self[0]

	@property
	def maxim(self):
		return self[1]  # Return maximum limit (could be None for unlimited)
	
	def __str__(self):
		minimum, maximum = self[0], self[1]
		if maximum is None:
			if minimum == 0:
				return "Expand()"
			else:
				return f"Expand(minimum={minimum})"
		else:
			return f"Expand(minimum={minimum}, maximum={maximum})"

class Grow(Dimension):
	"""
	Grow dimension that consumes space in order from smallest to largest.
	"""

	__slots__ = ()
	
	def __new__(cls, minimum=0, maximum=None):
		assert isinstance(minimum, (int, float)), f"Grow minimum must be a number, got {type(minimum).__name__}: {minimum}"
		assert maximum is None or isinstance(maximum, (int, float)), f"Grow maximum must be a number or None, got {type(maximum).__name__}: {maximum}"
		return tuple.__new__(cls, (minimum, maximum))

	@property
	def minim(self):
		return self[0]

	@property
	def maxim(self):
		return self[1]  # Return maximum limit (could be None for unlimited)
	
	def __str__(self):
		minimum, maximum = self[0], self[1]
		if maximum is None:
			if minimum == 0:
				return "Grow()"
			else:
				return f"Grow(minimum={minimum})"
		else:
			return f"Grow(minimum={minimum}, maximum={maximum})"

# -------

class Layout:
	# Alignment constants
	# Note: Boolean values work as alignment too - False=START (0.0), True=END (1.0)
	START = 0.0
	CENTER = 0.5
	END = 1.0
	
	# Legacy aliases for backward compatibility
	LEFT = START
	RIGHT = END
	
	def __init__(self):
		# Store computed sizes and positions as arrays for easy axis indexing
		# [width, height] and [x, y] - allows using [axis] and [1-axis] patterns
		self._computed_size: list[int | None] = [None, None]  # [width, height]
		self._computed_pos: list[int | None] = [None, None]   # [x, y]
	
	def query_width_request(self) -> int:
		# Default implementation returns 0
		return 0
	
	def query_height_request(self) -> int:
		# Default implementation returns 0
		return 0
	
	def query_space_request(self) -> tuple[int, int]:
		# Convenience method that combines width and height requests
		return (self.query_width_request(), self.query_height_request())
	
	def distribute_width(self, available_width: int) -> int:
		# Default implementation returns the query width (no distribution)
		width = self.query_width_request()
		self._computed_size[0] = width  # Store in array position 0 (width)
		return width
	
	def distribute_height(self, available_height: int) -> int:
		# Default implementation returns the query height (no distribution)
		height = self.query_height_request()
		self._computed_size[1] = height  # Store in array position 1 (height)
		return height
	
	def get_computed_width(self) -> int | None:
		"""Get the computed width from the last distribution pass."""
		return self._computed_size[0]
	
	def get_computed_height(self) -> int | None:
		"""Get the computed height from the last distribution pass."""
		return self._computed_size[1]
	
	def get_computed_size(self, axis=None):
		"""Get computed size. If axis specified, return size for that axis, otherwise return (width, height) tuple."""
		if axis is None:
			return (self._computed_size[0], self._computed_size[1])
		return self._computed_size[axis]
	
	def position_at(self, x: int, y: int) -> None:
		"""Position this widget at the specified coordinates.
		
		This method sets the widget's position and recursively positions
		any child widgets based on the layout algorithm.
		
		Args:
			x: The x-coordinate (left edge) of the widget
			y: The y-coordinate (top edge) of the widget
		"""
		self._computed_pos[0] = x  # Store in array position 0 (x)
		self._computed_pos[1] = y  # Store in array position 1 (y)
	
	def get_computed_x(self) -> int | None:
		"""Get the computed x position from the last positioning pass."""
		return self._computed_pos[0]
	
	def get_computed_y(self) -> int | None:
		"""Get the computed y position from the last positioning pass."""
		return self._computed_pos[1]
	
	def get_computed_position(self, axis=None):
		"""Get computed position. If axis specified, return position for that axis, otherwise return (x, y) tuple."""
		if axis is None:
			return (self._computed_pos[0], self._computed_pos[1])
		return self._computed_pos[axis]
	
	def get_computed_rect(self) -> tuple[int | None, int | None, int | None, int | None]:
		"""Get the computed rectangle (x, y, width, height) from the last layout passes."""
		return (self._computed_pos[0], self._computed_pos[1], self._computed_size[0], self._computed_size[1])
	
	def layout(self, x: int, y: int, width: int, height: int) -> tuple[int, int]:
		"""Perform complete layout: size distribution and positioning.
		
		This is a convenience method that performs both size distribution and
		positioning in the correct order.
		
		Args:
			x: The x-coordinate for positioning
			y: The y-coordinate for positioning
			width: The available width for size distribution
			height: The available height for size distribution
			
		Returns:
			tuple[int, int]: The actual (width, height) used by the layout
		"""
		# First distribute sizes
		actual_width = self.distribute_width(width)
		actual_height = self.distribute_height(height)
		
		# Then position at the specified coordinates
		self.position_at(x, y)
		
		return (actual_width, actual_height)
	
	def get_preferred_width(self) -> int | None:
		# Default implementation returns None (not shrinkable)
		return None
	
	def try_shrink_width(self, target_width: int) -> int:
		"""Try to shrink to target width with intelligent content reflow.
		
		This method is called when the layout algorithm needs a widget to shrink
		below its preferred width. The widget should attempt to reflow its content
		(e.g., text wrapping) to fit the target width and return the actual width
		it can achieve.
		
		Args:
			target_width: The desired width to shrink to
			
		Returns:
			The actual width achieved after content reflow. May be larger than
			target_width if the content cannot be made smaller.
		
		Default implementation just clamps to minimum width.
		"""
		return max(target_width, self.query_width_request())

	@staticmethod
	def _argument_expand_2(value, default_second=None):
		"""Expand a single value to a tuple of two values.
		
		Args:
			value: The value to expand (can be single value, tuple, or list)
			default_second: If provided, use this as the second value when expanding
			               single values instead of repeating the first value
		
		Returns:
			tuple: Two-element tuple
		"""
		if not isinstance(value, (list, tuple)):
			# Single value - use default_second if provided, otherwise repeat the value
			second_value = default_second if default_second is not None else value
			return (value, second_value)
		elif len(value) == 1:
			# Single element in sequence - same logic as above
			second_value = default_second if default_second is not None else value[0]
			return (value[0], second_value)
		elif len(value) == 2:
			return tuple(value)
		assert False, "Invalid value format"

	@staticmethod
	def _argument_expand_4(value):
		"""Expand a single value to a tuple of four values."""
		if not isinstance(value, (list, tuple)):
			return (value,) * 4
		elif len(value) == 1:
			return (value[0],) * 4
		elif len(value) == 2:
			return (value[0], value[1]) * 2
		elif len(value) == 4:
			return tuple(value)
		assert False, "Invalid value format"

# --- single-child layouts

class LayoutSingle(Layout):
	def __init__(self, child=None):
		super().__init__()
		self.child = child

	def query_width_request(self):
		# Query the width requirements of the child layout
		if self.child:
			return self.child.query_width_request()
		return super().query_width_request()
	
	def query_height_request(self):
		# Query the height requirements of the child layout
		if self.child:
			return self.child.query_height_request()
		return super().query_height_request()
	
	def distribute_width(self, available_width: int) -> int:
		# Pass through width distribution to child
		if self.child:
			width = self.child.distribute_width(available_width)
			self._computed_size[0] = width
			return width
		return super().distribute_width(available_width)
	
	def distribute_height(self, available_height: int) -> int:
		# Pass through height distribution to child
		if self.child:
			height = self.child.distribute_height(available_height)
			self._computed_size[1] = height
			return height
		return super().distribute_height(available_height)
	
	def position_at(self, x: int, y: int) -> None:
		"""Position this layout and its child at the specified coordinates."""
		super().position_at(x, y)
		# Pass through positioning to child (same position)
		if self.child:
			self.child.position_at(x, y)

class LayoutWindow(LayoutSingle):
	pass

class LayoutPadding(LayoutSingle):
	def __init__(self, padding=10, child=None):
		super().__init__(child)
		self.padding = self._argument_expand_4(padding)

	def query_width_request(self):
		# Calculate horizontal padding
		width_padding = self.padding[0] + self.padding[2]
		# Query the width requirements of the child layout
		if self.child:
			return self.child.query_width_request() + width_padding
		# If no child, return just the horizontal padding
		return width_padding
	
	def query_height_request(self):
		# Calculate vertical padding
		height_padding = self.padding[1] + self.padding[3]
		# Query the height requirements of the child layout
		if self.child:
			return self.child.query_height_request() + height_padding
		# If no child, return just the vertical padding
		return height_padding
	
	def distribute_width(self, available_width: int) -> int:
		# Calculate horizontal padding
		width_padding = self.padding[0] + self.padding[2]
		
		# Distribute to child with padding subtracted
		if self.child:
			child_width = available_width - width_padding
			if child_width > 0:
				actual_child_width = self.child.distribute_width(child_width)
				width = actual_child_width + width_padding
				self._computed_size[0] = width
				return width
		
		# If no child or no space, return just the padding
		width = width_padding
		self._computed_size[0] = width
		return width
	
	def distribute_height(self, available_height: int) -> int:
		# Calculate vertical padding
		height_padding = self.padding[1] + self.padding[3]
		
		# Distribute to child with padding subtracted
		if self.child:
			child_height = available_height - height_padding
			if child_height > 0:
				actual_child_height = self.child.distribute_height(child_height)
				height = actual_child_height + height_padding
				self._computed_size[1] = height
				return height
		
		# If no child or no space, return just the padding
		height = height_padding
		self._computed_size[1] = height
		return height
	
	def position_at(self, x: int, y: int) -> None:
		"""Position this padding layout and its child with padding offset."""
		super().position_at(x, y)
		# Position child with padding offset
		if self.child:
			child_x = x + self.padding[0]  # left padding
			child_y = y + self.padding[1]  # top padding
			self.child.position_at(child_x, child_y)

class LayoutExpand(LayoutSingle):
	def __init__(self, expand=True, child=None):
		super().__init__(child)
		self.expand = self._argument_expand_2(expand)

# --- multi-child layouts

class LayoutGroup(Layout):
	HORIZONTAL = 0
	VERTICAL = 1

	# Base class for all container layouts
	def __init__(self, *children):
		super().__init__()
		self.children = children

class LayoutContainer(LayoutGroup):
	# Unified 1D container layout that can arrange children vertically or horizontally
	def __init__(self, *, axis=LayoutGroup.VERTICAL, align=Layout.START, gap=0, children=()):
		super().__init__(*children)
		self.axis = axis
		self.gap = gap  # Space between children
		# Handle alignment: single value applies to primary axis, defaults cross axis to START
		self.align = self._argument_expand_2(align, Layout.START)
		# Cache for generated gap widgets to avoid recreating them during layout passes
		self._gap_widget_cache = []
		# Cache for the complete children_with_gaps list
		self._children_with_gaps_cache = None
	
	@classmethod
	def vertical(cls, *, align=Layout.START, gap=0, children=()):
		# align can be single value (for vertical axis) or 2-tuple (vertical, horizontal)
		# gap can be int/float for spacing, or a callable that returns Layout widgets
		return cls(axis=LayoutGroup.VERTICAL, align=align, gap=gap, children=children)
	
	@classmethod
	def horizontal(cls, *, align=Layout.START, gap=0, children=()):
		# align can be single value (for horizontal axis) or 2-tuple (horizontal, vertical)
		# gap can be int/float for spacing, or a callable that returns Layout widgets
		return cls(axis=LayoutGroup.HORIZONTAL, align=align, gap=gap, children=children)
	
	def _get_gap_info(self):
		"""Analyze the gap configuration and return gap handling strategy.
		
		Returns:
			dict with keys:
			- 'type': 'simple' or 'widget'
			- 'size': For simple gaps, the numeric size (may be 0)
			- 'builder': For widget gaps, the builder function
			- 'total_simple_gap': Total space needed for simple gaps
		"""
		if not self.children or len(self.children) <= 1:
			return {'type': 'simple', 'size': 0, 'builder': None, 'total_simple_gap': 0}
		
		gap_count = len(self.children) - 1
		gap_value = self.gap
		
		# Handle Fixed dimensions by reducing to numeric value
		if isinstance(gap_value, Fixed):
			# Reduce Fixed dimension to its numeric value
			gap_value = gap_value.minim
		
		if callable(gap_value):
			# gap is a builder function - use widget-based gaps
			return {'type': 'widget', 'size': 0, 'builder': gap_value, 'total_simple_gap': 0}
		elif gap_value is None:
			# None is an alias for 0 - use simple gaps with size 0
			gap_value = 0
		
		if isinstance(gap_value, (int, float)):
			# gap is a simple number - use optimized simple gaps
			if gap_value >= 0:
				total_gap = gap_count * gap_value
				return {'type': 'simple', 'size': gap_value, 'builder': None, 'total_simple_gap': total_gap}
			else:
				# Negative gap value - raise error for explicit handling
				raise ValueError(f"Gap size cannot be negative: {gap_value}")
		elif isinstance(self.gap, (Expand, Grow)):
			# Expand/Grow dimension gap - use widget-based gaps with LayoutSpacer
			if self.axis == LayoutGroup.HORIZONTAL:
				gap_builder = lambda: LayoutSpacer(width=self.gap, height=0)
			else:  # LayoutGroup.VERTICAL
				gap_builder = lambda: LayoutSpacer(width=0, height=self.gap)
			return {'type': 'widget', 'size': 0, 'builder': gap_builder, 'total_simple_gap': 0}
		else:
			# Unknown gap type - raise error for explicit handling
			raise TypeError(f"Unsupported gap type: {type(self.gap).__name__}. "
							f"Gap must be a number, Fixed/Expand/Grow dimension, or callable.")
	
	def _get_children_with_gaps(self):
		"""Return children with gaps inserted between them.
		
		For simple numeric gaps (including size 0), this returns just the children (gaps handled in positioning).
		For widget-based gaps, this returns children with LayoutSpacer widgets inserted.
		"""
		# Return cached result if available
		if self._children_with_gaps_cache is not None:
			return self._children_with_gaps_cache
		
		gap_info = self._get_gap_info()
		
		if gap_info['type'] == 'simple':
			# Simple gaps (including size 0) - return children as-is (gaps handled in positioning)
			self._children_with_gaps_cache = self.children
			return self._children_with_gaps_cache
		
		# Widget-based gaps - build children with gap widgets
		gap_builder = gap_info['builder']
		
		# Ensure we have enough cached gap widgets
		gap_count = len(self.children) - 1
		while len(self._gap_widget_cache) < gap_count:
			self._gap_widget_cache.append(gap_builder())

		# Build children with gaps using cached widgets
		children_it = iter(self.children)
		children_with_gaps = [next(children_it)]
		for gap_widget, child in zip(self._gap_widget_cache[:gap_count], children_it):
			children_with_gaps.append(gap_widget)
			children_with_gaps.append(child)

		# Cache the result
		self._children_with_gaps_cache = children_with_gaps
		return self._children_with_gaps_cache

	def _invalidate_gap_cache(self):
		"""Clear the gap widget cache. Call this when gap configuration changes."""
		self._gap_widget_cache.clear()
		self._children_with_gaps_cache = None
	
	def query_width_request(self):
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		# Get gap information for accurate size calculation
		gap_info = self._get_gap_info()
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal: sum widths + simple gaps
			child_width = sum(child.query_width_request() for child in children_with_gaps)
			return child_width + gap_info['total_simple_gap']
		else:
			# Vertical: max width (gaps don't affect width)
			return max(child.query_width_request() for child in children_with_gaps)
	
	def query_height_request(self):
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		# Get gap information for accurate size calculation
		gap_info = self._get_gap_info()
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal: max height (gaps don't affect height)
			return max(child.query_height_request() for child in children_with_gaps)
		else:
			# Vertical: sum heights + simple gaps
			child_height = sum(child.query_height_request() for child in children_with_gaps)
			return child_height + gap_info['total_simple_gap']
	
	def distribute_width(self, available_width: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			self._computed_size[0] = 0
			return 0
		
		if self.axis == LayoutGroup.VERTICAL:
			# Vertical container: all children get the same available width
			for child in children_with_gaps:
				child.distribute_width(available_width)
			self._computed_size[0] = available_width
			return available_width
		
		# Horizontal container: distribute width among children, accounting for simple gaps
		gap_info = self._get_gap_info()
		
		# For simple gaps, reduce available space by total gap space
		child_available_width = available_width - gap_info['total_simple_gap']
		child_available_width = max(0, child_available_width)  # Ensure non-negative
		
		def get_width_info(child):
			# Check if widget has preferred width (indicating it can shrink)
			min_request = child.query_width_request()
			preferred_width = child.get_preferred_width()
			if preferred_width is not None:
				can_shrink = True
			else:
				preferred_width = min_request
				can_shrink = False
			
			return (min_request, getattr(child, 'width', None), preferred_width, can_shrink)
		
		# Use generalized distribution algorithm
		all_widgets = self._distribute_space_general(children_with_gaps, child_available_width, get_width_info)
		
		# Apply the allocated widths
		for info in all_widgets:
			info['child'].distribute_width(info['allocated'])
		
		# Calculate actual width needed: sum of allocated child widths + gaps
		total_child_width = sum(info['allocated'] for info in all_widgets)
		actual_width_needed = total_child_width + gap_info['total_simple_gap']
		
		# Container claims the maximum of available width and actual width needed
		container_width = max(available_width, actual_width_needed)
		self._computed_size[0] = container_width
		return container_width
	
	def distribute_height(self, available_height: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			self._computed_size[1] = 0
			return 0
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal container: all children get the same available height
			for child in children_with_gaps:
				child.distribute_height(available_height)
			self._computed_size[1] = available_height
			return available_height
		
		# Vertical container: distribute height among children, accounting for simple gaps
		gap_info = self._get_gap_info()
		
		# For simple gaps, reduce available space by total gap space
		child_available_height = available_height - gap_info['total_simple_gap']
		child_available_height = max(0, child_available_height)  # Ensure non-negative
		
		def get_height_info(child):
			# Height distribution doesn't typically involve shrinking
			min_request = child.query_height_request()
			return (min_request, getattr(child, 'height', None), min_request, False)
		
		# Use generalized distribution algorithm
		all_widgets = self._distribute_space_general(children_with_gaps, child_available_height, get_height_info)
		
		# Apply the allocated heights
		for info in all_widgets:
			info['child'].distribute_height(info['allocated'])
		
		# Calculate actual height needed: sum of allocated child heights + gaps
		total_child_height = sum(info['allocated'] for info in all_widgets)
		actual_height_needed = total_child_height + gap_info['total_simple_gap']
		
		# Container claims the maximum of available height and actual height needed
		container_height = max(available_height, actual_height_needed)
		self._computed_size[1] = container_height
		return container_height
	
	def _distribute_space_general(self, children, available_space, get_child_info):
		"""Generalized space distribution algorithm that works for both width and height.
		
		Args:
			children: List of child widgets
			available_space: Total space available for distribution
			get_child_info: Function that takes a child and returns (min_request, dimension, preferred_size, can_shrink)
			
		Returns:
			List of info dictionaries with allocated space for each widget
		"""
		# Step 1: Collect and categorize child information by distribution strategy
		fixed_widgets = []
		variable_widgets = []  # Both Expand and Grow widgets together
		shrinkable_widgets = []  # Widgets that can shrink below their minimum
		total_minimum = 0
		total_preferred = 0
		
		for child in children:
			min_request, dimension, preferred_size, can_shrink = get_child_info(child)
			
			# Determine dimension type for distribution
			if dimension is not None:
				actual_dimension = dimension
			else:
				# No explicit dimension - treat as Fixed at query request
				actual_dimension = Fixed(min_request)
			
			info = {
				'child': child,
				'dimension': actual_dimension,
				'min_space': min_request,
				'preferred_space': preferred_size,
				'allocated': preferred_size,  # Start with preferred size
				'can_shrink': can_shrink,
				'is_grow': isinstance(actual_dimension, Grow)  # Track if this is a Grow widget for sorting
			}
			
			# Categorize by distribution strategy
			if isinstance(actual_dimension, Fixed):
				fixed_widgets.append(info)
			elif isinstance(actual_dimension, (Expand, Grow)):
				variable_widgets.append(info)
			else:
				# Unknown dimension type - treat as Fixed
				fixed_widgets.append(info)
			
			# Track shrinkable widgets separately
			if can_shrink:
				shrinkable_widgets.append(info)
			
			total_minimum += min_request
			total_preferred += preferred_size
		
		# Step 2: Handle space deficit first (shrinking), then redistribute any excess
		extra_space = available_space - total_preferred
		
		if extra_space < 0 and shrinkable_widgets:
			# Step 3a: Shrink widgets that can shrink to reclaim needed space
			space_to_reclaim = -extra_space  # Make it positive
			self._shrink_widgets(shrinkable_widgets, space_to_reclaim)
			
			# Step 3b: Calculate how much space we actually have after shrinking
			# Widgets might have shrunk more than needed, creating excess space
			total_allocated_after_shrink = sum(info['allocated'] for info in fixed_widgets + variable_widgets)
			extra_space = available_space - total_allocated_after_shrink
		
		# Step 3: Distribute any extra space using unified grow algorithm
		if extra_space > 0 and variable_widgets:
			self._distribute_variable_widgets(variable_widgets, extra_space)
		
		# Return all widgets for the caller to apply allocations
		return fixed_widgets + variable_widgets
	
	def _distribute_variable_widgets(self, variable_widgets, available_space):
		"""Distribute space to both Expand and Grow widgets using grow algorithm.
		
		Both widget types grow equally, but Grow widgets drive the iteration order.
		"""
		if not variable_widgets:
			return
		
		remaining_space = available_space
		
		# Step 1: Filter out widgets that have reached their maximum
		active_grow_widgets = []
		active_expand_widgets = []
		for info in variable_widgets:
			max_size = info['dimension'].maxim
			if max_size is None or info['allocated'] < max_size:
				if info['is_grow']:
					active_grow_widgets.append(info)
				else:
					active_expand_widgets.append(info)
		
		# Sort active grow widgets by allocated width (smallest first)
		active_grow_widgets.sort(key=lambda info: info['allocated'])

		def allocate_space_to_widgets(widgets, remaining_space, allocation):
			"""Give space to widgets, respecting maximums, and return space left."""
			if not widgets or remaining_space <= 0 or allocation <= 0:
				return remaining_space
			
			for info in widgets[:]:  # Use slice copy to avoid issues when modifying the list
				max_size = info['dimension'].maxim
				old_size = info['allocated']
				new_size = old_size + allocation
				
				if max_size is not None and new_size >= max_size:
					new_size = max_size
					widgets.remove(info)  # Remove from list if max reached
				
				space_used = new_size - old_size
				info['allocated'] = new_size
				remaining_space -= space_used
				
				if remaining_space <= 0:
					break
			
			return max(0, remaining_space)
		
		widgets_at_min = []

		if active_grow_widgets:
			# Implement unified grow algorithm: all variable widgets grow together
			current_min = active_grow_widgets[0]['allocated']

			for info in active_grow_widgets:
				# If we have a Grow widget at current_min, add it to the list
				next_target = info['allocated']
				if next_target == current_min:
					widgets_at_min.append(info)
					continue

				# Bring all widgets at current_min level up to next_target
				total_widgets_to_expand = len(widgets_at_min) + len(active_expand_widgets)
				space_needed_per_widget = next_target - current_min
				total_space_needed = space_needed_per_widget * total_widgets_to_expand

				if total_space_needed > remaining_space:
					space_needed_per_widget = remaining_space // total_widgets_to_expand
					if space_needed_per_widget <= 0:
						# Not enough space to give even 1 pixel to each widget
						break
				
				remaining_space = allocate_space_to_widgets(widgets_at_min, remaining_space, space_needed_per_widget)
				remaining_space = allocate_space_to_widgets(active_expand_widgets, remaining_space, space_needed_per_widget)

				if remaining_space <= 0:
					# No space left to allocate
					return
				
				widgets_at_min.append(info)	# Now we can safely add this widget to the list of widgets at min
				current_min = next_target	# ... And update current_min to the next target size

		# Distribute remaining space evenly among Expand widgets, and any un-finished Grow widgets
		active_expand_widgets += widgets_at_min
		while remaining_space > 0 and active_expand_widgets:
			allocation_per_widget = remaining_space // len(active_expand_widgets)
			if allocation_per_widget <= 0:
				# Not enough space to give even 1 pixel to each widget - break to avoid infinite loop
				break
			remaining_space = allocate_space_to_widgets(active_expand_widgets, remaining_space, allocation_per_widget)
	
	def _shrink_widgets(self, shrinkable_widgets, space_to_reclaim):
		"""Shrink widgets that can shrink using intelligent content reflow.
		
		This method uses try_shrink_width() to allow widgets to shrink intelligently
		and may give back extra space if widgets can't shrink as much as requested.
		"""
		if not shrinkable_widgets or space_to_reclaim <= 0:
			return
		
		remaining_to_reclaim = space_to_reclaim
		
		# Sort shrinkable widgets by current allocated size (largest first for shrinking)
		active_shrinkable = [info for info in shrinkable_widgets 
							if info['allocated'] > info['min_space']]
		active_shrinkable.sort(key=lambda info: info['allocated'], reverse=True)
		
		def shrink_widgets_intelligently(widgets, remaining_to_reclaim, target_shrink_per_widget):
			"""Shrink widgets using try_shrink_width and return space left to reclaim."""
			if not widgets or remaining_to_reclaim <= 0 or target_shrink_per_widget <= 0:
				return remaining_to_reclaim
			
			for info in widgets[:]:  # Use slice copy to avoid issues when modifying the list
				old_size = info['allocated']
				target_size = old_size - target_shrink_per_widget
				
				# Use try_shrink_width for intelligent shrinking
				if hasattr(info['child'], 'try_shrink_width'):
					actual_size = info['child'].try_shrink_width(target_size)
				else:
					# Fallback to simple clamping for widgets without intelligent shrinking
					actual_size = max(target_size, info['min_space'])
				
				# Ensure we don't go below minimum
				actual_size = max(actual_size, info['min_space'])
				
				# If widget couldn't shrink at all, remove it to avoid infinite loops
				if actual_size >= old_size:
					widgets.remove(info)
					continue
				
				if actual_size <= info['min_space']:
					actual_size = info['min_space']
					widgets.remove(info)  # Remove from list if minimum reached
				
				space_reclaimed = old_size - actual_size
				info['allocated'] = actual_size
				remaining_to_reclaim -= space_reclaimed
				
				if remaining_to_reclaim <= 0:
					break
			
			return max(0, remaining_to_reclaim)
		
		widgets_at_max = []
		
		if active_shrinkable:
			# Implement shrinking algorithm: work from largest to smallest
			current_max = active_shrinkable[0]['allocated']
			
			for info in active_shrinkable:
				# If we have a widget at current_max, add it to the list
				next_target = info['allocated']
				if next_target == current_max:
					widgets_at_max.append(info)
					continue
				
				# Bring all widgets at current_max level down to next_target
				shrink_per_widget = current_max - next_target
				total_shrink_needed = shrink_per_widget * len(widgets_at_max)
				
				if total_shrink_needed > remaining_to_reclaim:
					shrink_per_widget = remaining_to_reclaim // len(widgets_at_max)
					if shrink_per_widget <= 0:
						# Not enough space to reclaim even 1 pixel from each widget
						break
				
				remaining_to_reclaim = shrink_widgets_intelligently(widgets_at_max, remaining_to_reclaim, shrink_per_widget)
				
				if remaining_to_reclaim <= 0:
					# Reclaimed enough space
					return
				
				widgets_at_max.append(info)  # Add this widget to the list at current level
				current_max = next_target  # Update current level
		
		# Distribute remaining shrinking evenly among all remaining shrinkable widgets
		while remaining_to_reclaim > 0 and widgets_at_max:
			shrink_per_widget = remaining_to_reclaim // len(widgets_at_max)
			if shrink_per_widget <= 0:
				# Not enough space to reclaim even 1 pixel from each widget - break to avoid infinite loop
				break
			remaining_to_reclaim = shrink_widgets_intelligently(widgets_at_max, remaining_to_reclaim, shrink_per_widget)
	
	def position_at(self, x: int, y: int) -> None:
		"""Position this container and all its children according to the layout algorithm."""
		super().position_at(x, y)
		
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return
		
		# Position children using unified axis-based method
		self._position_children_unified(x, y, children_with_gaps, self.axis)
	
	def _position_children_unified(self, container_x: int, container_y: int, children, axis: int) -> None:
		"""Unified positioning method that works for both horizontal and vertical containers.
		
		Args:
			container_x: X coordinate of container
			container_y: Y coordinate of container  
			children: List of child widgets to position (may include gap widgets or just actual children)
			axis: 0 for horizontal (primary axis = width), 1 for vertical (primary axis = height)
		"""
		# Get container size and gap information
		container_size = self.get_computed_size()
		container_pos = [container_x, container_y]
		gap_info = self._get_gap_info()
		
		# Handle None values by defaulting to 0
		container_axis_size = container_size[axis] or 0
		container_cross_size = container_size[1-axis] or 0
		
		if gap_info['type'] == 'simple':
			# Optimized positioning for simple numeric gaps
			actual_children = self.children
			gap_size = gap_info['size']
			
			# Calculate total space used along primary axis (children only, gaps added separately)
			total_child_size = sum(child.get_computed_size(axis) or 0 for child in actual_children)
			total_gap_size = gap_info['total_simple_gap']
			total_axis_size = total_child_size + total_gap_size
			
			# Calculate starting position based on primary axis alignment  
			if total_axis_size < container_axis_size:
				# There's extra space - use primary axis alignment
				extra_space = container_axis_size - total_axis_size
				start_axis = container_pos[axis] + int(extra_space * self.align[0])  # align[0] is primary axis
			else:
				# No extra space - start at container edge
				start_axis = container_pos[axis]
			
			# Position each child with gaps
			current_axis = start_axis
			cross_axis = 1 - axis  # Cross axis is the other dimension
			
			for i, child in enumerate(actual_children):
				child_size = child.get_computed_size()
				child_axis_size = child_size[axis] or 0
				child_cross_size = child_size[cross_axis] or 0
				
				# Calculate cross-axis position based on cross-axis alignment
				if child_cross_size < container_cross_size:
					# There's extra space on cross axis - use cross axis alignment
					extra_cross = container_cross_size - child_cross_size
					child_cross = container_pos[cross_axis] + int(extra_cross * self.align[1])  # align[1] is cross axis
				else:
					# No extra space - align to container edge
					child_cross = container_pos[cross_axis]
				
				# Build position tuple in correct order [x, y]
				pos = [0, 0]
				pos[axis] = current_axis
				pos[cross_axis] = child_cross
				
				# Position the child
				child.position_at(pos[0], pos[1])
				
				# Advance position by child size + gap (except for last child)
				current_axis += child_axis_size
				if i < len(actual_children) - 1:  # Not the last child
					current_axis += gap_size
		elif gap_info['type'] == 'widget':
			# Positioning for widget-based gaps
			# Calculate total space used along primary axis
			total_axis_size = sum(child.get_computed_size(axis) or 0 for child in children)
			
			# Calculate starting position based on primary axis alignment  
			if total_axis_size < container_axis_size:
				# There's extra space - use primary axis alignment
				extra_space = container_axis_size - total_axis_size
				start_axis = container_pos[axis] + int(extra_space * self.align[0])  # align[0] is primary axis
			else:
				# No extra space - start at container edge
				start_axis = container_pos[axis]
			
			# Position each child
			current_axis = start_axis
			cross_axis = 1 - axis  # Cross axis is the other dimension
			
			for child in children:
				child_size = child.get_computed_size()
				child_axis_size = child_size[axis] or 0
				child_cross_size = child_size[cross_axis] or 0
				
				# Calculate cross-axis position based on cross-axis alignment
				if child_cross_size < container_cross_size:
					# There's extra space on cross axis - use cross axis alignment
					extra_cross = container_cross_size - child_cross_size
					child_cross = container_pos[cross_axis] + int(extra_cross * self.align[1])  # align[1] is cross axis
				else:
					# No extra space - align to container edge
					child_cross = container_pos[cross_axis]
				
				# Build position tuple in correct order [x, y]
				pos = [0, 0]
				pos[axis] = current_axis
				pos[cross_axis] = child_cross
				
				# Position the child
				child.position_at(pos[0], pos[1])
				current_axis += child_axis_size

# --- leaf node layouts

class LayoutWidget(Layout):
	# def __init__(self):
	# 	super().__init__()
	pass

class LayoutSpacer(LayoutWidget):
	def __init__(self, width=0, height=0):
		super().__init__()
		# Use Dimension auto-wrapping to handle both raw values and Dimension instances
		self.width = Dimension(width)
		self.height = Dimension(height)
	
	def query_width_request(self):
		return self.width.minim
	
	def query_height_request(self):
		return self.height.minim
	
	def distribute_width(self, available_width: int) -> int:
		# Spacers with Fixed dimensions stay at their minimum
		# Spacers with Expand/Grow dimensions could grow, but for gaps we usually want them fixed
		# For now, keep gap spacers at their minimum size
		width = self.width.minim
		self._computed_size[0] = width
		return width
	
	def distribute_height(self, available_height: int) -> int:
		# Spacers with Fixed dimensions stay at their minimum
		# Spacers with Expand/Grow dimensions could grow, but for gaps we usually want them fixed
		# For now, keep gap spacers at their minimum size
		height = self.height.minim
		self._computed_size[1] = height
		return height

class LayoutText(LayoutWidget):
	def __init__(self, text, font=None, color=None):
		super().__init__()
		self.text = text
		self.font = font
		self.color = color
	
	@staticmethod
	def get_extents(text, font=None):
		"""Estimate the extents (width, height) of text.
		
		This is a convenience method that uses the global text measurement
		functions to calculate text dimensions.
		
		Args:
			text: The text string to measure
			font: Font information (passed to measurement functions)
			
		Returns:
			tuple[int, int]: Estimated (width, height) in pixels
		"""
		if not text:
			return (0, 0)
		
		metrics = get_font_metrics(font)
		font_height = metrics['height']
		
		# For multiline text, calculate based on lines
		lines = text.split('\n')
		if len(lines) > 1:
			max_line_width = max(measure_text_width(line, font) for line in lines)
			width = max_line_width
			height = len(lines) * font_height
		else:
			width = measure_text_width(text, font)
			height = font_height
		
		return (width, height)
	
	def query_width_request(self):
		# Return minimum width (reasonable minimum for text rendering)
		if not self.text:
			return 0
		
		# Minimum width should be based on actual content, but allow for some shrinking
		# Use a small representative text sample to determine reasonable minimum
		sample_chars = "Wj"  # Wide and narrow character combination
		min_char_width = measure_text_width(sample_chars, self.font) // 2
		return max(min_char_width * 2, 16)  # At least space for a couple characters
	
	def query_height_request(self):
		# Use the static method for text measurement
		_, height = self.get_extents(self.text, self.font)
		return height
	
	def get_preferred_width(self):
		"""Return the preferred width (unwrapped text width).
		
		This indicates that the text can shrink below this size by wrapping.
		"""
		# Use the static method for text measurement
		width, _ = self.get_extents(self.text, self.font)
		return width
	
	def try_shrink_width(self, target_width: int) -> int:
		"""Try to shrink to target width with intelligent text wrapping.
		
		This method wraps text at word boundaries and returns the actual
		width achieved, which may be larger than target_width if the text
		contains very long words.
		"""
		if not self.text:
			return 0
		
		# Try wrapping at word boundaries
		words = self.text.split()
		if not words:
			return 0
		
		# Find the longest word - this sets our absolute minimum
		longest_word_width = max(measure_text_width(word, self.font) for word in words)
		min_width = self.query_width_request()
		actual_min = max(min_width, longest_word_width)
		
		if target_width <= actual_min:
			return actual_min
		
		# Simulate text wrapping by building complete lines and measuring them
		lines = []
		current_line_words = []
		
		for word in words:
			# Try adding this word to the current line
			test_line_words = current_line_words + [word]
			test_line_text = ' '.join(test_line_words)
			test_line_width = measure_text_width(test_line_text, self.font)
			
			if test_line_width <= target_width:
				# Word fits on current line
				current_line_words = test_line_words
			else:
				# Word doesn't fit, finish current line and start new one
				if current_line_words:
					lines.append(' '.join(current_line_words))
					current_line_words = [word]
				else:
					# Single word too long for line - force it anyway
					current_line_words = [word]
		
		# Don't forget the last line
		if current_line_words:
			lines.append(' '.join(current_line_words))
		
		# Find the actual width needed (measure the widest line)
		if lines:
			actual_width = max(measure_text_width(line, self.font) for line in lines)
			return max(actual_width, actual_min)
		else:
			return actual_min
	
	def distribute_width(self, available_width: int) -> int:
		"""Accept the allocated width for text wrapping.
		
		The text will use the allocated width and wrap accordingly.
		"""
		# Clamp to minimum width
		min_width = self.query_width_request()
		width = max(available_width, min_width)
		self._computed_size[0] = width
		return width

class LayoutButton(LayoutWidget):
	def __init__(self, text, id, width=None, height=None):
		super().__init__()
		self.id = id
		
		# Use Dimension auto-wrapping for cleaner initialization
		self.width = None if width is None else Dimension(width)
		self.height = None if height is None else Dimension(height)
		
		# Set text using the method to create the private LayoutText
		self.set_text(text)
	
	def set_text(self, text):
		"""Update the button text and refresh the internal layout calculations."""
		# Create a new LayoutText for text measurement calculations
		self._text_layout = LayoutText(text)
	
	def get_text(self):
		"""Get the current button text from the internal layout."""
		return self._text_layout.text
	
	def query_width_request(self):
		# Return explicit width if provided, otherwise calculate from text
		if self.width is not None:
			return self.width.minim
		
		# Use private LayoutText for text measurement
		text_width = self._text_layout.query_width_request()
		return max(text_width + 20, 75)  # Min 75px width, add padding
	
	def query_height_request(self):
		# Return explicit height if provided, otherwise calculate from text
		if self.height is not None:
			return self.height.minim
		
		# Use private LayoutText for text measurement
		text_height = self._text_layout.query_height_request()
		return max(text_height + 5, 25)  # Min 25px height, add padding
	
	def distribute_width(self, available_width: int) -> int:
		# If no explicit width dimension, behave like Fixed (return query width)
		if self.width is None:
			width = self.query_width_request()
			self._computed_size[0] = width
			return width
		
		# Handle different dimension types
		if isinstance(self.width, Fixed):
			width = self.width.minim
			self._computed_size[0] = width
			return width
		elif isinstance(self.width, (Expand, Grow)):
			# For Expand/Grow, use the available width (clamped to minimum and maximum)
			min_width = self.width.minim
			max_width = self.width.maxim
			
			result = max(available_width, min_width)
			if max_width is not None:
				result = min(result, max_width)
			self._computed_size[0] = result
			return result
		else:
			# Fallback for unknown dimension types
			width = self.query_width_request()
			self._computed_size[0] = width
			return width
	
	def distribute_height(self, available_height: int) -> int:
		# If no explicit height dimension, behave like Fixed (return query height)
		if self.height is None:
			height = self.query_height_request()
			self._computed_size[1] = height
			return height
		
		# Handle different dimension types
		if isinstance(self.height, Fixed):
			height = self.height.minim
			self._computed_size[1] = height
			return height
		elif isinstance(self.height, (Expand, Grow)):
			# For Expand/Grow, use the available height (clamped to minimum and maximum)
			min_height = self.height.minim
			max_height = self.height.maxim
			
			result = max(available_height, min_height)
			if max_height is not None:
				result = min(result, max_height)
			self._computed_size[1] = result
			return result
		else:
			# Fallback for unknown dimension types
			height = self.query_height_request()
			self._computed_size[1] = height
			return height
	
	def get_preferred_width(self):
		"""Return preferred width if the button can shrink (text wrapping), otherwise None.
		
		A button can shrink if it has a width dimension that could accommodate text wrapping.
		"""
		if self.width is None:
			# No explicit width - button uses text width, could potentially wrap
			text_width = self._text_layout.get_preferred_width()
			return max(text_width + 20, 75)  # Add padding and minimum width
		elif isinstance(self.width, (Expand, Grow)):
			# Variable width - could potentially shrink for text wrapping
			text_width = self._text_layout.get_preferred_width()
			button_preferred = max(text_width + 20, 75)  # Add padding and minimum width
			
			# Only return preferred width if it's larger than the dimension minimum
			if button_preferred > self.width.minim:
				return button_preferred
		
		# Fixed width or other cases - not shrinkable
		return None
	
	def try_shrink_width(self, target_width: int) -> int:
		"""Try to shrink button width, but buttons don't wrap so just clamp to minimum."""
		if self.width is None:
			# Auto-sized button - can't shrink below text + padding
			return self.query_width_request()
		elif isinstance(self.width, (Expand, Grow)):
			# Variable width button - clamp to dimension minimum
			return max(target_width, self.width.minim)
		else:
			# Fixed width button - return fixed size
			return self.query_width_request()

class LayoutEdit(LayoutWidget):
	def __init__(self, text, multiline=False, read_only=False, width=None, height=None):
		super().__init__()
		self.multiline = multiline
		self.read_only = read_only
		
		# Use Dimension auto-wrapping for cleaner initialization
		self.width = None if width is None else Dimension(width)
		self.height = None if height is None else Dimension(height)
		
		# Set text using the method to create the private LayoutText
		self.set_text(text)
	
	def set_text(self, text):
		"""Update the edit control text and refresh the internal layout calculations."""
		# Create a new LayoutText for text measurement calculations
		self._text_layout = LayoutText(text)
	
	def get_text(self):
		"""Get the current edit control text from the internal layout."""
		return self._text_layout.text
	
	def query_width_request(self):
		# Return explicit width if provided, otherwise calculate from text
		if self.width is not None:
			return self.width.minim
		
		# Use private LayoutText for text measurement
		text_width = self._text_layout.query_width_request()
		return text_width + 20  # Add padding for edit control borders and internal spacing
	
	def query_height_request(self):
		# Return explicit height if provided, otherwise calculate from text
		if self.height is not None:
			return self.height.minim
		
		# Use private LayoutText for text measurement
		text_height = self._text_layout.query_height_request()
		return text_height + 10  # Add padding for edit control borders and internal spacing
	
	def get_preferred_width(self):
		"""Return preferred width if the edit control can shrink (text wrapping), otherwise None.
		
		An edit control can shrink if it's multiline and has a width dimension that could accommodate text wrapping.
		"""
		if not self.multiline:
			# Single-line edit controls don't wrap - not shrinkable
			return None
		
		if self.width is None:
			# No explicit width - edit control uses text width, could potentially wrap
			text_width = self._text_layout.get_preferred_width()
			return text_width + 20  # Add padding
		elif isinstance(self.width, (Expand, Grow)):
			# Variable width - could potentially shrink for text wrapping
			text_width = self._text_layout.get_preferred_width()
			edit_preferred = text_width + 20  # Add padding
			
			# Only return preferred width if it's larger than the dimension minimum
			if edit_preferred > self.width.minim:
				return edit_preferred
		
		# Fixed width or other cases - not shrinkable
		return None

class LayoutLink(LayoutText):
	def __init__(self, text, url, font=None, color=None):
		self.text = text
		self.url = url
		self.font = font
		self.color = color

class LayoutHorizontalLine(LayoutWidget):
	def query_width_request(self):
		return 0  # No horizontal space request
	
	def query_height_request(self):
		return 1  # 1px tall

# -------

def build_about_dialog(about_text, github_link):
	"""Build the layout for the about dialog.
	
	Args:
		about_text: The main text content for the dialog
		github_link: URL for the GitHub repository link
	"""
	return LayoutWindow(
		LayoutContainer.vertical(
			children=(
				LayoutPadding(10,
					LayoutContainer.vertical(
						gap=5,  # 5px gap between text and link
						children=(
							LayoutEdit(about_text, multiline=True, read_only=True, width=380, height=150),
							LayoutLink("Visit GitHub Repository", github_link, font="Arial", color="blue")
						)
					),
				),
				LayoutHorizontalLine(),
				LayoutPadding(10,
					LayoutContainer.horizontal(
						align=Layout.END,
						gap=5,  # 5px gap between buttons
						children=(
							LayoutButton("Copy", id=1003, width=75, height=25),
							LayoutButton("OK", id=1002, width=75, height=25),
						)
					)
				)
			)
		)
	)


def build_test_button_layout():
	"""Build a simple test layout for testing distribution functionality.
	
	This creates a horizontal container with buttons and gaps to test:
	- Fixed dimension buttons
	- Expand/Grow dimensions
	- Gap spacers
	- Maximum size limits
	"""
	return LayoutContainer.horizontal(
		gap=10,  # Creates LayoutSpacer widgets between buttons
		children=(
			LayoutButton("Fixed", id=1, width=75),  # Fixed width
			LayoutButton("Expand", id=2, width=Expand(minimum=50, maximum=120)),  # Expand width with max
			LayoutButton("Grow Small", id=3, width=Grow(minimum=30)),  # Grow width (small, no max)
			LayoutButton("Grow Large", id=4, width=Grow(minimum=100, maximum=150)),  # Grow width (large, with max)
			LayoutButton("Auto", id=5),  # Auto-sized based on text
		)
	)


def build_test_text_layout():
	"""Build a test layout for text wrapping functionality.
	
	This creates a horizontal container with text that can wrap.
	"""
	return LayoutContainer.horizontal(
		gap=10,
		children=(
			LayoutButton("Fixed", id=1, width=75),  # Fixed width button
			LayoutText("This is a long text that should wrap when space is limited", font="Arial"),  # Wrappable text
			LayoutButton("End", id=2, width=50),  # Another fixed button
		)
	)


def build_test_vertical_layout():
	"""Build a simple vertical test layout for testing height distribution functionality.
	
	This creates a vertical container with buttons and gaps to test:
	- Fixed dimension buttons
	- Expand/Grow dimensions
	- Gap spacers
	- Maximum size limits
	"""
	return LayoutContainer.vertical(
		gap=5,  # Creates LayoutSpacer widgets between buttons
		children=(
			LayoutButton("Fixed Height", id=1, height=25),  # Fixed height
			LayoutButton("Expand Height", id=2, height=Expand(minimum=20, maximum=60)),  # Expand height with max
			LayoutButton("Grow Small", id=3, height=Grow(minimum=15)),  # Grow height (small, no max)
			LayoutButton("Grow Large", id=4, height=Grow(minimum=40, maximum=80)),  # Grow height (large, with max)
			LayoutButton("Auto Height", id=5),  # Auto-sized based on text
		)
	)

# -------

if __name__ == "__main__":
	"""Run a simple demonstration when the module is executed directly."""
	
	# Simple demonstration of the layout system
	print("Window Layout Engine Demo")
	print("=" * 25)
	
	# Build a sample dialog
	about_text = """FullThumbs PiP Viewer
Version: 1.0.0-dev
A Picture-in-Picture viewer application for Windows."""
	
	github_link = "https://github.com/Fredderic/FullThumbs"
	layout = build_about_dialog(about_text, github_link)
	
	print(f"Full Dialog Layout: {type(layout).__name__}")
	print(f"Full Dialog Dimensions: {layout.query_space_request()}")
	print()
	
	# Build test button layout for distribution testing
	test_layout = build_test_button_layout()
	print(f"Test Button Layout: {type(test_layout).__name__}")
	print(f"Test Layout Dimensions: {test_layout.query_space_request()}")
	print()
	
	# Show the button details
	print("Button layout children:")
	children_with_gaps = test_layout._get_children_with_gaps()
	for i, child in enumerate(children_with_gaps):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			width_info = f"width={child.width}" if child.width else "auto-width"
			print(f"  {i}: {type(child).__name__}('{text}') - {width_info} -> {child.query_space_request()}")
		else:
			print(f"  {i}: {type(child).__name__}(spacer) -> {child.query_space_request()}")
	
	print()
	
	# Test distribution with different available widths
	print("Testing width distribution:")
	test_widths = [300, 370, 400, 500, 800]  # minimum, some extra, lots extra, way too much
	
	for test_width in test_widths:
		print(f"\nDistributing {test_width}px width:")
		actual_width = test_layout.distribute_width(test_width)
		print(f"  Actual distributed width: {actual_width}px")
		
		# Test specific widgets with known allocations to better understand distribution
		print("  Expected behavior:")
		print(f"    Fixed: always 75px")
		print(f"    Expand(50, max=120): grows from 50px, capped at 120px")
		print(f"    Grow Small(30): grows from 30px, no limit")
		print(f"    Grow Large(100, max=150): grows from 100px, capped at 150px")
		print(f"    Auto: always 75px (acts like Fixed)")
		print(f"    Spacers: always 10px each (4 total = 40px)")
		
		non_spacer_space = test_width - 40  # Subtract spacer space
		print(f"    Non-spacer space to distribute: {non_spacer_space}px")
		
		fixed_space = 75 + 75  # Fixed + Auto
		variable_space = non_spacer_space - fixed_space
		print(f"    Space for variable widgets: {variable_space}px")
	
	print()
	
	# Test text wrapping with a new layout
	print("Testing text wrapping:")
	text_layout = build_test_text_layout()
	print(f"Text Layout Dimensions: {text_layout.query_space_request()}")
	
	# Test with various widths to see how text behaves
	test_text_widths = [200, 300, 400, 600]  # From constrained to spacious
	
	for test_width in test_text_widths:
		print(f"\nDistributing {test_width}px width for text layout:")
		actual_width = text_layout.distribute_width(test_width)
		print(f"  Actual distributed width: {actual_width}px")
		
		# Show expected behavior
		print("  Expected behavior:")
		print(f"    Fixed button: 75px")
		print(f"    Text: can shrink from preferred size (wrapping)")
		print(f"    End button: 50px")
		print(f"    Spacers: 20px total")
		print(f"    Available for text: {test_width - 75 - 50 - 20}px")
	
	print()
	
	# Test height distribution with vertical layout
	print("Testing height distribution:")
	vertical_layout = build_test_vertical_layout()
	print(f"Vertical Layout Dimensions: {vertical_layout.query_space_request()}")
	
	test_heights = [125, 150, 200, 300]  # minimum, some extra, lots extra, way too much
	
	for test_height in test_heights:
		print(f"\nDistributing {test_height}px height:")
		actual_height = vertical_layout.distribute_height(test_height)
		print(f"  Actual distributed height: {actual_height}px")
		
		print("  Expected behavior:")
		print(f"    Fixed: always 25px")
		print(f"    Expand(20, max=60): grows from 20px, capped at 60px")
		print(f"    Grow Small(15): grows from 15px, no limit")
		print(f"    Grow Large(40, max=80): grows from 40px, capped at 80px")
		print(f"    Auto: always 25px (acts like Fixed)")
		print(f"    Spacers: always 5px each (4 total = 20px)")
		
		non_spacer_space = test_height - 20  # Subtract spacer space
		print(f"    Non-spacer space to distribute: {non_spacer_space}px")
		
		fixed_space = 25 + 25  # Fixed + Auto
		variable_space = non_spacer_space - fixed_space
		print(f"    Space for variable widgets: {variable_space}px")
	
	print()
	
	# Test positioning functionality
	print("Testing positioning:")
	simple_layout = LayoutContainer.horizontal(
		children=(
			LayoutButton("Left", id=1, width=75),
			LayoutButton("Right", id=2, width=50),
		)
	)
	
	# Perform complete layout at position (100, 200) with size 200x50
	actual_size = simple_layout.layout(100, 200, 200, 50)
	print(f"Simple layout actual size: {actual_size}")
	print(f"Container position: {simple_layout.get_computed_position()}")
	print(f"Container rect: {simple_layout.get_computed_rect()}")
	
	# Check child positions
	children_with_gaps = simple_layout._get_children_with_gaps()
	for i, child in enumerate(children_with_gaps):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			rect = child.get_computed_rect()
			print(f"  Button '{text}': {rect}")
		else:
			rect = child.get_computed_rect()
			print(f"  Spacer: {rect}")
	
	print()
	
	# Test alignment
	print("Testing alignment (centered buttons in larger container):")
	centered_layout = LayoutContainer.horizontal(
		align=Layout.CENTER,  # Center horizontally and vertically
		children=(
			LayoutButton("A", id=1, width=50, height=20),
			LayoutButton("B", id=2, width=50, height=20),
		)
	)
	
	# Layout in a larger space than needed
	actual_size = centered_layout.layout(0, 0, 300, 100)
	print(f"Centered layout actual size: {actual_size}")
	print(f"Container rect: {centered_layout.get_computed_rect()}")
	
	# Check child positions - should be centered
	children_with_gaps = centered_layout._get_children_with_gaps()
	for i, child in enumerate(children_with_gaps):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			rect = child.get_computed_rect()
			print(f"  Button '{text}': {rect}")
		else:
			rect = child.get_computed_rect()
			print(f"  Spacer: {rect}")
	
	expected_total_width = 100  # 50 + 50
	expected_x_offset = (300 - expected_total_width) // 2  # (300 - 100) / 2 = 100
	expected_y_offset = (100 - 20) // 2  # (100 - 20) / 2 = 40
	print(f"  Expected horizontal offset: {expected_x_offset}, vertical offset: {expected_y_offset}")
	print(f"  Note: Container only uses space it needs (100x100), not full available (300x100)")
	print(f"        Alignment happens within the container's bounds, not the full available space")
	
	print()
	
	# Test with padding to create a larger container that does use full space
	print("Testing alignment with padding (forces container to use full space):")
	padded_layout = LayoutPadding(
		padding=50,  # 50px padding on all sides
		child=LayoutContainer.horizontal(
			align=Layout.CENTER,
			children=(
				LayoutButton("X", id=1, width=40, height=20),
				LayoutButton("Y", id=2, width=40, height=20),
			)
		)
	)
	
	# Layout in available space
	actual_size = padded_layout.layout(0, 0, 300, 200)
	print(f"Padded layout actual size: {actual_size}")
	print(f"Outer container rect: {padded_layout.get_computed_rect()}")
	print(f"Inner container rect: {padded_layout.child.get_computed_rect()}")
	
	# Check child positions
	inner_children = padded_layout.child._get_children_with_gaps()
	for i, child in enumerate(inner_children):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			rect = child.get_computed_rect()
			print(f"  Button '{text}': {rect}")
	
	print(f"  Inner container available space: {200}x{100} (200x200 - 100px vertical padding)")
	print(f"  Buttons total width: 80px, so offset should be (200-80)/2 = 60px from inner left")
	print(f"  Inner left starts at x=50, so buttons should start at x=110")
	
	print()
	
	# Test improved alignment functionality
	print("Testing improved alignment (START/END vs LEFT/RIGHT):")
	
	# Test horizontal container with explicit cross-axis alignment
	horizontal_layout = LayoutContainer.horizontal(
		align=(Layout.CENTER, Layout.END),  # Center horizontally, align to bottom vertically
		children=(
			LayoutButton("A", id=1, width=50, height=20),
			LayoutButton("B", id=2, width=50, height=30),  # Different height to see cross-axis alignment
		)
	)
	
	# Layout in a larger space
	horizontal_layout.layout(0, 0, 200, 80)
	print(f"Horizontal container with (CENTER, END) alignment:")
	print(f"  Container rect: {horizontal_layout.get_computed_rect()}")
	
	children_with_gaps = horizontal_layout._get_children_with_gaps()
	for i, child in enumerate(children_with_gaps):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			rect = child.get_computed_rect()
			print(f"    Button '{text}': {rect}")
	
	print(f"  Expected: Buttons centered horizontally within 200px, aligned to bottom within 80px")
	print()
	
	# Test vertical container with cross-axis alignment
	vertical_layout = LayoutContainer.vertical(
		align=(Layout.END, Layout.CENTER),  # Align to bottom vertically, center horizontally
		children=(
			LayoutButton("X", id=3, width=40, height=25),
			LayoutButton("Y", id=4, width=60, height=25),  # Different width to see cross-axis alignment
		)
	)
	
	# Layout in a larger space
	vertical_layout.layout(0, 0, 150, 100)
	print(f"Vertical container with (END, CENTER) alignment:")
	print(f"  Container rect: {vertical_layout.get_computed_rect()}")
	
	children_with_gaps = vertical_layout._get_children_with_gaps()
	for i, child in enumerate(children_with_gaps):
		if hasattr(child, 'get_text'):
			text = child.get_text()
			rect = child.get_computed_rect()
			print(f"    Button '{text}': {rect}")
	
	print(f"  Expected: Buttons aligned to bottom within 100px, centered horizontally within 150px")
	print()
	
	# Test single-axis alignment (should default cross-axis to START)
	single_align_layout = LayoutContainer.horizontal(
		align=Layout.END,  # Only specify primary axis - cross axis should default to START
		children=(
			LayoutButton("Single", id=5, width=80, height=20),
		)
	)
	
	single_align_layout.layout(0, 0, 200, 60)
	print(f"Single alignment (END only) - cross axis should default to START:")
	print(f"  Container rect: {single_align_layout.get_computed_rect()}")
	button = single_align_layout._get_children_with_gaps()[0]
	print(f"  Button rect: {button.get_computed_rect()}")
	print(f"  Expected: Button aligned to right (END) horizontally, top (START) vertically")
	
	print()
	print("For comprehensive testing, run: python test_window_layout.py")
	print("For selective tests:")
	print("  Dimensions only: python -m unittest test_window_layout.TestDimensionClasses -v")
	print("  Widgets only:    python -m unittest test_window_layout.TestLayoutWidgets -v")
	print("  Containers only: python -m unittest test_window_layout.TestLayoutContainers -v")
	print("  Complex only:    python -m unittest test_window_layout.TestComplexLayouts -v")
