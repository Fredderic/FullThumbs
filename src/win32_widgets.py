"""
Win32-specific widget implementations that extend the pure layout engine.

This module provides Win32-specific versions of layout widgets that account for
native widget characteristics like borders, padding, and system metrics.
"""

from functools import lru_cache, cached_property
from window_layout import (
	Layout,
	LayoutPluginContext,
	LayoutGroup,
	LayoutWindow,
	LayoutWidget,
	LayoutSeparatorLine,
	LayoutContainer,
	LayoutPadding,
	layout_context,
	Grow,
	LayoutText,
	LayoutButton,
	LayoutEdit,
	LayoutSpacer,
)

# Cache reset helpers
# Don't use caching decorators since they're causing issues
import ctypes
from ctypes import wintypes
import win32gui, win32con, win32api

# Win32 API functions for getting system metrics
user32 = ctypes.windll.user32

# Set up function argument types
user32.CreateWindowExW.argtypes = [
	wintypes.DWORD,		# dwExStyle
	wintypes.LPCWSTR,	# lpClassName
	wintypes.LPCWSTR,	# lpWindowName
	wintypes.DWORD,		# dwStyle
	wintypes.INT,		# x
	wintypes.INT,		# y
	wintypes.INT,		# nWidth
	wintypes.INT,		# nHeight
	wintypes.HWND,		# hWndParent
	wintypes.HMENU,		# hMenu
	wintypes.HINSTANCE,	# hInstance
	wintypes.LPVOID		# lpParam
]
user32.CreateWindowExW.restype = wintypes.HWND

# -------

class Win32Widget(LayoutWidget):
	"""Base class for Win32 widgets that need to manage native window handles."""
	
	def __init__(self):
		self._hwnd = None
	
	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position the widget relative to the parent window's client area.
		The data parameter is expected to contain parent_hwnd for Win32 widgets."""
		super().position_at(x, y, data)
		
		# If we have a window handle, update its position
		if self._hwnd:
			try:
				width = self._computed_size[0]
				height = self._computed_size[1]
				win32gui.MoveWindow(self._hwnd, x, y, width, height, True)
			except Exception as e:
				print(f"Error positioning {type(self).__name__}: {e}")
		# Create native widget if this is our first positioning and we have a parent
		elif data is not None and isinstance(data, dict) and 'parent_hwnd' in data:
			parent_hwnd = data['parent_hwnd']
			self._create_native_widget(parent_hwnd, x, y)
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create the native Win32 widget. Override in derived classes."""
		raise NotImplementedError("Win32Widget subclasses must implement _create_native_widget")

# -------

@layout_context
class Win32LayoutContext(LayoutPluginContext):
	"""Win32-specific layout context that provides Win32 widgets and measurement."""
	
	def __init__(self):
		super().__init__()
		self._measurement_dc = None
		self._original_font = None
	
	def _get_measurement_dc(self):
		"""Get cached measurement DC, creating one if needed."""
		if self._measurement_dc is None:
			self._measurement_dc = win32gui.GetDC(0)  # Get desktop DC
			# Remember the original font so we can restore it at cleanup
			self._original_font = win32gui.GetCurrentObject(self._measurement_dc, 6)  # OBJ_FONT
		return self._measurement_dc
	
	def _cleanup_dc(self):
		"""Clean up the measurement DC."""
		if hasattr(self, '_measurement_dc') and self._measurement_dc is not None:
			try:
				# Restore original font before releasing DC
				if self._original_font is not None:
					win32gui.SelectObject(self._measurement_dc, self._original_font)
				win32gui.ReleaseDC(0, self._measurement_dc)
			except Exception as e:
				print(f"Error cleaning up measurement DC: {e}")
			self._measurement_dc = None
			self._original_font = None
	__del__ = _cleanup_dc
	
	# ---

	def create_text(self, text, font=None, color=None):
		"""Create a Win32Text widget."""
		return Win32Text(text, font, color)
	
	@lru_cache
	def measure_text_width(self, text, font=None):
		"""Win32-specific text width measurement using GDI."""
		dc = self._get_measurement_dc()
		
		# Select font if provided, otherwise use default GUI font
		if font:
			win32gui.SelectObject(dc, font)
		else:
			dialog_font = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT
			if dialog_font:
				win32gui.SelectObject(dc, dialog_font)
		
		# Measure text width
		text_size = win32gui.GetTextExtentPoint32(dc, text or ' ')
		return text_size[0]
	
	@lru_cache
	def get_font_metrics(self, font=None):
		"""Win32-specific font metrics using GDI."""
		dc = self._get_measurement_dc()
		
		# Select font if provided, otherwise use default GUI font
		if font:
			win32gui.SelectObject(dc, font)
		else:
			dialog_font = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT
			if dialog_font:
				win32gui.SelectObject(dc, dialog_font)
		
		# Get font height using a sample character
		text_size = win32gui.GetTextExtentPoint32(dc, 'Mg')  # Mixed case for ascent/descent
		height = text_size[1]
		# Approximate ascent/descent (Win32 doesn't easily provide this via win32gui)
		ascent = int(height * 0.8)  # Typical ratio
		descent = height - ascent
		
		return {
			'height': height,
			'ascent': ascent,
			'descent': descent
		}

