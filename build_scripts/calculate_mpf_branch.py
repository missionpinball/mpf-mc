# Finds the appropriate MPF branch to go with this mpf-mc branch

import git
import os

mpf_repo = git.Repo('c:\\projects\\mpf')
this_mpf_mc_branch = os.environ['APPVEYOR_REPO_BRANCH']

if 'origin/{}'.format(this_mpf_mc_branch) in mpf_repo.refs:
    mpf_branch = this_mpf_mc_branch
else:
    mpf_branch = 'dev'

with open('checkout_mpf_branch.bat', 'w') as f:
    f.write('cd \\projects\\mpf\n')
    f.write('git checkout {}\n'.format(mpf_branch))
