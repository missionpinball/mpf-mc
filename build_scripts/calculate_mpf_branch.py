# Finds the appropriate MPF branch to go with this mpf-mc branch

import git
import os
import sys
parent_directory = (os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)))

sys.path.insert(1, parent_directory)
# pylint: disable-msg=wrong-import-position
from mpfmc._version import __short_version__

mpf_repo = git.Repo('c:\\projects\\mpf')
this_mpf_mc_branch = os.environ['APPVEYOR_REPO_BRANCH']

if 'origin/{}'.format(this_mpf_mc_branch) in mpf_repo.refs:
    mpf_branch = this_mpf_mc_branch
elif 'origin/{}'.format(__short_version__) in mpf_repo.refs:
    mpf_branch = __short_version__
else:
    mpf_branch = 'dev'

with open('checkout_mpf_branch.bat', 'w') as f:
    f.write('cd \\projects\\mpf\n')
    f.write('git checkout {}\n'.format(mpf_branch))
