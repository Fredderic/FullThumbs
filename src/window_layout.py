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

+ Fit sizing widths
+ Grow and shrink widths
+ Wrap text
+ Fit sizing heights
+ Grow and shrink heights
- Positioning
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
	# Note: Boolean values work as alignment too - False=LEFT (0.0), True=RIGHT (1.0)
	LEFT = 0.0
	CENTER = 0.5
	RIGHT = 1.0
	
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
		return self.query_width_request()
	
	def distribute_height(self, available_height: int) -> int:
		# Default implementation returns the query height (no distribution)
		return self.query_height_request()
	
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
	def _argument_expand_2(value):
		"""Expand a single value to a tuple of two values."""
		if not isinstance(value, (list, tuple)):
			return (value, value)
		elif len(value) == 1:
			return (value[0], value[0])
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
			return self.child.distribute_width(available_width)
		return super().distribute_width(available_width)
	
	def distribute_height(self, available_height: int) -> int:
		# Pass through height distribution to child
		if self.child:
			return self.child.distribute_height(available_height)
		return super().distribute_height(available_height)

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
				return actual_child_width + width_padding
		
		# If no child or no space, return just the padding
		return width_padding
	
	def distribute_height(self, available_height: int) -> int:
		# Calculate vertical padding
		height_padding = self.padding[1] + self.padding[3]
		
		# Distribute to child with padding subtracted
		if self.child:
			child_height = available_height - height_padding
			if child_height > 0:
				actual_child_height = self.child.distribute_height(child_height)
				return actual_child_height + height_padding
		
		# If no child or no space, return just the padding
		return height_padding

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
		self.children = children

