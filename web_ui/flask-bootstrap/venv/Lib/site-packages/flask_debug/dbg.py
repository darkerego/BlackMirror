from collections import OrderedDict
from functools import wraps
import sys

from flask import current_app, render_template, Blueprint, url_for, redirect, g
import inflection
from jinja2 import PackageLoader, ChoiceLoader

from .security import requires_debug


class DebugBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super(DebugBlueprint, self).__init__(*args, **kwargs)
        self.__menu = OrderedDict()
        self.__plugins = None

    def _debug_load_plugins(self):
        if self.__plugins is not None:
            # already loaded
            return

        dbg.__plugins = {}

        for name, mod in sys.modules.items():
            if (name.startswith('flask_debug_') and
                    hasattr(mod, 'initialize_debug_ext')):
                mod.initialize_debug_ext(dbg)
                dbg.__plugins[name] = mod

        # collect loaders
        loaders = [dbg.jinja_loader]
        for name, mod in dbg.__plugins.items():
            template_folder = getattr(mod, 'template_folder', None)
            if template_folder:
                loaders.append(PackageLoader(name, template_folder))

        # replace blueprints loader with new loader that includes extensions
        dbg.jinja_loader = ChoiceLoader(loaders)

    def _debug_get_menu(self):
        return self.__menu

    def _debug_get_plugins(self):
        return self.__plugins

    def route(self, rule, menu_name=True, require_debug=True, **options):
        # if only there was nonlocal in py2...
        wrapper = super(DebugBlueprint, self).route(rule, **options)

        @wraps(wrapper)
        def _(f):
            endpoint = options.get('endpoint', f.__name__)

            if require_debug:
                f = requires_debug(f)

            # menu entry, auto-generated
            name = menu_name
            if name is True:
                name = endpoint
                if name.startswith('debug_'):
                    name = name[len('debug_'):]
                    name = inflection.titleize(name)

            wrapped = wrapper(f)
            if name:
                endpoint = '{}.{}'.format(self.name, endpoint)
                self.__menu[endpoint] = name
            return wrapped

        return _


dbg = DebugBlueprint('debug', __name__, template_folder='templates')


@dbg.route('/_debug/', menu_name=None)  # the root
def debug_root():
    return redirect(url_for('.debug_reflect'))


@dbg.route('/_reflect/')
def debug_reflect():
    return render_template(
        'flask_debug/reflect.html',
        app=current_app,
    )


@dbg.route('/_config/')
def debug_config():
    return render_template(
        'flask_debug/config.html',
        app=current_app,
    )


@dbg.before_request
def make_current_app_available():
    g.app = current_app
    g.menu = dbg._debug_get_menu()
    g.dbg = dbg

    g.bootstrap_base_template = 'flask_debug/bootstrap_base.html'
    if 'bootstrap' in getattr(current_app, 'extensions', {}):
        g.bootstrap_base_template = 'bootstrap/base.html'
