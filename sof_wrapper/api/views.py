from flask import Blueprint, jsonify, request
import logging

base_blueprint = Blueprint('base', __name__)


@base_blueprint.route('/')
def root():
    return {'ok': True}


@base_blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response


@base_blueprint.route('/auditlog', methods=('OPTIONS', 'POST'))
def auditlog_addevent():
    """Add event to audit log

    API for client applications to add any event to the audit log.  The message
    will land in the same audit log as any auditable internal event, including
    recording the authenticated user making the call.

    Returns a json friendly message, i.e. {"message": "ok"} or details on error
    ---
    operationId: auditlog_addevent
    tags:
      - audit
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          id: message
          required:
            - message
          properties:
            user:
              type: string
              description: user identifier, such as email address or ID
            patient:
              type: string
              description: patient identifier (if applicable)
            level:
              type: string
              description: context such as "error", default "info"
            message:
              type: string
              description: message text
    responses:
      200:
        description: successful operation
        schema:
          id: response_ok
          required:
            - message
          properties:
            message:
              type: string
              description: Result, typically "ok"
      401:
        description: if missing valid OAuth token
    security:
      - ServiceToken: []

    """
    body = request.get_json()
    if not body:
        return jsonify(message="Missing JSON data"), 400

    message = body.get('message')
    level = body.pop('level', 'info')
    if not hasattr(logging, level.upper()):
        return jsonify(message="Unknown logging `level`: {level}"), 400
    if not message:
        return jsonify(message="missing required 'message' in post"), 400

    log_level_method = getattr(logging, level.lower())
    log_level_method(body)
    return jsonify(message='ok')
