from kivy.uix.screenmanager import ScreenManager as KivyScreenManager


class ScreenManager(KivyScreenManager):
    def __init__(self, mc):

        super().__init__()

        self.mc = mc