# -------

class Win32Text(Win32Widget, LayoutText):
	"""Win32-specific text that will use actual Win32 text measurement when implemented."""
	
	def __init__(self, text: str, font: str | None = None, color: str | None = None):
		LayoutText.__init__(self, text, font)
		Win32Widget.__init__(self)
		self._hwnd: int | None = None
		self.color = color
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create a native Win32 static text control."""
		self._hwnd = win32gui.CreateWindow(
			"STATIC",  # Window class
			self.text,
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT,
			x, y, self._computed_size[0], self._computed_size[1],
			parent_hwnd, 0, win32api.GetModuleHandle(None), None
		)
		return self._hwnd

class Win32Button(Win32Widget, LayoutButton):
	"""Win32-specific button that accounts for native button characteristics."""
	
	def __init__(self, text, id, width=None, height=None):
		LayoutButton.__init__(self, text, id, width, height)
		Win32Widget.__init__(self)
		# Cache Win32-specific metrics
		self._border_width = user32.GetSystemMetrics(32)  # SM_CXEDGE
		self._border_height = user32.GetSystemMetrics(33) # SM_CYEDGE
		self._internal_padding = (6, 4, 6, 4)  # left, top, right, bottom - typical Win32 button padding
		# Use Win32Text for internal text measurement
		self._text_layout = Win32Text(text)
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create a native Win32 button control."""
		self._hwnd = win32gui.CreateWindow(
			"BUTTON",  # Window class
			self.get_text(),
			win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
			x, y, self._computed_size[0], self._computed_size[1],
			parent_hwnd, self.id, win32api.GetModuleHandle(None), None
		)
		return self._hwnd
	
	def set_text(self, text):
		"""Update the button text using Win32Text."""
		self._text_layout = Win32Text(text)
	
	def query_width_request(self):
		# Get base width from parent, then add Win32-specific padding
		if self.width is not None:
			return self.width.minim
		
		# Calculate Win32-specific width
		text_width = self._text_layout.query_width_request()
		win32_padding = self._internal_padding[0] + self._internal_padding[2] + (self._border_width * 2)
		return max(text_width + win32_padding, 75)
	
	def query_height_request(self):
		# Get base height from parent, then add Win32-specific padding
		if self.height is not None:
			return self.height.minim
		
		# Calculate Win32-specific height
		text_height = self._text_layout.query_height_request()
		win32_padding = self._internal_padding[1] + self._internal_padding[3] + (self._border_height * 2)
		return max(text_height + win32_padding, 25)

