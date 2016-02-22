# How to add a test:
# Copy this file
# Rename TestTemplate to TestWhatever in line 9
# Rename machine path and config file in lines 11 and 14

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestTemplate(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/test_template'

    def get_config_file(self):
        return 'test_template.yaml'

    def test_something(self):
        pass
