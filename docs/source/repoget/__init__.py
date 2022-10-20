'''
repoget initialize extension
'''
from .repoget import *


def setup(app):
    """
    :type app: sphinx.application.Sphinx
    """
    app.add_config_value('repoget_token', '', True, (str, ))
    app.add_config_value('repoget_clonedir', 'repos', True, (str, ))
    app.connect('config-inited', config_inited)
    app.connect('build-finished', build_finished)
