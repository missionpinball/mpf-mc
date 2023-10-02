"""Text Input widget.

The :class:`MpfTextInput` widget is used to all the player (or an operator) to
enter text. It can be linked to a :class:`Text` widget which displays the text
that's been entered so far.

"""
from collections import deque
from typing import Optional
from kivy.clock import Clock

from mpfmc.widgets.text import Text

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class MpfTextInput(Text):

    """Text input widget."""

    widget_type_name = 'text_input'
    animation_properties = list()

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        """initialize text input.

        Note that this class is called *MpfTextInput* instead of *TextInput*
        because Kivy has a class called *TextInput* which collides with this
        one if they have the same name.
        """
        super().__init__(mc=mc, config=config, key=key)

        del kwargs

        self.linked_text_widget = None
        self.linked_text_widget_right_edge = None
        self.active = False
        self.registered_event_handlers = set()

        # setup the char list and set the current displayed char
        self.char_list = deque()
        self.char_list.extend(self.config['char_list'])
        self.char_list.append('back')
        self.char_list.append('end')
        self.current_list = self.char_list
        self.final_list = deque()
        self.final_list.append('back')
        self.final_list.append('end')
        self._is_blocking = False

        Clock.schedule_once(self.find_linked_text_widget)

    def __repr__(self) -> str:
        try:
            return '<TextInput Widget key={}>'.format(self.key)
        except AttributeError:
            return '<TextInput Widget>'

    def find_linked_text_widget(self, dt) -> None:
        del dt

        for target in self.mc.targets.values():
            w = target.find_widgets_by_key(self.config['key'])
            if w:
                if w[0] != self and isinstance(w[0], Text):
                    self.linked_text_widget = w[0]
                elif len(w) > 1 and isinstance(w[1], Text):
                    self.linked_text_widget = w[1]
                break

        if self.linked_text_widget:
            self.active = True
            self._register_events()

            if self.config['dynamic_x']:
                # bind() is weak meth, so we don't have to unbind
                self.linked_text_widget.bind(size=self.set_relative_position)
                self.linked_text_widget_right_edge = (
                    self.linked_text_widget.get_text_width() + self.linked_text_widget.x)

        self.jump(self.config['initial_char'])

    def _register_events(self) -> None:
        if not self.config['shift_left_event']:
            self.config['shift_left_event'] = (
                'text_input_{}_shift_left'.format(self.key))

        if not self.config['shift_right_event']:
            self.config['shift_right_event'] = (
                'text_input_{}_shift_right'.format(self.key))

        if not self.config['select_event']:
            self.config['select_event'] = (
                'text_input_{}_select'.format(self.key))

        if not self.config['abort_event']:
            self.config['abort_event'] = (
                'text_input_{}_abort'.format(self.key))

        if not self.config['force_complete_event']:
            self.config['force_complete_event'] = (
                'text_input_{}_force_complete'.format(self.key))

        for event in self.config.get('block_events', []):
            self.registered_event_handlers.add(self.mc.events.add_handler(
                event, self.block_enable, priority=2  # Priority avoids conflicts with select/abort event handlers
            ))
            self.mc.bcp_processor.register_trigger(event)
        for event in self.config.get('release_events', []):
            self.registered_event_handlers.add(self.mc.events.add_handler(
                event, self.block_disable, priority=2
            ))
            self.mc.bcp_processor.register_trigger(event)

        self.registered_event_handlers.add(self.mc.events.add_handler(
            self.config['shift_left_event'], self.shift, places=-1))
        self.mc.bcp_processor.register_trigger(self.config['shift_left_event'])
        self.registered_event_handlers.add(self.mc.events.add_handler(
            self.config['shift_right_event'], self.shift, places=1))
        self.mc.bcp_processor.register_trigger(self.config['shift_right_event'])
        self.registered_event_handlers.add(self.mc.events.add_handler(
            self.config['select_event'], self.select))
        self.mc.bcp_processor.register_trigger(self.config['select_event'])
        self.registered_event_handlers.add(self.mc.events.add_handler(
            self.config['abort_event'], self.abort))
        self.mc.bcp_processor.register_trigger(self.config['abort_event'])
        self.registered_event_handlers.add(self.mc.events.add_handler(
            self.config['force_complete_event'], self.complete))
        self.mc.bcp_processor.register_trigger(self.config['force_complete_event'])

    def _deregister_events(self) -> None:
        self.mc.events.remove_handlers_by_keys(self.registered_event_handlers)

    def jump(self, char: str) -> None:
        # Unfortunately deque.index() is Python 3.5+, so we have to do it this
        # way.

        if not self.current_list:
            return

        counts_remaining = len(self.current_list)
        while self.current_list[0] != char:
            self.current_list.rotate(1)
            counts_remaining -= 1

            if not counts_remaining:
                raise ValueError("Cannot set text_input character to "
                                 "{} as that is not a valid entry in the "
                                 "widget's character list".format(char))

        self.shift(0, True)

    def shift(self, places: int = 1, force: bool = False, **kwargs) -> None:
        del kwargs
        if self._is_blocking:
            return
        if self.active or force:
            self.current_list.rotate(-places)

            self.mc.post_mc_native_event('text_input_{}_active_character'.format(self.key),
                                         text=self.current_list[0])

            if self.current_list[0] == 'end':
                self.font_size = self.config['font_size'] / 2
                self.update_text('END')
            elif self.current_list[0] == ' ':
                self.font_size = self.config['font_size'] / 2
                self.update_text('SPACE')
            elif self.current_list[0] == 'back':
                self.font_size = self.config['font_size'] / 2
                self.update_text('BACK')
            else:
                self.font_size = self.config['font_size']
                self.update_text(self.current_list[0])

            if self.config['dynamic_x'] and self.linked_text_widget:
                self.set_relative_position()

    def select(self, **kwargs) -> None:
        del kwargs
        if not self.active:
            return

        if self.current_list[0] == 'back':

            if self.linked_text_widget.text:
                # set the text_entry text to whatever the last char was
                self.current_list = self.char_list
                self.jump(self.linked_text_widget.text[-1:])
                # remove the last char from the associated widget
                self.linked_text_widget.update_text(
                    self.linked_text_widget.text[:-1])

        elif self.current_list[0] == 'end':
            self.complete()

        else:
            self.linked_text_widget.update_text(
                self.linked_text_widget.text + self.current_list[0])

            if len(self.linked_text_widget.text) >= self.config['max_chars']:
                # only show back and end
                self.current_list = self.final_list
                self.jump("end")

            if len(self.linked_text_widget.text) > self.config['max_chars']:
                # we are done
                self.complete()

        self.mc.post_mc_native_event('text_input_{}_select'.format(self.key),
                                     text=self.linked_text_widget.text, length=len(self.linked_text_widget.text))

    def set_relative_position(self, *args) -> None:
        del args

        new_right_edge = (self.linked_text_widget.get_text_width() +
                          self.linked_text_widget.x)

        self.x += new_right_edge - self.linked_text_widget_right_edge
        self.linked_text_widget_right_edge = new_right_edge

        if self.x < (self.linked_text_widget_right_edge +
                     self.config['dynamic_x_pad']):
            self.x += (self.linked_text_widget_right_edge +
                       self.config['dynamic_x_pad'] - self.x)

    def complete(self, **kwargs) -> None:
        del kwargs
        self.done()
        self.mc.post_mc_native_event('text_input_{}_complete'.format(self.key),
                                     text=self.linked_text_widget.text)
        """event: text_input_(key)_complete

        desc: This event is posted by a *text_input* display widget when the
            entered text is finalized.

        args:
            text: A string of the final characters that were entered.
        """

    def abort(self, **kwargs) -> None:
        del kwargs
        self.done()
        self.mc.post_mc_native_event('text_input_{}_abort'.format(self.key),
                                     text=self.linked_text_widget.text)
        """event: text_input_(key)_abort

        desc: This event is posted by a *text_input* display widget when the
            entering process was aborted.

        args:
            text: A string of the characters that were entered so far.
        """

    def done(self) -> None:
        self._deregister_events()
        self.active = False
        self.text = ''
        self._container.parent.remove_widget(self)

    def prepare_for_removal(self) -> None:
        self.done()
        super().prepare_for_removal()

    def block_enable(self, **kwargs) -> None:
        del kwargs
        self._is_blocking = True

    def block_disable(self, **kwargs) -> None:
        del kwargs
        self._is_blocking = False


widget_classes = [MpfTextInput]
