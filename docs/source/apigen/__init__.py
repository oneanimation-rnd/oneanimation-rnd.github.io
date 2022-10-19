from .extension import generate_api, cleanup


def setup(app):
    ''':type app: sphinx.application.Sphinx'''
    app.add_config_value('apigen_cleanup', True, True, bool)
    app.add_config_value('apigen_dir', 'api', True, str)
    app.connect('config-inited', generate_api)
    app.connect('build-finished', cleanup)
