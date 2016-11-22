import os
import sys

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util


# pylint: disable-msg=too-many-arguments
# pylint: disable-msg=too-many-statements
def set_position(parent_w, parent_h, w, h, x=None, y=None,
                 anchor_x=None, anchor_y=None, adjust_top=None,
                 adjust_right=None, adjust_bottom=None, adjust_left=None):
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
            return the horizontal center (parent width / 2). Can also start
            with the strings "left", "center", or "right" which can be combined
            with values. (e.g right-2, left+4, center-1)
        y: (Optional) Specifies the y (vertical) position of the widget from
            the bottom edge of the slide. Can be a numeric value which
            represents the actual y value, or can be a percentage (string with
            percent sign, like '20%') which is set taking into account the size
            of the parent height. (e.g. parent height of 600 with y='20%'
            results in y=120. Can also be negative to position the widget
            partially off the bottom of the slide. Default value of None will
            return the vertical center (parent height / 2). Can also start
            with the strings "top", "middle", or "bottom" which can be combined
            with values. (e.g top-2, bottom+4, middle-1)
        anchor_x: (Optional) Which edge of the widget will be used for
            positioning. ('left', 'center' (or 'middle'), or 'right'. If None,
            'center' will be used.
        anchor_y: (Optional) Which edge of the widget will be used for
            positioning. ('top', 'middle' (or 'center'), or 'bottom'. If None,
            'center' will be used.
        adjust_top: (Optional) Moves the "top" of this widget down, meaning any
            positioning that includes calculations involving the top (anchor_y
            of 'top' or 'middle') use the alternate top position. Postive
            values move the top towards the center of the widget, negative
            values move it away. Negative values can be used to give the
            widget "space" on the top, and positive values can be used to
            remove unwanted space from the top of the widget. Note that this
            setting does not actually crop or cut off the top of the widget,
            rather, it just adjusts how the positioning is calculated.
        adjust_right: (Optional) ajusts the position calculations for the
            right side of the widget. Positive values move the right position
            towards the center, negative values move it away from the center.
        adjust_bottom: (Optional) ajusts the position calculations for the
            bottom of the widget. Positive values move the bottom position
            towards the center, negative values move it away from the center.
        adjust_left: (Optional) ajusts the position calculations for the
            left side of the widget. Positive values move the left position
            towards the center, negative values move it away from the center.

    Returns: Tuple of x, y coordinates for the lower-left corner of the
        widget you're placing.

    See the widgets documentation for examples.

    """
    # Set defaults
    if x is None:
        x = 'center'
    if not anchor_x:
        anchor_x = 'center'
    if y is None:
        y = 'middle'
    if not anchor_y:
        anchor_y = 'middle'
    if not adjust_top:
        adjust_top = 0
    if not adjust_right:
        adjust_right = 0
    if not adjust_bottom:
        adjust_bottom = 0
    if not adjust_left:
        adjust_left = 0

    # ----------------------
    # X / width / horizontal
    # ----------------------

    # Set position
    if isinstance(x, str):

        x = str(x).replace(' ','')
        start_x = 0

        if x.startswith('right'):
            x = x.strip('right')
            start_x = parent_w

        elif x.startswith('middle'):
            x = x.strip('middle')
            start_x = parent_w / 2

        elif x.startswith('center'):
            x = x.strip('center')
            start_x = parent_w / 2

        elif x.startswith('left'):
            x = x.strip('left')

        if not x:
            x = '0'

        x = percent_to_float(x, parent_w)
        x += start_x

    # Adjust for anchor_x & adjust_right/left
    if anchor_x in ('center', 'middle'):
        x -= (w - adjust_right + adjust_left) / 2
    elif anchor_x == 'right':
        x -= w - adjust_right
    else:  # left
        x -= adjust_left

    # --------------------
    # Y / height / vertical
    # --------------------

    # Set position
    if isinstance(y, str):

        y = str(y).replace(' ', '')
        start_y = 0

        if y.startswith('top'):
            y = y.strip('top')
            start_y = parent_h

        elif y.startswith('middle'):
            y = y.strip('middle')
            start_y = parent_h / 2

        elif y.startswith('center'):
            y = y.strip('center')
            start_y = parent_h / 2

        elif y.startswith('bottom'):
            y = y.strip('bottom')

        if not y:
            y = '0'

        y = percent_to_float(y, parent_h)
        y += start_y

    # Adjust for anchor_y & adjust_top/bottom
    if anchor_y in ('middle', 'center'):
        y -= (h - adjust_top + adjust_bottom) / 2
    elif anchor_y == 'top':
        y -= h - adjust_top
    else:  # bottom
        y -= adjust_bottom

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
    if machine_path.startswith('/') or machine_path.startswith('\\'):
        machine_path = machine_path
    else:
        machine_path = os.path.join(machine_files_default, machine_path)

    machine_path = os.path.abspath(machine_path)

    # Add the machine folder to sys.path so we can import modules from it
    if machine_path not in sys.path:
        sys.path.append(machine_path)

    return machine_path


def load_machine_config(config_file_list, machine_path,
                        config_path='config', existing_config=None):

    machine_config = dict()

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
            ConfigProcessor.load_config_file(config_file, 'machine', ignore_unknown_sections=True))

    return machine_config
