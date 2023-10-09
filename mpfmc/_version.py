import os

__version__ = '0.57.0.dev10'
__short_version__ = '0.57'
__bcp_version__ = '1.1'
__config_version__ = '6'
__mpf_version_required__ = '0.57.0.dev19'  # ALSO UPDATE in pyproject.toml

# pylint: disable-msg=invalid-name
version = f"MPF-MC v{__version__}"
'''A friendly version string for this build of MPF.'''

# pylint: disable-msg=invalid-name
extended_version = f"MPF-MC v{__version__} (config_version={__config_version__}, BCP v{__bcp_version__}, \
                     Requires MPF API compatibility v{ __mpf_version_required__} or newer)"
