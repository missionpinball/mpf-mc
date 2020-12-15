from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.config_collection import ConfigCollection


class SoundLoopSetCollection(ConfigCollection):

    config_section = 'sound_loop_sets'
    collection = 'sound_loop_sets'
    class_label = 'SoundLoopSets'

    def __init__(self, mc, collection, config_section):
        super().__init__(mc, collection, config_section)

        self._validate_handler = None

    def create_entries(self, config: dict, **kwargs) -> None:
        # config is localized to this collection's section
        del kwargs

        # No need to create entries if sound system is not enabled
        if self.mc.sound_system is None or self.mc.sound_system.audio_interface is None:
            self.machine.log.info("Unable to create sound_loop_sets - sound system is not available")
            return

        for name, settings in config.items():
            try:
                self[name] = self.process_config(settings)
            except (AudioException, ValueError) as ex:
                raise ValueError("An error occurred while processing the '{}' entry in "
                                 "the sound_loop_sets config collection: {}".format(name, ex))

        # Validation of referenced sound assets must be completed after all
        # assets have been loaded (can use the init_done event for that)
        self._validate_handler = self.mc.events.add_handler("init_done", self._validate_sound_assets)

    def validate_entries_from_root_config(self, **kwargs):
        """Do nothing here."""

    def process_config(self, config: dict) -> dict:
        # processes the 'sound_loop_sets' section of a config file to populate the
        # mc.sound_loop_sets dict.

        # config is localized to 'sound_loop_sets' section
        return self.process_loop_set(config)

    def process_loop_set(self, config: dict) -> dict:
        # config is localized to a single sound loop set settings within a list

        self.mc.config_validator.validate_config('sound_loop_sets', config)

        # Clamp volume between 0 and 1
        if 'volume' in config and config['volume']:
            if config['volume'] < 0:
                config['volume'] = 0
            elif config['volume'] > 1:
                config['volume'] = 1

        # Validate optional layers
        if 'layers' in config:
            for layer in config["layers"]:
                self.mc.config_validator.validate_config('sound_loop_sets:layers', layer)

                # Clamp layer volume between 0 and 1
                if layer['volume'] < 0:
                    layer['volume'] = 0
                elif layer['volume'] > 1:
                    layer['volume'] = 1

        return config

    def _validate_sound_assets(self, **kwargs) -> None:
        """Validate the referenced sound assets in the loop set layers.

        Notes:
            This must be performed after all the sound assets have been loaded.
        """
        del kwargs
        if self._validate_handler:
            self.mc.events.remove_handler(self._validate_handler)

        if hasattr(self.mc, 'sounds'):
            for name, config in self.items():
                # Validate sound setting (make sure only valid sound assets are referenced)
                if config["sound"] not in self.mc.sounds:
                    raise ValueError("The '{}' sound_loop_set references an invalid sound asset "
                                     "name '{}' in its sound setting".format(name, config["sound"]))
                if self.mc.sounds[config["sound"]].streaming:
                    raise ValueError("The '{}' sound_loop_set references a streaming sound asset "
                                     "'{}' in its sound setting (only in-memory sounds are "
                                     "supported in loop sets)".format(name, config["sound"]))

                # Validate sound settings in layers (make sure only valid sound assets are referenced)
                for layer in config["layers"]:
                    if layer["sound"] not in self.mc.sounds:
                        raise ValueError("The '{}' sound_loop_set references an invalid sound asset "
                                         "name '{}' in one of its layers".format(name, layer["sound"]))
                    if self.mc.sounds[layer["sound"]].streaming:
                        raise ValueError("The '{}' sound_loop_set references a streaming sound asset "
                                         "'{}' in one of its layers (only in-memory sounds are "
                                         "supported in loop sets)".format(name, layer["sound"]))


CollectionCls = SoundLoopSetCollection
