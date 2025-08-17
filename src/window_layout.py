from __future__ import annotations

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

Nice to haves:
- Stretch alignment options: "Space around" and "Space between" layout
	- Space between is just using Grow spacers between the widgets
		- This is already implemented in the layout system
		- Though doing it again could still be useful
	- Space Around is the same, but with an extra spacer at the start and end
		- This is not directly supported by the current system
		- You would need to add all the spacers yourself, and specify no gaps
	- But, we should be able to do better using the system for numeric gaps
		- Stretch over widget gaps should still work just fine, but...
		- Only widget gaps (and none) should be supported under stretch alignment

+ Fit sizing widths
+ Grow and shrink widths
+ Wrap text
+ Fit sizing heights
+ Grow and shrink heights
+ Positioning
- Draw widgets
"""

import math, operator
from functools import lru_cache
from typing import Optional, TypeVar, Any

# Global layout context for plugin system - will be initialized with decorator
_layout_context: Optional[LayoutPluginContext] = None


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
				if isinstance(args[0], (int, float, bool)):
					return Fixed(args[0])
				elif isinstance(args[0], Dimension):
					# Already a Dimension instance, return it unchanged
					return args[0]
			# If we get here, it's an invalid call to the base class
			raise TypeError("Dimension base class cannot be instantiated directly")
		else:
			# Called on a subclass - tuple.__new__ will handle the data
			return tuple.__new__(cls)

	@classmethod
	def orNone(cls, value):
		return None if value is None else cls(value)
	
	@property
	def minim(self):
		"""The minimum size for this dimension."""
		raise NotImplementedError("Subclasses must implement minim property")
	
	@property
	def maxim(self):
		"""The maximum size for this dimension, or None for unlimited."""
		raise NotImplementedError("Subclasses must implement maxim property")

	# def __str__(self):
	# 	return super().__str__()
	
	def __repr__(self):
		return f"{self.__class__.__name__}({self[0]})"

class Fixed(Dimension):
	"""
	Fixed dimension that always returns the same size.
	"""

	__slots__ = ()
	
	def __new__(cls, value):
		if isinstance(value, bool):
			value = int(value)
		assert isinstance(value, (int, float, bool)), \
			f"Fixed value must be a number, got {type(value).__name__}: {value}"
		return tuple.__new__(cls, (value,))

	@property
	def minim(self):
		return self[0]
	
	@property
	def maxim(self):
		return self[0]

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
	
	def __repr__(self):
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
	
	def __repr__(self):
		minimum, maximum = self[0], self[1]
		if maximum is None:
			if minimum == 0:
				return "Grow()"
			else:
				return f"Grow(minimum={minimum})"
		else:
			return f"Grow(minimum={minimum}, maximum={maximum})"

# -------

# _NOT_FOUND = object()

# class resettable_cached_property:
# 	def __init__(self, func):
# 		self.func = func
# 		self.attrname = None
# 		self.__doc__ = func.__doc__

# 	def __set_name__(self, owner, name):
# 		if self.attrname is None:
# 			self.attrname = name

# 	def __get__(self, instance, owner=None):
# 		if instance is None:
# 			return self
# 		instance_dict = instance.__dict__
# 		val = instance_dict.get(self.attrname, _NOT_FOUND)
# 		if val is _NOT_FOUND:
# 			val = self.func(instance)
# 			instance_dict[self.attrname] = val
# 			(instance_dict.setdefault('__cached_properties', {})
# 					.setdefault('@property', set()).add(self.attrname) )
# 		return val

# 	__class_getitem__ = classmethod(GenericAlias)

# 	@classmethod
# 	def _reset_cache(cls, instance):
# 		"""Reset the cache for the specified instance."""
# 		if (cache := instance.__dict__.get('__cached_properties')) is not None:
# 			for attrname in cache.get('@property', ()):
# 				if hasattr(instance, attrname):
# 					delattr(instance, attrname)
# 			cache.clear()

# F = TypeVar('F', bound=Callable[..., object])
# class resettable_cached_method:
# 	def __init__(self, func: F):
# 		self.func = func
# 		self.__doc__ = func.__doc__

# 	def __set_name__(self, owner, name):
# 		self.owner = owner
# 		self.cache_key = sys.intern(f'__resettable_cached_method:{name}')

# 	def __get__(self, instance, owner):
# 		if instance is None:
# 			# Called on the class, not an instance.
# 			return self
# 		# Called on an instance, so bind the instance to our __call__ method.
# 		return cast(F, partial(self, instance))

# 	def __call__(self, instance, *args, **kwargs):
# 		# Call the original function and cache the result
# 		instance_dict = instance.__dict__
# 		if (cache := instance_dict.get(self.cache_key, _NOT_FOUND)) is _NOT_FOUND:
# 			cache = instance_dict.setdefault(self.cache_key, {})
# 			instance_dict.setdefault('__cached_properties', set()).add(self.cache_key)
# 		key = hash( (*args, _NOT_FOUND, *kwargs.items()) )
# 		if (result := cache.get(key, _NOT_FOUND)) is _NOT_FOUND:
# 			result = self.func(instance, *args, **kwargs)
# 			cache[key] = result
# 		return result

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
		self._computed_size = [0, 0]  # [width, height]
		self._computed_pos = [0, 0]   # [x, y]
	
	def query_width_request(self) -> int:
		# Check if query_axis_request is overridden
		qar = type(self).query_axis_request
		if qar != Layout.query_axis_request:
			return qar(self, 0)
		# Default implementation returns 0
		return 0

	def query_height_request(self) -> int:
		# Check if query_axis_request is overridden
		qar = type(self).query_axis_request
		if qar != Layout.query_axis_request:
			return qar(self, 1)
		# Default implementation returns 0
		return 0
	
	def query_axis_request(self, axis: int) -> int:
		"""Query the request for a specific axis (0 for width, 1 for height)."""
		assert axis in (0, 1), ValueError(f"Invalid axis {axis}, must be 0 (width) or 1 (height)")
		
		# First check if individual width/height methods are overridden
		if axis == 0:
			width_method = type(self).query_width_request
			if width_method != Layout.query_width_request:
				return width_method(self)
		else:
			height_method = type(self).query_height_request
			if height_method != Layout.query_height_request:
				return height_method(self)
		
		return 0
	
	def query_space_request(self) -> tuple[int, int]:
		# Convenience method that combines width and height requests
		return (self.query_axis_request(0), self.query_axis_request(1))

	def distribute_width(self, available_width: int) -> int:
		# Default implementation returns the query width (no distribution)
		width = self.query_axis_request(0)
		self._computed_size[0] = width  # Store in array position 0 (width)
		return width
	
	def distribute_height(self, available_height: int) -> int:
		# Default implementation returns the query height (no distribution)
		height = self.query_axis_request(1)
		self._computed_size[1] = height  # Store in array position 1 (height)
		return height
	
	def get_computed_width(self) -> int:
		"""Get the computed width from the last distribution pass."""
		return self._computed_size[0]
	
	def get_computed_height(self) -> int:
		"""Get the computed height from the last distribution pass."""
		return self._computed_size[1]
	
	def get_computed_size(self, axis=None) -> tuple[int, int] | int:
		"""Get computed size. If axis specified, return size for that axis, otherwise return (width, height) tuple."""
		if axis is None:
			return (self._computed_size[0], self._computed_size[1])
		return self._computed_size[axis]
	
	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position this widget at the specified coordinates.
		
		This method sets the widget's position and recursively positions
		any child widgets based on the layout algorithm.
		
		Args:
			x: The x-coordinate (left edge) of the widget
			y: The y-coordinate (top edge) of the widget
			data: Optional data to pass through to child widgets (e.g. parent_hwnd for Win32 widgets)
		"""
		self._computed_pos[0] = x  # Store in array position 0 (x)
		self._computed_pos[1] = y  # Store in array position 1 (y)
	
	#@resettable_cached_method
	def get_computed_x(self) -> int | None:
		"""Get the computed x position from the last positioning pass."""
		return self._computed_pos[0]
	
	#@resettable_cached_method
	def get_computed_y(self) -> int | None:
		"""Get the computed y position from the last positioning pass."""
		return self._computed_pos[1]
	
	#@resettable_cached_method
	def get_computed_position(self, axis=None):
		"""Get computed position. If axis specified, return position for that axis, otherwise return (x, y) tuple."""
		if axis is None:
			return (self._computed_pos[0], self._computed_pos[1])
		return self._computed_pos[axis]
	
	#@resettable_cached_method
	def get_computed_rect(self) -> tuple[int | None, int | None, int | None, int | None]:
		"""Get the computed rectangle (x, y, width, height) from the last layout passes."""
		return (self._computed_pos[0], self._computed_pos[1], self._computed_size[0], self._computed_size[1])
	
	def layout(self, x: int, y: int, width: int, height: int, data=None) -> tuple[int, int]:
		"""Perform complete layout: size distribution and positioning.
		
		This is a convenience method that performs both size distribution and
		positioning in the correct order.
		
		Args:
			x: The x-coordinate for positioning
			y: The y-coordinate for positioning
			width: The available width for size distribution
			height: The available height for size distribution
			data: Optional data to pass through to child widgets
			
		Returns:
			tuple[int, int]: The actual (width, height) used by the layout
		"""
		# First distribute sizes
		actual_width = self.distribute_width(width)
		actual_height = self.distribute_height(height)
		
		# Then position at the specified coordinates
		self.position_at(x, y, data)
		
		return (actual_width, actual_height)
	
	#@resettable_cached_method
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
	def _argument_expand_2(value, default_second=None, *, mapper=None):
		"""Expand a single value to a tuple of two values.
		
		Args:
			value: The value to expand (can be single value, tuple, or list)
			default_second: If provided, use this as the second value when expanding
						   single values instead of repeating the first value
		
		Returns:
			tuple: Two-element tuple
		"""
		if isinstance(value, Dimension) or not isinstance(value, (list, tuple)):
			# Single value - use default_second if provided, otherwise repeat the value
			second_value = value if default_second is None else default_second
			value = (value, second_value)
		elif len(value) == 1:
			# Single element in sequence - same logic as above
			second_value = value[0] if default_second is None else default_second
			value = (value[0], second_value)
		elif len(value) != 2:
			assert False, "Invalid value format"
		return tuple(value) if mapper is None else tuple(map(mapper, value))

	@staticmethod
	def _argument_expand_4(value, *, mapper=None):
		"""Expand a single value to a tuple of four values."""
		if isinstance(value, Dimension) or not isinstance(value, (list, tuple)):
			value = (value,) * 4
		elif len(value) == 1:
			value = (value[0],) * 4
		elif len(value) == 2:
			value = (value[0], value[1]) * 2
		elif len(value) != 4:
			assert False, "Invalid value format"
		return tuple(value) if mapper is None else tuple(map(mapper, value))

