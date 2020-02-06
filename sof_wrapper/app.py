from flask import Flask

from sof_wrapper import auth, api
from sof_wrapper.extensions import oauth


def create_app(testing=False, cli=False):
    """Application factory, used to create application
    """
    app = Flask('sof_wrapper')
    app.config.from_object('sof_wrapper.config')

    configure_extensions(app, cli)
    register_blueprints(app)

    return app


def configure_extensions(app, cli):
    """configure flask extensions
    """
    oauth.init_app(app)


def register_blueprints(app):
    """register all blueprints for application
    """
    app.register_blueprint(auth.views.blueprint)
    app.register_blueprint(api.views.base_blueprint)
