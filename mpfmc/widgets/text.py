"""A text widget on a slide."""
import re
from typing import Optional

from kivy.uix.label import Label
from kivy.properties import AliasProperty, NumericProperty, BooleanProperty, \
    ReferenceListProperty, ListProperty
from kivy.graphics import Rectangle, Color, Rotate, Scale

from mpfmc.uix.widget import Widget
from mpfmc.uix.bitmap_font.label_bitmap_font import LabelBitmapFont

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
class McFontLabel(Label):

    """Normal label."""

    def get_label(self):
        """Return the label."""
        return self._label


# pylint: disable-msg=too-many-instance-attributes
class BitmapFontLabel(Label):

    """Injects a font or bitmap font into a text widget."""

    def __init__(self, mc: "MpfMc", font_name, **kwargs):

        self.mc = mc
        self.mc.track_leak_reference(self)
        kwargs.setdefault('font_name', font_name)
        kwargs.setdefault('font_kerning', True)

        super().__init__(**kwargs)

    def get_label(self):
        """Return the label."""
        return self._label

    def _create_label(self):
        d = Label._font_properties
        dkw = dict(list(zip(d, [getattr(self, x) for x in d])))
        self._label = LabelBitmapFont(self.mc, **dkw)


var_finder = re.compile(r"(?<=\()[a-zA-Z_0-9|]+(?=\))")
string_finder = re.compile(r"(?<=\$)[a-zA-Z_0-9]+")


