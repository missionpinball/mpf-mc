from mpfmc.core.mc_custom_code import McCustomCode


class MyCode(McCustomCode):

    def on_connect(self, **kwargs):
        self.add_mpf_event_handler("test_event", self._my_handler)

    def _my_handler(self, **kwargs):
        del kwargs
        self.post_event_to_mpf_and_mc("my_return_event")
