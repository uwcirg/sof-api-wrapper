from flask import Blueprint, current_app


base_blueprint = Blueprint('base', __name__)


@base_blueprint.route('/')
def root():
    current_app.logger.warn(
        'example message', extra={'extra_i': 12, 'extra_j': 'whee'})
    return {'ok':True}

@base_blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
