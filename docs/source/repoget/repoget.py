import os
import re
import shutil
from collections import OrderedDict
from multiprocessing.pool import ThreadPool
from threading import RLock

import git
import github
from loguru import logger

from .repoget_conf import RepogetConf


class Repoget:

    def __init__(self):
        self._conf = RepogetConf()
        self._repos = OrderedDict()
        self.sphinx = None
        self.sphinx_config = None
        self._rlock = RLock()
        self._owners = {}

    def fetch_repos(self):
        """:retval: List[github.Repository.Repository]"""

        for owner_info in self._conf.get_owners():
            owner = owner_info['name']
            typ = owner_info.get('type', 'user')
            self._owners[owner] = owner_info.copy()
            token = owner_info.get('token', '')
            gh = github.Github(token if token else None)
            gh_owner = getattr(gh, 'get_' + typ)(owner)
            for repo in self._conf.filter_repos(gh_owner.get_repos(),
                                                owner=owner):
                self._repos[repo.full_name] = {
                    'name': repo.name,
                    'gh_repo': repo,
                    'owner': {
                        'name': owner,
                        'type': typ,
                        'gh': gh_owner,
                        'token': token
                    },
                }

        return self._repos

    def ensure_local_clone(self, full_name, clone_dir):
        '''
        :type repo: github.Repository.Repository
        :type clone_dir: str
        :rtype: git.Repo or None
        '''
        local_clone = None
        perform = ''

        repo = self._repos[full_name]['gh_repo']
        repo_name = repo.name
        owner_dir = os.path.join(
                clone_dir,
                self._repos[full_name]['owner']['name'])
        repo_dir = os.path.join(owner_dir, repo_name)
        token = self._repos[repo.full_name]['owner']['token']

        try:
            local_clone = git.Repo(repo_dir)
            default_commit = repo.get_branch(repo.default_branch).commit

            if default_commit.sha == local_clone.active_branch.commit.hexsha:
                logger.info(f'{repo_dir} is upto date!')

            elif (local_clone.remotes[0].url in (repo.clone_url, repo.ssh_url)
                  and repo.default_branch == local_clone.active_branch.name):
                perform = 'pull'

            else:
                shutil.rmtree(repo_dir)
                perform = 'clone'

        except git.NoSuchPathError:
            perform = 'clone'

        except (git.InvalidGitRepositoryError, IndexError, TypeError):
            shutil.rmtree(repo_dir)
            perform = 'clone'

        if perform == 'pull':
            remote = local_clone.remotes[0]
            remote.pull(repo.default_branch, force=True)

        elif perform == 'clone':
            clone_url = repo.clone_url
            logger.info(f'cloning {repo.clone_url} => {repo_dir}')
            if token and token != 'N/A':
                clone_url = re.sub('(https://)',
                                   r'\1%s:x-oauth-basic@' % token, clone_url)
            local_clone = git.Repo.clone_from(clone_url, repo_dir, depth=1)

        return local_clone

    def find_paths_in_clone(self, full_name):
        ''':rtype: List[str]'''
        repo = self._repos[full_name]['gh_repo']
        settings = self._conf.get_repo_settings(repo)
        return settings.get_repo_paths(
            self._repos[full_name]['local_clone'].working_dir)

    def config_inited(self, app, config):
        """
        :type app: sphinx.application.Sphinx
        :type config: sphinx.config.Config
        """
        self.sphinx = app
        self.sphinx_config = config

        self.fetch_repos()
        clone_dir = os.path.abspath(config.repoget_clonedir)

        for owner, info in self._owners.items():
            owner_dir = os.path.join(clone_dir, owner)
            info['owner_dir'] = owner_dir
            if not os.path.isdir(owner_dir):
                os.makedirs(owner_dir)

        pool = ThreadPool()
        results = {}

        for full_name in self._repos.keys():
            results[full_name] = pool.apply_async(
                self.ensure_local_clone,
                args=(full_name, clone_dir))

        for full_name in self._repos.keys():
            local_clone = results[full_name].get()
            self._repos[full_name]['local_clone'] = local_clone

        pool.close()

        paths = []
        for full_name in self._repos.keys():
            paths.extend(self.find_paths_in_clone(full_name))

        existing_paths = config.autoapi_dirs
        if existing_paths:
            paths.extend(existing_paths)
        config.autoapi_dirs = paths

    def build_finished(self, app, exception):
        """
        :type app: sphinx.application.Sphinx
        :type extension: Exception
        """


def main():
    pass


if __name__ == '__main__':
    main()
