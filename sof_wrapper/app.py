from flask import Flask
from flask_cors import CORS
import logging
from logging import config as logging_config
from pythonjsonlogger.jsonlogger import JsonFormatter
import os
from werkzeug.middleware.proxy_fix import ProxyFix

from sof_wrapper import auth, api
from sof_wrapper.extensions import oauth, sess
from sof_wrapper.logserverhandler import LogServerHandler


def create_app(testing=False, cli=False):
    """Application factory, used to create application
    """
    app = Flask('sof_wrapper')
    app.config.from_object('sof_wrapper.config')
    app.config['TESTING'] = testing
    CORS(app)

    configure_logging(app)
    configure_extensions(app, cli)
    register_blueprints(app)
    configure_proxy(app)

    return app


def configure_logging(app):
    app.logger  # must call to initialize prior to config or it'll replace

    config = 'logging.ini'
    if not os.path.exists(config):
        # look above the testing dir when testing or debugging locally
        config = os.path.join('..', config)

    logging_config.fileConfig(config, disable_existing_loggers=False)

    if not app.config['LOGSERVER_URL']:
        return

    log_server_handler = LogServerHandler(
        level=logging.INFO,
        jwt=app.config['LOGSERVER_TOKEN'],
        url=app.config['LOGSERVER_URL'])

    json_formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s")
    log_server_handler.setFormatter(json_formatter)

    # Hardcode event/audit logs to INFO - no debugging clutter desired
    log_server_handler.setLevel(logging.INFO)

    app.logger.addHandler(log_server_handler)
    app.logger.debug(
        "cosri confidential backend logging initialized",
        extra={'bonus': 'data', 'tags': ['testing', 'logging']})


def configure_extensions(app, cli):
    """configure flask extensions
    """
    oauth.init_app(app)
    sess.init_app(app)


def register_blueprints(app):
    """register all blueprints for application
    """
    app.register_blueprint(auth.views.blueprint)
    app.register_blueprint(api.views.base_blueprint)
    app.register_blueprint(api.fhir.blueprint)


def configure_proxy(app):
    """Add werkzeug fixer to detect headers applied by upstream reverse proxy"""
    if app.config.get('PREFERRED_URL_SCHEME', '').lower() == 'https':
        app.wsgi_app = ProxyFix(
            app=app.wsgi_app,

            # trust X-Forwarded-Host
            x_host=1,

            # trust X-Forwarded-Port
            x_port=1,
        )
