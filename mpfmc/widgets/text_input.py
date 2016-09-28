"""
Text Input widget
=================

The :class:`MpfTextInput` widget is used to all the player (or an operator) to
enter text. It can be linked to a :class:`Text` widget which displays the text
that's been entered so far.

"""
from collections import deque
from kivy.clock import Clock
from mpfmc.widgets.text import Text


class MpfTextInput(Text):
    widget_type_name = 'text_input'

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)
        """

        Note that this class is called *MpfTextInput* instead of *TextInput*
        because Kivy has a class called *TextInput* which collides with this
        one if they have the same name.
        """

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

        Clock.schedule_once(self.find_linked_text_widget, .1)

    def __repr__(self):
        try:
            return '<TextInput Widget key={}>'.format(self.key)
        except AttributeError:
            return '<TextInput Widget>'

    def find_linked_text_widget(self, dt):
        del dt

        for target in self.mc.targets.values():
            for w in target.parent.walk():
                try:
                    if w.key == self.config['key']:
                        self.linked_text_widget = w
                        break
                except AttributeError:
                    pass
            for x in target.screens:
                for y in x.walk():
                    try:
                        if y.key == self.config['key']:
                            self.linked_text_widget = y
                            break
                    except AttributeError:
                        pass

            if self.linked_text_widget:
                break

        if self.linked_text_widget:
            self.active = True
            self._register_events()

            if self.config['dynamic_x']:
                # bind() is weak meth, so we don't have to unbind
                self.linked_text_widget.bind(size=self.set_relative_position)
                self.linked_text_widget_right_edge = (
                    self.linked_text_widget.width + self.linked_text_widget.x)

                self.jump(self.config['initial_char'])

    def _register_events(self):
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

    def _deregister_events(self):
        self.mc.events.remove_handlers_by_keys(self.registered_event_handlers)

    def jump(self, char):
        # Unfortunately deque.index() is Python 3.5+, so we have to do it this
        # way.
        counts_remaining = len(self.char_list)
        while self.char_list[0] != char:
            self.char_list.rotate(1)
            counts_remaining -= 1

            if not counts_remaining:
                raise ValueError("Cannot set text_input character to "
                                 "{} as that is not a valid entry in the "
                                 "widget's character list".format(char))

        self.shift(0, True)

    def shift(self, places=1, force=False, **kwargs):
        del kwargs
        if self.active or force:
            self.char_list.rotate(-places)

            if self.char_list[0] == 'end':
                self.font_size = self.config['font_size'] / 2
                self.update_text('END')
            elif self.char_list[0] == ' ':
                self.font_size = self.config['font_size'] / 2
                self.update_text('SPACE')
            elif self.char_list[0] == 'back':
                self.font_size = self.config['font_size'] / 2
                self.update_text('BACK')
            else:
                self.font_size = self.config['font_size']
                self.update_text(self.char_list[0])

            if self.config['dynamic_x'] and self.linked_text_widget:
                self.set_relative_position()

    def select(self, **kwargs):
        del kwargs
        if not self.active:
            return

        if self.char_list[0] == 'back':
            # set the text_entry text to whatever the last char was
            self.jump(self.linked_text_widget.text[-1:])
            # remove the last char from the associated widget
            self.linked_text_widget.update_text(
                self.linked_text_widget.text[:-1])

        elif self.char_list[0] == 'end':
            self.complete()

        else:
            self.linked_text_widget.update_text(
                self.linked_text_widget.text + self.char_list[0])

            if len(self.linked_text_widget.text) == self.config['max_chars']:
                self.complete()

    def set_relative_position(self, *args):
        del args

        new_right_edge = (self.linked_text_widget.width +
                          self.linked_text_widget.x)

        self.x += new_right_edge - self.linked_text_widget_right_edge
        self.linked_text_widget_right_edge = new_right_edge

        if self.x < (self.linked_text_widget_right_edge +
                     self.config['dynamic_x_pad']):
            self.x += (self.linked_text_widget_right_edge +
                       self.config['dynamic_x_pad'] - self.x)

    def complete(self, **kwargs):
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

    def abort(self, **kwargs):
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

    def done(self):
        self._deregister_events()
        self.active = False
        self.text = ''
        self.parent.remove_widget(self)

    def prepare_for_removal(self):
        self.done()
        super().prepare_for_removal()
