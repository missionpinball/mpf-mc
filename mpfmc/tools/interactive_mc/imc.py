"""Interactive Media Controller"""
import asyncio
import os

from ruamel import yaml

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.codeinput import CodeInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen

from pygments.lexers import YamlLexer

from mpf.core.bcp.bcp import Bcp
from mpf.core.clock import ClockBase
from mpf.core.config_processor import ConfigProcessor
from mpf.core.events import EventManager
from mpf.core.mode_controller import ModeController
from mpf.core.config_validator import ConfigValidator
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.config_processor import ConfigProcessor as MpfConfigProcessor

import mpfmc
from mpfmc.config_players.plugins.slide_player import MpfSlidePlayer


class Settings(object):

    """Empty settings."""

    def get_settings(self):
        return {}


class InteractiveMc(App):

    def __init__(self, mpf_path, machine_path, args, **kwargs):
        del mpf_path
        del machine_path
        del args
        super().__init__(**kwargs)

        self.config_validator = ConfigValidator(self, True, False)
        self.mpf_config_processor = MpfConfigProcessor(self.config_validator)
        files = [os.path.join(mpfmc.__path__[0], 'tools/interactive_mc/imcconfig.yaml')]
        self.machine_config = self.mpf_config_processor.load_config_files_with_cache(files, "machine")
        self.machine_config['mpf'] = dict()
        self.machine_config['mpf']['allow_invalid_config_sections'] = True
        self.config = self.machine_config
        self._initialized = False
        self.options = dict(bcp=True, production=False)
        self.clock = ClockBase(self)

        # needed for bcp
        self.settings = Settings()
        self.machine_vars = {}
        self.modes = []

        self.events = EventManager(self)
        self.mode_controller = ModeController(self)
        self.bcp = Bcp(self)
        self.slide_player = MpfSlidePlayer(self)
        self.slide_player.instances['imc'] = dict()

        self.clock.loop.run_until_complete(self.events.post_queue_async("init_phase_1"))
        self.events.process_event_queue()
        self.clock.loop.run_until_complete(self.events.post_queue_async("init_phase_2"))
        self.events.process_event_queue()
        self.clock.loop.run_until_complete(self.events.post_queue_async("init_phase_3"))
        self.events.process_event_queue()
        self.clock.loop.run_until_complete(self.events.post_queue_async("init_phase_4"))
        self.events.process_event_queue()
        self.clock.loop.run_until_complete(self.events.post_queue_async("init_phase_5"))

        self.sm = ScreenManager()
        self.slide_screen = Screen(name="Slide Player")
        self.widget_screen = Screen(name="Widget Player")
        self.sm.add_widget(self.slide_screen)
        self.sm.add_widget(self.widget_screen)
        self.slide_player_code = YamlCodeInput(lexer=YamlLexer(),
                                               tab_width=4)
        self.slide_player_code.bind(on_triple_tap=self.send_slide_to_mc)

        self.slide_player_code.text = '''my_test_slide:
    widgets:
      - type: text
        text: iMC
        color: red
      - type: line
        points: 1, 1, 1, 32, 128, 32, 128, 1, 1, 1
        color: lime
      - type: rectangle
        width: 50
        height: 20
        color: yellow
'''

        self.send_button = Button(text='Send',
                                  size=(150, 60),
                                  size_hint=(None, None),
                                  background_normal='',
                                  background_color=(0, .6, 0, 1),
                                  pos=(0, 1),
                                  pos_hint={'top': 0.1, 'right': 0.95})

        self.send_button.bind(on_press=self.send_slide_to_mc)

        self.slide_screen.add_widget(self.slide_player_code)
        self.slide_screen.add_widget(self.send_button)

        self.slide_player.register_player_events(dict())

    def register_monitor(self, monitor_class, monitor):
        pass

    def build(self):
        return self.sm

    def send_slide_to_mc(self, value):
        del value

        try:
            settings = YamlInterface.process(self.slide_player_code.text)
        except Exception as e:
            msg = str(e).replace('"', '\n')
            Popup(title='Error in your config',
                  content=Label(text=msg, size=(750, 350)),
                  size_hint=(None, None),
                  size=(Window.width, 400)).open()
            return

        try:
            settings = (self.slide_player.validate_config_entry(settings,
                                                                'slides'))
        except Exception as e:
            msg = str(e).replace('"', '\n')
            Popup(title='Error in your config',
                  content=Label(text=msg, size=(750, 350)),
                  size_hint=(None, None),
                  size=(Window.width, 400)).open()
            return

        if self._initialized:
            self.slide_player.clear_context('imc')
        else:
            self._initialized = True
        self.slide_player.play(settings, 'imc', 100)
        self.clock.loop.run_until_complete(asyncio.sleep(.1, loop=self.clock.loop))

    def set_machine_var(self, name, value):
        pass


class YamlCodeInput(CodeInput):

    def insert_text(self, substring, from_undo=False):
        s = substring.replace('\t', '    ')
        return super().insert_text(s, from_undo=from_undo)
