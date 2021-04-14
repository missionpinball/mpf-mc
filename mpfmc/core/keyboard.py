"""Handles key strokes in the media manager."""
import logging

from kivy.core.window import Window
from kivy.uix.widget import Widget as KivyWidget


class Keyboard(KivyWidget):

    """Handles key strokes in the media manager."""

    def __init__(self, mc, **kwargs):
        super().__init__(**kwargs)

        self.mc = mc
        self.log = logging.getLogger("Keyboard")

        self.keyboard_events = list()
        self.key_map = dict()
        self.toggle_keys = set()
        self.inverted_keys = list()
        self.active_keys = dict()
        self.debug = False

        # todo need to change the parsing logic to make these work
        self.special_keys = {
            'equals': '=',
            'minus': '-',
            'dash': '-',
            'leftbracket': '[',
            'rightbracket': ']',
            'backslash': '\\',
            'apostrophe': "'",
            'semicolon': ';',
            'colon': ':',
            'comma': ',',
            'period': '.',
            'slash': '/',
            'question': '?',
        }

        self.keyboard = Window.request_keyboard(callback=None, target=self)

        self.keyboard.bind(on_key_down=self._on_keyboard_down,
                           on_key_up=self._on_keyboard_up)

        for k, v in self.mc.machine_config['keyboard'].items():

            if k == 'debug' and v:
                self.debug = True
                continue

            k = str(k)  # k is the value of the key entry in the config
            switch_name = v.get('switch', None)
            # set whether a key is the push on / push off type
            toggle_key = v.get('toggle', None)
            invert = v.get('invert', None)
            event = v.get('event', None)
            mc_event = v.get('mc_event', None)
            params = v.get('params', None)
            # todo add args processing?

            # Process the key map entry
            k = k.replace('+', '-').lower().split('-')
            key = k[-1]
            mods = k[:-1]

            if mods:
                mods = sorted(mods)

            # What happens when it's pressed?
            if switch_name:  # We're processing a key entry for a switch
                if invert:
                    self.inverted_keys.append(switch_name)
                self.add_key_map(key, mods, switch_name, toggle_key)

            elif event:  # we're processing an entry for an event
                event_dict = {'event': event, 'params': params}
                self.add_key_map(key, mods, event_dict=event_dict)

            elif mc_event:  # we're processing an entry for an mc_event
                event_dict = {'mc_event': mc_event, 'params': params}
                self.add_key_map(key, mods, event_dict=event_dict)

    @staticmethod
    def get_key_string(key: str, mods: [str]) -> str:
        """Return string for key + modifiers.

        Args:
            key: string of key
            mods: list of modifiers as string

        Returns: string
        """
        try:
            mods = sorted(mods)
        except AttributeError:
            pass

        return '{}-{}'.format(key, '-'.join(mods))

    # pylint: disable-msg=too-many-arguments
    def add_key_map(self, key, mods, switch_name=None, toggle_key=False,
                    event_dict=None):
        """Add an entry to the key_map which is used to see what to do when key events are received.

        Args:
            key: The character or name of the key
            mods: List of strings for modifier keys for this entry
            switch_name: String name of the switch this key combination is tied
                to.
            toggle_key: Boolean as to whether this key should be a toggle key.
                (i.e. push on / push off).
            event_dict: Dictionary of events with parameters that will be
            posted when this key combination is pressed. Default is None.
        """
        key_string = self.get_key_string(key, mods)

        if switch_name:
            self.key_map[key_string] = switch_name
        elif event_dict:
            self.key_map[key_string] = event_dict

        if toggle_key:
            self.toggle_keys.add(key_string)

    def _on_keyboard_up(self, keyboard, keycode):
        del keyboard
        key = keycode[1]
        self.process_key_release(key)
        return True

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        del keyboard
        del text
        key = keycode[1]

        # only consider numlock modifier for keys on the numlock field
        if "numlock" in modifiers and not key.startswith("num"):
            modifiers.remove("numlock")

        if self.debug:
            if modifiers:
                print("KEYS: {}+{}".format('+'.join(modifiers), key))
            else:
                print("KEYS: {}".format(key))

        if key in self.active_keys:
            return True
        else:
            return self.process_key_down(key, modifiers)

    def process_key_down(self, key, mods):
        """Process a key down event and change switches accordingly."""
        key_string = self.get_key_string(key, mods)
        self.log.debug("Processing key stroke for key %s", key_string)

        if key_string not in self.key_map:
            return False

        if key_string in self.toggle_keys:  # is this is a toggle key?
            self.active_keys[key] = None
            self.send_switch(state=-1, name=self.key_map[key_string])

        else:
            # do we have an event or a switch?
            if isinstance(self.key_map[key_string], str):  # switch

                if self.key_map[key_string] in self.inverted_keys:
                    self.send_switch(state=0, name=self.key_map[key_string])
                    self.active_keys[key] = ''.join(('-',
                                                     self.key_map[key_string]))

                else:
                    self.send_switch(state=1, name=self.key_map[key_string])
                    self.active_keys[key] = self.key_map[key_string]

            elif isinstance(self.key_map[key_string], dict):  # event
                event_dict = self.key_map[key_string]
                event_params = event_dict['params'] or {}

                if 'event' in event_dict:
                    self.mc.post_mc_native_event(str(event_dict['event']),
                                                 **event_params)

                elif 'mc_event' in event_dict:
                    self.log.warning("The keyboard setting 'mc_event:' will "
                                     "go away soon since now regular 'event:'"
                                     "entries are posted to the MC and MPF.")
                    # todo deprecate this
                    self.mc.events.post(event_dict['mc_event'],
                                        **event_params)

        return True

    def process_key_release(self, key):
        """Process a key up event and change switches accordingly."""
        action = self.active_keys.pop(key, None)

        if action:
            if action.startswith('-'):
                self.send_switch(state=1, name=action[1:])
            else:
                self.send_switch(state=0, name=action)

    def send_switch(self, name, state):
        """Notify mpf via BCP about a switch change."""
        if self.mc.bcp_client_connected:
            self.mc.bcp_processor.send('switch', name=name, state=state)
