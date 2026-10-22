"""
This file contains some helper functions to support high-DPI displays
in the Tk GUI.

This is required because on Wayland, it always reports 96 DPI. And with
GNOME's `xwayland-native-scaling` (or any other compositor that expects
X11 clients to scale themselves) the GUI ends up tiny.
"""

import contextlib
import ctypes
import ctypes.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkinter import Tk

# The DPI that the hard-coded pixel sizes in the GUI have been designed for.
_baseline_dpi = 96.0

_ui_scale: float = 1.0


def get_ui_scale() -> float:
    return _ui_scale


def get_integer_ui_scale() -> int:
    """
    :return: The UI scale rounded to a whole number, for things that should be scaled
             without interpolation (i.e. the emulator's video output.)
    """
    return max(1, round(_ui_scale))


def scaled(pixels: int) -> int:
    return round(pixels * _ui_scale)


def _get_xft_dpi() -> float | None:
    """
    Reads the `Xft.dpi` value from the X resource database (i.e. what `xrdb -query` would print.)
    """
    with contextlib.suppress(OSError, AttributeError):
        libx11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        libx11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        libx11.XOpenDisplay.restype = ctypes.c_void_p
        libx11.XResourceManagerString.argtypes = [ctypes.c_void_p]
        libx11.XResourceManagerString.restype = ctypes.c_char_p
        libx11.XCloseDisplay.argtypes = [ctypes.c_void_p]

        display = libx11.XOpenDisplay(None)
        if not display:
            return None
        try:
            resources = libx11.XResourceManagerString(display)
        finally:
            libx11.XCloseDisplay(display)

        if resources is None:
            return None

        for line in resources.decode("utf-8", errors="replace").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "Xft.dpi":
                with contextlib.suppress(ValueError):
                    dpi = float(value.strip())
                    if dpi > 0:
                        return dpi

    return None


def initialise_ui_scaling(window: "Tk") -> None:
    global _ui_scale

    tk_dpi = window.winfo_fpixels("1i")
    dpi = tk_dpi
    if window.tk.call("tk", "windowingsystem") == "x11":
        xft_dpi = _get_xft_dpi()
        # Only ever scale _up_, so that this does not make things worse for setups
        # where Tk already got it right.
        if xft_dpi is not None and xft_dpi > tk_dpi:
            # `tk scaling` is measured in pixels per point (1/72 of an inch.)
            window.tk.call("tk", "scaling", xft_dpi / 72)
            dpi = xft_dpi

    _ui_scale = max(1.0, dpi / _baseline_dpi)

    if _ui_scale > 1:
        from tkinter import font, ttk

        # Treeview rows have a fixed pixel height by default, so the (now larger) text would overlap.
        line_height = font.nametofont("TkDefaultFont", root=window).metrics("linespace")
        ttk.Style(window).configure("Treeview", rowheight=line_height + scaled(4))