class Win32Edit(Win32Widget, LayoutEdit):
	"""Win32-specific edit control that accounts for native edit characteristics."""
	
	def __init__(self, text, multiline=False, read_only=False, width=None, height=None):
		LayoutEdit.__init__(self, text, multiline, read_only, width, height)
		Win32Widget.__init__(self)
		# Cache Win32-specific metrics
		self._border_width = user32.GetSystemMetrics(32)  # SM_CXEDGE
		self._border_height = user32.GetSystemMetrics(33) # SM_CYEDGE
		self._internal_padding = (3, 2, 3, 2) if not multiline else (3, 3, 3, 3)
		# Use Win32Text for internal text measurement
		self._text_layout = Win32Text(text)
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create a native Win32 edit control."""
		style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.ES_AUTOHSCROLL
		if self.multiline:
			style |= win32con.ES_MULTILINE | win32con.ES_AUTOVSCROLL
		if self.read_only:
			style |= win32con.ES_READONLY
		
		self._hwnd = win32gui.CreateWindow(
			"EDIT",  # Window class
			self.get_text(),  # Initial text
			style,
			x, y, self._computed_size[0], self._computed_size[1],
			parent_hwnd, 0, win32api.GetModuleHandle(None), None
		)
		return self._hwnd
	
	def set_text(self, text):
		"""Update the edit control text using Win32Text."""
		self._text_layout = Win32Text(text)
	
	def query_width_request(self):
		if self.width is not None:
			return self.width.minim
		# Calculate Win32-specific width
		text_width = self._text_layout.query_width_request()
		win32_padding = self._internal_padding[0] + self._internal_padding[2] + (self._border_width * 2)
		return text_width + win32_padding
	
	def query_height_request(self):
		if self.height is not None:
			return self.height.minim
		# Calculate Win32-specific height
		text_height = self._text_layout.query_height_request()
		win32_padding = self._internal_padding[1] + self._internal_padding[3] + (self._border_height * 2)
		return text_height + win32_padding

# Thin wrappers that do nothing special (yet)
class Win32Spacer(LayoutSpacer):
	pass

class Win32Container(LayoutContainer):
	pass

class Win32Padding(LayoutPadding):
	pass

class Win32SeparatorLine(Win32Widget, LayoutSeparatorLine):
	def __init__(self, *, axis=LayoutGroup.HORIZONTAL):
		LayoutSeparatorLine.__init__(self, axis=axis)
		Win32Widget.__init__(self)
	
	def query_width_request(self):
		# For vertical lines, we need 2 pixels for the etched effect
		# For horizontal lines, we want 0 to allow growth
		width = super().query_width_request()
		return width * 2 if width > 0 else width
	
	def query_height_request(self):
		# For horizontal lines, we need 2 pixels for the etched effect
		# For vertical lines, we want 0 to allow growth
		height = super().query_height_request()
		return height * 2 if height > 0 else height
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create a native Win32 separator line control."""
		# Ensure positive dimensions
		width = max(self._computed_size[0], 1)
		height = max(self._computed_size[1], 1)
		
		style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_NOTIFY
		if self.axis == LayoutGroup.HORIZONTAL:
			style |= win32con.SS_ETCHEDHORZ
		else:
			style |= win32con.SS_ETCHEDVERT
		
		self._hwnd = win32gui.CreateWindow(
			"STATIC",  # Window class
			"",        # No text
			style,
			max(x, 0), max(y, 0), width, height, 
			parent_hwnd, 0, win32api.GetModuleHandle(None), None
		)
		return self._hwnd

# Win32 window class definition
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSEX(ctypes.Structure):
	_fields_ = [
		("cbSize", wintypes.UINT),
		("style", wintypes.UINT),
		("lpfnWndProc", WNDPROC),
		("cbClsExtra", ctypes.c_int),
		("cbWndExtra", ctypes.c_int),
		("hInstance", wintypes.HANDLE),
		("hIcon", wintypes.HANDLE),
		("hCursor", wintypes.HANDLE),
		("hbrBackground", wintypes.HANDLE),
		("lpszMenuName", wintypes.LPCWSTR),
		("lpszClassName", wintypes.LPCWSTR),
		("hIconSm", wintypes.HANDLE),
	]

