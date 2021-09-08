"""Audit

funtions to simplify adding context and extra data to log messages destined for audit logs
"""
from flask import current_app, g, session


def audit_entry(message, level='info', extra=None):
    """Log entry, adding in session info such as active user"""
    if not extra:
        extra = {}
    extra['user'] = session.get('user')# or get_redis_session_data(g.session_id).get('user')
    try:
        log_at_level = getattr(current_app.logging, level.upper())
    except:
        raise ValueError(f"audit_entry given bogus level: {level}")

    log_at_level(message, extra=extra)
