from mpfmc.core.utils import percent_to_float
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestUtils(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/utils'

    def get_config_file(self):
        return 'test_utils.yaml'

    def test_percent_to_float(self):
        num = 1
        total = 1
        self.assertEqual(percent_to_float(num, total), 1.0)

        num = 1
        total = 2
        self.assertEqual(percent_to_float(num, total), 1.0)

        num = 0
        total = 2
        self.assertEqual(percent_to_float(num, total), 0.0)

        num = '1'
        total = 1
        self.assertEqual(percent_to_float(num, total), 1.0)

        num = '1'
        total = 2
        self.assertEqual(percent_to_float(num, total), 1.0)

        num = '0'
        total = 2
        self.assertEqual(percent_to_float(num, total), 0.0)

        num = '100%'
        total = 1
        self.assertEqual(percent_to_float(num, total), 1.0)

        num = '100%'
        total = 2
        self.assertEqual(percent_to_float(num, total), 2.0)

        num = '0%'
        total = 2
        self.assertEqual(percent_to_float(num, total), 0.0)

        num = '25%'
        total = 800
        self.assertEqual(percent_to_float(num, total), 200.0)

        num = '200%'
        total = 1
        self.assertEqual(percent_to_float(num, total), 2.0)
