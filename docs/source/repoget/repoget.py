import github
import git
import os
import sys
import json
import re
import shutil
from multiprocessing.pool import ThreadPool
from loguru import logger


__all__ = ['config_inited', 'build_finished']


TOKEN = None
GHCLIENT = None
CURDIR = os.path.dirname(__file__)


PATHS = {
        'python',
        'maya',
        r'houdini/python[\d.]*libs',
        }


def ensure_github(func=None):
    def _wrapper(app, config):
        global TOKEN, GHCLIENT
        if GHCLIENT is None:
            TOKEN = config.repoget_token
            GHCLIENT = github.Github(TOKEN)
        if func is not None:
            return func(app, config)
    if func is None:
        return _wrapper()
    return _wrapper


def get_modules(app):
    """
    :type app: sphinx.application.Sphinx
    """
    confdir = app.confdir
    modules_json = os.path.join(confdir, 'repos.json')


def get_repos():
    """:retval: List[github.Repository.Repository]"""
    organization = GHCLIENT.get_organization('oneanimation-rnd')
    return [repo
            for repo in organization.get_repos()
            if re.match(r'^(oa|bd)[._-]', repo.name)]


def clone_repo(repo, clone_dir):
    '''
    :type repo: github.Repository.Repository
    :type clone_dir: str
    :rtype: git.Repo or None
    '''
    local_clone = None
    perform = ''

    repo_name = repo.name
    repo_dir = os.path.join(clone_dir, repo_name)

    try:
        local_clone = git.Repo(repo_dir)
        default_commit = repo.get_branch(repo.default_branch).commit.sha
        if default_commit == local_repo.active_branch.commit.hexsha:
            logger.info(f'{repo_dir} is upto date!')
        elif repo.default_branch == local_clone.active_branch.name:
            perform = 'pull'
        else:
            raise git.InvalidGitRepositoryError('wrong branch name')

    except git.NoSuchPathError:
        perform = 'clone'

    except git.InvalidGitRepositoryError:
        shutil.rmtree(repo_dir)
        perform = 'clone'

    if perform == 'pull':
        remote = local_clone.remotes[0]
        remote.pull(repo.default_branch, force=True)

    if perform == 'clone':
        clone_url = re.sub('(https://)', r'\1%s:x-oauth-basic@' % TOKEN, repo.clone_url)
        logger.info(clone_url)
        logger.info(f'cloning {clone_url} => {repo_dir}')
        local_clone = git.Repo.clone_from(clone_url, repo_dir, depth=1)

    return local_clone


def find_paths_in_clone(clone):
    ''':type clone: git.repo.base.Repo'''
    paths = []
    workdir = clone.working_tree_dir
    for dirname, dirs, files in os.walk(workdir, followlinks=False):
        rel_path = os.path.relpath(dirname, workdir)
        for path in PATHS:
            if re.match('^' + path + '$', rel_path):
                paths.extend([os.path.join(dirname, d) for d in dirs])
                paths.extend([
                    os.path.join(dirname, f)
                    for f in files
                    if f.endswith('.py') or f.endswith('.pyi')])
                dirs = []
        if '.git' in dirs:
            dirs.remove('.git')
    return paths

@ensure_github
def config_inited(app, config):
    """
    :type app: sphinx.application.Sphinx
    :type config: sphinx.config.Config
    """
    repos = get_repos()
    pool = ThreadPool()
    clone_dir = os.path.abspath(config.repoget_clonedir)
    results = []
    for repo in repos:
        results.append(pool.apply_async(clone_repo, args=(repo, clone_dir)))
    clones = [res.get() for res in results]
    paths = []
    for clone in clones:
        paths.extend(find_paths_in_clone(clone))
    for path in paths:
        print(path)
    config.autoapi_dirs = paths


def build_finished(app, exception):
    """
    :type app: sphinx.application.Sphinx
    :type extension: Exception
    """


def generate_conf_data(filename='repoget.json'):
    parent_dir = os.path.dirname(CURDIR)
    sys.path.append(parent_dir)
    import conf
    global TOKEN, GHCLIENT
    TOKEN = conf.repoget_token
    GHCLIENT = github.Github(TOKEN)
    for repo in get_repos():
        print(repo)
    conf


if __name__ == '__main__':
    main()
