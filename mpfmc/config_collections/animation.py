from typing import Union, List
from mpfmc.core.config_collection import ConfigCollection

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.uix.widget import Widget   # pylint: disable-msg=cyclic-import,unused-import


class AnimationCollection(ConfigCollection):

    config_section = 'animations'
    collection = 'animations'
    class_label = 'Animations'

    def process_config(self, config: Union[dict, list]) -> List["Widget"]:
        # processes the 'animations' section of a config file to populate the
        # mc.animation_configs dict.

        # config is localized to 'animations' section

        if isinstance(config, dict):
            config = [config]

        # iterate and build our final processed list
        new_list = list()
        for animation in config:
            new_list.append(self.process_animation(animation, self.mc.config_validator))

        return new_list

    @staticmethod
    def process_animation(config: dict, config_validator) -> dict:
        # config is localized to a single animation's settings within a list

        # str means it's a named animation
        if isinstance(config, str):
            config = dict(named_animation=config)

        # dict is settings for an animation
        elif isinstance(config, dict):
            config_validator.validate_config('widgets:animations', config)

            if len(config['property']) > len(config['value']):
                raise ValueError('Animation must have at least the same number of settings '
                                 'in its "value" list ({}) as the number settings '
                                 'in its "property" list ({}).'.
                                 format(config['value'], config['property']))

        return config


CollectionCls = AnimationCollection
