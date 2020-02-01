from flask import Blueprint, current_app, redirect, request, url_for
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


    redir_url = url_for('auth.authorize', _external=True)
    # errors with r4 even if iss and aud params match
    #iss = 'https://launch.smarthealthit.org/v/r2/fhir'
    print('redirecting to authorize_url', redir_url)
    # SoF requires iss to be passed as aud querystring param
    return sof.authorize_redirect(redir_url, aud=iss)


@blueprint.route('/authorize')
def authorize():
    """
    Direct identity provider to redirect here after auth
    """
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
        'patient_data': response.json()
    }


@blueprint.route('/users/<int:user_id>')
def users(user_id):
    return {'ok':True}
