"""Starts the MPF media controller."""

import argparse
import logging
import os
import socket
import sys
import threading
from datetime import datetime
import time
import errno
import psutil
from mpf.core.config_loader import YamlMultifileConfigLoader, ProductionConfigLoader

from mpf.commands.logging_formatters import JSONFormatter


# Note, other imports are done deeper in this file, which we need to do there
# since Kivy does so much with singletons and we don't want MPF to import
# them when it reads this command


class Command:

    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-statements
    def __init__(self, mpf_path, machine_path, args):   # noqa
        """Run MC."""
        p = psutil.Process(os.getpid())
        # increase priority slightly. this will keep MPF responsive when MC lags
        if sys.platform == "win32":
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10)
        # undo all of Kivy's built-in logging so we can do it our way
        os.environ['KIVY_NO_FILELOG'] = '1'
        os.environ['KIVY_NO_CONSOLELOG'] = '1'
        # pylint: disable-msg=import-outside-toplevel
        from kivy.logger import Logger

        for handler in Logger.handlers:
            Logger.removeHandler(handler)
        sys.stderr = sys.__stderr__

        # Need to have these in here because we don't want them to load when
        # the module is loaded as an mpf.command
        # pylint: disable-msg=import-outside-toplevel
        from mpf.core.utility_functions import Util

        del mpf_path

        parser = argparse.ArgumentParser(description='Starts the MPF Media Controller')

        parser.add_argument("-b",
                            action="store_false", dest="bcp", default=True,
                            help="Do not set up the BCP server threads")

        parser.add_argument("-c",
                            action="store", dest="configfile",
                            default="config", metavar='config_file(s)',
                            help="The name of a config file to load. Default is "
                                 "config.yaml. Multiple files can be used via a comma-"
                                 "separated list (no spaces between)")

        parser.add_argument("-C",
                            action="store", dest="mcconfigfile",
                            default="mcconfig.yaml",
                            metavar='config_file',
                            help="The MPF framework default config file. Default is "
                                 "<mpf-mc install folder>/mcconfig.yaml")

        parser.add_argument("-f",
                            action="store_true", dest="force_assets_load", default=False,
                            help="Load all assets upon startup. Useful for "
                            "ensuring all assets are set up properly "
                            "during development.")

        parser.add_argument("-l",
                            action="store", dest="logfile",
                            metavar='file_name',
                            default=os.path.join("logs", datetime.now().strftime(
                                "%Y-%m-%d-%H-%M-%S-mc-" + socket.gethostname() +
                                ".log")),
                            help="The name (and path) of the log file")

        parser.add_argument("-L",
                            action="store", dest="mc_logfile",
                            metavar='file_name',
                            default=None,
                            help="The name (and path) of the log file")

        parser.add_argument("--json-logging",
                            action="store_true", dest="jsonlogging",
                            default=False,
                            help="Enables json logging to file. ")

        parser.add_argument("-p",
                            action="store_true", dest="pause", default=False,
                            help="Pause the terminal window on exit. Useful "
                            "when launching in a separate window so you can "
                            "see any errors before the window closes.")

        parser.add_argument("-P",
                            action="store_true", dest="production", default=False,
                            help="Production mode. Will suppress errors, wait for hardware on start and "
                                 "try to exit when startup fails. Run this inside a loop.")

        parser.add_argument("-t",
                            action="store_false", dest='text_ui', default=True,
                            help="Use the ASCII text-based UI")

        parser.add_argument("--both",
                            action="store_true", dest='mpf_both', default=False)

        parser.add_argument("-v",
                            action="store_const", dest="loglevel", const=logging.DEBUG,
                            default=logging.INFO, help="Enables verbose logging to the"
                                                       " log file")

        parser.add_argument("-V",
                            action="store_true", dest="consoleloglevel",
                            default=logging.INFO,
                            help="Enables verbose logging to the console. Do NOT on "
                                 "Windows platforms")

        parser.add_argument("-a",
                            action="store_true", dest="no_load_cache",
                            help="Forces the config to be loaded from files "
                                 "and not cache")

        parser.add_argument("-A",
                            action="store_false", dest="create_config_cache",
                            help="Does not create the cache config files")

        # The following are just included for full compatibility with mpf.py
        # which is needed when using "mpf both".

        parser.add_argument("-x",
                            action="store_const", dest="force_platform",
                            const='virtual', help=argparse.SUPPRESS)

        parser.add_argument("--vpx",
                            action="store_const", dest="force_platform",
                            const='virtual_pinball', help=argparse.SUPPRESS)

        parser.add_argument("-X",
                            action="store_const", dest="force_platform",
                            const='smart_virtual', help=argparse.SUPPRESS)

        parser.add_argument("--no-sound",
                            action="store_true", dest="no_sound", default=False)

        args = parser.parse_args(args)

        args.configfile = Util.string_to_event_list(args.configfile)

        # Configure logging. Creates a logfile and logs to the console.
        # Formatting options are documented here:
        # https://docs.python.org/2.7/library/logging.html#logrecord-attributes

        try:
            os.makedirs(os.path.join(machine_path, 'logs'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        if args.mc_logfile:
            args.logfile = args.mc_logfile

        full_logfile_path = os.path.join(machine_path, args.logfile)

        try:
            os.remove(full_logfile_path)
        except OSError:
            pass

        # initialise file log
        if args.jsonlogging:
            formatter = JSONFormatter()
            file_log = logging.FileHandler(full_logfile_path)
            file_log.setFormatter(formatter)
            logging.getLogger('').addHandler(file_log)
        else:
            logging.basicConfig(level=args.loglevel,
                                format='%(asctime)s : %(name)s : %(message)s',
                                filename=full_logfile_path,
                                filemode='a')

        # define a Handler which writes INFO messages or higher to the
        # sys.stderr

        if args.text_ui and args.mpf_both:
            console = logging.NullHandler()
            console.setLevel(logging.ERROR)
        else:
            console = logging.StreamHandler()
            console.setLevel(args.consoleloglevel)

        # set a format which is simpler for console use
        formatter = logging.Formatter('%(name)s: %(message)s')

        # tell the handler to use this format
        console.setFormatter(formatter)

        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

        # pylint: disable-msg=import-outside-toplevel
        from mpfmc.core.mc import MpfMc

        logging.info("Loading MPF-MC controller")

        thread_stopper = threading.Event()

        # load config
        if not args.production:
            config_loader = YamlMultifileConfigLoader(machine_path, args.configfile,
                                                      not args.no_load_cache, args.create_config_cache)
        else:
            config_loader = ProductionConfigLoader(machine_path)

        config = config_loader.load_mc_config()

        try:
            MpfMc(options=vars(args),
                  config=config,
                  thread_stopper=thread_stopper).run()
            logging.info("MC run loop ended.")
        except Exception as e:  # noqa
            logging.exception(str(e))

        logging.info("Stopping child threads... (%s remaining)", len(threading.enumerate()) - 1)

        thread_stopper.set()

        while len(threading.enumerate()) > 1:
            time.sleep(.1)

        logging.info("All child threads stopped.")
        logging.shutdown()

        if args.pause:
            input('Press ENTER to continue...')

        sys.exit()


def get_command():
    return 'mc', Command
