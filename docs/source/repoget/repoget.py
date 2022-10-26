import os
import re
import shutil
from collections import OrderedDict
from multiprocessing.pool import ThreadPool
from threading import RLock

import git
import github
from loguru import logger

from .conf import RepogetConf


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

        owner_types = ['organization', 'user']

        def _fetch_repos_by_type(typ):
            for owner_info in getattr(self._conf, 'get_' + typ + 's')():
                owner = owner_info['name']
                self._owners[owner] = typ
                token = owner_info['token']
                gh = github.Github(token)
                gh_owner = getattr(gh, 'get_' + typ)(owner)
                for repo in self._conf.filter_repos(gh_owner.get_repos(),
                                                    **{typ: owner}):
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

        for typ in owner_types:
            _fetch_repos_by_type(typ)

        return self._repos

    def ensure_local_clone(self, repo, clone_dir):
        '''
        :type repo: github.Repository.Repository
        :type clone_dir: str
        :rtype: git.Repo or None
        '''
        local_clone = None
        perform = ''

        repo_name = repo.name
        owner_dir = os.path.join(clone_dir, repo.owner.login)
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
            clone_url = re.sub('(https://)', r'\1%s:x-oauth-basic@' % token,
                               repo.clone_url)
            logger.info(clone_url)
            logger.info(f'cloning {clone_url} => {repo_dir}')
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

        for owner in self._owners:
            owner_dir = os.path.join(clone_dir, owner)
            if not os.path.isdir(owner_dir):
                os.makedirs(owner_dir)

        pool = ThreadPool()
        results = {}

        for repo in self._repos.keys():
            results[repo] = pool.apply_async(
                self.ensure_local_clone,
                args=(self._repos[repo]['gh_repo'], clone_dir))

        for repo in self._repos.keys():
            local_clone = results[repo].get()
            self._repos[repo]['local_clone'] = local_clone

        pool.close()

        paths = []
        for repo in self._repos.keys():
            paths.extend(self.find_paths_in_clone(repo))

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
