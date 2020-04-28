from flask import Blueprint, current_app, redirect, request, url_for, session
import requests

from sof_wrapper.extensions import oauth
from sof_wrapper.auth.helpers import extract_payload


blueprint = Blueprint('auth', __name__, url_prefix='/auth')


def debugging_compliance_fix(session):
    def _fix(response):
        current_app.logger.debug(
            'access_token request url: %s', response.request.url)
        current_app.logger.debug(
            'access_token request headers: %s', response.request.headers)
        current_app.logger.debug(
            'access_token request body: %s', response.request.body)

        current_app.logger.debug('access_token response: %s', response)
        current_app.logger.debug(
            'access_token response.status_code: %s', response.status_code)
        current_app.logger.debug(
            'access_token response.content: %s', response.content)

        response.raise_for_status()

        return response
    session.register_compliance_hook('access_token_response', _fix)


@blueprint.route('/launch')
def launch():
    """
    SMART-on-FHIR launch endpoint
    set /auth/launch as SoF App Launch URL
    """
    iss = request.args['iss']
    current_app.logger.debug('iss from EHR: %s', iss)
    session.setdefault('iss', iss)

    launch = request.args.get('launch')
    if launch:
        # launch value received from EHR
        current_app.logger.debug('launch: %s', launch)

    # errors with r4 even if iss and aud params match
    # iss = 'https://launch.smarthealthit.org/v/r2/fhir'

    # fetch conformance statement from /metadata
    ehr_metadata_url = '%s/metadata' % iss
    metadata = requests.get(
        ehr_metadata_url,
        headers={'Accept': 'application/json'},
    )
    metadata.raise_for_status()
    metadata_security = metadata.json()['rest'][0]['security']

    # todo: use less fragile lookup logic (JSONPath?)
    authorize_url = metadata_security['extension'][0]['extension'][0]['valueUri']
    token_url = metadata_security['extension'][0]['extension'][1]['valueUri']

    # set client id and secret from flask config
    oauth.register(
        name='sof',
        access_token_url=token_url,
        authorize_url=authorize_url,
        compliance_fix=debugging_compliance_fix,
        # todo: try using iss
        # api_base_url=iss+'/',
        client_kwargs={'scope': current_app.config['SOF_CLIENT_SCOPES']},
    )
    # work around back-end caching of dynamic config values
    oauth.sof.authorize_url = authorize_url
    oauth.sof.access_token_url = token_url

    # URL to pass (as QS param) to EHR Authz server
    # EHR Authz server will redirect to this URL after authorization
    return_url = url_for('auth.authorize', _external=True)

    current_app.logger.debug('redirecting to EHR Authz. will return to: %s', return_url)
    token = session.get('auth_info')['token']
    user = extract_payload(token.get('id_token')).get('profile', '')
    current_app.logger.info(
        "launch",
        extra={'subject': "Patient/{}".format(token.get('patient', '')),
               'user': user})

    current_app.logger.debug('passing iss as aud: %s', iss)
    return oauth.sof.authorize_redirect(
        redirect_uri=return_url,
        # SoF requires iss to be passed as aud querystring param
        aud=iss,
        # must pass launch param back when using EHR launch
        launch=launch,
    )


@blueprint.route('/authorize')
def authorize():
    """
    Direct identity provider to redirect here after auth
    """
    # raise 400 if error passed (as querystring params)
    if 'error' in request.args:
        error_details = {
            'error': request.args['error'],
            'error_description': request.args['error_description'],
        }
        return error_details, 400
    # authlib persists OAuth client details via secure cookie
    # if not '_sof_authlib_state_' in session:
        # return 'authlib state cookie missing; restart auth flow', 400

    # todo: define fetch_token function that requests JSON (Accept: application/json header)
    # https://github.com/lepture/authlib/blob/master/authlib/oauth2/client.py#L154
    token = oauth.sof.authorize_access_token(_format='json')
    user = extract_payload(token.get('id_token')).get('profile', '')
    current_app.logger.info(
        "login",
        extra={'subject': "Patient/{}".format(token.get('patient', '')),
               'user': user})

    # Brenda Jackson
    #patient_url = 'https://launch.smarthealthit.org/v/r2/fhir/Patient/5c41cecf-cf81-434f-9da7-e24e5a99dbc2'
    #response = oauth.sof.get(patient_url)
    #response.raise_for_status()

    iss = session['iss']
    current_app.logger.debug('iss from session: %s', iss)

    session['auth_info'] = {
        'token': token,
        'iss': iss,
        # debugging data
        'req': request.args,
        #'patient_data': response.json(),
    }

    frontend_url = current_app.config['LAUNCH_DEST']

    current_app.logger.info('redirecting to frontend app: %s', frontend_url)
    return redirect(frontend_url)


@blueprint.route('/auth-info')
def auth_info():
    auth_info = session['auth_info']
    iss = session['auth_info']['iss']
    return {
        # debugging
        'token_data': auth_info['token'],

        "fakeTokenResponse": {
            "access_token": auth_info['token']['access_token'],
            "token_type": "Bearer",
        },
        "fhirServiceUrl": iss,
        "patientId":auth_info['token']['patient'],
    }


@blueprint.route('/users/<int:user_id>')
def users(user_id):
    return {'ok': True}


@blueprint.before_request
def before_request_func():
    current_app.logger.debug('before_request session: %s', session)
    current_app.logger.debug(
        'before_request authlib state present: %s',
        '_sof_authlib_state_' in session)


@blueprint.after_request
def after_request_func(response):
    current_app.logger.debug('after_request session: %s', session)
    current_app.logger.debug(
        'after_request authlib state present: %s',
        '_sof_authlib_state_' in session)

    # todo: make configurable
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'

    return response
