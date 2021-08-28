import pickle
import requests

from flask import Blueprint, abort, current_app, request, session, g

from sof_wrapper.rxnav import add_drug_classes

blueprint = Blueprint('fhir', __name__)
r2prefix = '/v/r2/fhir'
r4prefix = '/v/r4/fhir'


def collate_results(*result_sets):
    """Compile given result sets into a single bundle"""
    results = {'resourceType': 'Bundle', 'entry': []}

    for rs in result_sets:
        if 'entry' in rs:
            results['entry'].extend(rs['entry'])

    results['total'] = len(results['entry'])
    return results


def annotate_meds(med_bundle):
    """Annotate bundled resources and return a copy"""
    annotated_bundle = med_bundle.copy()
    annotated_bundle['entry'] = []

    for med in med_bundle['entry']:
        annotated_bundle['entry'].append(add_drug_classes(med, rxnav_url=current_app.config["RXNAV_URL"]))
    return annotated_bundle


@blueprint.route(f'{r4prefix}/emr/MedicationRequest', defaults={'patient_id': None})
@blueprint.route(f'{r4prefix}/emr/MedicationRequest/<string:patient_id>')
def emr_med_requests(patient_id):
    base_url = session.get('iss') or get_redis_session_data(g.session_id).get('iss')
    emr_url = f'{base_url}/MedicationRequest'
    params = {"subject": f"Patient/{patient_id}"} if patient_id else {}

    return emr_meds(emr_url, params, request.headers)


@blueprint.route(f'{r2prefix}/emr/MedicationOrder', defaults={'patient_id': None})
@blueprint.route(f'{r2prefix}/emr/MedicationOrder/<string:patient_id>')
def emr_med_orders(patient_id):
    base_url = session.get('iss') or get_redis_session_data(g.session_id).get('iss')
    emr_url = f'{base_url}/MedicationOrder'
    params = {"patient": f"Patient/{patient_id}"} if patient_id else {}

    return emr_meds(emr_url, params, request.headers)


def emr_meds(emr_url, params, headers):
    # TODO: enhance for audit or remove PHI?
    current_app.logger.debug(
        f"fire request for emr meds on {emr_url}/?{params}")

    upstream_headers = {}
    if 'Authorization' in headers:
        upstream_headers = {'Authorization': headers['Authorization']}

    response = requests.get(
        url=emr_url,
        params=params,
        headers=upstream_headers,
    )
    response.raise_for_status()
    current_app.logger.debug("emr returned {} MedicationRequests".format(
        len(response.json().get("entry", []))))
    return response.json()


@blueprint.route(f'{r4prefix}/pdmp/MedicationRequest')
def pdmp_med_requests(**kwargs):
    """return results from PDMP request for MedicationRequest

    Include as kwargs or request parameters for remote query.
    - 'subject:Patient.name.given': given name
    - 'subject:Patient.name.family': family name
    - 'subject:Patient.birthdate': DOB in `eqYYYY-MM-DD` format

    """
    # script-fhir-facade refers to r4 MedicationRequest as MedicationOrder
    pdmp_url = '{base_url}/v/r4/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
    )
    params = kwargs or request.args
    return pdmp_meds(pdmp_url, params)


@blueprint.route(f'{r2prefix}/pdmp/MedicationOrder')
def pdmp_med_orders(**kwargs):
    """return results from PDMP request for MedicationOrder

    Include as kwargs or request parameters for remote query.
    - 'subject:Patient.name.given': given name
    - 'subject:Patient.name.family': family name
    - 'subject:Patient.birthdate': DOB in `eqYYYY-MM-DD` format

    """
    # script-fhir-facade refers to r4 MedicationRequest as MedicationOrder
    pdmp_url = '{base_url}/v/r4/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
        )
    params = kwargs or request.args
    return pdmp_meds(pdmp_url, params)


def pdmp_meds(pdmp_url, params):
    # TODO: remove hack to generate fake records for Brenda from Darth
    if (
            params.get('subject:Patient.name.family') == 'Jackson' and
            params.get('subject:Patient.name.given') == 'Brenda' and
            params.get('subject:Patient.birthdate') == 'eq1956-10-14'):
        # avoid type errors on request.args by replacing
        params = {
            'subject:Patient.name.family': 'Vader',
            'subject:Patient.name.given': 'Darth',
            'subject:Patient.birthdate': 'eq1945-01-15'
        }

    # TODO: enhance for audit or remove PHI?
    current_app.logger.debug(
        f"fire request for PDMP meds on {pdmp_url}/?{params}")
    response = requests.get(pdmp_url, params=params)
    response.raise_for_status()
    current_app.logger.debug("PDMP returned {} MedicationRequest/Orders".format(
        len(response.json().get("entry", []))))
    return response.json()


