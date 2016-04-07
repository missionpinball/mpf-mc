# Checks to see if the latest commit includes an updated _version.py file
# Finds the appropriate MPF branch to go with this mpf-mc branch

import git
import os

mpf_mc_repo = git.Repo('c:\\projects\\mpf-mc')
mpf_mc_git = git.Git('c:\\projects\\mpf-mc')
mpf_repo = git.Repo('c:\\projects\\mpf')
mpf_git = git.Git('c:\\projects\\mpf')

# http://stackoverflow.com/questions/25556696/python-get-a-list-of-changed-files-between-two-commits-or-branches
def git_diff(branch1, branch2):
    format = '--name-only'
    commits = list()
    differ = mpf_mc_git.diff('%s..%s' % (branch1, branch2), format).split("\n")
    for line in differ:
        if len(line):
            commits.append(line)

    return commits

commits = list(mpf_mc_repo.iter_commits('dev', max_count=2))

if 'mpfmc/_version.py' in git_diff(commits[0], commits[1]):
    print("Setting DEPLOY_TO_PYPI = 1")
    deploy = 1
else:
    print("Setting DEPLOY_TO_PYPI = 0")
    deploy = 0

this_mpf_mc_branch = os.environ['APPVEYOR_REPO_BRANCH']

if 'origin/{}'.format(this_mpf_mc_branch) in mpf_repo.refs:
    mpf_branch = this_mpf_mc_branch
else:
    mpf_branch = 'dev'

print("Setting MPF branch to '{}'".format(mpf_branch))
mpf_repo.head.reference = mpf_branch

# Environment variables are only available during this Python process, so write
# the result to a batch file which will be run in the next step to set it for
# real.
with open('set_env.bat', 'w') as f:
    f.write('set DEPLOY_TO_PYPI={}\n'.format(deploy))
    f.write('cd \\projects\\mpf\n')
    f.write('git checkout {}\n'.format(mpf_branch))
