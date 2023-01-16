from kivy.properties import DictProperty
from kivy.properties import NumericProperty
from kivy.uix.effectwidget import EffectBase

class LinearGradientEffect(EffectBase):
    """GLSL effect to apply a linear gradient to a texture."""

    color_stops = DictProperty()
    '''This defines the colors of the gradient at each point.

    The key of this dictionary is the position [0, 1] along the gradient and the value is the
    RGBA color at that position.
    '''

    angle = NumericProperty(0.0)
    '''This defines the angle of the gradient.'''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_color_stops(self, *args):
        self.do_glsl()

    def on_angle(self, *args):
        self.do_glsl()

    def do_glsl(self):
        linear_gradient_stops_glsl = self.__create_gradient_stops_glsl()
        self.glsl = linear_gradient_glsl.format(linear_gradient_stops_glsl, float(self.angle))

    def __create_gradient_stops_glsl(self):
        sorted_positions = sorted(self.color_stops)
        positions = len(sorted_positions)
        
        if not positions:
            return ""
        elif positions == 1:
            first_color = next(iter(self.color_stops.values()))
            return "gradient_color = {};".format(self.__rgba_list_to_vec4_glsl(first_color))
        
        stops = list()
        for current_stop_index in range(1, len(sorted_positions)):
            previous_stop_index = current_stop_index - 1
            
            previous_position = sorted_positions[previous_stop_index]
            current_position = sorted_positions[current_stop_index]
            
            previous_color = self.__rgba_list_to_vec4_glsl(self.color_stops[previous_position]) 
            current_color = self.__rgba_list_to_vec4_glsl(self.color_stops[current_position])
            
            stop_glsl = self.__create_gradient_stop_glsl(
                    "gradient_color" if current_stop_index > 1 else previous_color,
                    current_color,
                    previous_position,
                    current_position)
            
            stops.append(stop_glsl)
        
        return "\n".join(stops)

    def __create_gradient_stop_glsl(self, old_color, new_color, old_position, new_position):
        return "gradient_color = mix({}, {}, smoothstep({}, {}, position));".format(
                old_color,
                new_color,
                float(old_position),
                float(new_position))

    def __rgba_list_to_vec4_glsl(self, channels):
        red = float(channels[0])
        green = float(channels[1])
        blue = float(channels[2])
        alpha = float(channels[3])
        
        return "vec4({}, {}, {}, {})".format(red, green, blue, alpha)


linear_gradient_glsl = '''
        vec4 linear_gradient_color(float position)
        {{
            vec4 gradient_color = vec4(1.0);
            {}
            return gradient_color;
        }}
        
        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            // To apply the gradient at an angle, we convert the UV coordinates to polar, rotate
            // the point by the desired angle, then convert back to cartesian and use either the
            // x or y axis as the gradient position. A linear gradient changes color along one axis
            // only so it doesn't matter which axis we use to sample the gradient; however, it will
            // impact what the default angle of the gradient is when rendered.
            
            // Unlike most high-level languages, GLSL trig functions operate in radians not degrees
            float gradient_angle = radians({});
            
            // To convert the UV to polar, we must first shift it so the origin is in the center,
            // otherwise we would be constrained to one quarter of the coordinate space since UVs
            // are never negative.
            tex_coords -= 0.5;
            
            // Next, we convert the coordinates to polar
            float theta = atan(tex_coords.y, tex_coords.x);
            float distance = length(tex_coords);
            
            // Now we apply the desired angle offset, convert back to cartesian, move the
            // origin back to the lower-left to make this a valid UV, and finally sample the
            // x-coordinate to use it as the gradient position.
            // 
            // Since we're only sampling the x-coordinate, we don't need worry about computing the
            // y-coordinate in cartesian. We choose to sample x here instead of y because sampling
            // x will result in a horizonal gradient with the 0 position on the left. A horizontal
            // gradient with 0 on the left matches how gradients are represented in most image
            // editing software so this may be more intuitive as the default.
            float gradient_position = cos(theta + gradient_angle) * distance + 0.5;
            
            vec4 gradient_color = linear_gradient_color(gradient_position);
            
            // Perform a 'multiply' blend mode. Other blend modes could be added later but multiply
            // is simple and applicable to many use-cases.
            return color * gradient_color;
        }}
        '''

effect_cls = LinearGradientEffect
name = 'linear_gradient'
