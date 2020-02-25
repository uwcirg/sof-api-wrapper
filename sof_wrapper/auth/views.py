from flask import Blueprint, current_app, redirect, request, url_for, session
from urllib.parse import urlencode
import base64
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

    launch = request.args.get('launch')
    if launch:
        # launch value recieved from EHR
        decoded_launch = base64.b64decode(request.args['launch']+'===')
        current_app.logger.info('decoded_launch: %s', decoded_launch)

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
    oauth.register(
        name='sof',
        access_token_url=token_url,
        authorize_url=authorize_url,

        # todo: try using iss
        #api_base_url=iss+'/',
        #client_kwargs={'scope': 'user:email'},
    )

    # URL to pass (as QS param) to EHR Authz server
    # EHR Authz server will redirect to this URL after authorization
    return_url = url_for('auth.authorize', _external=True)

    current_app.logger.info('redirecting to EHR Authz. will return to: %s', return_url)

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
    #if not '_sof_authlib_state_' in session:
        #return 'authlib state cookie missing; restart auth flow', 400

    token = oauth.sof.authorize_access_token()

    # Brenda Jackson
    patient_url = 'https://launch.smarthealthit.org/v/r2/fhir/Patient/5c41cecf-cf81-434f-9da7-e24e5a99dbc2'
    response = oauth.sof.get(patient_url)
    response.raise_for_status()

    session['auth_info'] = {
        'token': token,

        # debugging data
        'req': request.args,
        'patient_data': response.json(),
    }

    frontend_url = '{launch_dest}?{querystring_params}'.format(
        launch_dest=current_app.config['LAUNCH_DEST'],
        querystring_params=urlencode({
            "iss": "https://launch.smarthealthit.org/v/r2/fhir",
            "patient": token['patient'],
        }),
    )

    current_app.logger.info('redirecting to frontend app: %s', frontend_url)
    return redirect(frontend_url)


@blueprint.route('/auth-info')
def auth_info():
    auth_info = session['auth_info']

    return {
        # from front-end launch-context.json
        "client_id": "6c12dff4-24e7-4475-a742-b08972c4ea27",
        "scope": "patient/*.read launch/patient",

        "fakeTokenResponse": {
            "access_token": auth_info['token']['access_token'],
            "token_type": "Bearer",
        },
        "fhirServiceUrl":"https://launch.smarthealthit.org/v/r2/fhir",
        "iss":"https://launch.smarthealthit.org/v/r2/fhir",
        "server":"https://launch.smarthealthit.org/v/r2/fhir",
        "patientId":auth_info['token']['patient'],
    }


@blueprint.route('/users/<int:user_id>')
def users(user_id):
    return {'ok':True}


@blueprint.before_request
def before_request_func():
    current_app.logger.info('before_request session: %s', session)
    current_app.logger.info('before_request authlib state present: %s', '_sof_authlib_state_' in session)


@blueprint.after_request
def after_request_func(response):
    current_app.logger.info('after_request session: %s', session)
    current_app.logger.info('after_request authlib state present: %s', '_sof_authlib_state_' in session)

    # todo: make configurable
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'

    return response
