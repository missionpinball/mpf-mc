import os
import toml

__version__ = '0.57.0.dev6'
__short_version__ = '0.57'
__bcp_version__ = '1.1'
__config_version__ = '6'
# __mpf_version_required__  SET THIS IN THE pyproject.toml dependencies section, e.g. mpf >= 0.57.0.dev2

def get_mpf_required_version():
    # Get the directory containing the current script.
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # Construct the full path to pyproject.toml based on the script's location.
    toml_path = os.path.join(dir_path, "..", "pyproject.toml")

    data = toml.load(toml_path)
    dependencies = data['project']['dependencies']
    for dep in dependencies:
        if dep.startswith("mpf "):
            return dep.split('>=')[1].strip()

    return None  # If version not found

__mpf_version_required__ = get_mpf_required_version() or "0.0.0"

# pylint: disable-msg=invalid-name
version = f"MPF-MC v{__version__}"
'''A friendly version string for this build of MPF.'''

# pylint: disable-msg=invalid-name
extended_version = f"MPF-MC v{__version__} (config_version={__config_version__}, BCP v{__bcp_version__}, \
                     Requires MPF API compatibility v{ __mpf_version_required__} or newer)"
