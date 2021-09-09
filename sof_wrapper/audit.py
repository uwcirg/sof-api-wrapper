"""Audit

functions to simplify adding context and extra data to log messages destined for audit logs
"""
from flask import current_app
from sof_wrapper.wrapped_session import get_session_value


def audit_entry(message, level='info', extra=None):
    """Log entry, adding in session info such as active user"""
    try:
        log_at_level = getattr(current_app.logger, level.lower())
    except AttributeError:
        raise ValueError(f"audit_entry given bogus level: {level}")

    if extra is None:
        extra = {}
    extra['user'] = get_session_value('user')
    subject = get_session_value('subject')
    if subject:
        extra['subject'] = subject

    log_at_level(message, extra=extra)
