import git

repo = git.Repo('c:\\projects\\mpf-mc')
g = git.Git('c:\\projects\\mpf-mc')

# http://stackoverflow.com/questions/25556696/python-get-a-list-of-changed-files-between-two-commits-or-branches
def git_diff(branch1, branch2):
    format = '--name-only'
    commits = list()
    differ = g.diff('%s..%s' % (branch1, branch2), format).split("\n")
    for line in differ:
        if len(line):
            commits.append(line)

    return commits

commits = list(repo.iter_commits('dev', max_count=2))

if 'mpfmc/_version.py' in git_diff(commits[0], commits[1]):
    print("Setting DEPLOY_TO_PYPI = 1")
    deploy = 1
else:
    print("Setting DEPLOY_TO_PYPI = 0")
    deploy = 0

# Environment variables are only available during this Python process, so write
# the result to a batch file which will be run in the next step to set it for
# real.
with open('set_env_vars.bat', 'w') as f:
    f.write('set DEPLOY_TO_PYPI={}'.format(deploy))
