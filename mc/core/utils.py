import os
import sys

from mpf.system.config import CaseInsensitiveDict
from mpf.system.config import Config as MpfConfig
from mpf.system.utility_functions import Util


def get_insert_index(z, target_widget):
    index = 0

    # this might be able to be a count of a list comprehension or something

    for i, w in enumerate(target_widget.children):

        try:
            if w.config['z'] <= z:
                index = i + 1
                # need to increment index until we hit the next priority
                if z < w.config['z']:
                    break

                    # BTW I have no idea why this simpler code doesn't
                    # work:
                    # for i, w in enumerate(self.children):
                    #     if w.config['z'] > my_priority:
                    #         index = i
                    #         break
        except TypeError:
            # have to save to index in case this is the last loop
            index = i + 1

    return index


def set_position(parent_w, parent_h, w, h, x=0, y=0, h_pos='center',
                 v_pos='center', anchor_x=None, anchor_y=None):
    """Returns the x,y position for the lower-left corner of a widget
    within a larger parent frame based on several positioning parameters.

    Args:
        parent_w: Width of the parent frame.
        parent_h: Height of the parent frame.
        w: Width of the element you're placing.
        h: Height of the element you're placing.
        x: (Optional) shifts the x (horizontal) position. If x is a
            number (int or float) then it will move the widget +/- that many
            pixels (+ is right, - is left). If x is a string ending in a
            percent sign (e.g. "80%"), then it will move the widget +/- that
            percent of the slide's width. (e.g. 10% for a slide with a width of
            800px will position the widget 80px to the right of where it would
            otherwise be placed based on the h_pos and align_x values. The
            default value is '0' which does not shift the widget.
        y: (Optional) shifts the y (vertical) position. If y is a
            number (int or float) then it will move the widget +/- that many
            pixels (+ is up, - is down). If y is a string ending in a
            percent sign (e.g. "80%"), then it will move the widget +/- that
            percent of the slide's height. (e.g. 10% for a slide with a
            height of 600px will position the widget 60px above of where it
            would otherwise be placed based on the v_pos and align_y values.
            The default value is '0' which does not shift the widget.
        h_pos: (Optional) String which describes the horizontal position in the
            parent frame this widget will be placed. Options include 'left',
            'right', and 'center' (or 'middle'). Default is 'center'.
        v_pos: (Optional) String which describes the vertical position in the
            parent frame this widget will be placed. Options include 'top',
            'bottom', and 'center' (or 'middle'). Default is 'center'.
        anchor_x: (Optional) Which edge of the widget will be used for
            positioning. If not specified, it will be set to match the 'h_pos'
            value.
        anchor_y: (Optional) Which edge of the widget will be used for
            positioning. If not specified, it will be set to match the 'v_pos'
            value.


    Returns: Tuple of x, y coordinates for the lower-left corner of the
        widget you're placing.

    """

    # Set the anchors. The idea is that if a pos is set but not an anchor, the
    # intention is that they should be the same. e.g. v_pos = top means the
    # anchor should also be 'top

    if not v_pos:
        v_pos = 'center'
    if not h_pos:
        h_pos = 'center'
    if not anchor_x:
        anchor_x = h_pos
    if not anchor_y:
        anchor_y = v_pos

    # set the initial final position based on those anchors

    final_x = 0
    final_y = 0

    if v_pos in ('center', 'middle'):
        final_y = parent_h / 2

    elif v_pos == 'top':
        final_y = parent_h

    if h_pos in ('center', 'middle'):
        final_x = parent_w / 2

    elif h_pos == 'right':
        final_x = parent_w

    # apply the x/y values to those positions

    if not x:
        x = 0
    if not y:
        y = 0

    if str(x)[-1] == '%':
        if h_pos == 'left':
            final_x = (float(x[:-1]) * parent_w / 100) - final_x
        elif h_pos in ('center', 'middle'):
            final_x = (float(x[:-1]) * (parent_w - final_x) / 100)
        elif h_pos == 'right':
            final_x = ((float(x[:-1]) * parent_w / 100) - final_x) * -1

    else:
        final_x += float(x)

    if str(y)[-1] == '%':
        if v_pos == 'bottom':
            final_y = (float(y[:-1]) * parent_h / 100) - final_y
        elif v_pos in ('center', 'middle'):
            final_y = (float(y[:-1]) * (parent_h - final_y) / 100)
        elif v_pos == 'top':
            final_y = ((float(y[:-1]) * parent_h / 100) - final_y) * -1
    else:
        final_y += float(y)

    # calculate and apply the offsets based on the anchors

    x_offset = 0
    y_offset = 0

    if anchor_x in ('center', 'middle'):
        x_offset = w / -2
    elif anchor_x == 'right':
        x_offset = -w

    if anchor_y in ('center', 'middle'):
        y_offset = h / -2
    elif anchor_y == 'top':
        y_offset = -h

    final_x += x_offset
    final_y += y_offset

    return final_x, final_y


def set_machine_path(machine_path, machine_files_default='machine_files'):
    # If the machine folder value passed starts with a forward or
    # backward slash, then we assume it's from the mpf root. Otherwise we
    # assume it's in the mpf/machine_files folder
    if (machine_path.startswith('/') or machine_path.startswith('\\')):
        machine_path = machine_path
    else:
        machine_path = os.path.join(machine_files_default, machine_path)

    machine_path = os.path.abspath(machine_path)

    # Add the machine folder to sys.path so we can import modules from it
    sys.path.append(machine_path)
    return machine_path


def load_machine_config(config_file_list, machine_path,
                        config_path='config', existing_config=None):
    for num, config_file in enumerate(config_file_list):

        if not existing_config:
            machine_config = CaseInsensitiveDict()
        else:
            machine_config = existing_config

        if not (config_file.startswith('/') or
                    config_file.startswith('\\')):
            config_file = os.path.join(machine_path, config_path,
                                       config_file)

        machine_config = Util.dict_merge(machine_config,
                                         MpfConfig.load_config_file(
                                                 config_file))

    return machine_config
