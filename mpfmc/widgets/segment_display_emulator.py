"""Widget emulating a segment display."""
from typing import Optional, List, Dict
import math

from kivy.clock import Clock
from kivy.graphics.vertex_instructions import Mesh
from kivy.properties import NumericProperty, BooleanProperty, ListProperty, AliasProperty, StringProperty
from kivy.graphics import Color, Rotate, Scale

from mpfmc.uix.widget import Widget
from mpf.core.segment_mappings import FOURTEEN_SEGMENTS

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc             # pylint: disable-msg=cyclic-import,unused-import
    from mpfmc.assets.image import ImageAsset   # pylint: disable-msg=cyclic-import,unused-import

# Constants for punctuation segments (dot/period and comma)
DP = 1 << 14
COM = 1 << 15
OFF = 0


class SegmentDisplayEmulator(Widget):

    """Widget emulating a segment display."""

    widget_type_name = 'SegmentDisplayEmulator'
    merge_settings = ('height', 'width')
    animation_properties = ('x', 'y', 'scale', 'width', 'height', 'opacity', 'segment_on_color')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        super().__init__(mc=mc, config=config, key=key)

        # Initialize the character segment map with the default 14-segment mappings from MPF
        self._segment_map = {k: self.get_character_encoding(v) for k, v in FOURTEEN_SEGMENTS.items()}

        # Override default character segment mappings with specific settings
        if "character_map" in self.config and self.config["character_map"] is not None:
            for k, v in self.config["character_map"].items():
                self._segment_map[k] = v

        # Initialize the encoded display characters
        self._encoded_characters = [OFF] * self.character_count

        self._segment_colors = None
        self._segment_mesh_objects = None
        self._update_event_handler_key = None

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(text=self._update_text,
                  pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  segment_off_color=self._draw_widget,
                  segment_on_color=self._draw_widget)

        # Bind an event handler to a custom trigger event to update this
        if self.config['number']:
            self._update_event_handler_key = self.mc.events.add_handler(
                "update_segment_display_{}".format(self.config['number']),
                self.update_segment_display)

        self._calculate_segment_points()
        self._update_text()

    @staticmethod
    def get_character_encoding(segments: FOURTEEN_SEGMENTS) -> int:
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

        # The code in this module is based on an open source sixteen segment display project:
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
        side_bevel_multiplier = 1 if self.side_bevel_enabled else 0

        segment_factor = segment_width * 0.8
        diagonal_slope = self.char_height / self.char_width
        sqrt2 = math.sqrt(2)
        sqrt3 = math.sqrt(3)

        # Base positions of points without bevel and interval
        x0 = self.char_width / 2 - segment_width / 2
        x1 = self.char_width / 2
        x2 = self.char_width / 2 + segment_width / 2
        x3 = self.char_width - segment_width
        x4 = self.char_width - segment_width / 2
        x5 = self.char_width

        y0 = 0
        y1 = segment_width / 2
        y2 = segment_width
        y3 = self.char_height / 2 - segment_width / 2
        y4 = self.char_height / 2
        y5 = self.char_height / 2 + segment_width / 2

        # Create dictionary of segment points keyed by segment name/letter
        segment_points = {"d": [bevel_width * 2 + segment_interval / sqrt2, y0,
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
                          "c": [x5, y0 + bevel_width * 2 + segment_interval / sqrt2,
                                x5, y4 - segment_interval / 2 - segment_width / 2 * side_bevel_multiplier,
                                x4, y4 - segment_interval / 2,
                                x3, y3 - segment_interval / 2,
                                x3, y2 + segment_interval / sqrt2,
                                x5 - bevel_width, y0 + bevel_width + segment_interval / sqrt2],
                          "m": [x2, y2 + segment_interval,
                                x2, y3 - segment_interval,
                                x0, y3 - segment_interval,
                                x0, y2 + segment_interval],
                          "l": [(segment_width + segment_factor) / diagonal_slope + segment_interval,
                                y2 + segment_interval,
                                x0 - segment_interval, x0 * diagonal_slope - segment_factor - segment_interval,
                                x0 - segment_interval, y3 - segment_interval,
                                (y3 - segment_interval) / diagonal_slope - segment_interval, y3 - segment_interval,
                                segment_width + segment_interval,
                                y2 * diagonal_slope + segment_factor + segment_interval,
                                segment_width + segment_interval, y2 + segment_interval]}

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

        # Sort the segment dictionary by segment name (key)
        segment_points = {key: value for key, value in sorted(segment_points.items(), key=lambda item: item[0])}

        # Determine if characters are slanted (if so, apply slant translation)
        if self.character_slant_angle > 0.0:
            segment_points.update(
                {k: self._apply_character_slant_to_points(v, slant_slope) for k, v in segment_points.items()})

        if self.dot_enabled:
            # Store center point of dot/period circle (diameter will be segment_width)
            segment_points["dp"] = [self.char_width + segment_width, segment_width / 2]

        if self.comma_enabled:
            #  (comma should fit in padding on right side of character/element)
            # TODO: calculate comma points
            pass

        self._segment_points = list(segment_points.values())

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
        del args

        if self.canvas is None:
            return

        self.canvas.clear()
        self._segment_colors = []
        self._segment_mesh_objects = []

        with self.canvas:
            Color(*self.color)
            Scale(self.scale, origin=self.center)
            Rotate(angle=self.rotation, origin=self.center)

            x_offset = self.x + self.padding
            y_offset = self.y + self.padding

            for encoded_char in self._encoded_characters:
                colors = [None] * 14
                mesh_objects = [None] * 14
                for segment in range(14):
                    colors[segment] = self._create_segment_color(segment, encoded_char)
                    mesh_objects[segment] = self._create_segment_mesh_object(segment, x_offset, y_offset)

                self._segment_colors.append(colors)
                self._segment_mesh_objects.append(mesh_objects)
                x_offset += self.char_width + self.character_spacing

    def update_segment_display(self, text: str, transition: dict = None, **kwargs):
        """Method to update the segment display."""
        if transition is None:
            self.text = text

    def _update_text(self, *args):
        """Process the new text value to prepare it for display"""
        self._encoded_characters = self.encode_characters(self.text, self.character_count, self._segment_map,
                                                          self.dot_enabled, self.comma_enabled)
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

    def _update_segment_colors(self):
        for char_index in range(self.character_count):
            char_code = self._encoded_characters[char_index]
            for segment in range(16):
                if (1 << segment) & char_code:
                    self._segment_colors[char_index][segment].rgba = self.segment_on_color
                else:
                    self._segment_colors[char_index][segment].rgba = self.segment_off_color

    def prepare_for_removal(self) -> None:
        if self._update_event_handler_key:
            self.mc.events.remove_handler_by_key(self._update_event_handler_key)
        super().prepare_for_removal()

    @staticmethod
    def encode_characters(text: str, character_count: int, segment_map: Dict[int, int],
                          dot_enabled: bool, comma_enabled: bool) -> List[int]:
        text_position = 0
        encoded_characters = []
        while text_position < len(text):
            char = text[text_position]
            text_position += 1
            encoded_char = segment_map.get(ord(char))
            if dot_enabled or comma_enabled:
                # embed dots is enabled and dot is inactive
                try:
                    next_char = text[text_position]
                except IndexError:
                    next_char = " "
                if dot_enabled and next_char == ".":
                    # next char is a dot -> turn dot on
                    encoded_char |= DP
                    text_position += 1
                elif comma_enabled and next_char == ",":
                    # next char is a dot -> turn dot on
                    encoded_char |= COM
                    text_position += 1

            encoded_characters.append(encoded_char)

        # remove leading segments if mapping is too long
        if character_count < len(encoded_characters):
            encoded_characters = encoded_characters[-character_count:]

        while character_count > len(encoded_characters):
            # prepend spaces to pad mapping
            encoded_characters.insert(0, OFF)

        return encoded_characters

    def _start_transition(self):
        # encode the new characters
        # calculate the number of steps (based on display size, transition type, and step size)
        # generate list of strings (all transition steps)
        # set clock callbacks
        pass

    def _update_transition(self):
        # update the display with the next transition string in the list
        pass

    def _cancel_transition(self):
        # cancel and remove clock callback
        # set final text value
        pass

    def _stop_transition(self):
        # remove clock callback
        # set updated text value
        pass

    @staticmethod
    def generate_push_transition(current_encoded_characters: List[int], new_encoded_characters: List[int],
                                 direction_right: bool) -> List[List[int]]:

        display_length = len(current_encoded_characters)

        # create a big list of a concatenation of new and current encoded characters
        if direction_right:
            encoded_characters = new_encoded_characters
            encoded_characters.extend(current_encoded_characters)

            transition_steps = []

            for index in range(1, display_length + 1):
                transition_steps.append(encoded_characters[display_length - index:2 * display_length - index])
        else:
            encoded_characters = current_encoded_characters
            encoded_characters.extend(new_encoded_characters)

            transition_steps = []

            for index in range(1, display_length + 1):
                transition_steps.append(encoded_characters[index:index + display_length])

        return transition_steps

    @staticmethod
    def generate_cover_transition(current_encoded_characters: List[int], new_encoded_characters: List[int],
                                  direction_right: bool) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        if direction_right:
            for index in range(display_length):
                encoded_characters = new_encoded_characters[-(index + 1):]
                encoded_characters.extend(current_encoded_characters[index + 1:])
                transition_steps.append(encoded_characters)
        else:
            for index in range(1, display_length + 1):
                encoded_characters = current_encoded_characters[:display_length - index]
                encoded_characters.extend(new_encoded_characters[:index])
                transition_steps.append(encoded_characters)

        return transition_steps

    @staticmethod
    def generate_uncover_transition(current_encoded_characters: List[int], new_encoded_characters: List[int],
                                    direction_right: bool) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        if direction_right:
            for index in range(1, display_length + 1):
                encoded_characters = new_encoded_characters[:index]
                encoded_characters.extend(current_encoded_characters[:display_length - index])
                transition_steps.append(encoded_characters)
        else:
            for index in range(1, display_length + 1):
                encoded_characters = current_encoded_characters[index:]
                encoded_characters.extend(new_encoded_characters[-index:])
                transition_steps.append(encoded_characters)

        return transition_steps

    @staticmethod
    def generate_wipe_transition(current_encoded_characters: List[int], new_encoded_characters: List[int],
                                 direction_right: bool) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        if direction_right:
            for index in range(1, display_length + 1):
                encoded_characters = new_encoded_characters[:index]
                encoded_characters.extend(current_encoded_characters[index:])
                transition_steps.append(encoded_characters)
        else:
            for index in range(1, display_length + 1):
                encoded_characters = current_encoded_characters[:display_length - index]
                encoded_characters.extend(new_encoded_characters[-index:])
                transition_steps.append(encoded_characters)

        return transition_steps

    @staticmethod
    def generate_wipe_split_transition(current_encoded_characters: List[int],
                                       new_encoded_characters: List[int]) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        characters = int(display_length / 2)
        if characters * 2 == display_length:
            characters -= 1

        while characters > 0:
            encoded_characters = current_encoded_characters[:characters]
            encoded_characters.extend(new_encoded_characters[characters:characters + (display_length - 2 * characters)])
            encoded_characters.extend(current_encoded_characters[-characters:])
            transition_steps.append(encoded_characters)
            characters -= 1

        transition_steps.append(new_encoded_characters)

        return transition_steps

    @staticmethod
    def generate_push_split_open_transition(current_encoded_characters: List[int],
                                            new_encoded_characters: List[int]) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        characters = int(display_length / 2)
        split_point = characters
        if characters * 2 == display_length:
            characters -= 1
        else:
            split_point += 1

        while characters > 0:
            encoded_characters = current_encoded_characters[split_point - characters:split_point]
            encoded_characters.extend(new_encoded_characters[characters:characters + (display_length - 2 * characters)])
            encoded_characters.extend(current_encoded_characters[split_point:split_point + characters])
            transition_steps.append(encoded_characters)
            characters -= 1

        transition_steps.append(new_encoded_characters)

        return transition_steps

    @staticmethod
    def generate_push_split_close_transition(current_encoded_characters: List[int],
                                             new_encoded_characters: List[int]) -> List[List[int]]:

        display_length = len(current_encoded_characters)
        transition_steps = []

        split_point = int(display_length / 2)
        characters = 1
        if split_point * 2 < display_length:
            split_point += 1

        while characters <= split_point:
            encoded_characters = new_encoded_characters[split_point - characters:split_point]
            encoded_characters.extend(current_encoded_characters[characters:characters + (display_length - 2 * characters)])
            encoded_characters.extend(new_encoded_characters[split_point:split_point + characters])
            transition_steps.append(encoded_characters)
            characters += 1

        return transition_steps

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

    text = StringProperty("")
    '''Contains the text string to display

    :attr:`text` is an :class:`kivy.properties.StringProperty` and defaults to "".
    '''


widget_classes = [SegmentDisplayEmulator]
