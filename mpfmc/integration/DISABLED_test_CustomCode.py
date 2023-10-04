# Oct 3 2023, I can't figure out why this fails. Custom code definitely works for the MC (mc_demo uses it)
# I can't see where the on_connect() method is called, maybe that needs to be updated?

"""Test custom code in MC."""
from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase


class TestCustomCode(MpfIntegrationTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/custom_code/'

    def test_asd(self):
        self.mock_event("my_return_event")

        # post event in MPF
        self.post_event("test_event")
        self.advance_time_and_run(.1)

        self.assertEventCalled("my_return_event")
