from flask import Blueprint, current_app, redirect, request, url_for, session
import requests

from sof_wrapper.extensions import oauth


blueprint = Blueprint('auth', __name__, url_prefix='/auth')

@blueprint.route('/launch')
def launch():
    """
    SMART-on-FHIR launch endpoint
    set /auth/launch as SoF App Launch URL
    """
    iss = request.args['iss']
    # errors with r4 even if iss and aud params match
    #iss = 'https://launch.smarthealthit.org/v/r2/fhir'

    # fetch conformance statement from /metadata
    ehr_metadata_url = '%s/metadata' % iss
    metadata = requests.get(ehr_metadata_url)
    metadata_security = metadata.json()['rest'][0]['security']

    # todo: use less fragile lookup logic (JSONPath?)
    authorize_url = metadata_security['extension'][0]['extension'][0]['valueUri']
    token_url = metadata_security['extension'][0]['extension'][1]['valueUri']

    # set client id and secret from flask config
    # todo: determine if any details need to be preserved between requests
    oauth.init_app(current_app)
    oauth.register(
        name='sof',
        access_token_url=token_url,
        authorize_url=authorize_url,

        # todo: try using iss
        #api_base_url=iss+'/',
        #client_kwargs={'scope': 'user:email'},
    )
    sof = oauth.create_client('sof')

    # URL to pass (as QS param) to EHR Authz server
    # EHR Authz server will redirect to this URL after authorization
    return_url = url_for('auth.authorize', _external=True)

    current_app.logger.info('redirecting to EHR Authz. will return to: %s', return_url)

    # SoF requires iss to be passed as aud querystring param
    return sof.authorize_redirect(redirect_uri=return_url, aud=iss)


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
    if not '_sof_authlib_state_' in session:
        return 'authlib state cookie missing; restart auth flow', 400

    oauth.init_app(current_app)
    oauth.register('sof')
    token = oauth.sof.authorize_access_token()

    # Brenda Jackson
    patient_url = 'https://launch.smarthealthit.org/v/r2/fhir/Patient/5c41cecf-cf81-434f-9da7-e24e5a99dbc2'
    response = oauth.sof.get(patient_url)
    response.raise_for_status()

    return {
        'req': request.args,
        'token': token,
        'patient_data': response.json(),
    }


@blueprint.route('/users/<int:user_id>')
def users(user_id):
    return {'ok':True}


@blueprint.before_request
def before_request_func():
    current_app.logger.info('session: %s', session)
