"""
Win32-specific widget implementations that extend the pure layout engine.

This module provides Win32-specific versions of layout widgets that account for
native widget characteristics like borders, padding, and system metrics.
"""

from __future__ import annotations

from functools import lru_cache, cached_property
import ctypes
from ctypes import windll
import math
import sys
from weakref import WeakValueDictionary
from window_layout import (
	Layout,
	LayoutPluginContext,
	LayoutGroup,
	LayoutWindow,
	LayoutWidget,
	LayoutSeparatorLine,
	LayoutContainer,
	LayoutPadding,
	layout_context_class,
	Grow,
	LayoutText,
	LayoutButton,
	LayoutEdit,
	LayoutSpacer,
	FontObject,
)

# Cache reset helpers
# Don't use caching decorators since they're causing issues
import ctypes
from ctypes import wintypes
import win32gui, win32con, win32api

# Win32 API functions for getting system metrics
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Define CREATESTRUCT structure for WM_CREATE
class CREATESTRUCT(ctypes.Structure):
	_fields_ = [
		("lpCreateParams", ctypes.c_void_p),
		("hInstance", wintypes.HANDLE),
		("hMenu", wintypes.HMENU),
		("hwndParent", wintypes.HWND),
		("cy", wintypes.INT),
		("cx", wintypes.INT),
		("y", wintypes.INT),
		("x", wintypes.INT),
		("style", wintypes.LONG),
		("lpszName", wintypes.LPCWSTR),
		("lpszClass", wintypes.LPCWSTR),
		("dwExStyle", wintypes.DWORD),
	]

# Define PAINTSTRUCT structure
class PAINTSTRUCT(ctypes.Structure):
	_fields_ = [
		("hdc", wintypes.HDC),
		("fErase", wintypes.BOOL),
		("rcPaint", wintypes.RECT),
		("fRestore", wintypes.BOOL),
		("fIncUpdate", wintypes.BOOL),
		("rgbReserved", wintypes.BYTE * 32),
	]

# Set up BeginPaint/EndPaint function types
user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = wintypes.BOOL

# Set up function argument types for CreateWindowExW
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

# Set up GetWindowLongPtrW/SetWindowLongPtrW for window instance storage
if hasattr(ctypes.c_void_p, '_type_'):
	# 64-bit Python
	LONG_PTR = ctypes.c_void_p
else:
	# 32-bit Python
	LONG_PTR = ctypes.c_long

user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowLongPtrW.restype = LONG_PTR

# Set up InvalidateRect
user32.InvalidateRect.argtypes = [
	wintypes.HWND,      # hWnd
	wintypes.LPRECT,    # lpRect
	wintypes.BOOL       # bErase
]
user32.InvalidateRect.restype = wintypes.BOOL

# Set up GetDeviceCaps
gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int


class Win32FontBase:
	"""Base class for Win32 font objects.
	
	This class provides the common interface and properties for both system fonts
	and created fonts.
	
	Attributes:
		handle: The Win32 HFONT handle
		face_name: Font family name
		size: Size in points if positive, or direct height in logical units if negative
		bold: Whether the font is bold
		italic: Whether the font is italic
		underline: Whether the font is underlined
	"""
	
	def __init__(self, hfont: int, face_name: str, size: int, bold: bool, italic: bool, underline: bool):
		"""Initialize font properties."""
		self._hfont = hfont
		self._face_name = face_name
		self._size = size
		self._bold = bold
		self._italic = italic
		self._underline = underline
	
	@property
	def handle(self) -> int:
		"""Get the Win32 font handle."""
		return self._hfont
	
	def replace(self, face_name: str | None = None, size: int | None = None, *,
			   bold: bool | None = None, italic: bool | None = None, 
			   underline: bool | None = None) -> 'Win32Font':
		"""Create a new font based on this one, with some properties changed."""
		# Use current values for any unspecified properties
		new_face = face_name if face_name is not None else self._face_name
		new_size = size if size is not None else self._size
		new_bold = bold if bold is not None else self._bold
		new_italic = italic if italic is not None else self._italic
		new_underline = underline if underline is not None else self._underline
		
		# Create font - caching will handle the case of unchanged properties
		return Win32Font.create(new_face, new_size, bold=new_bold, 
							  italic=new_italic, underline=new_underline)


