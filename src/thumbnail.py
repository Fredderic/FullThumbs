"""
DWM thumbnail management for FullThumbs application.
"""

import ctypes
from ctypes import byref
import win32gui

from .constants import PIP_PADDING

# ------- DWM thumbnail properties structure and constants

class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
	"""DWM thumbnail properties structure."""
	_fields_ = [
		("dwFlags", ctypes.c_uint),
		("rcDestination", ctypes.c_long * 4),    # RECT
		("rcSource", ctypes.c_long * 4),         # RECT
		("opacity", ctypes.c_ubyte),
		("fVisible", ctypes.c_bool),
		("fSourceClientAreaOnly", ctypes.c_bool),
	]
# DWM Constants
DWM_TNP_RECTDESTINATION = 0x00000001
DWM_TNP_RECTSOURCE = 0x00000002
DWM_TNP_OPACITY = 0x00000004
DWM_TNP_VISIBLE = 0x00000008
DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010

# -------

dwmapi_lib = ctypes.windll.dwmapi

# DwmRegisterThumbnail
dwmapi_lib.DwmRegisterThumbnail.argtypes = [
	ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
]
dwmapi_lib.DwmRegisterThumbnail.restype = ctypes.c_long

# DwmUpdateThumbnailProperties
dwmapi_lib.DwmUpdateThumbnailProperties.argtypes = [
	ctypes.c_void_p, ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES)
]
dwmapi_lib.DwmUpdateThumbnailProperties.restype = ctypes.c_long

# -------

def calculate_aspect_fit_rect(target_rect, source_width, source_height):
	"""Calculate aspect ratio fit rectangle."""
	target_left, target_top, target_right, target_bottom = target_rect
	target_width = target_right - target_left
	target_height = target_bottom - target_top
	
	scale_w = target_width / source_width
	scale_h = target_height / source_height
	scale = min(scale_w, scale_h)
	
	new_width = int(source_width * scale)
	new_height = int(source_height * scale)
	
	x_offset = (target_width - new_width) // 2
	y_offset = (target_height - new_height) // 2
	
	return (
		target_left + x_offset,
		target_top + y_offset,
		target_left + x_offset + new_width,
		target_top + y_offset + new_height
	)


class ThumbnailManager:
	"""Manages DWM thumbnail operations."""
	
	def __init__(self, target_hwnd, target_rect, source_hwnd):
		self.target_hwnd = target_hwnd
		self.target_rect = target_rect
		self.source_hwnd = source_hwnd

		self.thumb_handle = None
		self.current_thumb_rect = None
		self.is_valid = True

		self.register_thumbnail()
	
	def update_thumbnail_rect(self, target_rect):
		"""Update thumbnail properties."""
		self.target_rect = target_rect

		source_left, source_top, source_right, source_bottom = win32gui.GetClientRect(self.source_hwnd)
		if source_left >= source_right or source_top >= source_bottom:
			# print("Source window dimensions are invalid. Cannot update thumbnail properties.")
			raise ValueError("Invalid source window dimensions.")
		
		self.current_thumb_rect = target_rect = calculate_aspect_fit_rect(
			target_rect, source_right - source_left, source_bottom - source_top
		)
		
		props = DWM_THUMBNAIL_PROPERTIES()
		props.dwFlags = DWM_TNP_RECTDESTINATION | DWM_TNP_VISIBLE | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY
		props.rcDestination = target_rect
		props.fVisible = True
		props.opacity = 255
		
		result = dwmapi_lib.DwmUpdateThumbnailProperties(self.thumb_handle, byref(props))
		if result != 0:
			# print(f"Failed to update thumbnail properties: HRESULT {result}")
			raise RuntimeError(f"Failed to update thumbnail properties: HRESULT {result}")
		
		win32gui.InvalidateRect(self.target_hwnd, None, True)
	
	def register_thumbnail(self):
		"""Register a new thumbnail."""
		try:
			self.thumb_handle = ctypes.c_void_p()
			
			result = dwmapi_lib.DwmRegisterThumbnail(
				self.target_hwnd, self.source_hwnd, byref(self.thumb_handle)
			)
			if result != 0:
				print(f"Failed to register thumbnail: HRESULT {result}")
				return False
			
			self.update_thumbnail_rect(self.target_rect)
			
		except Exception as e:
			print(f"Error with DWM thumbnail: {e}")
			print("Note: DWM thumbnails often don't work for true exclusive fullscreen apps.")
			return False
	
	def cleanup_thumbnail(self):
		"""Cleanup thumbnail resources but preserve the last known position."""
		if self.thumb_handle:
			dwmapi_lib.DwmUnregisterThumbnail(self.thumb_handle)
			self.thumb_handle = None
			self.is_valid = False  # Mark as invalid but keep current_thumb_rect
	
	def check_within_thumbnail_rect(self, x, y):
		"""Check if coordinates are within thumbnail rectangle."""
		if self.current_thumb_rect:
			left, top, right, bottom = self.current_thumb_rect
			return left < x < right and top < y < bottom
		return False
