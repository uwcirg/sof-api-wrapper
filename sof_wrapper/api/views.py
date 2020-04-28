from flask import Blueprint

base_blueprint = Blueprint('base', __name__)


@base_blueprint.route('/')
def root():
    return {'ok': True}


@base_blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
