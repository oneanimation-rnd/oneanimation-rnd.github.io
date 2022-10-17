from __future__ import print_function

import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

__all__ = ['generate_api']

def generate_api(app, config):
    """
    :type app: sphinx.application.Sphinx
    :type config: sphinx.config.Config
    """
    modules = os.path.join(app.confdir, 'modules.json')
    if not os.path.isfile(modules):
        print('modules file %s not found ... Skipping!!' % (modules, ))
        return

    with open(modules) as _file:
        modules_info = json.load(_file)

    if not modules_info or not isinstance(modules_info, dict):
        print('modules info is uninteresting (%s) ... Skipping!' %
              type(modules_info))
        return

    apidir = os.path.join(app.confdir, config.apigen_dir)
    namespacedir = os.path.join(apidir, 'namespaces')

    if os.path.isdir(apidir):
        shutil.rmtree(apidir)

    os.makedirs(namespacedir)

    if not os.path.isdir(namespacedir):
        print(namespacedir, 'does not exist')

    templates_dir = os.path.join(os.path.dirname(__file__), '_templates')
    template_loader = FileSystemLoader(templates_dir)
    templates_env = Environment(loader=template_loader)

    for namespace, packages in modules_info.items():
        print('processing', namespace, packages)
        if not packages:
            continue
        namespace_filename = '%s.rst' % namespace
        namespace_rst = os.path.join(namespacedir, namespace_filename)

        try:
            ns_template = templates_env.get_template(namespace_filename)
        except TemplateNotFound:
            ns_template = templates_env.get_template('namespace.rst')

        print('Writing %s using %s ...' % (namespace_rst, ns_template.name))
        with open(namespace_rst, 'w+', encoding='utf-8') as _outfile:
            _outfile.write(
                ns_template.render(namespace=namespace, packages=packages))


def cleanup(app, exception):
    if not app.config.apigen_cleanup:
        return
    apidir = os.path.join(app.confdir, app.config.apigen_dir)
    if os.path.exists(apidir):
        shutil.rmtree(apidir)