class LOGFONT(ctypes.Structure):
	"""Win32 LOGFONT structure for getting/setting font information."""
	_fields_ = [
		("lfHeight", ctypes.c_long),
		("lfWidth", ctypes.c_long),
		("lfEscapement", ctypes.c_long),
		("lfOrientation", ctypes.c_long),
		("lfWeight", ctypes.c_long),
		("lfItalic", ctypes.c_byte),
		("lfUnderline", ctypes.c_byte),
		("lfStrikeOut", ctypes.c_byte),
		("lfCharSet", ctypes.c_byte),
		("lfOutPrecision", ctypes.c_byte),
		("lfClipPrecision", ctypes.c_byte),
		("lfQuality", ctypes.c_byte),
		("lfPitchAndFamily", ctypes.c_byte),
		("lfFaceName", ctypes.c_wchar * 32)
	]


class Win32SystemFont(Win32FontBase):
	"""Represents a system font object in Win32.
	
	These fonts are managed by Windows and should not be deleted when this object
	is destroyed. System fonts are cached both by their handle and properties to
	ensure consistent reuse.
	"""
	
	# Cache of font handles to system font instances.
	# Uses a regular dict since these are permanent system resources we want to keep cached
	_handle_cache = {}
	
	# Map of stock object IDs that are fonts to their names
	_STOCK_FONTS = None  # Will be populated by _init_stock_fonts()
	
	@classmethod
	def _init_stock_fonts(cls) -> dict[str, int]:
		"""Initialize the map of stock font objects.
		
		Instead of probing for fonts (which can return false positives),
		we'll use the known stock font IDs from Windows. These are documented
		and guaranteed to be fonts when they exist.
		"""
		if cls._STOCK_FONTS is not None:
			return cls._STOCK_FONTS
		
		# Map of known stock fonts to their ID values (from wingdi.h)
		known_fonts = {
			"OEM_FIXED": 10,       # Terminal
			"ANSI_FIXED": 11,      # Courier
			"ANSI_VAR": 12,        # MS Sans Serif
			"SYSTEM": 13,          # System
			"DEVICE_DEFAULT": 14,   # Device Default
			"SYSTEM_FIXED": 16,     # System Fixed
			"DEFAULT_GUI": 17       # Segoe UI on modern Windows
		}
		
		# Only include fonts that exist and can be wrapped
		found_fonts = {}
		for name, stock_id in known_fonts.items():
			try:
				# Try to get the font handle
				handle = win32gui.GetStockObject(stock_id)
				if not handle:
					continue
					
				# Try to create a font wrapper - this will validate the font
				# and cache it in both handle and property caches
				font = cls.from_handle(handle)
				if font is None:
					continue
					
				# Add to our stock font mapping
				found_fonts[name] = stock_id
			except:
				pass  # Skip any that fail
		
		cls._STOCK_FONTS = found_fonts
		return found_fonts
	
	@staticmethod
	def from_handle(hfont: int) -> 'Win32SystemFont | None':
		"""Create a system font wrapper from an HFONT handle.
		
		Args:
			hfont: HFONT handle to wrap
			
		Returns:
			Win32SystemFont instance or None if handle is invalid
			
		Note:
			Results are cached by handle. The same handle will always return
			the same Win32SystemFont instance.
		"""
		# Check cache first
		cached = Win32SystemFont._handle_cache.get(hfont)
		if cached is not None:
			return cached
		
		# Get font information using GetObject
		lf = LOGFONT()
		try:
			if not windll.gdi32.GetObjectW(hfont, ctypes.sizeof(LOGFONT), ctypes.byref(lf)):
				return None
		except:
			return None  # Invalid font handle		# Get device context for DPI calculation
		hdc = win32gui.GetDC(0)
		try:
			# Convert logical height to points
			dpi = gdi32.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
			if lf.lfHeight < 0:
				size = int((-lf.lfHeight * 72.0) / dpi)
			else:
				size = lf.lfHeight  # Use height directly if positive
		finally:
			win32gui.ReleaseDC(0, hdc)
		
		# Create font properties
		face_name = lf.lfFaceName
		bold = lf.lfWeight >= win32con.FW_BOLD
		italic = bool(lf.lfItalic)
		underline = bool(lf.lfUnderline)
		
		# Check the Win32Font cache first - maybe we already have a font with these properties
		cache_key = Win32Font._make_cache_key(face_name, size, bold, italic, underline)
		font = Win32Font._active_fonts.get(cache_key)
		if font is not None:
			return font
		
		# Create new system font instance
		font = Win32SystemFont(
			hfont=hfont,
			face_name=face_name,
			size=size,
			bold=bold,
			italic=italic,
			underline=underline
		)
		
		# Cache by both handle and properties
		Win32SystemFont._handle_cache[hfont] = font
		Win32Font._active_fonts[cache_key] = font
		
		return font
	
	@classmethod
	def get_stock_font(cls, name: str) -> 'Win32SystemFont':
		"""Get a stock font by name.
		
		Args:
			name: Name of the stock font from _STOCK_FONTS
			
		Returns:
			Win32SystemFont instance for the requested stock font
			
		Raises:
			KeyError: If the name is not a known stock font
			WindowsError: If the font could not be retrieved
		"""
		# Initialize stock fonts if needed
		stock_fonts = cls._init_stock_fonts()
		
		stock_id = stock_fonts.get(name)
		if stock_id is None:
			raise KeyError(f"Unknown stock font: {name}. Must be one of {list(stock_fonts.keys())}")
		
		hfont = win32gui.GetStockObject(stock_id)
		if not hfont:
			raise WindowsError(f"Failed to get stock font: {name}")
		
		font = cls.from_handle(hfont)
		if font is None:
			raise WindowsError(f"Failed to create font wrapper for stock font: {name}")
		
		return font
	
	@classmethod
	def get_default_gui_font(cls) -> 'Win32SystemFont':
		"""Get the default GUI font used by Windows."""
		return cls.get_stock_font("DEFAULT_GUI")
	
	@classmethod
	def enumerate_stock_fonts(cls) -> list['Win32SystemFont']:
		"""Get a list of all available stock fonts.
		
		This enumerates all stock objects that are fonts, detecting which ones
		are available in the current Windows version.
		
		Returns:
			List of Win32SystemFont instances for each available stock font
		"""
		# Initialize stock fonts if needed
		stock_fonts = cls._init_stock_fonts()
		
		fonts = []
		for name in stock_fonts:
			try:
				fonts.append(cls.get_stock_font(name))
			except WindowsError:
				pass  # Skip fonts that fail to load
		return fonts


