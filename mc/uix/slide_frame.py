from kivy.uix.screenmanager import ScreenManager
from mc.uix.slide import Slide


class SlideFrame(ScreenManager):
    def __init__(self, mc, name):
        super().__init__()
        self.mc = mc
        self.name = name

        mc.targets[name] = self

    @property
    def current_slide(self):
        return self.current_screen

    @current_slide.setter
    def current_slide(self, value):
        self.current_screen = value

    def add_slide(self, name, config, priority=0):
        Slide(mc=self.mc, name=name, target=self.name, config=config)

        if not self.current_slide or priority >= self.current_slide.priority:
            self.current_slide = name
