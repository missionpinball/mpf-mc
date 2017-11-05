from mpf.tests.MpfMachineTestCase import BaseMpfMachineTestCase
from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class FullMachineTestCase(BaseMpfMachineTestCase, MpfIntegrationTestCase, MpfSlideTestCase):

    """MPF + MC machine test case."""

    fps = 3

    pass
