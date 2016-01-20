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


def set_position(parent_w, parent_h, w, h, x=None, y=None, h_pos=None,
                 v_pos=None):
    """Calculates the x,y position for the upper-left corner of this
    element
    based on several positioning parameters.

    Args:
        v_pos: String which describes the vertical anchor position this
            calculation should be based on. Options include 'top',
            'bottom',
            and 'center' (or 'middle'). Default is 'center' if no `y`
            parameter is given, and 'top' if there is a `y` parameter.
        h_pos: String which describes the horizontal anchor position this
            calculation should be based on. Options include 'left',
            'right',
            and 'center' (or 'middle'). Default is 'center' if no `x`
            parameter is given, and 'left' if there is an `x` parameter.
        x: The x (horizontal value) you'd like to position this element in.
            If this is an positive integer, it will be the number of pixels
            to the left of the h_pos anchor. If it's negative, it will be
            the number of pixels to the right of the h_pos anchor. If this
            is a float between -1.0 and 1.0, then this will be the percent
            between the left edge and the h_pos anchor for positive values,
            and the right edge and the h_pos anchor
            for negative values.
        y: The y (vertical value) you'd like to position this element in.
            If this is an positive integer, it will be the number of pixels
            below the v_pos anchor. If it's negative, it will be
            the number of pixels above the v_pos anchor. If this
            is a float between -1.0 and 1.0, then this will be the percent
            between the bottom edge and the v_pos anchor for positive
            values, and the top edge and the v_pos anchor for negative
            values.

    """

    # First figure out the anchor:
    if not h_pos:
        if x is not None:  # i.e. `if x:`
            h_pos = 'left'
        else:
            h_pos = 'center'

    if not v_pos:
        if y is not None:  # i.e. `if y:`
            v_pos = 'top'
        else:
            v_pos = 'center'

    # Next get the starting point for x, y based on that anchor
    if v_pos == 'bottom':
        final_y = 0
    elif v_pos == 'top':
        final_y = parent_h - h
    elif v_pos == 'center' or v_pos == 'middle':
        final_y = (parent_h - h) / 2
    else:
        raise ValueError('Received invalid v_pos value:', v_pos)

    if h_pos == 'left':
        final_x = 0
    elif h_pos == 'right':
        final_x = parent_w - w
    elif h_pos == 'center' or h_pos == 'middle':
        final_x = (parent_w - w) / 2
    else:
        raise ValueError("Received invalid 'h_pos' value:", h_pos)

    # Finally shift x, y based on values passed.
    if x is not None:
        if -1.0 < x < 1.0:
            final_x += x * parent_w
        else:
            final_x += x

    if y is not None:
        if -1.0 < y < 1.0:
            final_y += y * parent_h
        else:
            final_y += y

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