class Win32Font(Win32FontBase):
	"""Represents a created font in Win32 API format.
	
	This class creates and manages its own font handles, which are automatically
	cleaned up when no longer needed. Font instances are cached using both a 
	WeakValueDictionary (for active fonts) and an LRU cache (for recently used fonts).
	"""
	
	# Cache of currently active font instances
	_active_fonts = WeakValueDictionary()
	
	# Cache key generator
	@staticmethod
	def _make_cache_key(face_name: str, size: int, bold: bool, italic: bool, underline: bool) -> tuple:
		"""Create a cache key for font lookups."""
		return (face_name.lower(), size, bold, italic, underline)
	
	@classmethod
	@lru_cache(maxsize=32)  # Keep the last 32 fonts in the LRU cache
	def _create_font(cls, face_name: str, size: int, bold: bool, 
					italic: bool, underline: bool) -> Win32Font:
		"""Internal method to create a new font instance."""
		# Get device context for DPI awareness
		hdc = win32gui.GetDC(0)
		
		try:
			# If size is negative, use it directly as height
			# If positive, convert from points to logical units
			height = size if size < 0 else -int(size * gdi32.GetDeviceCaps(hdc, win32con.LOGPIXELSY) / 72.0)
			
			# Create font using CreateFontW (same method used in window_main.py)
			hfont = windll.gdi32.CreateFontW(
				height,         # Height (negative for character height)
				0,             # Width (0 = default)
				0,             # Escapement
				0,             # Orientation
				win32con.FW_BOLD if bold else win32con.FW_NORMAL,  # Weight
				int(italic),   # Italic
				int(underline), # Underline
				0,             # StrikeOut
				win32con.DEFAULT_CHARSET,  # CharSet
				win32con.OUT_DEFAULT_PRECIS,  # OutPrecision
				win32con.CLIP_DEFAULT_PRECIS,  # ClipPrecision
				win32con.DEFAULT_QUALITY,  # Quality
				win32con.DEFAULT_PITCH | win32con.FF_DONTCARE,  # PitchAndFamily
				face_name      # FaceName
			)
			
			if not hfont:
				raise WindowsError(f"Failed to create font: {face_name}")
			
			return cls(hfont, face_name, size, bold, italic, underline)
		finally:
			win32gui.ReleaseDC(0, hdc)
	
	@classmethod
	def create(cls, face_name: str, size: int = 10, *, bold: bool = False, 
			   italic: bool = False, underline: bool = False) -> Win32Font:
		"""Create a font with the specified properties.
		
		Args:
			face_name: Font family name (e.g. "Segoe UI", "Arial")
			size: Font size in points if positive, or direct character height in logical units if negative
			bold: Whether the font is bold
			italic: Whether the font is italic
			underline: Whether the font is underlined
		"""
		# Initialize stock fonts first to ensure they're in the cache
		Win32SystemFont._init_stock_fonts()
		
		# Create cache key
		cache_key = cls._make_cache_key(face_name, size, bold, italic, underline)
		
		# First check the weak reference cache for an active instance
		font = cls._active_fonts.get(cache_key)
		if font is not None:
			return font
		
		# If not in active cache, create new instance (will use LRU cache)
		font = cls._create_font(face_name, size, bold, italic, underline)
		
		# Add to active cache
		cls._active_fonts[cache_key] = font
		
		return font
	
	def __del__(self):
		"""Clean up the font when the object is destroyed."""
		if getattr(self, '_hfont', None):
			try:
				win32gui.DeleteObject(self._hfont)
			except Exception:
				pass  # Ignore errors during cleanup


