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
    return all((fnmatch.fnmatch(_path, _pattern)
                for _path, _pattern in zip(path_parts, pattern_parts)))


class RepoSettings:
    file_name = 'docs_info.yml'

    @classmethod
    def find_conf_file(cls, working_dir, file_name=None):
        if file_name is None:
            file_name = cls.file_name

        file_path = None
        for dirname, _, files in os.walk(working_dir, followlinks=False):
            if file_name in files:
                file_path = os.path.join(dirname, file_name)
                break

        return file_path

    def __init__(self, data=None, filepath=None, working_dir=None):

        if data is None:
            if filepath is None:
                filepath = self.find_conf_file(working_dir)

            if filepath is None:
                raise IOError('Could not find conf file in repo')

            data = {'name': os.path.basename(working_dir),
                    'settings': pyaml_env.parse_config(filepath)}

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
    def dirs(self):
        return self._data['settings'].get('dirs', [])

    @property
    def ignore(self):
        return self._data['settings'].get('ignore', [])

    def update_settings(self, settings):
        if isinstance(settings, RepoSettings):
            settings = settings._data
        self._data.update(settings)

    def update_from_working_dir(self, working_dir):
        try:
            repo_settings = RepoSettings(working_dir=working_dir)
        except (ValueError, IOError):
            return
        self.update_settings(repo_settings)

    @property
    def top_level_packages(self):
        return self._data['settings'].get('top_level_packages', [])

    def get_repo_dirs(self, working_dir, implicit_namespaces=False):
        repo_dirs = []
        ignore_dirs = []

        if self.enabled:
            for dirname, dirs, files in os.walk(working_dir,
                                                followlinks=False):
                relpath = os.path.relpath(dirname, working_dir)

                for pattern in self.dirs:
                    if pathmatch(relpath, pattern):
                        ignore_dirs.extend([
                            os.path.join(dirname, ign)
                            for ign in self.ignore
                            ])
                        if implicit_namespaces:
                            repo_dirs.append(dirname)
                        else:
                            repo_dirs.extend([
                                os.path.join(dirname, d) for d in dirs
                                if any((fnmatch.fnmatch(d, pat)
                                        for pat in self.top_level_packages))
                            ])

        return repo_dirs, ignore_dirs


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

    def get_owners(self):
        return self._data.get('owners', [])

    def get_owner_rules(self, owner_name):
        for owner in self.get_owners():
            if owner['name'] == owner_name:
                return owner['repos']
        return {'name': ['*']}

    def filter_repos(self, repos, rules=None, owner=''):
        '''
        :retval: List[github.Repository.Repository]
        '''
        filtered = []

        if rules is None:
            rules = self.get_owner_rules(owner)

        for repo in repos:
            for glob_pattern in rules.get('name', ['*']):
                if fnmatch.fnmatch(repo.name, glob_pattern):
                    filtered.append(repo)
                    break

        return filtered

    def get_repo_settings(self, repo):
        '''
        :type repo: github.Repository.Repository
        :rtype: RepoSettings
        '''
        repo_settings = self._data['repo_conf']['defaults'].copy()

        for override in reversed(self._data['repo_conf']['overrides']):
            apply = True
            if not fnmatch.fnmatch(repo.name, override.get('name', '*')):
                apply = False
            if not fnmatch.fnmatch(repo.owner.login, override.get(
                    'owner', '*')):
                apply = False
            if apply:
                repo_settings.update(override['settings'])

        return RepoSettings(data={'name': repo, 'settings': repo_settings})


if __name__ == '__main__':
    pass
