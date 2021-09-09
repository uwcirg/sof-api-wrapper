import pickle
from flask import g, current_app, session


def get_session_value(key, default=None):
    """Return session value for given key

    Typically flask-session allows for direct access via `session.get`
    but that only works when a browser cookie is available, which is
    not the case when launched from the dashboard.

    Until resolved, this function tries local and configured session
    and returns a value if found.
    """
    if key in session:
        return session.get(key, default)

    # session_id stored on entry point in `fhir_router`
    if 'session_id' in g:
        return get_redis_session_data(g.session_id).get(key, default)


def set_session_value(key, value):
    if 'session_id' not in g:
        session[key] = value
        return

    session_data = get_redis_session_data(g.session_id)
    session_data[key] = value


def get_redis_session_data(session_id):
    """Load session data associated with given session_id"""
    if session_id is None:
        return {}

    # TODO: further investigate using SessionHandler
    redis_handle = current_app.config['SESSION_REDIS']
    session_prefix = current_app.config.get('SESSION_KEY_PREFIX', 'session:')

    encoded_session_data = redis_handle.get(f'{session_prefix}{session_id}')

    # why doesn't this use the flask default JSON serializer?
    session_data = pickle.loads(encoded_session_data)
    return session_data


