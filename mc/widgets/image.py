
from kivy.uix.image import Image as KivyImage

from mc.uix.widget import MpfWidget


class Image(MpfWidget, KivyImage):

    def __init__(self, mc, config, slide, mode=None, priority=None):
        self.mc = mc
        self.config = config

        self.size_hint = (None, None)

        super().__init__(mode=mode, priority=priority, slide=slide,
                         config=config)
