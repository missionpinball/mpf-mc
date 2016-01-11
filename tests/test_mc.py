
from .MpfMcTestCase import KmcTestCase


class TestKmc(KmcTestCase):

    def test_mc_start(self):
        from kivy.core.window import Window
        print(Window.size)