class Text(Widget):

    """A text widget on a slide."""

    widget_type_name = 'Text'
    merge_settings = ('font_name', 'font_size', 'bold', 'italic', 'halign',
                      'valign', 'padding_x', 'padding_y', 'text_size',
                      'shorten', 'mipmap', 'markup', 'line_height',
                      'max_lines', 'strip', 'shorten_from', 'split_str',
                      'unicode_errors', 'color', 'casing')
    animation_properties = ('x', 'y', 'font_size', 'color', 'opacity', 'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None,
                 play_kwargs: Optional[dict] = None, **kwargs) -> None:
        if 'bitmap_font' in config and config['bitmap_font']:
            if 'font_name' not in config or not config['font_name']:
                raise ValueError("Text widget: font_name is required when bitmap_font is True.")
            self._label = BitmapFontLabel(mc, config['font_name'])
        else:
            self._label = McFontLabel()
        self._label.fbind('texture', self.on_label_texture)
        self.color_instruction = None
        self.rectangle = None
        self.rotate = None
        self.scale_instruction = None

        super().__init__(mc=mc, config=config, key=key)

        # Special handling for baseline anchor
        if self.config['anchor_y'] == 'baseline':
            self.anchor_y = 'bottom'
            self.adjust_bottom = self._label.get_label().get_descent() * -1

        self.original_text = self._get_text_string(config.get('text', ''))

        self.text_variables = dict()
        if play_kwargs:
            self.event_replacements = play_kwargs
        else:
            self.event_replacements = kwargs
        self._process_text(self.original_text)

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget)

    def get_text_width(self):
        """Return the text width."""
        if self._label.text:
            # this only makes sense if there is a text
            return self.width
        else:
            # otherwise text width is 0
            return 0

    def __repr__(self) -> str:
        if hasattr(self, '_label') and self._label:
            return '<Text Widget text={}>'.format(self._label.text)
        else:
            return '<Text Widget text=None>'

    def _draw_widget(self, *args):
        """Draws the image (draws a rectangle using the image texture)."""
        del args

        # Redrawing the widget doesn't reposition, so update manually
        anchor = (self.x - self.anchor_offset_pos[0], self.y - self.anchor_offset_pos[1])
        # Save the updated position as a new variable, such that consecutive text
        # changes don't introduce gradual shifts in position.
        pos = self.calculate_rounded_position(anchor)

        if (self._label.text and not self.rectangle) or (self.rectangle and not self._label.text):
            # only create instructions once
            # unfortunately, we also have to redo it when the text becomes empty or non-empty
            self.canvas.clear()
            with self.canvas:
                self.color_instruction = Color(*self.color)
                self.rotate = Rotate(angle=self.rotation, origin=anchor)
                self.scale_instruction = Scale(self.scale)
                self.scale_instruction.origin = anchor

                if self._label.text:
                    self.rectangle = Rectangle(pos=pos, size=self.size, texture=self._label.texture)
                else:
                    self.rectangle = None

        if self.rotate:
            self.rotate.origin = anchor
            self.rotate.angle = self.rotation
        if self.scale_instruction:
            self.scale_instruction.x = self.scale   # Kivy 1.6.0 requires explicit per-axis scale args
            self.scale_instruction.y = self.scale
            self.scale_instruction.z = self.scale
            self.scale_instruction.origin = anchor
        if self.rectangle:
            self.rectangle.pos = pos
            self.rectangle.size = self.size
            self.rectangle.texture = self._label.texture
        if self.color_instruction:
            self.color_instruction.rgba = self.color

    def on_label_texture(self, instance, texture):
        del instance
        if texture:
            self.size = texture.size

            if self.config['anchor_y'] == 'baseline':
                self.adjust_bottom = self._label.get_label().get_descent() * -1

    def update_kwargs(self, **kwargs) -> None:
        self.event_replacements.update(kwargs)
        self._process_text(self.original_text)

    def _get_text_string(self, text: str) -> str:
        if '$' not in text:
            return text

        for text_string in string_finder.findall(text):
            text = text.replace('${}'.format(text_string),
                                self._do_get_text_string(text_string))

        return text

    def _do_get_text_string(self, text_string: str) -> str:
        try:
            return str(self.mc.machine_config['text_strings'][text_string])
        except KeyError:
            # if the text string is not found, put the $ back on
            return '${}'.format(text_string)

    @staticmethod
    def _get_text_vars(text: str):
        return var_finder.findall(text)

    def _process_text(self, text: str) -> None:
        for var_string in self._get_text_vars(text):
            if var_string in self.event_replacements:
                text = text.replace('({})'.format(var_string),
                                    str(self.event_replacements[var_string]))

        if self._get_text_vars(text):
            # monitors won't be added twice, so it's ok to blindly call this
            self._setup_variable_monitors(text)

        self.update_vars_in_text(text)

    def update_vars_in_text(self, text: str) -> None:
        for var_string in self._get_text_vars(text):
            if var_string.startswith('machine|'):
                try:
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.machine_vars[var_string.split('|')[1]]))
                except KeyError:
                    text = text.replace('(' + var_string + ')', '')

            elif self.mc.player:
                if var_string.startswith('player|'):
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.player[var_string.split('|')[1]]))
                    continue
                if var_string.startswith('player') and '|' in var_string:
                    player_num, var_name = var_string.lstrip('player').split('|')
                    try:
                        value = self.mc.player_list[int(player_num) - 1][
                            var_name]

                        if value is not None:
                            text = text.replace('(' + var_string + ')',
                                                str(value))
                        else:
                            text = text.replace('(' + var_string + ')', '')
                    except IndexError:
                        text = text.replace('(' + var_string + ')', '')
                    continue
                if self.mc.player.is_player_var(var_string):
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.player[var_string]))
                    continue

            if var_string in self.event_replacements:
                text = text.replace('({})'.format(var_string),
                                    str(self.event_replacements[var_string]))

        self.update_text(text)

    def update_text(self, text: str) -> None:
        if text:
            if self.config['min_digits']:
                text = text.zfill(self.config['min_digits'])

            if self.config['number_grouping']:

                # find the numbers in the string
                number_list = [s for s in text.split() if s.isdigit()]

                # group the numbers and replace them in the string
                for item in number_list:
                    grouped_item = Text.group_digits(item)
                    text = text.replace(str(item), grouped_item)

            if self.config.get('casing', None) in ('lower', 'upper', 'title', 'capitalize'):
                text = getattr(text, self.config['casing'])()

        self._label.text = text
        self._label.texture_update()
        self._draw_widget()

    def _player_var_change(self, **kwargs) -> None:
        del kwargs
        self.update_vars_in_text(self.original_text)

    def _machine_var_change(self, **kwargs) -> None:
        del kwargs
        self.update_vars_in_text(self.original_text)

    def _setup_variable_monitors(self, text: str) -> None:
        for var_string in self._get_text_vars(text):
            if '|' not in var_string:
                self.add_player_var_handler(name=var_string)
                self.add_current_player_handler()
            else:
                source, variable_name = var_string.split('|')
                if source.lower().startswith('player'):

                    if source.lstrip('player'):  # we have player num
                        self.add_player_var_handler(name=variable_name)
                    else:  # no player num
                        self.add_player_var_handler(name=variable_name)
                        self.add_current_player_handler()
                elif source.lower() == 'machine':
                    self.add_machine_var_handler(name=variable_name)

    def add_player_var_handler(self, name: str) -> None:
        self.mc.events.replace_handler('player_{}'.format(name),
                                       self._player_var_change)

    def add_current_player_handler(self) -> None:
        self.mc.events.replace_handler('player_turn_start',
                                       self._player_var_change)

    def add_machine_var_handler(self, name: str) -> None:
        self.mc.events.add_handler('machine_var_{}'.format(name),
                                   self._machine_var_change)

    def prepare_for_removal(self) -> None:
        super().prepare_for_removal()
        self.mc.events.remove_handler(self._player_var_change)
        self.mc.events.remove_handler(self._machine_var_change)

    @staticmethod
    def group_digits(text: str, separator: str = ',', group_size: int = 3) -> str:
        """Enable digit grouping (i.e. adds comma separators between thousands digits).

        Args:
            text: The incoming string of text
            separator: String of the character(s) you'd like to add between the
                digit groups. Default is a comma. (",")
            group_size: How many digits you want in each group. Default is 3.

        Returns: A string with the separator added.

        MPF uses this method instead of the Python locale settings because the
        locale settings are a mess. They're set system-wide and it's really
        hard
        to make them work cross-platform and there are all sorts of external
        dependencies, so this is just way easier.

        """
        digit_list = list(text.split('.')[0])

        for i in range(len(digit_list))[::-group_size][1:]:
            digit_list.insert(i + 1, separator)

        return ''.join(digit_list)

    #
    # Properties
    #

    disabled_color = ListProperty([1, 1, 1, .3])
    '''The color of the text when the widget is disabled, in the (r, g, b, a)
    format.

    .. versionadded:: 1.8.0

    :attr:`disabled_color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [1, 1, 1, .3].
    '''

    def _get_text(self) -> str:
        return self._label.text

    def _set_text(self, text: str) -> None:
        self._label.text = text

    text = AliasProperty(_get_text, _set_text)
    '''Text of the label.
    '''

    def _get_text_size(self) -> list:
        return self._label.text_size

    def _set_text_size(self, text_size: list) -> None:
        self._label.text_size = text_size

    text_size = AliasProperty(_get_text_size, _set_text_size)
    '''By default, the label is not constrained to any bounding box.
    You can set the size constraint of the label with this property.
    The text will autoflow into the constraints. So although the font size
    will not be reduced, the text will be arranged to fit into the box as best
    as possible, with any text still outside the box clipped.

    This sets and clips :attr:`texture_size` to text_size if not None.

    .. versionadded:: 1.0.4

    For example, whatever your current widget size is, if you want the label to
    be created in a box with width=200 and unlimited height::

        Label(text='Very big big line', text_size=(200, None))

    .. note::

        This text_size property is the same as the
        :attr:`~kivy.core.text.Label.usersize` property in the
        :class:`~kivy.core.text.Label` class. (It is named size= in the
        constructor.)

    :attr:`text_size` is a :class:`~kivy.properties.ListProperty` and
    defaults to (None, None), meaning no size restriction by default.
    '''

    def _get_font_name(self) -> str:
        return self._label.font_name

    def _set_font_name(self, font_name: str) -> None:
        self._label.font_name = font_name

    font_name = AliasProperty(_get_font_name, _set_font_name)
    '''Filename of the font to use. The path can be absolute or relative.
    Relative paths are resolved by the :func:`~kivy.resources.resource_find`
    function.

    .. warning::

        Depending of your text provider, the font file can be ignored. However,
        you can mostly use this without problems.

        If the font used lacks the glyphs for the particular language/symbols
        you are using, you will see '[]' blank box characters instead of the
        actual glyphs. The solution is to use a font that has the glyphs you
        need to display. For example, to display |unicodechar|, use a font such
        as freesans.ttf that has the glyph.

        .. |unicodechar| image:: images/unicode-char.png

    :attr:`font_name` is a :class:`~kivy.properties.StringProperty` and
    defaults to 'Roboto'. This value is taken
    from :class:`~kivy.config.Config`.
    '''

    def _get_font_size(self):
        return self._label.font_size

    def _set_font_size(self, font_size) -> None:
        self._label.font_size = font_size

    font_size = AliasProperty(_get_font_size, _set_font_size)
    '''Font size of the text, in pixels.

    :attr:`font_size` is a :class:`~kivy.properties.NumericProperty` and
    defaults to 15sp.
    '''

    def _get_line_height(self) -> float:
        return self._label.line_height

    def _set_line_height(self, line_height: float) -> None:
        self._label.line_height = line_height

    bitmap_font = BooleanProperty(False)
    '''Flag indicating whether or not the font_name attribute refers to a
    bitmap font.'''

    line_height = AliasProperty(_get_line_height, _set_line_height)
    '''Line Height for the text. e.g. line_height = 2 will cause the spacing
    between lines to be twice the size.

    :attr:`line_height` is a :class:`~kivy.properties.NumericProperty` and
    defaults to 1.0.

    .. versionadded:: 1.5.0
    '''

    def _get_bold(self) -> bool:
        return self._label.bold

    def _set_bold(self, bold: bool) -> None:
        self._label.bold = bold

    bold = AliasProperty(_get_bold, _set_bold)
    '''Indicates use of the bold version of your font.

    .. note::

        Depending of your font, the bold attribute may have no impact on your
        text rendering.

    :attr:`bold` is a :class:`~kivy.properties.BooleanProperty` and defaults to
    False.
    '''

    def _get_italic(self) -> bool:
        return self._label.italic

    def _set_italic(self, italic: bool) -> None:
        self._label.italic = italic

    italic = AliasProperty(_get_italic, _set_italic)
    '''Indicates use of the italic version of your font.

    .. note::

        Depending of your font, the italic attribute may have no impact on your
        text rendering.

    :attr:`italic` is a :class:`~kivy.properties.BooleanProperty` and defaults
    to False.
    '''

    def _get_underline(self) -> bool:
        return self._label.underline

    def _set_underline(self, underline: bool) -> None:
        self._label.underline = underline

    underline = AliasProperty(_get_underline, _set_underline)
    '''Adds an underline to the text.

    .. note::
        This feature requires the SDL2 text provider.

    .. versionadded:: 1.10.0

    :attr:`underline` is a :class:`~kivy.properties.BooleanProperty` and
    defaults to False.
    '''

    def _get_strikethrough(self) -> bool:
        return self._label.strikethrough

    def _set_strikethrough(self, strikethrough: bool) -> None:
        self._label.strikethrough = strikethrough

    strikethrough = AliasProperty(_get_strikethrough, _set_strikethrough)
    '''Adds a strikethrough line to the text.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_padding_x(self):
        return self._label.padding_x

    def _set_padding_x(self, padding_x):
        self._label.padding_x = padding_x

    padding_x = AliasProperty(_get_padding_x, _set_padding_x)
    '''Horizontal padding of the text inside the widget box.
    '''

    def _get_padding_y(self):
        return self._label.padding_y

    def _set_padding_y(self, padding_y):
        self._label.padding_y = padding_y

    padding_y = AliasProperty(_get_padding_y, _set_padding_y)
    '''Vertical padding of the text inside the widget box.
    '''

    padding = ReferenceListProperty(padding_x, padding_y)
    '''Padding of the text in the format (padding_x, padding_y)

    :attr:`padding` is a :class:`~kivy.properties.ReferenceListProperty` of
    (:attr:`padding_x`, :attr:`padding_y`) properties.
    '''

    def _get_halign(self) -> str:
        return self._label.halign

    def _set_halign(self, halign: str) -> None:
        self._label.halign = halign

    halign = AliasProperty(_get_halign, _set_halign)
    '''Horizontal alignment of the text. Available options are : left, center,
    right and justify.

    .. warning::

        This doesn't change the position of the text texture of the Label
        (centered), only the position of the text in this texture. You probably
        want to bind the size of the Label to the :attr:`texture_size` or set a
        :attr:`text_size`.
    '''

    def _get_valign(self) -> str:
        return self._label.valign

    def _set_valign(self, valign: str) -> None:
        self._label.valign = valign

    valign = AliasProperty(_get_valign, _set_valign)
    '''Vertical alignment of the text. Available options are : `'bottom'`,
    `'middle'` (or `'center'`) and `'top'`.

    .. warning::

        This doesn't change the position of the text texture of the Label
        (centered), only the position of the text within this texture. You
        probably want to bind the size of the Label to the :attr:`texture_size`
        or set a :attr:`text_size` to change this behavior.
    '''

    def _get_outline_width(self) -> Optional[int]:
        return self._label.outline_width

    def _set_outline_width(self, outline_width: Optional[int]) -> None:
        self._label.outline_width = outline_width

    outline_width = AliasProperty(_get_outline_width, _set_outline_width)
    '''Width in pixels for the outline around the text. No outline will be
    rendered if the value is None.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_outline_color(self) -> list:
        return self._label.outline_color

    def _set_outline_color(self, outline_color: list) -> None:
        self._label.outline_color = outline_color

    outline_color = AliasProperty(_get_outline_color, _set_outline_color)
    '''The color of the text outline, in the (r, g, b) format.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_disabled_outline_color(self) -> list:
        return self._label.disabled_outline_color

    def _set_disabled_outline_color(self, disabled_outline_color: list) -> None:
        self._label.disabled_outline_color = disabled_outline_color

    disabled_outline_color = AliasProperty(_get_disabled_outline_color, _set_disabled_outline_color)
    '''The color of the text outline when the widget is disabled, in the
    (r, g, b) format.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_mipmap(self) -> bool:
        return self._label.mipmap

    def _set_mipmap(self, mipmap: bool) -> None:
        self._label.mipmap = mipmap

    mipmap = AliasProperty(_get_mipmap, _set_mipmap)
    '''Indicates whether OpenGL mipmapping is applied to the texture or not.
    Read :ref:`mipmap` for more information.
    '''

    def _get_shorten(self) -> bool:
        return self._label.shorten

    def _set_shorten(self, shorten: bool) -> None:
        self._label.shorten = shorten

    shorten = AliasProperty(_get_shorten, _set_shorten)
    '''
    Indicates whether the label should attempt to shorten its textual contents
    as much as possible if a :attr:`text_size` is given. Setting this to True
    without an appropriately set :attr:`text_size` will lead to unexpected
    results.

    :attr:`shorten_from` and :attr:`split_str` control the direction from
    which the :attr:`text` is split, as well as where in the :attr:`text` we
    are allowed to split.
    '''

    def _get_shorten_from(self) -> str:
        return self._label.shorten_from

    def _set_shorten_from(self, shorten_from: str) -> None:
        self._label.shorten_from = shorten_from

    shorten_from = AliasProperty(_get_shorten_from, _set_shorten_from)
    '''The side from which we should shorten the text from, can be left,
    right, or center.

    For example, if left, the ellipsis will appear towards the left side and we
    will display as much text starting from the right as possible. Similar to
    :attr:`shorten`, this option only applies when :attr:`text_size` [0] is
    not None, In this case, the string is shortened to fit within the specified
    width.
    '''

    def _get_is_shortened(self) -> bool:
        return self._label.is_shortened

    is_shortened = AliasProperty(_get_is_shortened, None)
    '''This property indicates if :attr:`text` was rendered with or without
    shortening when :attr:`shorten` is True.
    '''

    def _get_split_str(self) -> str:
        return self._label.split_str

    def _set_split_str(self, split_str: str) -> None:
        self._label.split_str = split_str

    split_str = AliasProperty(_get_split_str, _set_split_str)
    '''The string used to split the :attr:`text` while shortening the string
    when :attr:`shorten` is True.

    For example, if it's a space, the string will be broken into words and as
    many whole words that can fit into a single line will be displayed. If
    :attr:`split_str` is the empty string, `''`, we split on every character
    fitting as much text as possible into the line.
    '''

    def _get_ellipsis_options(self) -> dict:
        return self._label.ellipsis_options

    def _set_ellipsis_options(self, ellipsis_options: dict) -> None:
        self._label.ellipsis_options = ellipsis_options

    ellipsis_options = AliasProperty(_get_ellipsis_options, _set_ellipsis_options)
    '''Font options for the ellipsis string('...') used to split the text.

    Accepts a dict as option name with the value. Only applied when
    :attr:`markup` is true and text is shortened. All font options which work
    for :class:`Label` will work for :attr:`ellipsis_options`. Defaults for
    the options not specified are taken from the surronding text.

    .. code-block:: kv

        Label:
            text: 'Some very long line which will be cut'
            markup: True
            shorten: True
            ellipsis_options: {'color':(1,0.5,0.5,1),'underline':True}
    '''

    def _get_unicode_errors(self) -> str:
        return self._label.unicode_errors

    def _set_unicode_errors(self, unicode_errors: str) -> None:
        self._label.unicode_errors = unicode_errors

    unicode_errors = AliasProperty(_get_unicode_errors, _set_unicode_errors)
    '''How to handle unicode decode errors. Can be `'strict'`, `'replace'` or
    `'ignore'`.
    '''

    def _get_markup(self) -> bool:
        return self._label.markup

    def _set_markup(self, markup: bool) -> None:
        self._label.markup = markup

    markup = AliasProperty(_get_markup, _set_markup)
    '''If True, the text will be rendered using the
    :class:`~kivy.core.text.markup.MarkupLabel`: you can change the
    style of the text using tags. Check the
    :doc:`api-kivy.core.text.markup` documentation for more information.
    '''

    def _get_refs(self) -> dict:
        return self._label.refs

    refs = AliasProperty(_get_refs, None)
    '''List of ``[ref=xxx]`` markup items in the text with the bounding box of
    all the words contained in a ref, available only after rendering.

    For example, if you wrote::

        Check out my [ref=hello]link[/ref]

    The refs will be set with::

        {'hello': ((64, 0, 78, 16), )}

    The references marked "hello" have a bounding box at (x1, y1, x2, y2).
    These co-ordinates are relative to the top left corner of the text, with
    the y value increasing downwards. You can define multiple refs with the
    same name: each occurrence will be added as another (x1, y1, x2, y2) tuple
    to this list.

    The current Label implementation uses these references if they exist in
    your markup text, automatically doing the collision with the touch and
    dispatching an `on_ref_press` event.

    You can bind a ref event like this::

        def print_it(instance, value):
            print('User click on', value)
        widget = Label(text='Hello [ref=world]World[/ref]', markup=True)
        widget.on_ref_press(print_it)

    .. note::

        This works only with markup text. You need :attr:`markup` set to
        True.
    '''

    def _get_max_lines(self) -> Optional[int]:
        return self._label.max_lines

    def _set_max_lines(self, max_lines: Optional[int]) -> None:
        self._label.max_lines = max_lines

    max_lines = AliasProperty(_get_max_lines, _set_max_lines)
    '''Maximum number of lines to use, defaults to 0, which means unlimited.
    Please note that :attr:`shorten` take over this property. (with
    shorten, the text is always one line.)
    '''

    def _get_strip(self) -> bool:
        return self._label.strip

    def _set_strip(self, strip: bool) -> None:
        self._label.strip = strip

    strip = AliasProperty(_get_strip, _set_strip)
    '''Whether leading and trailing spaces and newlines should be stripped from
    each displayed line. If True, every line will start at the right or left
    edge, depending on :attr:`halign`. If :attr:`halign` is `justify` it is
    implicitly True.

    .. versionadded:: 1.9.0

    :attr:`strip` is a :class:`~kivy.properties.BooleanProperty` and
    defaults to False.
    '''

    def _get_font_hinting(self) -> Optional[str]:
        return self._label.font_hinting

    def _set_font_hinting(self, font_hinting: Optional[str]):
        self._label.font_hinting = font_hinting

    font_hinting = AliasProperty(_get_font_hinting, _set_font_hinting)
    '''What hinting option to use for font rendering.
    Can be one of `'normal'`, `'light'`, `'mono'` or None.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_font_kerning(self) -> bool:
        return self._label.font_kerning

    def _set_font_kerning(self, font_kerning: bool) -> None:
        self._label.font_kerning = font_kerning

    font_kerning = AliasProperty(_get_font_kerning, _set_font_kerning)
    '''Whether kerning is enabled for font rendering.

    .. note::
        This feature requires the SDL2 text provider.
    '''

    def _get_font_blended(self) -> bool:
        return self._label.font_blended

    def _set_font_blended(self, font_blended: bool) -> None:
        self._label.font_blended = font_blended

    font_blended = AliasProperty(_get_font_blended, _set_font_blended)
    '''Whether blended or solid font rendering should be used.

    .. note::
        This feature requires the SDL2 text provider.
    '''

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


widget_classes = [Text]
