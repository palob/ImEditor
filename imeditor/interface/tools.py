#!/usr/bin/python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib

def pil_to_pixbuf(img):
    """Convert the PIL image to a Pixbuf usable by Gtk"""
    data = GLib.Bytes.new(img.tobytes())
    w, h = img.size
    if img.mode == 'RGB':
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
            False, 8, w, h, w * 3)
    elif img.mode == 'RGBA':
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
            True, 8, w, h, w * 4)
    return pixbuf


class SpinButton(Gtk.SpinButton):
    def __init__(self, default, min_value, max_value, step=20, page=40):
        Gtk.SpinButton.__init__(self)
        self.set_digits(0)
        self.set_numeric(False)
        self.set_range(min_value, max_value)
        self.set_value(default)
        self.set_increments(step, page)
