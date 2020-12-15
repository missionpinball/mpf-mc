from mpf.tests.MpfTestCase import MpfTestCase
from mpfmc.widgets.display import DisplayWidget
from mpfmc.uix.widget import WidgetContainer

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.uix.slide import Slide       # pylint: disable-msg=cyclic-import,unused-import


class MpfSlideTestCase(MpfTestCase):

    def assertSlideOnTop(self, slide_name: str, target: str="default"):
        if not self.mc.targets[target].current_slide:
            self.fail("There is no slide on target {}".format(target))
        self.assertEqual(slide_name, self.mc.targets[target].current_slide.name)

    def assertTextOnTopSlide(self, text: str, target: str="default"):
        if not self.mc.targets[target].current_slide:
            self.fail("There is no slide on target {}".format(target))
        self.assertTextInSlide(text, self.mc.targets[target].current_slide.name)

    def assertTextNotOnTopSlide(self, text: str, target: str="default"):
        if not self.mc.targets[target].current_slide:
            return
        self.assertTextNotInSlide(text, self.mc.targets[target].current_slide.name)

    def assertSlideActive(self, slide_name: str):
        self.assertIn(slide_name, self.mc.active_slides, "Slide {} is not active.".format(slide_name))

    def assertSlideNotActive(self, slide_name: str):
        self.assertNotIn(slide_name, self.mc.active_slides, "Slide {} is active but should not.".format(slide_name))

    def _get_texts_from_slide(self, slide: "Slide"):
        texts = []
        for child in slide.children:
            if isinstance(child, WidgetContainer) and child.widget and \
                    isinstance(child.widget, DisplayWidget) and child.widget.current_slide:
                texts.extend(self._get_texts_from_slide(child.widget.current_slide))
            if isinstance(child, WidgetContainer) and child.widget and hasattr(child.widget, "text"):
                texts.append(child.widget.text)

        return texts

    def assertTextInSlide(self, text: str, slide_name: str):
        self.assertSlideActive(slide_name)
        self.assertIn(text, self._get_texts_from_slide(self.mc.active_slides[slide_name]),
                "Text {} not found in slide {}. Text found: {}".format(text, slide_name, self._get_texts_from_slide(self.mc.active_slides[slide_name])))

    def assertTextNotInSlide(self, text: str, slide_name: str):
        self.assertSlideActive(slide_name)
        self.assertNotIn(text, self._get_texts_from_slide(self.mc.active_slides[slide_name]),
                         "Text {} found in slide {} but should not be there.".format(text, slide_name))