@blueprint.route(f'{r4prefix}/MedicationRequest/<string:patient_id>')
@blueprint.route(f'{r4prefix}/MedicationRequest', defaults={'patient_id': None})
def medication_request(patient_id=None):
    """Return compiled list of MedicationRequests from available endpoints"""
    pdmp_args = {}
    if patient_id:
        patient_fhir = patient_by_id(patient_id)
        pdmp_args['subject:Patient.name.family'] = patient_fhir[
            'name'][0]['family']
        pdmp_args['subject:Patient.name.given'] = patient_fhir[
            'name'][0]['given'][0]
        pdmp_args['subject:Patient.birthdate'] = (
            f"eq{patient_fhir['birthDate']}")

    return annotate_meds(collate_results(
        pdmp_med_requests(**pdmp_args),
        emr_med_requests(patient_id),
    ))

@blueprint.route(f'{r2prefix}/MedicationOrder/<string:patient_id>')
@blueprint.route(f'{r2prefix}/MedicationOrder', defaults={'patient_id': None})
def medication_order(patient_id):
    """Return compiled list of MedicationOrders from available endpoints"""
    pdmp_args = {}
    if patient_id:
        patient_fhir = patient_by_id(patient_id)
        pdmp_args['subject:Patient.name.family'] = patient_fhir[
            'name'][0]['family']
        pdmp_args['subject:Patient.name.given'] = patient_fhir[
            'name'][0]['given'][0]
        pdmp_args['subject:Patient.birthdate'] = (
            f"eq{patient_fhir['birthDate']}")

    return annotate_meds(collate_results(
        pdmp_med_orders(**pdmp_args),
        emr_med_orders(patient_id),
    ))


@blueprint.route(f'{r2prefix}/Observation')
def observations():
    phr_url = '{base_url}/Observation'.format(
        base_url=current_app.config['PHR_URL'],
    )
    # todo: lookup from frontend with Patient details
    phr_params = {'patient._id': '53b07006-f454-ea11-8241-0a0332b55c97'}

    phr_observations = requests.get(
        url=phr_url,
        params=phr_params,
        headers={
            'Authorization': 'Bearer %s' % current_app.config['PHR_TOKEN'],
            'Accept': 'application/json',
        },
    )
    phr_observations.raise_for_status()
    return phr_observations.json()


@blueprint.route(f'{r4prefix}/Patient/<string:id>')
def patient_by_id(id):
    base_url = session.get('iss') or get_redis_session_data(g.session_id).get('iss')
    key = f'patient_{id}'
    if key in session:
        return session[key]

    patient_url = f'{base_url}/Patient/{id}'
    response = requests.get(patient_url)
    response.raise_for_status()
    patient_fhir = response.json()
    session[key] = patient_fhir

    return patient_fhir


def get_redis_session_data(session_id):
    """Load session data associated with given session_id"""
    if session_id is None:
        return {}

    # TODO: further investigate using SessionHandler
    redis_handle = current_app.config['SESSION_REDIS']
    session_prefix = current_app.config.get('SESSION_KEY_PREFIX', 'session:')

    encoded_session_data = redis_handle.get(f'{session_prefix}{session_id}')

    # why doesn't this use the flask default JSON serializer?
    session_data = pickle.loads(encoded_session_data)
    return session_data


@blueprint.route('/fhir-router/', defaults={'relative_path': '', 'session_id': None})
@blueprint.route('/fhir-router/<string:session_id>/<path:relative_path>')
def route_fhir(relative_path, session_id):
    g.session_id = session_id
    current_app.logger.debug('received session_id as path parameter: %s', session_id)

    session_data = get_redis_session_data(session_id)
    # prefer patient ID baked into access token JWT by EHR; fallback to initial transparent launch token for fEMR
    patient_id = session_data.get('token_response', {}).get('patient') or session_data.get('launch_token_patient')
    if not patient_id:
        abort(400, "no patient ID found in session; can't continue")

    iss = session_data.get('iss')
    if not iss:
        abort(400, "no iss found in session; can't continue")

    paths = relative_path.split('/')
    resource_name = paths.pop()

    route_map = {
        'MedicationOrder': medication_order,
        'MedicationRequest': medication_request
    }

    if resource_name in route_map:
        return route_map[resource_name](patient_id=patient_id)

    # use EHR FHIR server from launch
    # use session lookup across sessions if necessary
    upstream_fhir_base_url = iss
    upstream_fhir_url = '/'.join((upstream_fhir_base_url, relative_path))
    upstream_headers = {}
    if 'Authorization' in request.headers:
        upstream_headers = {'Authorization': request.headers['Authorization']}

    upstream_response = requests.get(
        url=upstream_fhir_url,
        headers=upstream_headers,
        params=request.args,
    )
    upstream_response.raise_for_status()
    return upstream_response.json()


@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization'

    return response
