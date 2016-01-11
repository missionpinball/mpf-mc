from kivy.properties import NumericProperty
from kivy.properties import ObjectProperty

from kivy.animation import Animation
from mpf.system.config import CaseInsensitiveDict


class MpfWidget(object):
    """Mixin class that's used to extend all the Kivy widget base classes with
    a few extra attributes and methods we need for everything to work with MPF.

    """
    mode = ObjectProperty(None, allownone=True)
    """:class:`Mode` object, which is the mode that created this widget."""

    priority = NumericProperty(0)
    """Priority of this widget."""

    config = CaseInsensitiveDict()
    """Dict which holds the settings for this widget."""

    screen = None
    """Screen that this widget will be used with."""

    def __init__(self, mode, priority, screen, config, **kwargs):
        super().__init__()

        self.screen = screen

        if '_parsed_' in config:
            self.config = config
        else:
            self.config = MpfWidget.parse_config(config)

        for k, v in self.config.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if 'animation' in config:
            if 'entrance' in config['animation']:
                for prop, settings in config['animation']['entrance'].items():

                    if 'start' in settings:
                        if hasattr(self, prop):
                            setattr(self, prop, settings['start'])

                    anim = Animation(t=settings['function'],
                                     duration=settings['time'],
                                     **{prop: settings['end']})
                    anim.start(self)

    def on_size(self, *args):

        self.pos = self.screen.set_position(self.screen, self,
                                            self.config['x'],
                                            self.config['y'],
                                            self.config['h_pos'],
                                            self.config['v_pos'])

    @staticmethod
    def parse_config(config):
        """Processes a dict config of screen settings and converts it into
        the format the widget class actually needs. Also checks & validates it.

        Args:
            config: The incoming dict to process.

        Returns:
            dict: Parsed dict, includes the _parsed_ key which indicates it's
                ready to go.

        """

        # run through the config file validator

        # run each widget through the widget config parser?
        # should there only be one instance of each widget?

        return config