class LayoutContainer(LayoutGroup):
	# Unified 1D container layout that can arrange children vertically or horizontally
	def __init__(self, *, axis=LayoutGroup.VERTICAL, align=Layout.LEFT, gap=0, children=()):
		super().__init__(*children)
		self.axis = axis
		self.gap = gap  # Space between children
		# Convert align to 2-tuple (works with float, int, or bool values)
		self.align = self._argument_expand_2(align)
		# Cache for generated gap widgets to avoid recreating them during layout passes
		self._gap_widget_cache = []
		# Cache for the complete children_with_gaps list
		self._children_with_gaps_cache = None
	
	@classmethod
	def vertical(cls, *, align=Layout.LEFT, gap=0, children=()):
		# align can be bool (False=LEFT, True=RIGHT) or float (0.0=LEFT, 0.5=CENTER, 1.0=RIGHT)
		# gap can be int/float for spacing, or a callable that returns Layout widgets
		return cls(axis=LayoutGroup.VERTICAL, align=align, gap=gap, children=children)
	
	@classmethod
	def horizontal(cls, *, align=Layout.LEFT, gap=0, children=()):
		# align can be bool (False=LEFT, True=RIGHT) or float (0.0=LEFT, 0.5=CENTER, 1.0=RIGHT)
		# gap can be int/float for spacing, or a callable that returns Layout widgets
		return cls(axis=LayoutGroup.HORIZONTAL, align=align, gap=gap, children=children)
	
	def _get_children_with_gaps(self):
		"""Return children with gaps inserted between them."""
		# Return cached result if available
		if self._children_with_gaps_cache is not None:
			return self._children_with_gaps_cache
		
		if not self.children or len(self.children) <= 1:
			self._children_with_gaps_cache = self.children
			return self._children_with_gaps_cache
		
		# Determine the gap builder function
		if callable(self.gap):
			# gap is a builder function
			gap_builder = self.gap
		elif self.gap > 0:
			# gap is a number - create default spacer builder
			if self.axis == LayoutGroup.HORIZONTAL:
				gap_builder = lambda: LayoutSpacer(width=self.gap, height=0)
			else:  # LayoutGroup.VERTICAL
				gap_builder = lambda: LayoutSpacer(width=0, height=self.gap)
		else:
			gap_builder = None
		
		# If no gaps needed, return children as-is
		if not gap_builder:
			self._children_with_gaps_cache = self.children
			return self._children_with_gaps_cache
		
		# Ensure we have enough cached gap widgets
		self._gap_widget_cache.extend(gap_builder()
				for _ in range(len(self.children) - len(self._gap_widget_cache) - 1))

		# Build children with gaps using cached widgets
		children_it = iter(self.children)
		children_with_gaps = [next(children_it)]
		for gap_widget, child in zip(self._gap_widget_cache, children_it):
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
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal: sum widths
			return sum(child.query_width_request() for child in children_with_gaps)
		else:
			# Vertical: max width
			return max(child.query_width_request() for child in children_with_gaps)
	
	def query_height_request(self):
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal: max height
			return max(child.query_height_request() for child in children_with_gaps)
		else:
			# Vertical: sum heights
			return sum(child.query_height_request() for child in children_with_gaps)
	
	def distribute_width(self, available_width: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		if self.axis == LayoutGroup.VERTICAL:
			# Vertical container: all children get the same available width
			for child in children_with_gaps:
				child.distribute_width(available_width)
			return available_width
		
		# Horizontal container: distribute width among children
		def get_width_info(child):
			# Check if widget has preferred width (indicating it can shrink)
			preferred_width = child.get_preferred_width()
			if preferred_width is not None:
				can_shrink = True
			else:
				preferred_width = child.query_width_request()
				can_shrink = False
			
			return (child.query_width_request(), getattr(child, 'width', None), preferred_width, can_shrink)
		
		# Use generalized distribution algorithm
		all_widgets = self._distribute_space_general(children_with_gaps, available_width, get_width_info)
		
		# Apply the allocated widths and return total
		total_allocated = 0
		for info in all_widgets:
			allocated = info['child'].distribute_width(info['allocated'])
			total_allocated += allocated
		
		return total_allocated
	
	def distribute_height(self, available_height: int) -> int:
		children_with_gaps = self._get_children_with_gaps()
		if not children_with_gaps:
			return 0
		
		if self.axis == LayoutGroup.HORIZONTAL:
			# Horizontal container: all children get the same available height
			for child in children_with_gaps:
				child.distribute_height(available_height)
			return available_height
		
		# Vertical container: distribute height among children
		def get_height_info(child):
			# Height distribution doesn't typically involve shrinking
			return (child.query_height_request(), getattr(child, 'height', None), child.query_height_request(), False)
		
		# Use generalized distribution algorithm
		all_widgets = self._distribute_space_general(children_with_gaps, available_height, get_height_info)
		
		# Apply the allocated heights and return total
		total_allocated = 0
		for info in all_widgets:
			allocated = info['child'].distribute_height(info['allocated'])
			total_allocated += allocated
		
		return total_allocated
	
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

# --- leaf node layouts

class LayoutWidget(Layout):
	pass

class LayoutSpacer(LayoutWidget):
	def __init__(self, width=0, height=0):
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
		return self.width.minim
	
	def distribute_height(self, available_height: int) -> int:
		# Spacers with Fixed dimensions stay at their minimum
		# Spacers with Expand/Grow dimensions could grow, but for gaps we usually want them fixed
		# For now, keep gap spacers at their minimum size
		return self.height.minim

class LayoutText(LayoutWidget):
	def __init__(self, text, font=None, color=None):
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
		return max(available_width, min_width)

class LayoutButton(LayoutWidget):
	def __init__(self, text, id, width=None, height=None):
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
			return self.query_width_request()
		
		# Handle different dimension types
		if isinstance(self.width, Fixed):
			return self.width.minim
		elif isinstance(self.width, (Expand, Grow)):
			# For Expand/Grow, use the available width (clamped to minimum and maximum)
			min_width = self.width.minim
			max_width = self.width.maxim
			
			result = max(available_width, min_width)
			if max_width is not None:
				result = min(result, max_width)
			return result
		else:
			# Fallback for unknown dimension types
			return self.query_width_request()
	
	def distribute_height(self, available_height: int) -> int:
		# If no explicit height dimension, behave like Fixed (return query height)
		if self.height is None:
			return self.query_height_request()
		
		# Handle different dimension types
		if isinstance(self.height, Fixed):
			return self.height.minim
		elif isinstance(self.height, (Expand, Grow)):
			# For Expand/Grow, use the available height (clamped to minimum and maximum)
			min_height = self.height.minim
			max_height = self.height.maxim
			
			result = max(available_height, min_height)
			if max_height is not None:
				result = min(result, max_height)
			return result
		else:
			# Fallback for unknown dimension types
			return self.query_height_request()
	
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
						align=Layout.RIGHT,
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
	print("For comprehensive testing, run: python test_window_layout.py")
	print("For selective tests:")
	print("  Dimensions only: python -m unittest test_window_layout.TestDimensionClasses -v")
	print("  Widgets only:    python -m unittest test_window_layout.TestLayoutWidgets -v")
	print("  Containers only: python -m unittest test_window_layout.TestLayoutContainers -v")
	print("  Complex only:    python -m unittest test_window_layout.TestComplexLayouts -v")
