from importlib import import_module
import multiprocessing


def _start_mc(mpf_path, machine_path, args):
    module = import_module('mpfmc.commands.mc')
    module.Command(mpf_path, machine_path, args)


def _start_imc(mpf_path, machine_path, args):
    # pylint: disable-msg=import-outside-toplevel
    from mpfmc.tools.interactive_mc.imc import InteractiveMc
    InteractiveMc(mpf_path, machine_path, args).run()


class Command:

    """Command which runs imc and mc."""

    def __init__(self, mpf_path, machine_path, args):
        """Run imc and mc."""

        mc = multiprocessing.Process(target=_start_mc,
                                     args=(mpf_path, machine_path, args))
        sb = multiprocessing.Process(target=_start_imc,
                                     args=(mpf_path, machine_path, args))

        multiprocessing.set_start_method('spawn')

        mc.start()
        sb.start()

        mc.join()
        sb.join()


def get_command():
    return 'imc', Command
