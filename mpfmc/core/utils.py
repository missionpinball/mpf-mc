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


def center_of_points_list(points: list) -> tuple:
    """Calculates the center (average) of points in a list."""

    # Extract all x coordinates from list of points (odd list positions)
    coordinates_x = points[::2]

    # Extract all y coordinates from list of points (even list positions)
    coordinates_y = points[1::2]

    return sum(coordinates_x) / len(coordinates_x), sum(coordinates_y) / len(coordinates_y)
