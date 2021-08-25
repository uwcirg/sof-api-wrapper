from flask import Flask
from flask_cors import CORS
from logging import config as logging_config
import os
import redis
import requests_cache
from werkzeug.middleware.proxy_fix import ProxyFix

from sof_wrapper import auth, api
from sof_wrapper.extensions import oauth, sess


def create_app(testing=False, cli=False):
    """Application factory, used to create application
    """
    app = Flask('sof_wrapper')
    app.config.from_object('sof_wrapper.config')
    app.config['TESTING'] = testing
    CORS(app)

    configure_logging(app)
    configure_cache(app)
    configure_extensions(app, cli)
    register_blueprints(app)
    configure_proxy(app)

    return app


def configure_cache(app):
    """Configure caching libraries"""

    # NB this effectively turns caching on for ALL requests API calls.
    # To temporarily disable, wrap w/ context manager:
    #
    #   with requests_cache.disabled():
    #     requests.get('http://httpbin.org/get')

    # Catch configuration problems early; require REQUEST_CACHE_URL
    if not app.config.get('REQUEST_CACHE_URL'):
        msg = "required configuration 'REQUEST_CACHE_URL' not present"
        app.logger.error(msg)
        raise RuntimeError(msg)

    app.logger.info(
        "Initiating requests.cache with %s", app.config.get('REQUEST_CACHE_URL'))
    requests_cache.install_cache(
        cache_name=app.name,
        backend='redis',
        expire_after=app.config['REQUEST_CACHE_EXPIRE'],
        include_get_headers=True,
        old_data_on_error=True,
        connection=redis.StrictRedis.from_url(app.config.get("REQUEST_CACHE_URL")),
    )


def configure_logging(app):
    app.logger  # must call to initialize prior to config or it'll replace

    config = 'logging.ini'
    if app.config.get('TESTING'):
        # look above the testing dir when testing
        config = os.path.join('..', config)

    logging_config.fileConfig(config, disable_existing_loggers=False)


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
