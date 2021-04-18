__version__ = '0.55.0-dev.6'
__short_version__ = '0.55'
__bcp_version__ = '1.1'
__config_version__ = '5'
__mpf_version_required__ = '0.55.0-dev.43'

# pylint: disable-msg=invalid-name
version = "MPF-MC v{}".format(__version__)
'''A friendly version string for this build of MPF.'''

# pylint: disable-msg=invalid-name
extended_version = "MPF-MC v{} (config_version={}, BCP v{}, Requires MPF v{})".format(
    __version__, __config_version__, __bcp_version__, __mpf_version_required__)
