import fnmatch
import os

import pyaml_env


def pathmatch(path, pattern):
    '''
    :type path: str
    :type pattern: str
    '''
    path_parts = path.split(os.path.sep)
    pattern_parts = pattern.split(os.path.sep)
    if len(path_parts) != len(pattern_parts):
        return False
    return all((
        fnmatch.fnmatch(_path, _pattern)
        for _path, _pattern in zip(path_parts, pattern_parts)
        ))


class RepoSettings:
    filename = 'repoget.yml'

    @classmethod
    def find_repo_conf(cls, working_dir):
        filepath = None
        for dirname, _, files in os.walk(working_dir, followlinks=False):
            if cls.filename in files:
                filepath = os.path.join(dirname, cls.filename)
                break
        return filepath

    def __init__(self, data=None, filepath=None, working_dir=None):

        if data is None:
            if filepath is None:
                for dirname, _, files in os.walk(working_dir,
                                                 followlinks=False):
                    if self.filename in files:
                        filepath = os.path.join(dirname, self.filename)
                        break
            data = pyaml_env.parse_config(filepath)

        if not isinstance(data['name'], str) and not isinstance(
                data['settings'], dict):
            raise TypeError('Data should have name and settings in it')

        self._data = data

    @property
    def name(self):
        return self._data['name']

    @property
    def settings(self):
        return self._data['settings']

    @property
    def enabled(self):
        return self._data['settings'].get('enabled')

    @property
    def paths(self):
        return self._data['settings'].get('paths', [])

    def update_settings(self, settings):
        if isinstance(settings, RepoSettings):
            settings = settings._data
        self._data.update(settings)

    @property
    def packages(self):
        return self._data['settings'].get('dirs', [])

    @property
    def modules(self):
        return self._data['settings'].get('files', [])

    def get_repo_paths(self, working_dir):
        repo_paths = []

        if self.enabled:
            for dirname, dirs, files in os.walk(working_dir, followlinks=False):
                relpath = os.path.relpath(dirname, working_dir)

                for pattern in self.paths:

                    if pathmatch(relpath, pattern):

                        repo_paths.extend([
                            os.path.join(dirname, d) for d in dirs
                            if any((fnmatch.fnmatch(d, pat)
                                    for pat in self.packages))
                        ])

                        repo_paths.extend([
                            os.path.join(dirname, f) for f in files
                            if any((fnmatch.fnmatch(f, pat)
                                    for pat in self.modules))
                        ])

        return repo_paths


class RepogetConf:
    filename = 'repoget.yml'

    @classmethod
    def get_conf_path(cls, directory=None, filename=None):
        if filename is None:
            filename = cls.filename
        if directory is None:
            current_dir = os.path.dirname(__file__)
            directory = os.path.dirname(current_dir)
        conf_file = os.path.join(directory, filename)
        if os.path.isfile(conf_file):
            return conf_file

    def __init__(self, filepath=None, stream=None):
        if stream is None:
            if filepath is None:
                filepath = self.get_conf_path()
            if not filepath:
                raise ValueError("Please provide a valid conf file")
            self._data = pyaml_env.parse_config(filepath)

    def get_users(self):
        return self._data.get('users', [])

    def get_organizations(self):
        return self._data.get('organizations', [])

    def get_org_rules(self, org_name):
        for org in self.get_organizations():
            if org['name'] == org_name:
                return org['repos']
        return {'name': '*'}

    def get_user_rules(self, org_name):
        for user in self.get_users():
            if user['name'] == org_name:
                return user['repos']
        return {'name': '*'}

    def filter_repos(self, repos, rules=None, organization='', user=''):
        '''
        :retval: List[github.Repository.Repository]
        '''
        filtered = []

        if rules is None:
            if organization:
                rules = self.get_org_rules(organization)
            elif user:
                rules = self.get_user_rules(user)

        for repo in repos:
            for glob_pattern in rules.get('name', []):
                if fnmatch.fnmatch(repo.name, glob_pattern):
                    filtered.append(repo)
                    break

        return filtered

    def get_repo_settings(self, repo):
        ''':type repo: github.Repository.Repository
        :rtype: RepoSettings
        '''
        repo_settings = self._data['repo_conf']['defaults'].copy()
        for override in reversed(self._data['repo_conf']['overrides']):
            apply = True
            if not fnmatch.fnmatch(
                    repo.name,
                    override.get('name', '*')):
                apply = False
            if not fnmatch.fnmatch(
                    repo.owner.login,
                    override.get('owner', '*')):
                apply = False
            if apply:
                repo_settings.update(override['settings'])
        return RepoSettings(data={'name': repo, 'settings': repo_settings})


if __name__ == '__main__':
    pass
