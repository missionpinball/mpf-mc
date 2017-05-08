import os
import sys

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util


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


def center_of_points_list(points: list) -> tuple:
    """Calculates the center (average) of points in a list."""

    # Extract all x coordinates from list of points (odd list positions)
    coordinates_x = points[::2]

    # Extract all y coordinates from list of points (even list positions)
    coordinates_y = points[1::2]

    return sum(coordinates_x) / len(coordinates_x), sum(coordinates_y) / len(coordinates_y)
