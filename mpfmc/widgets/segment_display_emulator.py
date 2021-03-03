"""Widget emulating a segment display."""
from typing import Optional, Union
import math

from kivy.properties import ObjectProperty, NumericProperty, AliasProperty, BooleanProperty, ListProperty
from kivy.graphics import Rectangle, Color, Rotate, Scale

from mpfmc.uix.widget import Widget

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc             # pylint: disable-msg=cyclic-import,unused-import
    from mpfmc.assets.image import ImageAsset   # pylint: disable-msg=cyclic-import,unused-import


class SegmentDisplayEmulatorWidget(Widget):

    """Widget emulating a segment display."""

    widget_type_name = 'SegmentDisplayEmulator'
    merge_settings = ('height', 'width')
    animation_properties = ('x', 'y', 'scale', 'opacity')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        super().__init__(mc=mc, config=config, key=key)
        pass

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
        del args

        if self.canvas is None:
            return

    @staticmethod
    def _flip_horizontal(points, width):
        flipped_points = []

        for index in range(0, len(points), 2):
            flipped_points.append(width - points[index])
            flipped_points.append(points[index + 1])

        return flipped_points

    @staticmethod
    def _flip_vertical(points, height):
        flipped_points = []

        for index in range(0, len(points), 2):
            flipped_points.append(points[index])
            flipped_points.append(height - points[index + 1])

        return flipped_points

    def _calculate_segment_points(self):
        """Calculate the points of all the display segments to be drawn."""

        # The code in this module is based on an open source sixteen segment display project:
        # https://github.com/Enderer/sixteensegment

        # Calculate the size dimensions of a single character/element in the display
        char_height = self.height - (self.padding * 2)
        char_width = (self.character_spacing * (self.character_count - 1) - (self.padding * 2)) / self.character_count

        segment_width = self.segment_width * char_width
        segment_interval = self.segment_interval * char_width
        bevel_width = self.bevel_width * char_width
        side_bevel_multiplier = 1 if self.side_bevel_enabled else 0

        segment_factor = segment_width * 0.8
        diagonal_slope = char_height / char_width
        sqrt2 = math.sqrt(2)
        sqrt3 = math.sqrt(3)

        # Base positions of points without bevel and interval
        x0 = char_width / 2 - segment_width / 2
        x1 = char_width / 2
        x2 = char_width / 2 + segment_width / 2
        x3 = char_width - segment_width
        x4 = char_width - segment_width / 2
        x5 = char_width

        y0 = 0
        y1 = segment_width / 2
        y2 = segment_width
        y3 = char_height / 2 - segment_width / 2
        y4 = char_height / 2
        y5 = char_height / 2 + segment_width / 2

        # Create dictionary of segment points keyed by segment name/letter
        segment_points = {"a": [bevel_width * 2 + segment_interval / sqrt2, y0,
                                x5 - (bevel_width * 2 + segment_interval / sqrt2), y0,
                                x5 - (bevel_width + segment_interval / sqrt2), y1,
                                x5 - (bevel_width * 2 + segment_interval / sqrt2), y2,
                                bevel_width * 2 + segment_interval / sqrt2, y2,
                                bevel_width + segment_interval / sqrt2, y1],
                          "g2": [x1 + segment_interval / 2, y3,
                                 x3 - segment_interval / 2 * sqrt3, y3,
                                 x4 - segment_interval / 2 * sqrt3, y4,
                                 x3 - segment_interval / 2 * sqrt3, y5,
                                 x1 + segment_interval / 2, y5],
                          "b": [x5, y0 + bevel_width * 2 + segment_interval / sqrt2,
                                x5, y4 - segment_interval / 2 - segment_width / 2 * side_bevel_multiplier,
                                x4, y4 - segment_interval / 2,
                                x3, y3 - segment_interval / 2,
                                x3, y2 + segment_interval / sqrt2,
                                x5 - bevel_width, y0 + bevel_width + segment_interval / sqrt2],
                          "j": [x2, y2 + segment_interval,
                                x2, y3 - segment_interval,
                                x0, y3 - segment_interval,
                                x0, y2 + segment_interval],
                          "h": [(segment_width + segment_factor) / diagonal_slope + segment_interval,
                                y2 + segment_interval,
                                x0 - segment_interval, x0 * diagonal_slope - segment_factor - segment_interval,
                                x0 - segment_interval, y3 - segment_interval,
                                (y3 - segment_interval) / diagonal_slope - segment_interval, y3 - segment_interval,
                                segment_width + segment_interval,
                                y2 * diagonal_slope + segment_factor + segment_interval,
                                segment_width + segment_interval, y2 + segment_interval]}

        # Create the rest of the segments by flipping/mirroring existing points (either horizontally or vertically)
        segment_points["c"] = self._flip_vertical(segment_points["b"], char_height)
        segment_points["d"] = self._flip_vertical(segment_points["a"], char_height)
        segment_points["e"] = self._flip_horizontal(segment_points["c"], char_width)
        segment_points["f"] = self._flip_horizontal(segment_points["b"], char_width)
        segment_points["g1"] = self._flip_horizontal(segment_points["g2"], char_width)
        segment_points["k"] = self._flip_horizontal(segment_points["h"], char_width)
        segment_points["l"] = self._flip_vertical(segment_points["h"], char_height)
        segment_points["m"] = self._flip_vertical(segment_points["j"], char_height)
        segment_points["n"] = self._flip_vertical(segment_points["k"], char_height)

        # Determine if characters are slanted
        if self.character_slant_angle < 0.0:
            slant_angle_radians = self.character_slant_angle * math.pi / 180.0
            slant_opposite_angle_radians = (90 - self.character_slant_angle) * math.pi / 180.0
            slant_horizontal_distance = char_height * math.sin(slant_angle_radians) / math.sin(
                slant_opposite_angle_radians)

            slant_slope = char_height / slant_horizontal_distance
            # TODO: implement slant on all x coordinates
            #  (use the slant slope to calculate x-coordinate offset based on y-coordinate

        # TODO: determine dot/period (dp) and comma (com) coordinates
        #  (comma should fit in padding on right side of character/element)
    
    #
    # Properties
    #

    rotation = NumericProperty(0)
    '''Rotation angle value of the widget.

    :attr:`rotation` is an :class:`~kivy.properties.NumericProperty` and defaults to
    0.
    '''

    scale = NumericProperty(1.0)
    '''Scale value of the widget.

    :attr:`scale` is an :class:`~kivy.properties.NumericProperty` and defaults to
    1.0.
    '''

    character_count = NumericProperty(1)
    '''The number of display characters in the segment display.

    :attr:`character_count` is an :class:`~kivy.properties.NumericProperty` and defaults to 1.
    '''

    character_slant_angle = NumericProperty(16)
    '''The angle at which the characters are slanted (degrees from vertical)

    :attr:`character_slant_angle` is an :class:`~kivy.properties.NumericProperty` and defaults to 16.
    '''

    character_spacing = NumericProperty(5)
    '''The space between each character/element.

    :attr:`character_spacing` is an :class:`~kivy.properties.NumericProperty` and defaults to 5.
    '''

    padding = NumericProperty(10)
    '''The padding around the display.

    :attr:`padding` is an :class:`~kivy.properties.NumericProperty` and defaults to 10.
    '''

    segment_width = NumericProperty(0.16)
    '''Width of each segment (as a percentage of character/element width).

    :attr:`segment_width` is an :class:`~kivy.properties.NumericProperty` and defaults to 0.16.
    '''

    segment_interval = NumericProperty(0.05)
    '''Spacing between segments (as a percentage of character/element width).

    :attr:`segment_interval` is an :class:`~kivy.properties.NumericProperty` and defaults to 0.05.
    '''

    bevel_width = NumericProperty(0.06)
    '''Size of bevels (as a percentage of character/element width).

    :attr:`bevel_width` is an :class:`~kivy.properties.NumericProperty` and defaults to 0.06.
    '''

    side_bevel_enabled = BooleanProperty(True)
    '''Determines if the sides should be beveled
    
    :attr:`side_bevel_enabled` is an :class:`kivy.properties.BooleanProperty` and defaults to True.
    '''

    segment_off_color = ListProperty([0.588, 0.596, 0.584, 1.0])
    '''The color of a segment that is off, in the (r, g, b, a) format.

    :attr:`segment_off_color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [0.588, 0.596, 0.584, 1.0].
    '''

    segment_on_color = ListProperty([0.867, 0.510, 0.090, 1.0])
    '''The color of a segment that is on, in the (r, g, b, a) format.

    :attr:`segment_on_color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [0.867, 0.510, 0.090, 1.0].
    '''

    dot_enabled = BooleanProperty(False)
    '''Determines if an integrated dot/period should be displayed

    :attr:`dot_enabled` is an :class:`kivy.properties.BooleanProperty` and defaults to False.
    '''

    comma_enabled = BooleanProperty(False)
    '''Determines if an integrated comma should be displayed

    :attr:`comma_enabled` is an :class:`kivy.properties.BooleanProperty` and defaults to False.
    '''


