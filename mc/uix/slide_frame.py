from kivy.uix.screenmanager import ScreenManager


class SlideFrame(ScreenManager):
    def __init__(self, mc):

        super().__init__()

        self.mc = mc