class Win32Color:
	"""Represents a color in Win32 API format.
	
	This class encapsulates color handling for Win32 widgets, providing
	convenient ways to specify colors and converting them to the
	Win32 RGB format.
	"""
	__slots__ = ('value', '_name')
	
	from win32_colors import NAMED_COLORS
	
	# Class variables for static colors
	black: Win32Color = None  # type: ignore
	white: Win32Color = None  # type: ignore
	
	def __init__(self, value: int):
		"""Create a color from a Win32 RGB value."""
		self.value = value
		self._name = None  # Cached color name, if it matches a named color
	
	@property
	def r(self) -> int:
		"""Red component (0-255)"""
		return self.value & 0xFF
	
	@property
	def g(self) -> int:
		"""Green component (0-255)"""
		return (self.value >> 8) & 0xFF
	
	@property
	def b(self) -> int:
		"""Blue component (0-255)"""
		return (self.value >> 16) & 0xFF
	
	@classmethod
	def lookup_name(cls, r: int, g: int, b: int) -> str | None:
		"""Get the name of a color if it matches a named color, otherwise None."""
		rgb = (r, g, b)
		for name, named_rgb in cls.NAMED_COLORS.items():
			if named_rgb == rgb:
				return name
		return None
	
	@classmethod
	def from_name(cls, name: str) -> Win32Color:
		"""Create a color from a CSS color name."""
		name = name.lower()
		if name not in cls.NAMED_COLORS:
			raise ValueError(f"Unknown color name: {name}")
		r, g, b = cls.NAMED_COLORS[name]
		color = cls.from_rgb(r, g, b)
		color._name = sys.intern(name)  # Cache the name since we know it
		return color
	
	@classmethod
	def from_rgb(cls, r: int, g: int, b: int) -> Win32Color:
		"""Create a color from RGB values (0-255)."""
		r = max(0, min(255, int(r)))
		g = max(0, min(255, int(g)))
		b = max(0, min(255, int(b)))
		color = cls(win32api.RGB(r, g, b))
		return color
	
	def __repr__(self) -> str:
		"""Get a string representation."""
		if self._name is None:
			self._name = self.lookup_name(self.r, self.g, self.b) or False
		if self._name:
			return f"Win32Color.from_name('{self._name}')"
		return f"Win32Color.from_rgb({self.r}, {self.g}, {self.b})"


# Initialize static color instances after class definition
Win32Color.black = Win32Color.from_name('black')
Win32Color.white = Win32Color.from_name('white')


def format_size(size: int) -> str:
	"""Format a file size into a human-readable string."""
	float_size = float(size)  # Convert to float for division
	for unit in ('bytes', 'KB', 'MB', 'GB', 'TB'):
		if float_size < 1024:
			return f"{float_size:.1f} {unit}" if float_size % 1 != 0 else f"{int(float_size)} {unit}"
		float_size /= 1024
	return f"{float_size:.1f} PB"


# -------

