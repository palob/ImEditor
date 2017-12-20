#!/usr/bin/python

from PIL import Image
from os import path

from interface import dialog
from filters import base
from editor.image import ImageObject
from editor.tools import get_middle_mouse, get_infos
from editor.draw import draw_rectangle, draw_ellipse


class Editor(object):
    def __init__(self, tab, img, filename, saved):
        super(Editor, self).__init__()
        self.tab = tab

        self.image = ImageObject(img, filename, saved)

        # History
        self.MAX_HIST = 100

        # Tasks
        self.task = 0  # 0 -> select, 1 -> paste, 2 -> pencil
        self.left_button_pressed = False

        # Selection vars
        self.selection = list()
        self.selected_img = None

        # Pencil settings
        self.pencil_shape = 'ellipse'
        self.pencil_color = 'black'
        self.pencil_size = 8


    def change_task(self, task='select'):
        """Change active task and its cursor"""
        if task == 'select':
            self.task = 0
            self.change_cursor('default')
        elif task == 'paste':
            self.task = 1
            self.change_cursor('move')
        elif task == 'pencil':
            self.task = 2
            self.change_cursor('draw')

    def change_cursor(self, cursor):
        """Change cursor that hovers the image"""
        img_widget = self.tab.img_widget.get_window()
        if img_widget:
            img_widget.set_cursor(self.tab.win.cursors[cursor])

    def do_tmp_change(self, img):
        """Update displayed image without modifying the history"""
        self.tab.update_image(img, True)
        self.image.tmp_img = img

    def do_change(self, img):
        """Update displayed image and save it in the history"""
        if self.image.tmp_img:
            self.image.tmp_img = None  # remove tmp image
        # Update size
        self.tab.width = img.width
        self.tab.height = img.height
        # Update image
        self.tab.update_image(img)
        # Save it in the history
        self.image.forget_img()
        self.image.add_img(img)
        self.image.increment_index()
        self.image.saved = False
        if self.image.get_n_img() > self.MAX_HIST:
            self.image.remove_first_img()
            self.image.decrement_index()

    def undo(self):
        """Go to the previous image in the history"""
        if self.image.get_n_img() > 1:
            if self.image.index > 0:
                self.image.decrement_index()
                self.tab.update_image(self.image.get_current_img())

    def redo(self):
        """Go to the next image of the history"""
        if self.image.get_n_img() > 1:
            if self.image.index + 1 < self.image.get_n_img():
                self.image.increment_index()
                self.tab.update_image(self.image.get_current_img())

    def apply_filter(self, func, value=None):
        """Apply a filter from filters/base.py"""
        if value:
            img = getattr(base, func)(self.image.get_current_img(), value)
        else:
            img = getattr(base, func)(self.image.get_current_img())
        self.do_change(img)

    def apply_filter_dialog(self, func, params):
        """Apply a filter from filters/base.py that need a GUI"""
        params_dialog = dialog.params_dialog(self.tab.win, *params)
        value = params_dialog.get_values()
        if value:
            self.apply_filter(func, value)

    def handle_event(self, widget, event, task):
        """Call the event with the needed vars"""
        # Only allow the left mouse button to do actions
        if hasattr(event, 'button') and event.button != 1:
            return
        # Get the good image
        if not self.image.tmp_img:
            img = self.image.get_current_img()
        else:
            img = self.image.tmp_img
        # Handle mouse coords
        if self.tab.zoom_level != 100:
            x, y = event.x, event.y
            x = x * self.tab.width / self.tab.disp_width
            y = y * self.tab.height / self.tab.disp_height
            mouse_coords = [round(x), round(y)]
        else:
            mouse_coords = [round(event.x), round(event.y)]
        # Call the good function to handle the event
        getattr(self, task + '_task')(img.copy(), mouse_coords)

    def press_task(self, img, mouse_coords):
        """Press event"""
        if self.task == 0:
            self.selection = mouse_coords
            self.tab.update_image(img)
        elif (self.task == 1 and self.selection):
            self.move_task(img, mouse_coords)
        elif self.task == 2:
            self.move_task(img, mouse_coords)
        self.left_button_pressed = True

    def move_task(self, img, mouse_coords):
        """Move event"""
        if not self.left_button_pressed:  # need that press_task have been called
            return
        if self.task == 0:
            coords = (self.selection, mouse_coords)
            draw_rectangle(img, coords, 0, outline_color='black')
            self.tab.update_image(img)
        elif self.task == 1:
            self.paste(mouse_coords)
        elif self.task == 2:
            coords = ((mouse_coords[0], mouse_coords[1]),
                (mouse_coords[0], mouse_coords[1]))
            if self.pencil_shape == 'ellipse':
                draw_ellipse(img, coords, self.pencil_size, self.pencil_color)
            elif self.pencil_shape == 'rectangle':
                draw_rectangle(img, coords, self.pencil_size, self.pencil_color)
            self.do_tmp_change(img)

    def release_task(self, img, mouse_coords):
        """Release event"""
        if self.task == 0 and mouse_coords != self.selection:
            self.selection.extend(mouse_coords)
        elif self.task == 1:
            self.do_change(img)
            self.change_task()
            self.selection = list()
        elif self.task == 2:
            self.do_change(img)
        self.left_button_pressed = False

    def copy(self):
        """Copy a part of/or the entire image"""
        img = self.image.get_current_img().copy()
        if len(self.selection) == 4:  # a part of the image is selected
            self.selected_img = img.crop(tuple(self.selection))
        else:  # copy the entire image
            self.selection = [0, 0]
            self.selected_img = img

    def paste(self, mouse_coords=None):
        """Paste the copied image"""
        if self.selected_img:
            if self.task != 1:
                self.change_task('paste')
            if mouse_coords:
                xy = get_middle_mouse(self.selected_img.size, mouse_coords)
            else:
                xy = (0, 0)
            img = self.image.get_current_img().copy()
            img.paste(self.selected_img, xy)
            self.do_tmp_change(img)
            self.selection = list()

    def cut(self):
        """Copy in removing the selected part"""
        self.copy()
        img = self.image.get_current_img().copy()
        blank_img = Image.new(img.mode, self.selected_img.size,
            'rgba(255, 255, 255, 0)')
        img.paste(blank_img, tuple(self.selection[:2]))
        self.do_change(img)
        self.selection = list()

    def crop(self):
        """Crop an image"""
        if self.selection:  # a part of the image is selected
            img = self.image.get_current_img().crop(tuple(self.selection))
            self.do_change(img)

    def save(self):
        """Save the image"""
        if path.isfile(self.image.filename):
            img = self.image.get_current_img()
            img.save(self.image.filename)
            self.image.saved = True
        else:
            self.save_as()

    def save_as(self):
        """Ask where to save the image"""
        filename = dialog.file_dialog(self.tab.win, 'save', path.basename(self.image.filename))
        if filename:
            img = self.image.get_current_img()
            img.save(filename)
            self.tab.win.filenames.append(filename)
            self.image.filename = filename
            self.tab.tab_label.set_title(path.basename(filename))
            self.image.saved = True

    def details(self):
        """Get informations about the image"""
        img_infos = get_infos(self.image.get_current_img(), self.image.filename)
        dialog.details_dialog(self.tab.win, img_infos)

    def close_image(self):
        """Close the image and all its history"""
        self.image.close_all_img()
