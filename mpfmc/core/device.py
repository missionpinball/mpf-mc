""" Contains the Device base class"""
from collections import OrderedDict

from mpf.core.device_manager import DeviceManager as MpfDeviceManager
from mpf.core.device_manager import DeviceCollection

import logging

from mpf.core.utility_functions import Util


class Device(object):
    """Devices in MPF-MC are similar to abstract devices in MPF, except
    there are no control events"""

    config_section = None  # String of the config section name
    collection = None  # String name of the collection
    class_label = None  # String of the friendly name of the device class

    @classmethod
    def device_class_init(cls, mc):
        cls.mc = mc
        cls.mc.mode_controller.register_load_method(
            cls.create_devices_from_mode_config, cls.config_section)

    @classmethod
    def process_config(cls, config):
        raise NotImplementedError

    @classmethod
    def create_devices_from_mode_config(cls, config, mode, mode_path,
                                        root_config_dict):
        cls.mc.device_manager.create_devices(cls.collection, config)

    def __repr__(self):
        return '<{self.class_label}.{self.name}>'.format(self=self)

    def enable_debugging(self):
        self.log.debug("Enabling debug logging")
        self.debug = True
        self._enable_related_device_debugging()

    def disable_debugging(self):
        self.log.debug("Disabling debug logging")
        self.debug = False
        self._disable_related_device_debugging()

    def _enable_related_device_debugging(self):
        pass

    def _disable_related_device_debugging(self):
        pass

    @classmethod
    def get_config_info(cls):
        return cls.collection, cls.config_section

    def device_added_to_mode(self, mode, player):
        # Called when a device is created by a mode
        pass

    def remove(self):
        raise NotImplementedError(
            '{} does not have a remove() method'.format(self.name))


class DeviceManager(MpfDeviceManager):

    def __init__(self, machine):


        self.machine = machine
        self.log = logging.getLogger('DeviceManager')

        self.collections = OrderedDict()
        self.device_classes = OrderedDict()  # collection_name: device_class

        self.machine.events.add_handler('init_phase_1',
                                        self._load_device_modules)

    def _load_device_modules(self):
        self.log.info("Loading devices...")
        self.machine.machine_config['mpf-mc']['device_modules'] = (
            self.machine.machine_config['mpf-mc']['device_modules'].split(' '))

        for device_type in self.machine.machine_config['mpf-mc']['device_modules']:
            device_cls = Util.string_to_class("mpfmc.devices." + device_type)
            device_cls.device_class_init(self.machine)

        for device_type in self.machine.machine_config['mpf-mc']['device_modules']:
            device_cls = Util.string_to_class("mpfmc.devices." + device_type)
            collection_name, config = device_cls.get_config_info()

            self.device_classes[collection_name] = device_cls

            # create the collection
            collection = DeviceCollection(self.machine, collection_name,
                                          device_cls.config_section)

            self.collections[collection_name] = collection
            setattr(self.machine, collection_name, collection)

            # Get the config section for these devices
            config = self.machine.machine_config.get(config, None)

            # create the devices
            if config:
                self.create_devices(collection_name, config)

    def create_devices(self, collection_name, config, validate=True):
        cls = self.device_classes[collection_name]

        collection = getattr(self.machine, collection_name)

        # create the devices
        for name, settings in config.items():

            if not settings:
                raise AssertionError("Device '{}' has an empty config."
                                     .format(name))

            collection[name] = cls.process_config(settings)
