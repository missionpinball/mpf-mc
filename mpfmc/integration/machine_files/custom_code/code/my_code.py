from mpfmc.core.custom_code import CustomCode


class MyCode(CustomCode):

    def on_connect(self, **kwargs):
        self.add_mpf_event_handler("test_event", self._my_handler)

    def _my_handler(self, **kwargs):
        del kwargs
        self.post_event_to_mpf_and_mc("my_return_event")
