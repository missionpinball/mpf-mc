from tests.MpfMcTestCase import MpfMcTestCase


class TestAnimation(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/animation'

    def get_config_file(self):
        return 'test_animation.yaml'

    def test_animation_config_processing(self):
        # The animation sections are more complex than regular sections,
        # so they do some more complex pre-processing before they go to the
        # config file validator.

        # slide def, list of animations
        s1w0 = self.mc.slide_configs['slide1'][0]['animations']

        self.assertIs(type(s1w0['entrance']), list)
        self.assertEqual(len(s1w0['entrance']), 2)
        self.assertIs(type(s1w0['entrance'][0]), dict)
        self.assertIs(type(s1w0['entrance'][1]), dict)
        self.assertEqual(s1w0['entrance'][0]['value'], [101])
        self.assertEqual(s1w0['entrance'][1]['value'], [100])

        # slide def, single dict animation
        s2w0 = self.mc.slide_configs['slide2'][0]['animations']

        self.assertIs(type(s2w0['entrance2']), list)
        self.assertEqual(len(s2w0['entrance2']), 1)
        self.assertIs(type(s2w0['entrance2'][0]), dict)
        self.assertEqual(s2w0['entrance2'][0]['value'], [0 ,0])
        self.assertEqual(s2w0['entrance2'][0]['property'], ['x', 'y'])

        # slide def, 1 event, list of 2 named animations
        s3w0 = self.mc.slide_configs['slide3'][0]['animations']
        self.assertIs(type(s3w0['entrance3']), list)
        self.assertEqual(len(s3w0['entrance3']), 2)
        self.assertIs(type(s3w0['entrance3'][0]), dict)
        self.assertIs(type(s3w0['entrance3'][1]), dict)
        self.assertEqual(s3w0['entrance3'][0]['named_animation'], 'fade_in')
        self.assertEqual(s3w0['entrance3'][1]['named_animation'], 'multi')

        # slide def, 2 events, list of named animations
        s4w0 = self.mc.slide_configs['slide4'][0]['animations']
        self.assertIs(type(s4w0['entrance4']), list)
        self.assertEqual(len(s4w0['entrance4']), 2)
        self.assertIs(type(s4w0['entrance4'][0]), dict)
        self.assertIs(type(s4w0['entrance4'][1]), dict)
        self.assertEqual(s4w0['entrance4'][0]['named_animation'], 'fade_in')
        self.assertEqual(s4w0['entrance4'][1]['named_animation'], 'multi')

        self.assertIs(type(s4w0['some_event4']), list)
        self.assertEqual(len(s4w0['some_event4']), 1)
        self.assertIs(type(s4w0['some_event4'][0]), dict)
        self.assertEqual(s4w0['some_event4'][0]['named_animation'], 'multi')

        # slide def, 2 events, 1 named animation, 1 dict
        s5w0 = self.mc.slide_configs['slide5'][0]['animations']
        self.assertIs(type(s5w0['entrance5']), list)
        self.assertEqual(len(s5w0['entrance5']), 2)
        self.assertIs(type(s5w0['entrance5'][0]), dict)
        self.assertIs(type(s5w0['entrance5'][1]), dict)
        self.assertEqual(s5w0['entrance5'][0]['named_animation'], 'fade_in')
        self.assertEqual(s5w0['entrance5'][1]['named_animation'], 'multi')

        self.assertIs(type(s5w0['event5']), list)
        self.assertEqual(len(s5w0['event5']), 1)
        self.assertIs(type(s5w0['event5'][0]), dict)
        self.assertEqual(s5w0['event5'][0]['value'], [98])

        # slide with 1 widget with no animations
        self.assertIn('animations', self.mc.slide_configs['slide6'][0])
        self.assertIsNone(self.mc.slide_configs['slide6'][0]['animations'])

        # Move on to test the named animations section

        self.assertEqual(len(self.mc.animation_configs), 2)

        # single animation, dict
        self.assertIs(type(self.mc.animation_configs['fade_in']), list)
        self.assertEqual(len(self.mc.animation_configs['fade_in']), 1)
        self.assertIs(type(self.mc.animation_configs['fade_in'][0]), dict)
        self.assertEqual(self.mc.animation_configs['fade_in'][0]['property'],
                         ['opacity'])
        self.assertEqual(self.mc.animation_configs['fade_in'][0]['easing'],
                         'linear')

        # two animations, list
        self.assertIs(type(self.mc.animation_configs['multi']), list)
        self.assertEqual(len(self.mc.animation_configs['multi']), 2)
        self.assertIs(type(self.mc.animation_configs['multi'][0]), dict)
        self.assertEqual(self.mc.animation_configs['multi'][0]['property'],
                         ['height'])
        self.assertEqual(self.mc.animation_configs['multi'][0]['easing'],
                         'linear')
        self.assertIs(type(self.mc.animation_configs['multi'][1]), dict)
        self.assertEqual(self.mc.animation_configs['multi'][1]['property'],
                         ['width'])
        self.assertEqual(self.mc.animation_configs['multi'][1]['easing'],
                         'linear')

    def test_animation_entrance(self):
        self.mc.events.post('show_slide7')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide7')

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0]
        self.assertTrue(widget.text == 'slide7')

        # make sure it's animating as we expect
        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': 400})

        # wait for it to finish and make sure it stopped
        self.advance_time(.5)
        self.assertIsNone(widget.animation.have_properties_to_animate(widget))

    def test_animation_from_event(self):
        # This will also test multiple animated properties on the same entry

        self.mc.events.post('show_slide2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0]
        self.assertTrue(widget.text == 'ANIMATION TEST')

        # make sure it's not animating
        self.assertIsNone(widget.animation)

        # post the event to animate it
        self.mc.events.post('entrance2')
        self.advance_time()

        # make sure it's doing what we expect
        self.assertEqual(widget.animation.duration, 1)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties,
                         {'x': 0, 'y': 0})
        self.advance_time(.5)
        self.assertLess(widget.x, 100)
        self.assertLess(widget.y, 200)

    def test_named_animation(self):
        self.mc.events.post('show_slide3')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide3')

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0]
        self.assertTrue(widget.text == 'text3')

        # make sure it's not animating
        self.assertIsNone(widget.animation)

        # post the event to animate it
        self.mc.events.post('entrance3')
        self.advance_time()
