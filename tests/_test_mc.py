
from .MpfMcTestCase import MpfMcTestCase


class TestKmc(MpfMcTestCase):

    def test_mc_start(self):
        from kivy.core.window import Window
        print(Window.size)