class Win32Window(LayoutWindow):
	"""Win32-specific window that creates an actual Win32 window with proper window procedure."""
	
	_window_class_registered = False
	_window_count = 0
	_window_class_name = "Win32LayoutWindow"  # Class name used for registration and creation
	_window_proc = None  # Store window procedure to prevent garbage collection

	def __init__(self, child=None, title="Win32 Window", width=None, height=None, client_origin=True):
		super().__init__(child)
		self.title = title
		
		# Store initial size (None is valid for either dimension)
		self.initial_size = (width, height)
		print(f"Win32Window created with initial size request: {self.initial_size}")
		
		# Whether specified dimensions are client area (True) or total window size (False)
		self.client_origin = client_origin
		
		self._hwnd = None
		
		# Register window class if not already done
		if not Win32Window._window_class_registered:
			self._register_window_class()
			Win32Window._window_class_registered = True
	
	@staticmethod
	def _register_window_class():
		"""Register the window class for Win32Window instances."""
		# Define window procedure
		@WNDPROC
		def window_proc(hwnd, msg, wparam, lparam):
			"""Window procedure that handles window messages."""
			try:
				if msg == win32con.WM_CREATE:
					print("Window created")
					return 0
				elif msg == win32con.WM_DESTROY:
					print("Window destroying")
					win32gui.PostQuitMessage(0)
					return 0
				elif msg == win32con.WM_SIZE:
					width = win32api.LOWORD(lparam)
					height = win32api.HIWORD(lparam)
					print(f"WM_SIZE: {width}x{height} (client area)")
					
					# Handle resize in associated window instance
					window_instance = None
					for obj in Win32Window._get_all_instances():
						if hasattr(obj, '_hwnd') and obj._hwnd == hwnd:
							window_instance = obj
							break
					
					if window_instance:
						window_instance._handle_resize(width, height)
					return 0
				elif msg == win32con.WM_PAINT:
					try:
						win32gui.ValidateRect(hwnd, None)
					except Exception as e:
						print(f"Paint error: {e}")
					return 0
				else:
					return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
			except Exception as e:
				print(f"Window procedure error: {e}")
				return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
		
		# Store the window procedure to prevent garbage collection
		Win32Window._window_proc = window_proc
		
		# Create and register the window class
		wc = WNDCLASSEX()
		wc.cbSize = ctypes.sizeof(WNDCLASSEX)
		wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
		wc.lpfnWndProc = window_proc
		wc.cbClsExtra = 0
		wc.cbWndExtra = 0
		wc.hInstance = win32api.GetModuleHandle(None)
		wc.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
		wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
		wc.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)
		wc.lpszMenuName = None
		wc.lpszClassName = Win32Window._window_class_name
		wc.hIconSm = 0
		
		try:
			print("Registering window class...")
			atom = user32.RegisterClassExW(ctypes.byref(wc))
			if atom == 0:
				err = ctypes.get_last_error()
				if err != 1410:  # ERROR_CLASS_ALREADY_EXISTS
					raise ctypes.WinError()
				print("Window class already registered")
			else:
				print("Window class registered successfully")
		except Exception as e:
			print(f"Window class registration error: {e}")
			raise  # Re-raise to see where it fails
	
	# ---

	_window_style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
	_window_style_ex = 0  # No extended styles

	def _get_window_size_for_layout(self, layout_width, layout_height):
		"""Given a desired client area (layout) size, return the total window size needed (including borders/title)."""
		rect = wintypes.RECT(0, 0, layout_width, layout_height)
		# Call AdjustWindowRectEx via ctypes
		if not user32.AdjustWindowRectEx(ctypes.byref(rect), self._window_style, False, self._window_style_ex):
			raise ctypes.WinError()
		win_width = rect.right - rect.left
		win_height = rect.bottom - rect.top
		return win_width, win_height

	def _get_layout_size_for_window(self, window_width, window_height):
		"""Given a total window size, return the available client area (layout) size."""
		rect = wintypes.RECT(0, 0, window_width, window_height)
		if not user32.AdjustWindowRectEx(ctypes.byref(rect), self._window_style, False, self._window_style_ex):
			raise ctypes.WinError()
		border_width = (rect.right - rect.left) - window_width
		border_height = (rect.bottom - rect.top) - window_height
		client_width = window_width - border_width
		client_height = window_height - border_height
		return client_width, client_height

	def _get_window_border_metrics(self):
		"""Get the border metrics for the window."""
		metrics = getattr(self, '_window_border_metrics', None)
		if metrics is None:
			# Call AdjustWindowRectEx via ctypes
			rect = wintypes.RECT(0, 0, 0, 0)
			if not user32.AdjustWindowRectEx(ctypes.byref(rect), self._window_style, False, self._window_style_ex):
				raise ctypes.WinError()
			self._window_border_metrics = metrics = (
					-rect.left, -rect.top, rect.right - rect.left, rect.bottom - rect.top )
		return metrics

	def query_width_request(self):
		# Query the width requirements of the child layout
		metrics = self._get_window_border_metrics()
		# Calculate horizontal padding
		request_width = self.child.query_width_request() if self.child else 1
		return request_width + metrics[2]

	def query_height_request(self):
		# Query the width requirements of the child layout
		metrics = self._get_window_border_metrics()
		# Calculate horizontal padding
		request_height = self.child.query_height_request() if self.child else 1
		return request_height + metrics[3]
	
	def distribute_width(self, available_width: int) -> int:
		metrics = self._get_window_border_metrics()
		# Adjust available width by removing border metrics
		if available_width < metrics[2]:
			raise ValueError("Available width is less than the window border width.")
		available_width -= metrics[2]  # Remove left + right border width
		inner_width = super().distribute_width(available_width)
		self._computed_size[0] = outer_width = inner_width + metrics[2]
		return outer_width  # Return total width including borders
	
	def distribute_height(self, available_height: int) -> int:
		metrics = self._get_window_border_metrics()
		if available_height < metrics[3]:
			raise ValueError("Available height is less than the window border height.")
		available_height -= metrics[3]  # Remove top + bottom border height
		inner_height = super().distribute_height(available_height)
		self._computed_size[1] = outer_height = inner_height + metrics[3]
		return outer_height  # Return total height including borders

	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position this window and its child widgets at the specified coordinates."""
		using_client_origin = self.client_origin
		if data is not None and 'client_origin' in data:
			using_client_origin = data['client_origin']
		
		# First store our position for layout calculations
		if using_client_origin:
			# Convert from client area coordinates to window coordinates
			metrics = self._get_window_border_metrics()
			window_x = x - metrics[0]  # Remove left border width
			window_y = y - metrics[1]  # Remove top border height
		else:
			window_x = x
			window_y = y
		Layout.position_at(self, window_x, window_y)
		
		# If we have a window handle, move the window
		if self._hwnd:
			# Get the current window size
			rect = win32gui.GetWindowRect(self._hwnd)
			width = rect[2] - rect[0]
			height = rect[3] - rect[1]
			
			try:
				win32gui.MoveWindow(self._hwnd, window_x, window_y, width, height, True)
			except Exception as e:
				print(f"Error moving window: {e}")
		
		# Position child widgets
		# The child is positioned relative to the client area (0,0)
		if self.child:
			assert self._hwnd is not None, "Window handle required for positioning"
			self.child.position_at(0, 0, {'parent_hwnd': self._hwnd})
	
	# ---
	
	@staticmethod
	def _get_all_instances():
		"""Get all Win32Window instances (for window procedure lookup)."""
		import gc
		return [obj for obj in gc.get_objects() if isinstance(obj, Win32Window)]
	
	def create_window(self):
		"""Create the actual Win32 window."""
		if self._hwnd is not None:
			return self._hwnd  # Already created
		
		if not Win32Window._window_class_registered:
			self._register_window_class()
			Win32Window._window_class_registered = True
		
		print("Creating window...")
		Win32Window._window_count += 1
		window_title = f"{self.title} ({Win32Window._window_count})"

		# Calculate initial size, handling width and height independently
		metrics = self._get_window_border_metrics() if self.client_origin else None
		print(f"Initial size request: {self.initial_size}, client_origin: {self.client_origin}")
		
		# Handle width		-- FIXME: deduplicate these two
		if self.initial_size[0] is not None:
			# Use specified width
			actual_width = max(self.initial_size[0], 100)
			print(f"Using specified width: {actual_width}")
			if metrics:
				actual_width += metrics[2]  # Add border width for client area sizing
				print(f"Adjusted for borders: {actual_width}")
		else:
			# Calculate from layout
			requested_width = self.query_width_request()
			print(f"Layout requested width: {requested_width}")
			if metrics:
				requested_width += metrics[2]
			actual_width = int(self.distribute_width(requested_width))
		
		# Handle height
		if self.initial_size[1] is not None:
			# Use specified height
			actual_height = max(self.initial_size[1], 100)
			print(f"Using specified height: {actual_height}")
			if metrics:
				actual_height += metrics[3]  # Add border height for client area sizing
				print(f"Adjusted for borders: {actual_height}")
		else:
			# Calculate from layout
			requested_height = self.query_height_request()
			print(f"Layout requested height: {requested_height}")
			if metrics:
				requested_height += metrics[3]
			actual_height = int(self.distribute_height(requested_height))
		
		print(f"Final window size will be: {actual_width}x{actual_height}")

		# Create the window
		try:
			hinstance = win32api.GetModuleHandle(None)
			if not hinstance:
				raise ctypes.WinError()
			
			print(f"Creating window of class '{self._window_class_name}' size {actual_width}x{actual_height}")
			
			# Convert strings to wide strings and handle properly
			lp_class_name = ctypes.c_wchar_p(self._window_class_name)
			lp_window_name = ctypes.c_wchar_p(window_title)
			
			# Create proper HANDLE for instance
			hinstance = wintypes.HINSTANCE(hinstance)
			
			hwnd = user32.CreateWindowExW(
				wintypes.DWORD(self._window_style_ex),  # Extended style
				lp_class_name,
				lp_window_name,
				wintypes.DWORD(self._window_style),
				wintypes.INT(win32con.CW_USEDEFAULT),
				wintypes.INT(win32con.CW_USEDEFAULT),
				wintypes.INT(actual_width),
				wintypes.INT(actual_height),
				wintypes.HWND(None),  # No parent window
				wintypes.HMENU(None),  # No menu
				hinstance,
				None  # No window creation data
			)
			
			if not hwnd:
				err = ctypes.get_last_error()
				raise ctypes.WinError(err)
			
			self._hwnd = hwnd
			print(f"Window created successfully (hwnd: {hwnd})")
			
			# Set window visibility
			user32.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
			user32.UpdateWindow(hwnd)
			
			rect = win32gui.GetWindowRect(hwnd)
			# Do initial layout and position all widgets
			client_rect = win32gui.GetClientRect(hwnd)
			width = client_rect[2] - client_rect[0]
			height = client_rect[3] - client_rect[1]
			self.layout(0, 0, width, height, {'parent_hwnd': self._hwnd})
			
			# Position the window itself at its current screen coordinates
			self.position_at(rect[0], rect[1], {'client_origin': False, 'parent_hwnd': self._hwnd})
			
			return hwnd
			
		except Exception as e:
			print(f"CreateWindowEx failed: {e}")
			if isinstance(e, OSError):
				print(f"Win32 error code: {e.winerror}")
			raise
	
	def _handle_resize(self, width, height):
		"""Handle window resize by updating the child layout."""
		# width and height are client area dimensions
		if self.child:
			self.child.layout(0, 0, width, height, {'parent_hwnd': self._hwnd})
	
	def _update_layout(self, actual_size):
		"""Update the layout if size has changed."""
		if self._hwnd is None or tuple(self._computed_size) == tuple(actual_size):
			return
		
		# Perform layout
		if actual_size:
			self.layout(0, 0, actual_size[0], actual_size[1], {'parent_hwnd': self._hwnd})
	
	def show(self):
		"""Show the window."""
		try:
			if self._hwnd is None:
				self.create_window()
				if self._hwnd is None:
					raise RuntimeError("Failed to create window")
			win32gui.ShowWindow(self._hwnd, win32con.SW_SHOW)
			win32gui.SetForegroundWindow(self._hwnd)
			print(f"Window shown successfully (hwnd: {self._hwnd})")
		except Exception as e:
			print(f"Failed to show window: {e}")
			raise
	
	def close(self):
		"""Close the window."""
		if self._hwnd is not None:
			win32gui.DestroyWindow(self._hwnd)
			self._hwnd = None

# -------

def build_horizontal_line_demo():
	"""Build a layout demonstrating horizontal lines with different positioning strategies."""
	return Win32Container.vertical(
		gap=20,  # Space between demonstrations
		children=(
			# Demo 1: Full-width horizontal line (edge to edge)
			Win32Container.vertical(
				gap=5,
				children=(
					Win32Text("Demo 1: Full-width horizontal line"),
					Win32SeparatorLine(),  # Should stretch across entire window width
				)
			),
			
			# Demo 2: Three horizontal lines with growing gaps
			Win32Container.vertical(
				gap=5,
				children=(
					Win32Text("Demo 2: Three lines with growing gaps"),
					Win32Container.horizontal(
						sizing=Grow(minimum=1),
						gap=20,
						children=(
							Win32SeparatorLine(),
							Win32SeparatorLine(),
							Win32SeparatorLine(),
						)
					),
				)
			),
			
			# Demo 3: Horizontal line with padding (inset from edges)
			Win32Container.vertical(
				gap=5,
				children=(
					Win32Text("Demo 3: Horizontal line with padding"),
					Win32Padding(20,  # 20px padding on all sides
						Win32SeparatorLine()
					),
				)
			),
		)
	)


def run_demo():
	# layout_content = LayoutWindow(child=build_horizontal_line_demo())
	layout_content = build_horizontal_line_demo()

	try:
		# Create a simple window
		print("Creating window with specified size 800x600")
		window = Win32Window(
			title="Test Window",
			width=800,
			height=600,
			child=layout_content
		)
		
		print("Window instance created, now creating Win32 window...")
		window.create_window()
		
		print("Window created, entering message loop...")
		try:
			win32gui.PumpMessages()
		except Exception as e:
			print(f"Message loop error: {e}")
			import traceback
			traceback.print_exc()
	except Exception as e:
		print(f"Test failed: {e}")
		import traceback
		traceback.print_exc()

if __name__ == "__main__":
	run_demo()