class Win32Widget(LayoutWidget):
	"""Base class for Win32 widgets that need to manage native window handles."""
	
	def __init__(self):
		self._hwnd = None
		self._window = None  # Reference to containing Win32Window
	
	def handle_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int | None:
		"""Handle a window message sent to this widget.
		
		Args:
			hwnd: Window handle message was sent to
			msg: Message identifier
			wparam: First message parameter
			lparam: Second message parameter
			
		Returns:
			int if message was handled, None to allow default processing
		"""
		return None
	
	def invalidate_window(self, rect=None, erase=True):
		"""Invalidate this widget's window or a region of it.
		
		Args:
			rect: Optional tuple of (left, top, right, bottom) or None for entire window
			erase: Whether to erase the background
		"""
		if self._hwnd is None:
			return  # No window to invalidate yet
		
		if rect is None:
			# Try invalidating entire window
			result = user32.InvalidateRect(self._hwnd, None, erase)
		else:
			# Use specified rectangle
			client_r = wintypes.RECT(rect[0], rect[1], rect[2], rect[3])
			result = user32.InvalidateRect(self._hwnd, ctypes.byref(client_r), erase)
		
		if not result:
			raise ctypes.WinError()
	
	def position_at(self, x: int, y: int, data=None) -> None:
		"""Position the widget relative to the parent window's client area.
		The data parameter is expected to contain:
		- parent_hwnd: Parent window handle
		- window: Win32Window instance for message dispatch
		"""
		super().position_at(x, y, data)
		
		if isinstance(data, dict):
			# Store window reference for message dispatch
			if 'window' in data:
				self._window = data['window']
			
			# If we have a window handle, update its position
			if self._hwnd:
				try:
					width = self._computed_size[0]
					height = self._computed_size[1]
					win32gui.MoveWindow(self._hwnd, x, y, width, height, False)  # Don't repaint immediately
					self.invalidate_window()  # Mark as needing repaint
				except Exception as e:
					print(f"Error positioning {type(self).__name__}: {e}")
				
			# Create native widget if this is our first positioning and we have a parent
			elif 'parent_hwnd' in data and 'window' in data:
				parent_hwnd = data['parent_hwnd']
				self._window = data['window']  # Store window reference before creating widget
				self._create_native_widget(parent_hwnd, x, y)
				# Widget map registration now happens in _create_native_widget
	
	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create the native Win32 widget. Override in derived classes."""
		raise NotImplementedError("Win32Widget subclasses must implement _create_native_widget")

# -------

@layout_context_class
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

	def create_text(self, text: str, font: FontObject | None = None, color: Win32Color | None = None) -> Win32Text:
		"""Create a Win32Text widget.
		
		Args:
			text: Text to display
			font: Font specification (string face name or Win32Font instance) or None to use default GUI font
			color: Text color or None for black
			
		Returns:
			New Win32Text widget instance
		"""
		return Win32Text(text, font, color)
	
	@staticmethod
	def _select_font(dc: int, font: Win32FontBase | int | None = None) -> None:
		"""Select a font into a device context, falling back to default GUI font if needed.
		
		Args:
			dc: Device context handle
			font: Win32Font/Win32SystemFont instance, HFONT handle, or None for default GUI font
		"""
		if font is not None:
			# If it's a font instance, use its handle
			if isinstance(font, Win32FontBase):
				win32gui.SelectObject(dc, font.handle)
			# Otherwise assume it's an HFONT handle
			else:
				win32gui.SelectObject(dc, font)
		else:
			# Get the default GUI font as a system font
			default_font = Win32SystemFont.get_default_gui_font()
			win32gui.SelectObject(dc, default_font.handle)
	
	@lru_cache
	def measure_text_width(self, text: str, font: Win32Font | None = None) -> int:
		"""Win32-specific text width measurement using GDI.
		
		Args:
			text: The text to measure
			font: Win32Font instance or None to use default GUI font
			
		Returns:
			Width of the text in pixels
		"""
		dc = self._get_measurement_dc()
		print(f"Measuring text width: '{text}'")
		
		self._select_font(dc, font)
		
		# Measure text width
		text_size = win32gui.GetTextExtentPoint32(dc, text or ' ')
		print(f"  -> Width: {text_size[0]}")
		return text_size[0]
	
	@lru_cache
	def get_font_metrics(self, font: Win32Font | None = None) -> dict[str, int]:
		"""Win32-specific font metrics using GDI.
		
		Args:
			font: Win32Font instance or None to use default GUI font
			
		Returns:
			Dictionary with height, ascent, and descent values in pixels
		"""
		dc = self._get_measurement_dc()
		
		self._select_font(dc, font)
		
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
	"""Win32-specific text that uses GDI text measurement and drawing."""
	
	def __init__(self, text: str, font: FontObject | None = None, color: Win32Color | None = None):
		LayoutText.__init__(self, text, font)
		Win32Widget.__init__(self)
		self._hwnd: int | None = None
		self.color = Win32Color.black if color is None else color
		# Convert string font specs to Win32Font instances
		if isinstance(font, str):
			self.font = Win32Font.create(font)  # Use default size/style
		elif not (font is None or isinstance(font, Win32Font)):
			raise TypeError("font must be None, a string (face name), or a Win32Font instance")
	
	def handle_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int | None:
		"""Handle window messages for this text control."""
		if msg == win32con.WM_CTLCOLORSTATIC and lparam == self._hwnd:
			hdc = wparam
			# Set text color and transparent background
			win32gui.SetTextColor(hdc, self.color.value)
			win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
			# Use hollow brush for transparent background
			return win32gui.GetStockObject(win32con.HOLLOW_BRUSH)
		return super().handle_message(hwnd, msg, wparam, lparam)

	def _create_native_widget(self, parent_hwnd, x, y):
		"""Create a native static control."""
		width = max(self._computed_size[0], self.query_width_request())		# -- FIXME : our computed size should be solid by this point
		height = max(self._computed_size[1], self.query_height_request())	#	- though it's 300, which is rather suspicious
		
		try:
			self._hwnd = win32gui.CreateWindow(
				"STATIC",  # Window class
				self.text,  # Initial text
				win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT,
				x, y, width, height,
				parent_hwnd, 0, win32api.GetModuleHandle(None), None
			)
			
			if not self._hwnd:
				print(f"Failed to create text control: error {win32api.GetLastError()}")
				return self._hwnd
				
			# Register with window's widget map immediately after creation
			if self._window is not None:
				self._window._widget_map[self._hwnd] = self
			
			# Set font (either custom or default GUI font)
			try:
				if self.font:
					# Use the Win32Font instance directly
					win32gui.SendMessage(self._hwnd, win32con.WM_SETFONT, self.font.handle, 0)
				else:
					# Default GUI font if no font specified
					default_font = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT
					if default_font:
						win32gui.SendMessage(self._hwnd, win32con.WM_SETFONT, default_font, 0)
			except Exception as e:
				print(f"Error setting font: {e}")
			
			# Make sure the text is visible initially
			# win32gui.UpdateWindow(self._hwnd)
			win32gui.SendMessage(self._hwnd, win32con.WM_PAINT, 0, 0)  # Queue a paint message
			
			return self._hwnd
			
		except Exception as e:
			print(f"Error creating text window: {e}")
			raise
	
	def set_text(self, text: str):
		"""Update the text and trigger a redraw."""
		self.text = text
		if self._hwnd:
			# Update text and queue redraw
			text_buffer = str(self.text).encode('utf-16le')
			win32gui.SendMessage(self._hwnd, win32con.WM_SETTEXT, 0, text_buffer)
			self.invalidate_window()  # Mark as needing repaint
			# win32gui.SendMessage(self._hwnd, win32con.WM_PAINT, 0, 0)  # Force immediate paint if InvalidateRect fails

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
	def __init__(self, *, axis=LayoutGroup.HORIZONTAL, thickness=2, width=None, height=None):
		LayoutSeparatorLine.__init__(self, axis=axis, thickness=thickness, width=width, height=height)
		Win32Widget.__init__(self)
	
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
	_window_map = {}  # Strong reference map of window handles to instances
	
	def __init__(self, child=None, title="Win32 Window", width=None, height=None, client_origin=True):
		super().__init__(child)
		self.title = title
		self._initial_layout_done = False
		
		# Store initial size (None is valid for either dimension)
		self.initial_size = (width, height)
		print(f"Win32Window created with initial size request: {self.initial_size}")
		
		# Whether specified dimensions are client area (True) or total window size (False)
		self.client_origin = client_origin
		
		self._hwnd = None
		
		# Map of window handles to widget instances
		self._widget_map = WeakValueDictionary()
		
		# Register window class if not already done
		if not Win32Window._window_class_registered:
			self._register_window_class()
			Win32Window._window_class_registered = True
	
	@staticmethod
	def _get_instance_from_hwnd(hwnd: int) -> 'Win32Window':
		"""Get the Python window instance associated with a window handle."""
		try:
			return Win32Window._window_map[hwnd]
		except KeyError:
			raise RuntimeError(f"No window instance found for handle {hwnd}")
	
	@staticmethod
	@WNDPROC
	def _window_proc(hwnd, msg, wparam, lparam):
		"""Window procedure that handles window messages."""
		try:
			# Special handling for messages that occur before window instance exists
			if msg == win32con.WM_GETMINMAXINFO:  # 0x0024 (36)
				# Check if we have an instance yet
				if hwnd not in Win32Window._window_map:
					# No instance yet, use default handling
					return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
			elif msg == win32con.WM_NCCALCSIZE:  # 0x0081 (129)
				# Let Windows calculate default non-client area
				return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
			elif msg == win32con.WM_NCCREATE:  # 0x0083 (131)
				# First message that contains creation parameters - perfect time to set up our instance
				create_struct = ctypes.cast(lparam, ctypes.POINTER(CREATESTRUCT)).contents
				instance_ptr = ctypes.cast(create_struct.lpCreateParams, 
										ctypes.POINTER(ctypes.py_object))
				# Store the instance in our map right away
				window = instance_ptr.contents.value
				Win32Window._window_map[hwnd] = window
				print(f"Window instance set up during WM_NCCREATE for {hwnd}")
				# Let Windows finish non-client creation
				return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
			elif msg == win32con.WM_DESTROY:
				print("Window destroying")
				win32gui.PostQuitMessage(0)
				return 0
			elif msg == win32con.WM_NCDESTROY:
				print("Window non-client area destroying")
				# Clean up our instance map only after all messages are processed
				Win32Window._window_map.pop(hwnd, None)
				return 0
			
			# For all other messages, first try to find the target window/widget
			try:
				# Get window instance from our map
				window = Win32Window._get_instance_from_hwnd(hwnd)
				
				# For control notifications (WM_CTLCOLOR*, WM_COMMAND, etc.)
				# try to dispatch to the control first since it has the most context
				if msg >= win32con.WM_CTLCOLORMSGBOX and msg <= win32con.WM_CTLCOLORSTATIC:
					# For these messages:
					# - hwnd is parent window handle
					# - wparam is HDC
					# - lparam is control handle
					widget = window._widget_map.get(lparam)
					if widget:
						result = widget.handle_message(hwnd, msg, wparam, lparam)
						if result is not None:
							return result
				elif msg == win32con.WM_COMMAND:
					# For command messages:
					# - hwnd is parent window handle
					# - HIWORD(wparam) is notification code
					# - LOWORD(wparam) is control ID
					# - lparam is control handle
					if lparam:  # Only for control notifications (not menu/accelerator)
						widget = window._widget_map.get(lparam)
						if widget:
							result = widget.handle_message(hwnd, msg, wparam, lparam)
							if result is not None:
								return result
				
				# Let the window handle any message (including unhandled control messages)
				result = window.handle_message(hwnd, msg, wparam, lparam)
				if result is not None:
					return result
				
				# Special post-dispatch handling for certain messages
				if msg == win32con.WM_SIZE:
					# Update layout if size message wasn't handled
					# Forward any existing layout data
					layout_data = {
						'window': window,
						'parent_hwnd': window._hwnd,
					}
					window._handle_resize(		# -- FIXME : i think this one is redundant
						win32api.LOWORD(lparam),
						win32api.HIWORD(lparam),
						layout_data
					)
					return 0
				elif msg == win32con.WM_PAINT:
					# Always validate paint region to prevent endless WM_PAINT messages
					try:
						ps = PAINTSTRUCT()
						hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
						if hdc:
							update_rect = (ps.rcPaint.left, ps.rcPaint.top, ps.rcPaint.right, ps.rcPaint.bottom)
							print(f"Update region: {update_rect}")
							user32.EndPaint(hwnd, ctypes.byref(ps))
					except Exception as e:
						print(f"Paint error: {e}")
					return 0
				elif msg == win32con.WM_CTLCOLORSTATIC:
					# Default handling for static controls without custom handlers
					default_color = Win32Color.black.value
					win32gui.SetTextColor(wparam, default_color)
					win32gui.SetBkMode(wparam, win32con.TRANSPARENT)
					return win32gui.GetStockObject(win32con.WHITE_BRUSH)
			except (RuntimeError, WindowsError) as e:
				# Window instance not found - this shouldn't happen except during WM_CREATE
				print(f"Warning: Could not get window instance ({msg=}): {e}")

			# Fall back to default processing for unhandled messages
			return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
		except Exception as e:
			print(f"Window procedure error: {e}")
			return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

	@classmethod
	def _register_window_class(cls):
		"""Register the window class for Win32Window instances."""
		# Create and register the window class
		wc = WNDCLASSEX()
		wc.cbSize = ctypes.sizeof(WNDCLASSEX)
		wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
		wc.lpfnWndProc = cls._window_proc  # Use our class method directly
		wc.cbClsExtra = 0
		wc.cbWndExtra = 0  # No extra bytes needed - using instance map instead
		wc.hInstance = win32api.GetModuleHandle(None)
		wc.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
		wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
		wc.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)
		wc.lpszMenuName = None
		wc.lpszClassName = cls._window_class_name
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

	def query_axis_request(self, axis):
		# Query the width/height requirements of the child layout
		metrics = self._get_window_border_metrics()
		# Calculate horizontal padding
		request_size = self.child.query_axis_request(axis) if self.child else 1
		return request_size + metrics[axis+2]
	
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
		assert data is not None, "Data must be provided for positioning"
		using_client_origin = data.get('client_origin', self.client_origin)
		
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
			self.child.position_at(0, 0, {**data, 'parent_hwnd': self._hwnd})
	
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
				print(f"  Adjusted for borders: {actual_width}")
		else:
			# Calculate from layout
			requested_width = self.query_width_request()
			print(f"Layout requested width: {requested_width}")
			if metrics:
				requested_width += metrics[2]
				print(f"  Adjusted for borders: {requested_width}")
			actual_width = math.ceil(self.distribute_width(requested_width))
		
		# Handle height
		if self.initial_size[1] is not None:
			# Use specified height
			actual_height = max(self.initial_size[1], 100)
			print(f"Using specified height: {actual_height}")
			if metrics:
				actual_height += metrics[3]  # Add border height for client area sizing
				print(f"  Adjusted for borders: {actual_height}")
		else:
			# Calculate from layout
			requested_height = self.query_height_request()
			print(f"Layout requested height: {requested_height}")
			if metrics:
				requested_height += metrics[3]
				print(f"  Adjusted for borders: {requested_height}")
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
			
			# Create a py_object to pass ourselves to the window procedure
			self._create_param = ctypes.py_object(self)
			
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
				ctypes.cast(ctypes.pointer(self._create_param), ctypes.c_void_p)  # Pass our instance
			)
			
			if not hwnd:
				err = ctypes.get_last_error()
				raise ctypes.WinError(err)
			
			# Ensure that _window_map was set by window creation
			assert Win32Window._window_map.get(hwnd) == self
			
			self._hwnd = hwnd
			print(f"Window created successfully (hwnd: {hwnd})")
			
			# Skip the explicit layout if we already got one from WM_SIZE
			if not self._initial_layout_done:
				# Compute desired position/size from window rect
				client_rect = win32gui.GetClientRect(hwnd)
				width = client_rect[2] - client_rect[0]
				height = client_rect[3] - client_rect[1]
				# Create layout data that will be inherited by all child widgets
				layout_data = {
					'parent_hwnd': self._hwnd,
					'window': self
				}
				# Do initial layout using the same handler as resize
				self._handle_resize(width, height, layout_data)
			
			# Show the window once layout is complete
			user32.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
			user32.UpdateWindow(hwnd)
			
			return hwnd
			
		except Exception as e:
			print(f"CreateWindowEx failed: {e}")
			if isinstance(e, OSError):
				print(f"Win32 error code: {e.winerror}")
			raise
	
	def handle_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int | None:
		"""Handle a window message.
		
		Args:
			hwnd: Window handle message was sent to
			msg: Message identifier
			wparam: First message parameter
			lparam: Second message parameter
			
		Returns:
			int if message was handled, None to allow default processing
		"""
		if msg == win32con.WM_SIZE:
			width = win32api.LOWORD(lparam)
			height = win32api.HIWORD(lparam)
			# Handle resize with fresh layout data
			layout_data = {
				'window': self,
				'parent_hwnd': hwnd  # self._hwnd won't be set yet during creation
			}
			self._handle_resize(width, height, layout_data)
			return 0
		return None

	def _handle_resize(self, width, height, data):
		"""Handle window resize by updating the child layout."""
		# width and height are client area dimensions
		if self.child:
			self.child.layout(0, 0, width, height, data)
			# First successful layout marks initialization complete
			if not self._initial_layout_done:
				self._initial_layout_done = True
	
	def _update_layout(self, actual_size, data):
		"""Update the layout if size has changed."""
		if self._hwnd is None or tuple(self._computed_size) == tuple(actual_size):
			return
		
		# Perform layout
		if actual_size:
			# Update layout data with current window state
			layout_data = {
				**data,
				'parent_hwnd': self._hwnd,
				'window': self,
				'initial_layout': False
			}
			self.layout(0, 0, actual_size[0], actual_size[1], layout_data)
	
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
					Win32Text("Demo 1: Full-width horizontal line",
							 font=Win32Font.create("Verdana", size=14, bold=True),
							 color=Win32Color.from_name('royalblue')),  # Using custom font and color
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
					Win32Text("Demo 3: Horizontal line with padding (inset from edges)"),
					Win32Padding(20,  # 20px padding on all sides
						Win32SeparatorLine()
					),
				)
			),
			
			# Demo 4: Horizontal line with constrained width
			Win32Container.vertical(
				gap=5,
				children=(
					Win32Text("Demo 4: Horizontal line with constrained width"),
					Win32SeparatorLine(width=300),  # Fixed width of 300px
				)
			),
		)
	)


def run_demo():
	# Build demo layout
	layout_content = build_horizontal_line_demo()

	try:
		# Create a simple window
		print("Creating window with specified size 800x600")
		window = Win32Window(
			title="Test Window",
			width=None, # 800,
			height=200,
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