# --- single-child layouts

class LayoutSingle(Layout):
	def __init__(self, child=None):
		super().__init__()
		self.child = child

	#@resettable_cached_method
	def query_width_request(self):
		if self.child:
			return self.child.query_width_request()
		return super().query_width_request()

	#@resettable_cached_method
	def query_height_request(self):
		if self.child:
			return self.child.query_height_request()
		return super().query_height_request()

	def distribute_width(self, available_width: int) -> int:
		if self.child:
			width = self.child.distribute_width(available_width)
			self._computed_size[0] = width
			return width
		return super().distribute_width(available_width)

	def distribute_height(self, available_height: int) -> int:
		if self.child:
			height = self.child.distribute_height(available_height)
			self._computed_size[1] = height
			return height
		return super().distribute_height(available_height)

	def position_at(self, x: int, y: int, data=None) -> None:
		super().position_at(x, y, data)
		if self.child:
			self.child.position_at(x, y, data)

# --- LayoutSized widget ---

class LayoutSized(LayoutSingle):
	"""
	LayoutSized wraps a single child and applies unified sizing and alignment.
	It uses a sizing property (Fixed, Expand, Grow) to claim space from its parent,
	and then positions/sizes its child within that space, prioritizing the child's explicit size.
	The sizing engine can be reused by LayoutContainer by passing aggregate requests and None for explicit size.
	"""
	def __init__(self, *, sizing=None, align=Layout.CENTER, child=None):
		super().__init__(child)
		self.sizing = self._argument_expand_2(sizing, mapper=Dimension.orNone)
		self.align = self._argument_expand_2(align)

	#@resettable_cached_method
	def query_width_request(self):
		# Use child's query and explicit width if available
		child_request = self.child.query_width_request() if self.child else 0
		explicit = getattr(self.child, 'width', None)
		return self._compute_axis_request(child_request, explicit, self.sizing[0])

	#@resettable_cached_method
	def query_height_request(self):
		child_request = self.child.query_height_request() if self.child else 0
		explicit = getattr(self.child, 'height', None)
		return self._compute_axis_request(child_request, explicit, self.sizing[1])

	@staticmethod
	def _compute_axis_request(requested, explicit, sizing):
		# If explicit dimension, use its minimum
		if explicit is not None:
			return explicit.minim
		# If sizing property, use its minimum
		if sizing is not None:
			return sizing.minim
		# Otherwise, use requested
		return requested

	def distribute_width(self, available_width: int) -> int:
		if self.child:
			# Compute the wrapper's claimed width
			child_request = self.child.query_width_request() if self.child else 0
			explicit = getattr(self.child, 'width', None)
			claimed = self._compute_axis_size(child_request, explicit, available_width, self.sizing[0])
			self.child.distribute_width(claimed)
		self._computed_size[0] = available_width
		return available_width

	def distribute_height(self, available_height: int) -> int:
		if self.child:
			# Compute the wrapper's claimed height
			child_request = self.child.query_height_request() if self.child else 0
			explicit = getattr(self.child, 'height', None)
			claimed = self._compute_axis_size(child_request, explicit, available_height, self.sizing[1])
			self.child.distribute_height(claimed)
		self._computed_size[1] = available_height
		return available_height

	@staticmethod
	def _compute_axis_size(requested, explicit, available, sizing):
		# If explicit dimension, branch by type
		if explicit is not None:
			size = max(explicit.minim, requested)
			if explicit.maxim is not None:
				size = min(size, explicit.maxim)
			return min(size, available)

		# If sizing property, branch by type
		if sizing is not None:
			if isinstance(sizing, Fixed):
				size = sizing.minim
			elif isinstance(sizing, Expand):
				# Proportional minimum
				if isinstance(sizing.minim, (int, float)) and 0 <= sizing.minim <= 1:
					min_size = math.ceil(sizing.minim * available)
				else:
					raise ValueError(f"Sizing minimum ({sizing.minim}) must be between 0 and 1.")
				size = max(min_size, requested)
				# Proportional maximum
				if sizing.maxim is not None:
					if isinstance(sizing.maxim, (int, float)) and 0 < sizing.maxim <= 1:
						max_size = math.ceil(sizing.maxim * available)
					else:
						raise ValueError(f"Sizing maximum ({sizing.maxim}) must be between 0 and 1.")
					size = min(size, max_size)
			elif isinstance(sizing, Grow):
				# Use a proportion of the remaining available space
				remaining = max(available - requested, 0)
				# Proportional minimum
				if isinstance(sizing.minim, (int, float)) and 0 <= sizing.minim <= 1:
					min_size = math.ceil(sizing.minim * remaining)
				else:
					raise ValueError(f"Sizing minimum ({sizing.minim}) must be between 0 and 1.")
				size = requested + min_size
				# Proportional maximum
				if sizing.maxim is not None:
					if isinstance(sizing.maxim, (int, float)) and 0 < sizing.maxim <= 1:
						max_size = requested + math.ceil(sizing.maxim * remaining)
					else:
						raise ValueError(f"Sizing maximum ({sizing.maxim}) must be between 0 and 1.")
					size = min(size, max_size)
			else:
				size = max(sizing.minim, requested)
			return min(size, available)

		# Otherwise, clamp requested to available
		return min(requested, available)

	def position_at(self, x: int, y: int, data=None) -> None:
		super().position_at(x, y, data)
		# Align child within claimed space
		if self.child:
			child_size = self.child.get_computed_size()
			wrapper_size = self.get_computed_size()
			offset_x = x + int((wrapper_size[0] - (child_size[0] or 0)) * self.align[0])
			offset_y = y + int((wrapper_size[1] - (child_size[1] or 0)) * self.align[1])
			self.child.position_at(offset_x, offset_y, data)

