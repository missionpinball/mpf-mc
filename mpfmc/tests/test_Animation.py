from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


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
        s1w0 = self.mc.slides['slide1']['widgets'][0]['animations']

        self.assertIs(type(s1w0['show_slide']), list)
        self.assertEqual(len(s1w0['show_slide']), 2)
        self.assertIs(type(s1w0['show_slide'][0]), dict)
        self.assertIs(type(s1w0['show_slide'][1]), dict)
        self.assertEqual(s1w0['show_slide'][0]['value'], ['101'])
        self.assertEqual(s1w0['show_slide'][1]['value'], ['100'])

        # slide def, single dict animation
        s2w0 = self.mc.slides['slide2']['widgets'][0]['animations']

        self.assertIs(type(s2w0['entrance2']), list)
        self.assertEqual(len(s2w0['entrance2']), 1)
        self.assertIs(type(s2w0['entrance2'][0]), dict)
        self.assertEqual(s2w0['entrance2'][0]['value'], ['0' ,'0'])
        self.assertEqual(s2w0['entrance2'][0]['property'], ['x', 'y'])

        # slide def, 1 event, list of 2 named animations
        s3w0 = self.mc.slides['slide3']['widgets'][0]['animations']
        self.assertIs(type(s3w0['entrance3']), list)
        self.assertEqual(len(s3w0['entrance3']), 2)
        self.assertIs(type(s3w0['entrance3'][0]), dict)
        self.assertIs(type(s3w0['entrance3'][1]), dict)
        self.assertEqual(s3w0['entrance3'][0]['named_animation'], 'fade_in')
        self.assertEqual(s3w0['entrance3'][1]['named_animation'], 'multi')

        # slide def, 2 events, list of named animations
        s4w0 = self.mc.slides['slide4']['widgets'][0]['animations']
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
        s5w0 = self.mc.slides['slide5']['widgets'][0]['animations']
        self.assertIs(type(s5w0['entrance5']), list)
        self.assertEqual(len(s5w0['entrance5']), 2)
        self.assertIs(type(s5w0['entrance5'][0]), dict)
        self.assertIs(type(s5w0['entrance5'][1]), dict)
        self.assertEqual(s5w0['entrance5'][0]['named_animation'], 'fade_in')
        self.assertEqual(s5w0['entrance5'][1]['named_animation'], 'multi')

        self.assertIs(type(s5w0['event5']), list)
        self.assertEqual(len(s5w0['event5']), 1)
        self.assertIs(type(s5w0['event5'][0]), dict)
        self.assertEqual(s5w0['event5'][0]['value'], ['98'])

        # slide with 1 widget with no animations
        self.assertIn('animations', self.mc.slides['slide6']['widgets'][0])
        self.assertIsNone(self.mc.slides['slide6']['widgets'][0]['animations'])

        # Move on to test the named animations section

        self.assertEqual(len(self.mc.animations), 3)

        # single animation, dict
        self.assertIs(type(self.mc.animations['fade_in']), list)
        self.assertEqual(len(self.mc.animations['fade_in']), 1)
        self.assertIs(type(self.mc.animations['fade_in'][0]), dict)
        self.assertEqual(self.mc.animations['fade_in'][0]['property'],
                         ['opacity'])
        self.assertEqual(self.mc.animations['fade_in'][0]['easing'],
                         'linear')

        # two animations, list, with values as percent strings
        self.assertIs(type(self.mc.animations['multi']), list)
        self.assertEqual(len(self.mc.animations['multi']), 2)
        self.assertIs(type(self.mc.animations['multi'][0]), dict)
        self.assertEqual(self.mc.animations['multi'][0]['property'],
                         ['y'])
        self.assertEqual(self.mc.animations['multi'][0]['easing'],
                         'linear')
        self.assertIs(type(self.mc.animations['multi'][1]), dict)
        self.assertEqual(self.mc.animations['multi'][1]['property'],
                         ['x'])
        self.assertEqual(self.mc.animations['multi'][1]['easing'],
                         'linear')

    def test_reset_animations_pre_show_slide(self):
        self.mc.events.post('show_slide13')
        self.advance_time(.1)

        widget = self.mc.targets['default'].current_slide.children[0].children[0]

        self.assertAlmostEqual(-130, widget.x, delta=20)
        self.advance_time(.5)
        self.assertAlmostEqual(-8, widget.x, delta=20)
        self.advance_time(.5)
        self.assertEqual(100.0, widget.x)

        self.mc.events.post('show_base_slide')
        self.advance_time()

        # animations should start from orig position
        self.mc.events.post('show_slide13')
        self.advance_time(.1)
        self.assertAlmostEqual(-130, widget.x, delta=20)
        self.advance_time(.5)
        self.assertAlmostEqual(-8, widget.x, delta=20)
        self.advance_time(.5)
        self.assertEqual(100.0, widget.x)

    def test_reset_animations_slide_play(self):
        self.mc.events.post('show_slide14')
        self.advance_time(.1)

        widget = self.mc.targets['default'].current_slide.children[0].children[0]

        self.assertAlmostEqual(-108, widget.x, delta=20)
        self.advance_time(.5)
        self.assertAlmostEqual(-8, widget.x, delta=30)
        self.advance_time(.5)
        self.assertEqual(100.0, widget.x)

        self.mc.events.post('show_base_slide')
        self.advance_time()

        # animations should start from orig position
        self.mc.events.post('show_slide14')
        self.advance_time(.1)
        self.assertAlmostEqual(-108, widget.x, delta=20)
        self.advance_time(.5)
        self.assertAlmostEqual(-8, widget.x, delta=20)
        self.advance_time(.5)
        self.assertEqual(100.0, widget.x)

    def test_reset_animations_standard_event(self):
        self.mc.events.post('show_slide15')
        self.advance_time(.1)

        widget = self.mc.targets['default'].current_slide.children[0].children[0]

        self.assertAlmostEqual(-132, widget.x, delta=20)
        self.advance_time(.5)
        self.assertAlmostEqual(-8, widget.x, delta=20)
        self.advance_time(.5)
        self.assertEqual(100.0, widget.x)

        self.mc.events.post('event1')
        self.advance_time()
        self.assertAlmostEqual(-132, widget.x, delta=20)

    def test_animation_show_slide(self):
        self.mc.events.post('show_slide7')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide7')

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'TEST ANIMATION ON show_slide')

        # make sure it's animating as we expect
        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': 400})

        # wait for it to finish and make sure it stopped
        self.advance_time(.5)
        self.assertIsNone(widget.animation.have_properties_to_animate(widget))

    def test_animation_show_slide_with_transition(self):
        self.mc.events.post('show_base_slide')
        self.advance_time()

        self.mc.events.post('show_slide10')
        self.advance_time()

        # transition is 1 sec, so animation should not start until that's done
        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'ANIMATION show_slide')
        self.assertFalse(widget.animation)

        self.advance_time(1)
        # slide should be fully transitioned in, so animation should be started

        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': 400})

    def test_animation_pre_show_slide(self):
        self.mc.events.post('show_base_slide')
        self.advance_time()

        self.mc.events.post('show_slide9')
        self.advance_time()

        # transition is 1 sec, but animation should run at the same time
        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'ANIMATION pre_show_slide')

        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': 400})

    def test_animation_pre_slide_leave(self):
        self.mc.events.post('show_slide11')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'ANIMATION pre_slide_leave')

        self.mc.events.post('show_base_slide_with_transition')
        self.advance_time()

        # transition is 1 sec, but leave animation should run at the same time
        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': -400})

        # todo this test passes and the events fire, but visually it doesn't
        # seem to work. Bug in kivy? Or maybe it's by design?

    def test_animation_slide_leave(self):
        self.mc.events.post('show_slide12')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'ANIMATION slide_leave')
        self.assertFalse(widget.animation)

        self.mc.events.post('show_base_slide_with_transition')
        self.advance_time()

        self.advance_time(1)
        # slide should be fully transitioned out, so animation should be
        # started

        self.assertTrue(widget.animation)
        self.assertEqual(widget.animation.duration, 0.5)
        self.assertTrue(widget.animation.have_properties_to_animate(widget))
        self.assertEqual(widget.animation.animated_properties, {'x': 0})

    def test_animation_from_event(self):
        # This will also test multiple animated properties on the same entry

        self.mc.events.post('show_slide2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0].children[0]
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
        widget = self.mc.targets['default'].current_slide.children[0].children[0]
        self.assertTrue(widget.text == 'text3')

        # make sure it's not animating
        self.assertIsNone(widget.animation)

        # make sure initial values are set
        self.assertEqual(widget.opacity, 0)
        self.assertEqual(widget.x, 177)
        self.assertEqual(widget.y, 138)

        # post the event to animate it
        self.mc.events.post('entrance3')
        self.advance_time(1.1)

        # post-animation opacity should be 1
        self.assertEqual(widget.opacity, 1)

        # advance past animation step 2
        self.advance_time(1.2)

        # check properties
        self.assertEqual(widget.x, 0)
        self.assertEqual(widget.y, 0)

        # add widget2
        self.mc.events.post('show_widget2')
        self.advance_time()

        # grab this widget
        widget = self.mc.targets['default'].current_slide.children[0].children[1]
        self.assertTrue(widget.text == 'widget2')

        # make sure it's not animating
        self.assertIsNone(widget.animation)

        # make sure initial values are set
        self.assertEqual(widget.opacity, 0)
        self.assertEqual(widget.x, 164.5)
        self.assertEqual(widget.y, 138)

        # post the event to animate it
        self.mc.events.post('animate_widget2')
        self.advance_time(1.1)

        # post-animation opacity should be 1
        self.assertEqual(widget.opacity, 1)

        # advance past animation step 2
        self.advance_time(1.2)

        # check properties
        self.assertEqual(widget.x, 0)
        self.assertEqual(widget.y, 0)

        self.mc.events.post('pulse_widget2')
        self.advance_time(1)

    def test_add_to_slide_from_offscreen(self):
        self.mc.events.post('show_slide8')
        self.advance_time()

        self.mc.events.post('show_widget1')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.children[0].children[1]
        self.assertEqual('WIDGET 1', widget.text)
        self.assertEqual(widget.pos[0], -144.5)

        self.mc.events.post('move_on_slide')
        self.advance_time(.6)
        self.assertEqual(widget.pos[0], 100)

        self.mc.events.post('move_off_slide')
        self.advance_time(.6)
        self.assertEqual(widget.pos[0], -100)
