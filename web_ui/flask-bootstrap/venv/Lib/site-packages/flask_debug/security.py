from functools import wraps

from flask import current_app, abort, request


def requires_debug(view):
    @wraps(view)
    def _(*args, **kwargs):
        strict = not current_app.config.get('FLASK_DEBUG_DISABLE_STRICT',
                                            False)
        if not current_app.debug:
            if strict:
                abort(404)  # don't even show we have flask-debug installed
            abort(403, 'This function is only available if the application '
                       'has been started in debug mode.')

        msg = []
        if strict:
            # extra security checks
            msg = []

            strict_env = {
                'SERVER_NAME': '127.0.0.1',
                'REMOTE_ADDR': '127.0.0.1',
                'SERVER_PORT': '5000',
            }

            for env, val in strict_env.items():
                if request.environ.get(env, None) != val:
                    msg.append('{} is not {!r}.'
                               .format(env, val))

            if not request.environ.get('SERVER_SOFTWARE', '').startswith(
                'Werkzeug/'
            ):
                msg.append('Not running on Werkzeug-Server.')

            if 'X-Forwarded-For' in request.headers:
                msg.append('Request has a X-Forwarded-For header.')

            if msg:
                msg.append('Strict security checks are enabled, to prevent '
                           'security issues in case you have forgotten to '
                           'disable debugging on a production system. You '
                           'can disable these by setting '
                           'FLASK_DEBUG_DISABLE_STRICT to True '
                           'in your applications configuration.')

        if msg:
            abort(403, '\n\n'.join(msg))
        return view(*args, **kwargs)
    return _
