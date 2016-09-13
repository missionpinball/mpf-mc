from mpf.tests.MpfTestCase import MpfTestCase


class MpfSlideTestCase(MpfTestCase):

    def assertSlideOnTop(self, slide_name, target="default"):
        if not self.mc.targets[target].current_slide:
            self.fail("There is no slide on target {}".format(target))
        self.assertEqual(slide_name, self.mc.targets[target].current_slide.name)

    def assertTextOnTopSlide(self, text, target="default"):
        if not self.mc.targets[target].current_slide:
            self.fail("There is no slide on target {}".format(target))
        self.assertTextInSlide(text, self.mc.targets[target].current_slide.name)

    def assertTextNotOnTopSlide(self, text, target="default"):
        if not self.mc.targets[target].current_slide:
            return
        self.assertTextNotInSlide(text, self.mc.targets[target].current_slide.name)

    def assertSlideActive(self, slide_name):
        self.assertIn(slide_name, self.mc.active_slides, "Slide {} is not active.".format(slide_name))

    def assertSlideNotActive(self, slide_name):
        self.assertNotIn(slide_name, self.mc.active_slides, "Slide {} is active but should not.".format(slide_name))

    def _get_texts_from_slide(self, slide):
        texts = []
        for children in slide.children:
            if children.children:
                texts.extend(self._get_texts_from_slide(children))
            if hasattr(children, "text"):
                texts.append(children.text)

        return texts

    def assertTextInSlide(self, text, slide_name):
        self.assertSlideActive(slide_name)
        self.assertIn(text, self._get_texts_from_slide(self.mc.active_slides[slide_name]),
                      "Text {} not found in slide {}.".format(text, slide_name))

    def assertTextNotInSlide(self, text, slide_name):
        self.assertSlideActive(slide_name)
        self.assertNotIn(text, self._get_texts_from_slide(self.mc.active_slides[slide_name]),
                         "Text {} found in slide {} but should not be there.".format(text, slide_name))