class LayoutWindow(LayoutSingle):
	pass

class LayoutPadding(LayoutSingle):
	def __init__(self, padding=10, child=None):
		super().__init__(child)
		self.padding = self._argument_expand_4(padding)

	#@resettable_cached_method
	def query_width_request(self):
		# Calculate horizontal padding
		width_padding = self.padding[0] + self.padding[2]
		# Query the width requirements of the child layout
		if self.child:
			return self.child.query_width_request() + width_padding
		# If no child, return just the horizontal padding
		return width_padding
	
	#@resettable_cached_method
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
	
	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position this padding layout and its child with padding offset."""
		super().position_at(x, y, data)
		# Position child with padding offset
		if self.child:
			child_x = x + self.padding[0]  # left padding
			child_y = y + self.padding[1]  # top padding
			self.child.position_at(child_x, child_y, data)

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

	# align can be single value (for horizontal axis) or 2-tuple (horizontal, vertical)
	# gap can be int/float for spacing, or a callable that returns Layout widgets

	def __init__(self, *, axis=LayoutGroup.VERTICAL, sizing=None, align=Layout.START, gap=0, children=()):
		super().__init__(*children)
		self.axis = axis
		self.sizing = self._argument_expand_2(sizing, mapper=Dimension.orNone)
		self.gap = gap  # Space between children
		self.align = self._argument_expand_2(align, Layout.START)
		# Cache for generated gap widgets to avoid recreating them during layout passes
		self._gap_widget_cache = []				# Cache for gap widgets to be inserted
		self._children_with_gaps_cache = None	# Cache for children with gaps inserted
		self._children_size = [None, None]		# Cache for children sizes (width, height)

	@classmethod
	def horizontal(cls, *, sizing=None, align=Layout.START, gap=0, children=()):
		return cls(axis=LayoutGroup.HORIZONTAL, sizing=sizing, align=align, gap=gap, children=children)
	
	@classmethod
	def vertical(cls, *, sizing=None, align=Layout.START, gap=0, children=()):
		return cls(axis=LayoutGroup.VERTICAL, sizing=sizing, align=align, gap=gap, children=children)

	#@resettable_cached_method
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
		# resettable_cached_property._reset_cache(self)

	# #@resettable_cached_method
	# def query_width_request(self):
	# 	return self._query_axis_request(LayoutGroup.HORIZONTAL, operator.methodcaller('query_width_request'))
	
	# #@resettable_cached_method
	# def query_height_request(self):
	# 	return self._query_axis_request(LayoutGroup.VERTICAL, operator.methodcaller('query_height_request'))
	
	#@resettable_cached_method
	def query_axis_request(self, axis: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		query_widths = map(operator.methodcaller('query_axis_request', axis), children_with_gaps)
		
		if self.axis == axis:
			# In-Axis: sum widths + simple gaps
			gap_info = self._get_gap_info()
			child_request =  sum(query_widths) + gap_info['total_simple_gap']
		else:
			# Cross-Axis: max width (gaps don't affect width)
			child_request =  max(query_widths)
		
		return LayoutSized._compute_axis_request(child_request, None, self.sizing[axis])
	
	def distribute_width(self, available_width: int) -> int:
		return self._distribute_axis(available_width, 0)
	
	def distribute_height(self, available_height: int) -> int:
		return self._distribute_axis(available_height, 1)
	
	def _distribute_axis(self, available_space: int, axis: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			self._computed_size[axis] = 0
			return 0
		
		distribute_func = operator.attrgetter(
			('distribute_width', 'distribute_height')[axis]
		)

		claimed = LayoutSized._compute_axis_size(
			self.query_axis_request(axis),
			None, available_space, self.sizing[axis]
		)
		
		if self.axis == 1-axis:
			# Cross-Axis container: all children get the same available size
			# For Expand/Grow widgets in cross-axis, we should use the available space
			axis_sizing = self.sizing[axis]; effective_space = available_space
			if isinstance(axis_sizing, Fixed):
				effective_space = axis_sizing.minim
			elif isinstance(axis_sizing, (Expand, Grow)):
				effective_space = max(available_space, axis_sizing.minim)
				if axis_sizing.maxim is not None:
					effective_space = min(effective_space, axis_sizing.maxim)

			# Take max since we need to fit all children (round up for GUI layout)
			max_computed_sizes = math.ceil(max(distribute_func(child)(effective_space)
									  for child in children_with_gaps))
			self._computed_size[axis] = max_computed_sizes
			self._children_size[axis] = max_computed_sizes
			# Return larger of effective_space vs max child
			return max(math.ceil(effective_space), max_computed_sizes)

		# Horizontal container: distribute width among children, accounting for simple gaps
		gap_info = self._get_gap_info()
		
		# For simple gaps, reduce available space by total gap space
		child_available_space = max(0, claimed - gap_info['total_simple_gap'])
		
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
		
		def get_height_info(child):
			# Height distribution doesn't typically involve shrinking
			min_request = child.query_height_request()
			return (min_request, getattr(child, 'height', None), min_request, False)
		
		# Use generalized distribution algorithm
		all_widgets = self._distribute_space_general(children_with_gaps, child_available_space,
				get_width_info if axis == 0 else get_height_info)
		
		# Apply the allocated widths
		for info in all_widgets:
			distribute_func(info['child'])(info['allocated'])
		
		# Calculate actual width needed: sum of allocated child widths + gaps
		total_child_space = sum(info['allocated'] for info in all_widgets)
		actual_space_needed = total_child_space + gap_info['total_simple_gap']
		self._children_size[axis] = actual_space_needed
		
		# Container claims the maximum of available width and actual width needed
		container_space = max(math.ceil(claimed), actual_space_needed)
		self._computed_size[axis] = container_space
		return container_space
	
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
				'min_space': math.ceil(min_request),  # Round up minimum
				'allocated': math.ceil(preferred_size),  # Round up initial allocation
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
				new_size = math.ceil(old_size + allocation)  # Round up new allocations
				
				if max_size is not None and new_size >= max_size:
					new_size = math.ceil(max_size)  # Round up max size
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
				target_size = math.ceil(old_size - target_shrink_per_widget)  # Round up target
				
				# Use try_shrink_width for intelligent shrinking
				if hasattr(info['child'], 'try_shrink_width'):
					actual_size = math.ceil(info['child'].try_shrink_width(target_size))  # Round up result
				else:
					# Fallback to simple clamping for widgets without intelligent shrinking
					actual_size = math.ceil(max(target_size, info['min_space']))  # Round up result
				
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
	
	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position this container and all its children according to the layout algorithm."""
		super().position_at(x, y, data)
		
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return
		
		# Position children using unified axis-based method
		self._position_children_unified(x, y, children_with_gaps, self.axis, data)
	
	def _position_children_unified(self, container_x: int, container_y: int, children, axis: int, data=None) -> None:
		"""Unified positioning method that works for both horizontal and vertical containers.
		
		Args:
			container_x: X coordinate of container
			container_y: Y coordinate of container  
			children: List of child widgets to position (may include gap widgets or just actual children)
			axis: 0 for horizontal (primary axis = width), 1 for vertical (primary axis = height)
			data: Optional data to pass through to child widgets
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
				child.position_at(pos[0], pos[1], data)
				
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
				child.position_at(pos[0], pos[1], data)
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
	
	#@resettable_cached_method
	def query_width_request(self):
		return self.width.minim
	
	#@resettable_cached_method
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
	def __init__(self, text: str, font: FontObject | None = None):
		super().__init__()
		self.text = text
		self.font = font
	
	@staticmethod
	@lru_cache
	def get_extents(text, font=None):
		"""Estimate the extents (width, height) of text.
		
		This is a convenience method that uses the plugin system
		to calculate text dimensions.
		
		Args:
			text: The text string to measure
			font: Font information (passed to measurement functions)
			
		Returns:
			tuple[int, int]: Estimated (width, height) in pixels
		"""
		if not text:
			return (0, 0)
		
		assert _layout_context is not None, "Layout context not initialized"
		metrics = _layout_context.get_font_metrics(font)
		font_height = metrics['height']
		
		# For multiline text, calculate based on lines
		lines = text.split('\n')
		if len(lines) > 1:
			max_line_width = max(_layout_context.measure_text_width(line, font) for line in lines)
			width = max_line_width
			height = len(lines) * font_height
		else:
			width = _layout_context.measure_text_width(text, font)
			height = font_height
		
		return (width, height)
	
	#@resettable_cached_method
	def query_width_request(self):
		# Return minimum width (reasonable minimum for text rendering)
		if not self.text:
			return 0
		
		# Minimum width should be based on actual content, but allow for some shrinking
		# Use a small representative text sample to determine reasonable minimum
		sample_chars = "Wj"  # Wide and narrow character combination
		assert _layout_context is not None, "Layout context not initialized"
		min_char_width = _layout_context.measure_text_width(sample_chars, self.font) // 2
		return max(min_char_width * 2, 16)  # At least space for a couple characters
	
	#@resettable_cached_method
	def query_height_request(self):
		"""Return the height needed to display this text.
		
		For multiline text, this will be multiplied by the number of lines.
		"""
		if not self.text:
			return 0
			
		assert _layout_context is not None, "Layout context not initialized"
		metrics = _layout_context.get_font_metrics(self.font)
		line_height = metrics['height']
		
		# Height scales with number of lines
		if '\n' in self.text:
			return line_height * len(self.text.split('\n'))
		return line_height
	
	#@resettable_cached_method
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
		assert _layout_context is not None, "Layout context not initialized"
		longest_word_width = max(_layout_context.measure_text_width(word, self.font) for word in words)
		
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
			
			test_line_width = _layout_context.measure_text_width(test_line_text, self.font)
			
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
			actual_width = max(_layout_context.measure_text_width(line, self.font) for line in lines)
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
		self.width = Dimension.orNone(width)
		self.height = Dimension.orNone(height)

		# Set text using the method to create the private LayoutText
		self.set_text(text)
	
	def set_text(self, text):
		"""Update the button text and refresh the internal layout calculations."""
		# Use the global layout context to create the appropriate text widget
		if _layout_context is not None:
			self._text_layout = _layout_context.create_text(text)
		else:
			self._text_layout = LayoutText(text)
		# resettable_cached_property._reset_cache(self)
	
	def get_text(self):
		"""Get the current button text from the internal layout."""
		return self._text_layout.text
	
	#@resettable_cached_method
	def query_width_request(self):
		# Return explicit width if provided, otherwise calculate from text
		if self.width is not None:
			return self.width.minim
		
		# Use private LayoutText for text measurement
		text_width = self._text_layout.query_width_request()
		return max(text_width + 20, 75)  # Min 75px width, add padding
	
	#@resettable_cached_method
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
	
	#@resettable_cached_method
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
		self.width = Dimension.orNone(width)
		self.height = Dimension.orNone(height)

		# Set text using the method to create the private LayoutText
		self.set_text(text)
	
	def set_text(self, text):
		"""Update the edit control text and refresh the internal layout calculations."""
		# Use the global layout context to create the appropriate text widget
		if _layout_context is not None:
			self._text_layout = _layout_context.create_text(text)
		else:
			self._text_layout = LayoutText(text)
	
	def get_text(self):
		"""Get the current edit control text from the internal layout."""
		return self._text_layout.text
	
	#@resettable_cached_method
	def query_width_request(self):
		# Return explicit width if provided, otherwise calculate from text
		if self.width is not None:
			return self.width.minim
		
		# Use private LayoutText for text measurement
		text_width = self._text_layout.query_width_request()
		return text_width + 20  # Add padding for edit control borders and internal spacing
	
	#@resettable_cached_method
	def query_height_request(self):
		# Return explicit height if provided, otherwise calculate from text
		if self.height is not None:
			return self.height.minim
		
		# Use private LayoutText for text measurement
		text_height = self._text_layout.query_height_request()
		return text_height + 10  # Add padding for edit control borders and internal spacing
	
	#@resettable_cached_method
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
	def __init__(self, url, title=None, font=None):
		super().__init__(title or url, font)
		self.url = url

class LayoutSeparatorLine(LayoutWidget):
	def __init__(self, *, axis=LayoutGroup.HORIZONTAL, thickness=2, width=None, height=None):
		super().__init__()
		self.axis = axis
		self.thickness = thickness
		self._width = None
		self._height = None

		# If explicit dimensions provided, use them
		if width is not None:
			self._width = Dimension(width)
		elif axis == LayoutGroup.HORIZONTAL:
			# Default horizontal lines to grow width
			self._width = Grow(minimum=0)
		else:  # Vertical
			# Default vertical lines to fixed width at thickness
			self._width = Fixed(thickness)
		
		if height is not None:
			self._height = Dimension(height)
		elif axis == LayoutGroup.VERTICAL:
			# Default vertical lines to grow height
			self._height = Grow(minimum=0)
		else:  # Horizontal
			# Default horizontal lines to fixed height at thickness
			self._height = Fixed(thickness)

	@property
	def width(self):
		return self._width
	
	@width.setter 
	def width(self, value):
		"""Set the width dimension. For vertical lines, this controls their thickness."""
		self._width = value = Dimension.orNone(value)
		if value is not None and self.axis == LayoutGroup.VERTICAL:
			# When setting width on vertical line, also update thickness
			self.thickness = value.minim

	@property
	def height(self):
		return self._height
	
	@height.setter
	def height(self, value):
		"""Set the height dimension. For horizontal lines, this controls their thickness."""
		self._height = value = Dimension.orNone(value)
		if value is not None and self.axis == LayoutGroup.HORIZONTAL:
			# When setting height on horizontal line, also update thickness
			self.thickness = value.minim

	@classmethod
	def horizontal(cls, thickness=1, width=None, height=None):
		return cls(axis=LayoutGroup.HORIZONTAL, thickness=thickness, width=width, height=height)

	@classmethod
	def vertical(cls, thickness=1, width=None, height=None):
		return cls(axis=LayoutGroup.VERTICAL, thickness=thickness, width=width, height=height)
	
	#@resettable_cached_method
	def query_width_request(self):
		# If we have an explicit width, use its minimum
		if self._width is not None:
			return self._width.minim
		# Default: 0px for horizontal (will expand), thickness for vertical
		return self.thickness if self.axis == LayoutGroup.VERTICAL else 0
	
	#@resettable_cached_method
	def query_height_request(self):
		# If we have an explicit height and it's Fixed, use its minimum
		if self._height is not None:
			if isinstance(self._height, Fixed):
				return self._height.minim
			# For Expand/Grow dimensions, use thickness as minimum if specified
			elif isinstance(self._height, (Expand, Grow)) and self._height.minim > 0:
				return self._height.minim
		# For vertical lines, default to thickness to ensure a non-zero request
		# This helps cross-axis container distribution work better
		return self.thickness
	
	def distribute_width(self, available_width: int) -> int:
		# If we have an explicit width dimension, use it
		if self._width is not None:
			# Handle the dimension normally like other widgets
			if isinstance(self._width, Fixed):
				width = self._width.minim
			elif isinstance(self._width, (Expand, Grow)):
				width = max(available_width, self._width.minim)
				if self._width.maxim is not None:
					width = min(width, self._width.maxim)
			else:
				width = self._width.minim
		else:
			# Default behavior:
			# - Horizontal lines use all available width
			# - Vertical lines use thickness
			width = available_width if self.axis == LayoutGroup.HORIZONTAL else self.thickness
		
		self._computed_size[0] = width
		return width
	
	def distribute_height(self, available_height: int) -> int:
		# If we have an explicit height dimension, use it
		if self._height is not None:
			# Handle the dimension normally like other widgets
			if isinstance(self._height, Fixed):
				height = self._height.minim
			elif isinstance(self._height, (Expand, Grow)):
				height = max(available_height, self._height.minim)
				if self._height.maxim is not None:
					height = min(height, self._height.maxim)
			else:
				height = self._height.minim
		else:
			# Default behavior:
			# - Horizontal lines use thickness
			# - Vertical lines use all available height
			height = self.thickness if self.axis == LayoutGroup.HORIZONTAL else available_height
		
		self._computed_size[1] = height
		return height

# -------
# Plugin System
# -------

# Type for font objects - platform specific (HFONT, QFont, etc)
FontObject = Any

def set_layout_context(context: 'LayoutPluginContext'):
	"""Set the global layout context."""
	global _layout_context
	_layout_context = context

def layout_context(context_class):
	"""Decorator to set a layout context class as the global context."""
	set_layout_context(context_class())
	return context_class

FontType = TypeVar('FontType')  # Allow any type for fonts

@layout_context
class LayoutPluginContext:
	"""Simple context for widget creation and text measurement.
	
	The font parameter in these methods can be any type appropriate for the GUI framework:
	- Win32: HFONT handle
	- Qt: QFont object
	- GTK: Pango font description
	- tkinter: Font tuple like ("Arial", 12, "bold")
	- etc.
	
	The default implementation assumes strings but derived classes can use any font type.
	"""
	
	def create_text(self, text: str, font: FontType | None = None) -> 'LayoutText':
		"""Create a text widget. Override in subclasses for platform-specific widgets."""
		return LayoutText(text, font)
	
	@lru_cache
	def measure_text_width(self, text: str, font: FontType | None = None) -> int:
		"""Measure text width. Override in subclasses for platform-specific measurement."""
		if not text:
			return 0
		
		# Character classification for better estimates
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
				# Non-ASCII characters
				if ord(char) >= 0x4E00 and ord(char) <= 0x9FFF:  # CJK range
					width += 16  # CJK characters are typically wider
				elif ord(char) >= 0x0100:  # Extended Latin and beyond
					width += 10  # Assume similar to capitals
				else:
					width += 8  # Default assumption
			else:
				width += 8  # Punctuation and other characters
		
		return width
	
	@lru_cache
	def get_font_metrics(self, font: str | None = None) -> dict[str, int]:
		"""Get font metrics. Override in subclasses for platform-specific metrics."""
		font_height = 16  # Default UI font height
		return {
			'height': font_height,
		}

# -------
# Demo and Testing
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
							LayoutLink(github_link, "Visit GitHub Repository", font="Arial")
						)
					),
				),
				LayoutSeparatorLine(),
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

def build_test_layout_sized():
	return LayoutSized(
		sizing=Fixed(50),
		# align=Layout.CENTER,
		# child=LayoutSeparatorLine.horizontal(),
	)

# -------

def dump_widget_sizes(widget, indent="  "):
	rect = widget.get_computed_rect()
	x, y, w, h = rect
	print(f"{indent}{widget.__class__.__name__}: x={x}, y={y}, width={w}, height={h}")

	if hasattr(widget, 'children'):
		for child in widget.children:
			dump_widget_sizes(child, indent + "  ")
	elif hasattr(widget, 'child') and widget.child:
		dump_widget_sizes(widget.child, indent + "  ")


def build_space_flow_test():
	"""Build a minimal test showing how space flows from layout to separators."""
	# Vertical container with both horizontal and vertical separator lines:
	# Horizontal lines:
	# - First one expands to container width (default)
	# - Second has fixed width of 150px
	# Vertical lines:
	# - First one expands to container height (default)
	# - Second has fixed height of 40px
	
	# Main vertical container
	return LayoutContainer.vertical(
		sizing=(Grow(minimum=0), Grow(minimum=0)),  # Tell container to grow in both dimensions
		children=(
			# Horizontal separators
			LayoutSeparatorLine(thickness=2),  # Default grow width behavior
			LayoutSeparatorLine(thickness=2, width=Fixed(150)),  # Fixed 150px width
			# Space between sections
			LayoutSpacer(height=10),
			# Vertical lines in a horizontal container
			LayoutContainer.horizontal(
				sizing=(None, Expand(minimum=0.33)),  # Use 33% of available height
				children=(
					LayoutSeparatorLine.vertical(thickness=2),  # Default grow height behavior
					LayoutSpacer(width=10),  # Space between lines
					LayoutSeparatorLine.vertical(thickness=2, height=Fixed(40))  # Fixed 40px height
				)
			),
			# Space between sections
			LayoutSpacer(height=10),
			# Test explicit height on horizontal lines
			LayoutSeparatorLine(thickness=1, height=Fixed(5)),  # Explicit height overrides thickness
			LayoutSeparatorLine(thickness=2, height=Expand(minimum=10, maximum=20))  # Expand with limits
		)
	)

def build_horizontal_line_demo():
	"""Build a layout demonstrating horizontal lines with different positioning strategies."""
	return LayoutContainer.vertical(
		gap=20,  # Space between demonstrations
		sizing=Grow(minimum=0),  # Allow container to grow
		children=(
			# Demo 1: Full-width horizontal line (edge to edge)
			LayoutContainer.vertical(
				gap=5,
				sizing=Grow(minimum=0),
				children=(
					LayoutText("Demo 1: Full-width horizontal line"),
					LayoutSeparatorLine(thickness=2),  # Fixed 2px height to simulate etched effect
				)
			),
			
			# Demo 2: Three horizontal lines with growing gaps
			LayoutContainer.vertical(
				gap=5,
				sizing=Grow(minimum=0),
				children=(
					LayoutText("Demo 2: Three lines with growing gaps"),
					LayoutContainer.horizontal(
						sizing=Grow(minimum=1),
						gap=20,
						children=(
							LayoutSeparatorLine(thickness=2),
							LayoutSeparatorLine(thickness=2),
							LayoutSeparatorLine(thickness=2),
						)
					),
				)
			),
			
			# Demo 3: Horizontal line with padding (inset from edges)
			LayoutContainer.vertical(
				gap=5,
				sizing=Grow(minimum=0),
				children=(
					LayoutText("Demo 3: Horizontal line with padding"),
					LayoutPadding(20,  # 20px padding on all sides
						LayoutSeparatorLine(thickness=2)
					),
				)
			),
		)
	)

def demo_layout_calculation(layout_content):
	"""Demonstrate the layout system calculations for horizontal lines.
	
	This function shows how the layout system calculates sizes and positions
	without any platform-specific dependencies.
	"""
	print("Layout Engine Demo - Horizontal Lines")
	print("=" * 45)
	print("This demo shows three different horizontal line layout strategies:")
	print("1. Full-width line (stretches edge to edge)")
	print("2. Three lines with growing gaps between them")
	print("3. Horizontal line with padding (inset from edges)")
	print()
	
	# Show the layout structure
	print(f"Layout Type: {type(layout_content).__name__}")
	print(f"Required Size: {layout_content.query_width_request()}x{layout_content.query_height_request()}")
	print()
	
	# Perform layout at different sizes to show responsiveness
	test_sizes = [(400, 300), (600, 400), (300, 250)]
	
	for width, height in test_sizes:
		print(f"Layout at {width}x{height}:")
		actual_size = layout_content.layout(0, 0, width, height)
		print(f"  Actual Size: {actual_size[0]}x{actual_size[1]}")
		print(f"  Layout Rect: {layout_content.get_computed_rect()}")
		
		# Show positions of horizontal lines
		line_count = 0
		def dump_widget_sizes(widget, filter=lambda e: True, indent="  "):
			nonlocal line_count
			rect = widget.get_computed_rect()
			x, y, w, h = rect
			if filter(widget):
				line_count += 1
				print(f"{indent}{widget.__class__.__name__} {line_count}: x={x}, y={y}, width={w}, height={h}")
				indent += "  "
			if hasattr(widget, 'children'):
				for child in widget.children:
					dump_widget_sizes(child, filter, indent)
			elif hasattr(widget, 'child') and widget.child:
				dump_widget_sizes(widget.child, filter, indent)
		line_count = 0
		dump_widget_sizes(layout_content, lambda e: isinstance(e, LayoutSeparatorLine))
		print()
	
	print("Demo complete. The layout system calculated positions for all widgets.")

def run_demo():
	layout_content = build_space_flow_test()
	
	print("Space Flow Test")
	print("==============")
	
	# Try different sizes to see how space flows through
	test_sizes = [(100, 100), (200, 200), (300, 300)]  # Make height match width to test vertical growth
	for width, height in test_sizes:
		print(f"\nTesting layout({width}, {height}):")
		
		# Step 1: layout() establishes total available space
		actual_size = layout_content.layout(0, 0, width, height)
		print(f"1. Layout call complete")
		print(f"   Container rect: {layout_content.get_computed_rect()}")
		
		# Horizontal separators
		h_expand = layout_content.children[0]
		h_fixed = layout_content.children[1]
		print(f"2. Horizontal separator (Expand) rect: {h_expand.get_computed_rect()}")
		print(f"3. Horizontal separator (Fixed) rect: {h_fixed.get_computed_rect()}")
		
		# Get horizontal container with vertical lines
		h_container = layout_content.children[3]  # Skip spacer
		v_expand = h_container.children[0]
		v_fixed = h_container.children[2]  # Skip spacer
		print(f"4. Vertical separator (Expand) rect: {v_expand.get_computed_rect()}")
		print(f"5. Vertical separator (Fixed) rect: {v_fixed.get_computed_rect()}")
		
		# Get last two horizontal lines with explicit heights
		h_explicit = layout_content.children[5]  # Skip spacer
		h_expand = layout_content.children[6]
		print(f"6. Horizontal separator (Fixed 5px height) rect: {h_explicit.get_computed_rect()}")
		print(f"7. Horizontal separator (Expand 10-20px height) rect: {h_expand.get_computed_rect()}")
	
	print("\nNote: Lines should behave as follows:")
	print("- Horizontal lines:")
	print("  * First one expands to container width (default)")
	print("  * Second stays at 150px width")
	print("  * Second-to-last has fixed 5px height (overriding 1px thickness)")
	print("  * Last one expands height between 10-20px")
	print("- Vertical lines:")
	print("  * First one expands to container height")
	print("  * Second stays at 40px height")

if __name__ == "__main__":
	run_demo()
