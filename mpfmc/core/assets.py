"""Threaded Asset Loader for MC."""
import logging
import threading
import traceback
from queue import PriorityQueue, Queue, Empty

import sys

from mpf.core.assets import BaseAssetManager
from mpf.exceptions.config_file_error import ConfigFileError


class ThreadedAssetManager(BaseAssetManager):

    """AssetManager which uses the Threading module."""

    def __init__(self, machine):
        """Initialise queues and start loader thread."""
        super().__init__(machine)
        self.loader_queue = PriorityQueue()  # assets for to the loader thread
        self.loaded_queue = Queue()  # assets loaded from the loader thread
        self.loader_thread = None
        self._loaded_watcher = False

        self._start_loader_thread()

    def _start_loader_thread(self):
        self.loader_thread = AssetLoader(loader_queue=self.loader_queue,
                                         loaded_queue=self.loaded_queue,
                                         exception_queue=self.machine.crash_queue,
                                         thread_stopper=self.machine.thread_stopper)
        self.loader_thread.daemon = True
        self.loader_thread.start()

    def load_asset(self, asset):
        """Put asset in loader queue."""
        # Internal method which handles the logistics of actually loading an
        # asset. Should only be called by Asset.load() as that method does
        # additional things that are needed.

        self.num_assets_to_load += 1

        # It's ok for an asset to make it onto this queue twice as the loader
        # thread will check the asset's loaded attribute to make sure it needs
        # to load it.

        # This is a PriorityQueue which will automatically put the asset into
        # the proper position in the queue based on its priority.

        self.loader_queue.put(asset)

        if not self._loaded_watcher:
            self._loaded_watcher = self.machine.clock.schedule_interval(self._check_loader_status, 0)

    def _check_loader_status(self, *args):
        del args
        # checks the loaded queue and updates loading stats
        try:
            while not self.loaded_queue.empty():
                asset, loaded = self.loaded_queue.get()
                if loaded:
                    asset.is_loaded()
                self.num_assets_loaded += 1
                self._post_loading_event()
        except AttributeError:
            pass

        if self.num_assets_to_load == self.num_assets_loaded:
            self.num_assets_loaded = 0
            self.num_assets_to_load = 0
            self.machine.clock.unschedule(self._loaded_watcher)
            self._loaded_watcher = None


class AssetLoader(threading.Thread):

    """Base class for the Asset Loader thread and actually loads the assets from disk.

    Args:
        loader_queue: A reference to the asset manager's loader_queue which
            holds assets waiting to be loaded. Items are automatically sorted
            in reverse order by priority, then creation ID.
        loaded_queue: A reference to the asset manager's loaded_queue which
            holds assets that have just been loaded. Entries are Asset
            instances.
        exception_queue: Send a reference to self.machine.crash_queue. This way if
            the asset loader crashes, it will write the crash to that queue and
            cause an exception in the main thread. Otherwise it fails silently
            which is super annoying. :)
    """

    def __init__(self, loader_queue, loaded_queue, exception_queue,
                 thread_stopper):
        """Initialise asset loader."""
        threading.Thread.__init__(self)
        self.log = logging.getLogger('Asset Loader')
        self.loader_queue = loader_queue
        self.loaded_queue = loaded_queue
        self.exception_queue = exception_queue
        self.thread_stopper = thread_stopper
        self.name = 'asset_loader'

    def run(self):
        """Run loop for the loader thread."""
        try:  # wrap the so we can send exceptions to the main thread
            while not self.thread_stopper.is_set():
                try:
                    asset = self.loader_queue.get(block=True, timeout=1)
                except Empty:
                    asset = None

                if asset:
                    with asset.lock:
                        if not asset.loaded:
                            try:
                                asset.do_load()
                            except Exception as e:
                                raise ConfigFileError(
                                    "Error while loading {} asset file '{}'".format(asset.attribute, asset.file),
                                    1, self.log.name, asset.name) from e
                            self.loaded_queue.put((asset, True))
                        else:
                            self.loaded_queue.put((asset, False))

            return

        # pylint: disable-msg=broad-except
        except Exception:  # pragma: no cover
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value,
                                               exc_traceback)
            msg = ''.join(line for line in lines)
            self.exception_queue.put(msg)
            raise
