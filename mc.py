"""Starts the MPF media controller."""

import argparse
import logging
import os
import socket
import sys
from datetime import datetime

from mc.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util
from mpf.core.config_processor import ConfigProcessor as MpfConfig
from kivy.config import Config
from kivy.logger import Logger
import version
from mc.core.mc import MpfMc
from mc.core.utils import set_machine_path, load_machine_config

parser = argparse.ArgumentParser(description='Starts the MPF Media Controller')

parser.add_argument("machine_path", help="Path of the machine folder.")

parser.add_argument("-l",
                    action="store", dest="logfile",
                    metavar='file_name',
                    default=os.path.join("logs", datetime.now().strftime(
                            "%Y-%m-%d-%H-%M-%S-mc-" + socket.gethostname() +
                            ".log")),
                    help="The name (and path) of the log file")

parser.add_argument("-c",
                    action="store", dest="configfile",
                    default="config", metavar='config_file(s)',
                    help="The name of a config file to load. Default is "
                         "config.yaml. Multiple files can be used via a comma-"
                         "separated list (no spaces between)")

parser.add_argument("-v",
                    action="store_const", dest="loglevel", const=logging.DEBUG,
                    default=logging.INFO, help="Enables verbose logging to the"
                                               " log file")

parser.add_argument("-V",
                    action="store_true", dest="consoleloglevel",
                    default=logging.INFO,
                    help="Enables verbose logging to the console. Do NOT on "
                         "Windows platforms")

parser.add_argument("-C",
                    action="store", dest="mcconfigfile",
                    default=os.path.join("mc", "mcconfig.yaml"),
                    metavar='config_file',
                    help="The MPF framework default config file. Default is "
                         "mc/mcconfig.yaml")

parser.add_argument("--version",
                    action="version", version=version.version_str,
                    help="Displays the MPF, config file, and BCP version info "
                         "and exits")

parser.add_argument("-b",
                    action="store_false", dest="bcp", default=True,
                    help="Do not set up the BCP server threads")

# The following are just included for full compatibility with mpf.py which is
# needed when launching from a batch file or shell script.
parser.add_argument("-x",
                    action="store_const", dest="force_platform",
                    const='virtual', help=argparse.SUPPRESS)

parser.add_argument("-X",
                    action="store_const", dest="force_platform",
                    const='smart_virtual', help=argparse.SUPPRESS)

args = parser.parse_args()
args.configfile = Util.string_to_list(args.configfile)


# Configure logging. Creates a logfile and logs to the console.
# Formatting options are documented here:
# https://docs.python.org/2.7/library/logging.html#logrecord-attributes

# try:
#     os.makedirs('logs')
# except OSError as exception:
#     if exception.errno != errno.EEXIST:
#         raise
#
# logging.basicConfig(level=args.loglevel,
#                     format='%(asctime)s : %(levelname)s : %(name)s : %(
# message)s',
#                     filename=args.logfile,
#                     filemode='w')
#
# # define a Handler which writes INFO messages or higher to the sys.stderr
# console = logging.StreamHandler()
# console.setLevel(args.consoleloglevel)
#
# # set a format which is simpler for console use
# formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')
#
# # tell the handler to use this format
# console.setFormatter(formatter)
#
# # add the handler to the root logger
# logging.getLogger('').addHandler(console)

def preprocess_config(config):
    kivy_config = config['kivy_config']

    try:
        kivy_config['graphics'].update(config['displays']['window'])
    except KeyError:
        pass

    try:
        kivy_config['graphics'].update(config['window'])
    except KeyError:
        pass

    if 'top' in kivy_config['graphics'] and 'left' in kivy_config['graphics']:
        kivy_config['graphics']['position'] = 'custom'

    for section, settings in kivy_config.items():
        for k, v in settings.items():
            try:
                if k in Config[section]:
                    Config.set(section, k, v)
            except KeyError:
                continue


mpf_config = ConfigProcessor.load_config_file(args.mcconfigfile)
machine_path = set_machine_path(args.machine_path,
                                mpf_config['mpf_mc']['paths'][
                                    'machine_files'])

mpf_config = load_machine_config(args.configfile, machine_path,
                                 mpf_config['mpf_mc']['paths'][
                                     'config'], mpf_config)

preprocess_config(mpf_config)


def main():
    # from mc.core.mc import MpfMc

    try:
        MpfMc(options=vars(args), config=mpf_config,
              machine_path=machine_path).run()
        Logger.info("MC run loop ended.")
    except Exception as e:
        Logger.exception("MC: An exception occurred - {}: {}".format(type(e).__name__, str(e)))

    sys.exit()


if __name__ == '__main__':
    main()
