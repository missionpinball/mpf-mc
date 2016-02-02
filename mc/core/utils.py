import os
import sys

from mpf.system.case_insensitive_dict import CaseInsensitiveDict
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


def set_position(parent_w, parent_h, w, h, x=None, y=None, anchor_x='center',
                 anchor_y='middle'):
    """Returns the x,y position for the lower-left corner of a widget
    within a larger parent frame based on several positioning parameters.

    Args:
        parent_w: Width of the parent frame.
        parent_h: Height of the parent frame.
        w: Width of the element you're placing.
        h: Height of the element you're placing.
        x: (Optional) Specifies the x (horizontal) position of the widget from
            the left edge of the slide. Can be a numeric value which
            represents the actual x value, or can be a percentage (string with
            percent sign, like '20%') which is set taking into account the size
            of the parent width. (e.g. parent width of 800 with x='20%'
            results in x=160. Can also be negative to position the widget
            partially off the left of the slide. Default value of None will
            return the horizontal center (parent width / 2).
        y: (Optional) Specifies the y (vertical) position of the widget from
            the bottom edge of the slide. Can be a numeric value which
            represents the actual y value, or can be a percentage (string with
            percent sign, like '20%') which is set taking into account the size
            of the parent height. (e.g. parent height of 600 with y='20%'
            results in y=120. Can also be negative to position the widget
            partially off the bottom of the slide. Default value of None will
            return the vertical center (parent height / 2).
        anchor_x: (Optional) Which edge of the widget will be used for
            positioning. ('left', 'center' (or 'middle'), or 'right'. If None,
            'center' will be used.
        anchor_y: (Optional) Which edge of the widget will be used for
            positioning. ('top', 'middle' (or 'center'), or 'bottom'. If None,
            'center' will be used.


    Returns: Tuple of x, y coordinates for the lower-left corner of the
        widget you're placing.

    """

    # Want to force None to be the default too
    if not anchor_x:
        anchor_x = 'center'
    if not anchor_y:
        anchor_y = 'middle'

    # set x/y
    if x is None:
        x = parent_w / 2
    else:
        x = percent_to_float(x, parent_w)

    if y is None:
        y = parent_h / 2
    else:
        y = percent_to_float(y, parent_h)

    # calculate the x/y offsets based on widget size and anchor
    if anchor_x in ('center', 'middle'):
        x += w / -2
    elif anchor_x == 'right':
        x += -w

    if anchor_y in ('middle', 'center'):
        y += h / -2
    elif anchor_y == 'top':
        y += -h

    return x, y


def percent_to_float(number_str, total):
    if str(number_str)[-1] == '%':
        return float(number_str[:-1]) * total / 100
    else:
        return float(number_str)


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
