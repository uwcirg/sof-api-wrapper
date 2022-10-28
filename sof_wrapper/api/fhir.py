import requests

from flask import Blueprint, current_app, g, request

from sof_wrapper.audit import audit_entry
from sof_wrapper.jsonify_abort import jsonify_abort
from sof_wrapper.rxnav import add_drug_classes
from sof_wrapper.wrapped_session import get_session_value

blueprint = Blueprint('fhir', __name__)
r2prefix = '/v/r2/fhir'
r4prefix = '/v/r4/fhir'

PROXY_HEADERS = ('Authorization', 'Cache-Control')

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
    base_url = get_session_value('iss')
    emr_url = f'{base_url}/MedicationRequest'
    params = {"subject": f"Patient/{patient_id}"} if patient_id else {}
    return emr_meds(emr_url, params, request.headers)


@blueprint.route(f'{r2prefix}/emr/MedicationOrder', defaults={'patient_id': None})
@blueprint.route(f'{r2prefix}/emr/MedicationOrder/<string:patient_id>')
def emr_med_orders(patient_id):
    base_url = get_session_value('iss')
    emr_url = f'{base_url}/MedicationOrder'
    params = {"patient": f"Patient/{patient_id}"} if patient_id else {}

    return emr_meds(emr_url, params, request.headers)


def emr_meds(emr_url, params, headers):
    upstream_headers = {}
    for header_name in PROXY_HEADERS:
        if header_name in request.headers:
            upstream_headers[header_name] = request.headers[header_name]

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
    params = kwargs or dict(request.args)
    # decoded JWT, or FHIR Practioner reference (eg Practitioner/ID)
    user = get_session_value('user')

    # in a demo deploy, SCRIPT_ENDPOINT_URL will be configured, but empty
    if user and "DEA" in user:
        DEA = user["DEA"]
    # in a demo deploy, SCRIPT_ENDPOINT_URL will be configured, but empty
    elif current_app.config.get("SCRIPT_ENDPOINT_URL") == "":
        DEA = "FAKEDEA123"
    else:
        return jsonify_abort(status_code=400, message="DEA not found")

    params['DEA'] = DEA
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
    # decoded JWT, or FHIR Practioner reference (eg Practitioner/ID)
    user = get_session_value('user')

    if user and "DEA" in user:
        DEA = user["DEA"]
    # in a demo deploy, SCRIPT_ENDPOINT_URL will be configured, but empty
    elif current_app.config.get("SCRIPT_ENDPOINT_URL") == "":
        DEA = "FAKEDEA123"
    else:
        return jsonify_abort(status_code=400, message="DEA not found")

    params['DEA'] = DEA
    return pdmp_meds(pdmp_url, params)


def pdmp_meds(pdmp_url, params):
    response = requests.get(pdmp_url, params=params)
    response.raise_for_status()
    audit_entry("PDMP returned {} MedicationRequest/Orders".format(
        len(response.json().get("entry", []))),
        extra={'tags': ['PDMP', 'MedicationRequest'], 'meds': [e for e in response.json().get("entry", [])]})
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
    base_url = get_session_value('iss')
    key = f'patient_{id}'
    value = get_session_value(key)
    if value:
        return value

    patient_url = f'{base_url}/Patient/{id}'

    upstream_headers = {}

    for header_name in PROXY_HEADERS:
        if header_name in request.headers:
            upstream_headers[header_name] = request.headers[header_name]

    response = requests.get(
        url=patient_url,
        headers=upstream_headers,
    )
    response.raise_for_status()
    patient_fhir = response.json()
    # TODO when possible w/o session cookie: set_session_value(key, patient_fhir)

    return patient_fhir


@blueprint.route('/fhir-router/', defaults={'relative_path': '', 'session_id': None})
@blueprint.route('/fhir-router/<string:session_id>/<path:relative_path>')
def route_fhir(relative_path, session_id):
    g.session_id = session_id
    current_app.logger.debug('received session_id as path parameter: %s', session_id)

    # prefer patient ID baked into access token JWT by EHR; fallback to initial transparent launch token for fEMR
    patient_id = get_session_value('token_response', {}).get('patient') or get_session_value('launch_token_patient')
    if not patient_id:
        return jsonify_abort(status_code=400, message="no patient ID found in session; can't continue")

    iss = get_session_value('iss')
    if not iss:
        return jsonify_abort(status_code=400, message="no iss found in session; can't continue")

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
    for header_name in PROXY_HEADERS:
        if header_name in request.headers:
            upstream_headers[header_name] = request.headers[header_name]

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
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Cache-Control'

    return response
