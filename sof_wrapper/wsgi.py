""" WSGI Entry Point"""
from werkzeug.middleware.proxy_fix import ProxyFix

from sof_wrapper.app import create_app

# WSGI object is named "application" by default
# https://modwsgi.readthedocs.io/en/develop/configuration-directives/WSGICallableObject.html
application = create_app()

if application.config.get('PREFERRED_URL_SCHEME', '').lower() == 'https':
    # traefik sets the following headers
    # X-Forwarded-For, X-Forwarded-Host, X-Forwarded-Port, X-Forwarded-Proto, X-Forwarded-Server, X-Real-Ip
    application = ProxyFix(application, x_for=1, x_host=1, x_port=1)
