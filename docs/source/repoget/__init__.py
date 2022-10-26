'''
repoget initialize extension
'''
from .repoget import Repoget


def setup(app):
    """
    :type app: sphinx.application.Sphinx
    """
    repoget = Repoget()
    app.add_config_value('repoget_token', '', True, (str, ))
    app.add_config_value('repoget_clonedir', 'repos', True, (str, ))
    app.connect('config-inited', repoget.config_inited)
    app.connect('build-finished', repoget.build_finished)
