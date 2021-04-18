"""Widget emulating a segment display."""
from typing import Optional, List, Dict, Any
import math

from kivy.clock import Clock
from kivy.graphics.vertex_instructions import Mesh, Ellipse, Rectangle
from kivy.properties import NumericProperty, BooleanProperty, ListProperty, StringProperty, OptionProperty
from kivy.graphics import Color, Rotate, Scale
from kivy.utils import get_color_from_hex

from mpfmc.uix.widget import Widget
from mpf.core.segment_mappings import FOURTEEN_SEGMENTS, SEVEN_SEGMENTS

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc             # pylint: disable-msg=cyclic-import,unused-import

# Constants for punctuation segments (dot/period and comma)
OFF = 0


class SegmentDisplayEmulator(Widget):

    """Widget emulating a segment display."""

    widget_type_name = 'SegmentDisplayEmulator'
    merge_settings = ('height', 'width')
    animation_properties = ('x', 'y', 'scale', 'width', 'height', 'opacity', 'rotation', 'segment_on_color')

    display_instances = []

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        super().__init__(mc=mc, config=config, key=key)

        # Initialize the character segment map with the default 14-segment mappings from MPF
        if self.display_type == "7seg":
            self._segment_map = {k: self.get_seven_segment_character_encoding(v) for k, v in SEVEN_SEGMENTS.items()}
            self._segment_count = 7
            self._dot_segment_index = 0
            self._comma_segment_index = 7
        elif self.display_type == "14seg":
            self._segment_map = {k: self.get_fourteen_segment_character_encoding(v) for k, v in
                                 FOURTEEN_SEGMENTS.items()}
            self._segment_count = 14
            self._dot_segment_index = 14
            self._comma_segment_index = 15

        # Override default character segment mappings with specific settings
        if "character_map" in self.config and self.config["character_map"] is not None:
            for k, v in self.config["character_map"].items():
                self._segment_map[k] = v

        # Initialize the encoded display characters
        self._encoded_characters = [OFF] * self.character_count

        self._flash_clock_event = None
        self._apply_flash_mask = False
        self._flash_character_mask = [0xFF] * self.character_count
        self._segment_colors = None
        self._segment_mesh_objects = None
        self._update_event_handler_key = None

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(text=self._update_text,
                  flash_mode=self._set_flash_mode,
                  pos=self._draw_widget,
                  size=self._draw_widget,
                  background_color=self._draw_widget,
                  segment_off_color=self._draw_widget,
                  segment_on_color=self._draw_widget)

        self._calculate_segment_points()
        self._update_text()
        self._set_flash_mode()

        self._update_event_handler_key = self.mc.events.add_handler(
            "update_segment_display",
            self.on_update_segment_display)

    def prepare_for_removal(self) -> None:
        """Prepare the widget to be removed."""
        if self._update_event_handler_key:
            self.mc.events.remove_handler_by_key(self._update_event_handler_key)
            self._update_event_handler_key = None

        # important to call base class to ensure the widget gets removed
        super().prepare_for_removal()

    @staticmethod
    def get_seven_segment_character_encoding(segments: SEVEN_SEGMENTS) -> int:
        """Returns segment value in order used in the segment display widget."""
        # Note: the l and n segments appear to be swapped in the encodings in the FOURTEEN_SEGMENTS dict
        return int(
            (segments.g << 6) | (segments.f << 5) | (segments.e << 4) |
            (segments.d << 3) | (segments.c << 2) | (segments.b << 1) | segments.a)

    @staticmethod
    def get_fourteen_segment_character_encoding(segments: FOURTEEN_SEGMENTS) -> int:
        """Returns segment value in order used in the segment display widget."""
        # Note: the l and n segments appear to be swapped in the encodings in the FOURTEEN_SEGMENTS dict
        return int(
            (segments.dp << 14) | (segments.l << 13) | (segments.m << 12) |
            (segments.n << 11) | (segments.k << 10) | (segments.j << 9) | segments.h << 8 |
            (segments.g2 << 7) | (segments.g1 << 6) | (segments.f << 5) | (segments.e << 4) |
            (segments.d << 3) | (segments.c << 2) | (segments.b << 1) | segments.a)

    @staticmethod
    def _flip_horizontal(points, width):
        """Flips the supplied points over the horizontal symmetry line"""
        flipped_points = []

        for index in range(0, len(points), 2):
            flipped_points.append(width - points[index])
            flipped_points.append(points[index + 1])

        return flipped_points

    @staticmethod
    def _flip_vertical(points, height):
        """Flips the supplied points over the vertical symmetry line"""
        flipped_points = []

        for index in range(0, len(points), 2):
            flipped_points.append(points[index])
            flipped_points.append(height - points[index + 1])

        return flipped_points

    @staticmethod
    def _apply_character_slant_to_points(points, slant_slope):
        """Applies slant to x-coordinates of segment points"""
        modified_points = []

        for index in range(0, len(points), 2):
            modified_points.append(points[index] + slant_slope * points[index + 1])
            modified_points.append(points[index + 1])

        return modified_points

    def _calculate_segment_points(self):
        """Calculate the points of all the display segments to be drawn."""

        # The coordinate calculations in this module are based on an open source sixteen segment display project:
        # https://github.com/Enderer/sixteensegment

        # Calculate the size dimensions of a single character/element in the display
        self.char_height = self.height - (self.padding * 2)

        # Determine if characters are slanted
        if self.character_slant_angle > 0.0:
            # Use some basic triangle trigonometry to determine the distance the letters are slanted at the top
            slant_angle_radians = self.character_slant_angle * math.pi / 180.0
            slant_opposite_angle_radians = (90 - self.character_slant_angle) * math.pi / 180.0
            slant_horizontal_distance = self.char_height * math.sin(slant_angle_radians) / math.sin(
                slant_opposite_angle_radians)

            # Calculate the slope of the slanted vertical line segments
            slant_slope = slant_horizontal_distance / self.char_height

            # Padding must be greater than or equal to slant_horizontal_distance
            if self.character_spacing < slant_horizontal_distance:
                self.character_spacing = slant_horizontal_distance
        else:
            slant_slope = 0

        # Calculate the width of each character (from corner to corner, not including spacing and padding)
        self.char_width = (self.width - self.character_spacing * (self.character_count - 1) - (
                self.padding * 2)) / self.character_count

        segment_width = self.segment_width * self.char_width
        segment_interval = self.segment_interval * self.char_width
        bevel_width = self.bevel_width * self.char_width

        # Base positions of points without bevel and interval
        x = [self.char_width / 2 - segment_width / 2,
             self.char_width / 2,
             self.char_width / 2 + segment_width / 2,
             self.char_width - segment_width,
             self.char_width - segment_width / 2,
             self.char_width]

        y = [0,
             segment_width / 2,
             segment_width,
             self.char_height / 2 - segment_width / 2,
             self.char_height / 2,
             self.char_height / 2 + segment_width / 2]

        if self.display_type == "14seg":
            segment_points = self._calculate_fourteen_segment_points(x, y, segment_width, segment_interval, bevel_width)
        elif self.display_type == "7seg":
            segment_points = self._calculate_seven_segment_points(x, y, segment_width, segment_interval, bevel_width)

        # Sort the segment dictionary by segment name (key)
        segment_points = {key: value for key, value in sorted(segment_points.items(), key=lambda item: item[0])}

        if self.dot_enabled:
            # Store center point of dot/period circle (diameter will be segment_width) (x, y, radius)
            self._dot_points = [self.char_width + segment_width / 2, 0, segment_width]

        if self.comma_enabled:
            #  (comma should fit in padding on right side of character/element)
            self._comma_points = [self.char_width + 0.5 * segment_width, -0.5 * segment_interval,
                                  self.char_width + 0.75 * segment_width, -1.5 * segment_interval,
                                  self.char_width + segment_width, -2.5 * segment_interval,
                                  self.char_width + 1.25 * segment_width, -1.5 * segment_interval,
                                  self.char_width + 1.5 * segment_width, -0.5 * segment_interval,
                                  self.char_width + 1.4 * segment_width, -0.75 * segment_width,
                                  self.char_width + 0.5 * segment_width, -2 * segment_width,
                                  self.char_width + 0.8 * segment_width, -0.5 * segment_width]

        # Determine if characters are slanted (if so, apply slant translation)
        if self.character_slant_angle > 0.0:
            segment_points.update(
                {k: self._apply_character_slant_to_points(v, slant_slope) for k, v in segment_points.items()})
            if self.comma_enabled:
                self._comma_points = self._apply_character_slant_to_points(self._comma_points, slant_slope)

        self._segment_points = list(segment_points.values())

    def _calculate_seven_segment_points(self, x: List[float], y: List[float],
                                        segment_width: float, segment_interval: float,
                                        bevel_width: float) -> Dict[str, float]:
        """Calculate the vertices for all segments in a seven-segment display."""

        side_bevel_multiplier = 1 if self.side_bevel_enabled else 0

        segment_factor = segment_width * 0.8
        diagonal_slope = self.char_height / self.char_width
        sqrt2 = math.sqrt(2)
        sqrt3 = math.sqrt(3)

        # Create dictionary of segment points keyed by segment name/letter
        segment_points = {"d": [bevel_width * 2 + segment_interval / sqrt2, y[0],
                                x[5] - (bevel_width * 2 + segment_interval / sqrt2), y[0],
                                x[5] - (bevel_width + segment_interval / sqrt2), y[1],
                                x[5] - (bevel_width * 2 + segment_interval / sqrt2), y[2],
                                bevel_width * 2 + segment_interval / sqrt2, y[2],
                                bevel_width + segment_interval / sqrt2, y[1]],
                          "g": [segment_width + segment_interval / 2 * sqrt3, y[3],
                                x[3] - segment_interval / 2 * sqrt3, y[3],
                                x[4] - segment_interval / 2 * sqrt3, y[4],
                                x[3] - segment_interval / 2 * sqrt3, y[5],
                                segment_width / 2 + segment_interval / 2 * sqrt3, y[5],
                                segment_width + segment_interval / 2 * sqrt3, y[4]],
                          "c": [x[5], y[0] + bevel_width * 2 + segment_interval / sqrt2,
                                x[5], y[4] - segment_interval / 2 - segment_width / 2 * side_bevel_multiplier,
                                x[4], y[4] - segment_interval / 2,
                                x[3], y[3] - segment_interval / 2,
                                x[3], y[2] + segment_interval / sqrt2,
                                x[5] - bevel_width, y[0] + bevel_width + segment_interval / sqrt2]}

        # Create the rest of the segments by flipping/mirroring existing points (either horizontally or vertically)
        segment_points["a"] = self._flip_vertical(segment_points["d"], self.char_height)
        segment_points["b"] = self._flip_vertical(segment_points["c"], self.char_height)
        segment_points["e"] = self._flip_horizontal(segment_points["c"], self.char_width)
        segment_points["f"] = self._flip_horizontal(segment_points["b"], self.char_width)

        return segment_points

    def _calculate_fourteen_segment_points(self, x: List[float], y: List[float],
                                           segment_width: float, segment_interval: float,
                                           bevel_width: float) -> Dict[str, float]:
        """Calculate the vertices for all segments in a fourteen-segment display."""

        side_bevel_multiplier = 1 if self.side_bevel_enabled else 0

        segment_factor = segment_width * 0.8
        diagonal_slope = self.char_height / self.char_width
        sqrt2 = math.sqrt(2)
        sqrt3 = math.sqrt(3)

        # Create dictionary of segment points keyed by segment name/letter
        segment_points = {"d": [bevel_width * 2 + segment_interval / sqrt2, y[0],
                                x[5] - (bevel_width * 2 + segment_interval / sqrt2), y[0],
                                x[5] - (bevel_width + segment_interval / sqrt2), y[1],
                                x[5] - (bevel_width * 2 + segment_interval / sqrt2), y[2],
                                bevel_width * 2 + segment_interval / sqrt2, y[2],
                                bevel_width + segment_interval / sqrt2, y[1]],
                          "g2": [x[1] + segment_interval / 2, y[3],
                                 x[3] - segment_interval / 2 * sqrt3, y[3],
                                 x[4] - segment_interval / 2 * sqrt3, y[4],
                                 x[3] - segment_interval / 2 * sqrt3, y[5],
                                 x[1] + segment_interval / 2, y[5]],
                          "c": [x[5], y[0] + bevel_width * 2 + segment_interval / sqrt2,
                                x[5], y[4] - segment_interval / 2 - segment_width / 2 * side_bevel_multiplier,
                                x[4], y[4] - segment_interval / 2,
                                x[3], y[3] - segment_interval / 2,
                                x[3], y[2] + segment_interval / sqrt2,
                                x[5] - bevel_width, y[0] + bevel_width + segment_interval / sqrt2],
                          "m": [x[2], y[2] + segment_interval,
                                x[2], y[3] - segment_interval,
                                x[0], y[3] - segment_interval,
                                x[0], y[2] + segment_interval],
                          "l": [(segment_width + segment_factor) / diagonal_slope + segment_interval,
                                y[2] + segment_interval,
                                x[0] - segment_interval, x[0] * diagonal_slope - segment_factor - segment_interval,
                                x[0] - segment_interval, y[3] - segment_interval,
                                (y[3] - segment_interval) / diagonal_slope - segment_interval, y[3] - segment_interval,
                                segment_width + segment_interval,
                                y[2] * diagonal_slope + segment_factor + segment_interval,
                                segment_width + segment_interval, y[2] + segment_interval]}

        # Create the rest of the segments by flipping/mirroring existing points (either horizontally or vertically)
        segment_points["a"] = self._flip_vertical(segment_points["d"], self.char_height)
        segment_points["b"] = self._flip_vertical(segment_points["c"], self.char_height)
        segment_points["e"] = self._flip_horizontal(segment_points["c"], self.char_width)
        segment_points["f"] = self._flip_horizontal(segment_points["b"], self.char_width)
        segment_points["g1"] = self._flip_horizontal(segment_points["g2"], self.char_width)
        segment_points["h"] = self._flip_vertical(segment_points["l"], self.char_height)
        segment_points["j"] = self._flip_vertical(segment_points["m"], self.char_height)
        segment_points["k"] = self._flip_horizontal(segment_points["h"], self.char_width)
        segment_points["n"] = self._flip_horizontal(segment_points["l"], self.char_width)

        return segment_points

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
        del args

        if self.canvas is None:
            return

        self.canvas.clear()
        self._segment_colors = []
        self._segment_mesh_objects = []

        # Get the list of encoded characters (apply flash mask if applicable)
        encoded_characters = [
            self._encoded_characters[index] & self._flash_character_mask[index] if self._apply_flash_mask else
            self._encoded_characters[index] for index in range(len(self._encoded_characters))]

        with self.canvas:
            Color(*self.background_color)
            Scale(self.scale, origin=self.center)
            Rotate(angle=self.rotation, origin=self.center)

            # Fill background
            Rectangle(pos=self.pos, size=self.size)

            x_offset = self.x + self.padding
            y_offset = self.y + self.padding

            for encoded_char in encoded_characters:

                colors = [None] * (self._segment_count + 2)
                mesh_objects = [None] * self._segment_count
                for segment in range(self._segment_count):
                    colors[segment] = self._create_segment_color(segment, encoded_char)
                    mesh_objects[segment] = self._create_segment_mesh_object(segment, x_offset, y_offset)

                self._segment_colors.append(colors)
                self._segment_mesh_objects.append(mesh_objects)
                if self.dot_enabled:
                    colors[self._dot_segment_index] = self._create_segment_color(self._dot_segment_index, encoded_char)
                    Ellipse(pos=(self._dot_points[0] + x_offset, self._dot_points[1] + y_offset),
                            size=(self._dot_points[2], self._dot_points[2]))

                if self.comma_enabled:
                    colors[self._comma_segment_index] = self._create_segment_color(self._comma_segment_index, encoded_char)
                    Mesh(vertices=[self._comma_points[0] + x_offset, self._comma_points[1] + y_offset, 0, 0,
                                   self._comma_points[2] + x_offset, self._comma_points[3] + y_offset, 0, 0,
                                   self._comma_points[4] + x_offset, self._comma_points[5] + y_offset, 0, 0,
                                   self._comma_points[6] + x_offset, self._comma_points[7] + y_offset, 0, 0,
                                   self._comma_points[8] + x_offset, self._comma_points[9] + y_offset, 0, 0,
                                   self._comma_points[10] + x_offset, self._comma_points[11] + y_offset, 0, 0,
                                   self._comma_points[12] + x_offset, self._comma_points[13] + y_offset, 0, 0,
                                   self._comma_points[14] + x_offset, self._comma_points[15] + y_offset, 0, 0],
                         indices=[0, 1, 2, 3, 4, 5, 6, 7],
                         mode="triangle_fan")

                x_offset += self.char_width + self.character_spacing

    def on_update_segment_display(self, segment_display_name: Any, **kwargs):
        """Event handler method to update the segment display."""
        if segment_display_name == self.config['name']:
            if 'text' in kwargs:
                self.text = kwargs['text']
            if 'color' in kwargs:
                self.segment_on_color = get_color_from_hex(kwargs['color'].pop())
                pass
            # todo: update flash

    def _update_text(self, *args):
        """Process the new text value to prepare it for display"""
        self._encoded_characters = self.encode_characters(self.text, self.character_count, self._segment_map,
                                                          self.dot_enabled, 1 << self._dot_segment_index,
                                                          self.comma_enabled, 1 << self._comma_segment_index)
        self._draw_widget()

    def _create_segment_color(self, segment: int, char_code: int):
        """Creates a Color vertex instruction for the specified segment number"""
        if (1 << segment) & char_code:
            return Color(self.segment_on_color[0], self.segment_on_color[1], self.segment_on_color[2],
                         self.segment_on_color[3])
        else:
            return Color(self.segment_off_color[0], self.segment_off_color[1], self.segment_off_color[2],
                         self.segment_off_color[3])

    def _create_segment_mesh_object(self, segment, x_offset, y_offset):
        """Creates a Mesh vertex instruction for the specified segment number"""
        points = self._segment_points[segment]
        vertices = []
        indices = []
        for index in range(0, len(points), 2):
            vertices.extend([points[index] + x_offset, points[index + 1] + y_offset, 0, 0])
            indices.append(int(index / 2))

        return Mesh(vertices=vertices, indices=indices, mode="triangle_fan")

    def _create_segment_dot_object(self, x_offset, y_offset):
        pass

    def _update_segment_colors(self):
        """Update the colors for every segment (on or off based on actual characters)."""
        for char_index in range(self.character_count):
            char_code = self._encoded_characters[char_index]
            for segment in range(16):
                if (1 << segment) & char_code:
                    self._segment_colors[char_index][segment].rgba = self.segment_on_color
                else:
                    self._segment_colors[char_index][segment].rgba = self.segment_off_color

    @staticmethod
    def encode_characters(text: str, character_count: int, segment_map: Dict[int, int],
                          dot_enabled: bool, dot_segment_mask: int,
                          comma_enabled: bool, comma_segment_mask: int) -> List[int]:
        """Encode the text characters to prepare for display."""
        text_position = 0
        encoded_characters = []
        while text_position < len(text):
            char = text[text_position]
            text_position += 1
            encoded_char = segment_map.get(ord(char), 0x00)
            if dot_enabled or comma_enabled:
                # embed dots is enabled and dot is inactive
                try:
                    next_char = text[text_position]
                except IndexError:
                    next_char = " "
                if dot_enabled and next_char == ".":
                    # next char is a dot -> turn dot on
                    encoded_char |= dot_segment_mask
                    text_position += 1
                elif comma_enabled and next_char == ",":
                    # next char is a dot -> turn dot on
                    encoded_char |= comma_segment_mask
                    text_position += 1

            encoded_characters.append(encoded_char)

        # remove leading segments if mapping is too long
        if character_count < len(encoded_characters):
            encoded_characters = encoded_characters[-character_count:]

        while character_count > len(encoded_characters):
            # prepend spaces to pad mapping
            encoded_characters.insert(0, OFF)

        return encoded_characters

    def _set_flash_mode(self):
        """Set the current flash mode."""
        if self.flash_mode == "off":
            self._flash_character_mask = [0xFF] * self.character_count
            self._stop_flash_timer()
        elif self.flash_mode == "all":
            self._flash_character_mask = [0x00] * self.character_count
            self._start_flash_timer()
        elif self.flash_mode == "match":
            self._flash_character_mask = [0xFF] * (self.character_count - 2)
            self._flash_character_mask.extend([0x00] * 2)
            self._start_flash_timer()
        elif self.flash_mode == "mask":
            mask = self.flash_mask.rjust(self.character_count, ' ')
            mask = mask[-self.character_count:]
            self._flash_character_mask = [0x00 if c == "F" else 0xFF for c in mask]
            for index in range(len(mask)):
                if mask[index] == "F":
                    self._flash_character_mask[index] = 0x00
            self._start_flash_timer()

    def _start_flash_timer(self):
        """Start the timer to control flashing."""
        self._apply_flash_mask = True
        if self._flash_clock_event:
            self._flash_clock_event.cancel()
        self._flash_clock_event = Clock.schedule_interval(self._flash_clock_callback, 1 / (self.flash_frequency * 2))
        self._draw_widget()

    def _stop_flash_timer(self):
        """Stop the timer that controls flashing."""
        self._apply_flash_mask = False
        if self._flash_clock_event:
            self._flash_clock_event.cancel()
            self._flash_clock_event = None
        self._draw_widget()

    def _flash_clock_callback(self, dt, *args):
        """Callback method for the clock."""
        del dt
        del args
        self._apply_flash_mask = not self._apply_flash_mask
        self._draw_widget()

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

    display_type = OptionProperty("14seg", options=["7seg", "14seg"])
    '''The type of display (7 segment, 14 segment).

    :attr:`display_type` is an :class:`~kivy.properties.OptionProperty` and defaults to `14SEG`.
    '''

    character_slant_angle = NumericProperty(0)
    '''The angle at which the characters are slanted (degrees from vertical)

    :attr:`character_slant_angle` is an :class:`~kivy.properties.NumericProperty` and defaults to 0.
    '''

    character_spacing = NumericProperty(10)
    '''The space between each character/element.

    :attr:`character_spacing` is an :class:`~kivy.properties.NumericProperty` and defaults to 10.
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

    background_color = ListProperty([0, 0, 0, 1.0])
    '''The background color of the display widget, in the (r, g, b, a) format.

    :attr:`background_color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [0, 0, 0, 1.0].
    '''

    dot_enabled = BooleanProperty(False)
    '''Determines if an integrated dot/period should be displayed

    :attr:`dot_enabled` is an :class:`kivy.properties.BooleanProperty` and defaults to False.
    '''

    comma_enabled = BooleanProperty(False)
    '''Determines if an integrated comma should be displayed

    :attr:`comma_enabled` is an :class:`kivy.properties.BooleanProperty` and defaults to False.
    '''

    text = StringProperty("")
    '''Contains the text string to display

    :attr:`text` is an :class:`kivy.properties.StringProperty` and defaults to "".
    '''

    flash_mode = OptionProperty("off", options=["off", "all", "match", "mask"])
    '''The current disiplay flash mode. Defaults to "off".

    :attr:`flash_mode` is an :class:`~kivy.properties.OptionProperty` and defaults to `off`.
    '''

    flash_frequency = NumericProperty(1)
    '''The number of times per second the display should flash.

    :attr:`flash_frequency` is an :class:`~kivy.properties.NumericProperty` and defaults to 1.
    '''

    flash_mask = StringProperty(None)
    '''Contains the flash mask string to use when flashing in mask mode. Each character of the flash
    mask string represents a character in the display. Character positions with an `F` character 
    will be flashed while any other character will not flash. 

    :attr:`flash_mask` is an :class:`kivy.properties.StringProperty` and defaults to None.
    '''


widget_classes = [SegmentDisplayEmulator]
