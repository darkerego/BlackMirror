from .dbg import dbg
from .security import requires_debug


class Debug(object):
    def __init__(self, app=None):
        import flask_debug_plugins
        dbg._debug_load_plugins()
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('FLASK_DEBUG_DISABLE_STRICT', False)
        app.register_blueprint(dbg)
